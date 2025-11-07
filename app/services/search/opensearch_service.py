from typing import Any, Dict, List, Optional

from loguru import logger
from opensearchpy import AsyncOpenSearch

from app.core.config import settings
from app.core.index_mappings import (get_chunk_meta_mapping, get_elements_mapping,
                                     get_media_meta_mapping)
from app.services.embeddings.embedding_service import EmbeddingService


class OpenSearchService:
    def __init__(self, embedding_service: EmbeddingService = None):
        self.client: Optional[AsyncOpenSearch] = None
        self.media_meta_index = settings.opensearch_media_index
        self.chunk_meta_index = settings.opensearch_chunk_index
        self.elements_index = settings.opensearch_elements_index

        # Initialize helper components with dependency injection
        self.embedding_service = embedding_service or EmbeddingService()

    async def initialize(self):
        """Initialize OpenSearch client"""
        try:
            self.client = AsyncOpenSearch(
                hosts=[{"host": settings.opensearch_host, "port": settings.opensearch_port}],
                http_auth=(settings.opensearch_username, settings.opensearch_password)
                if settings.opensearch_username
                else None,
                use_ssl=settings.opensearch_use_ssl,
                verify_certs=settings.opensearch_verify_certs,
                ssl_assert_hostname=False,
                ssl_show_warn=False,
            )

            await self._ensure_indices_exist()
            logger.info("OpenSearch service initialized")
        except Exception as e:
            logger.warning(f"Failed to initialize OpenSearch: {e}")
            logger.info("Application will continue without OpenSearch connection")

    async def close(self):
        """Close OpenSearch client"""
        if self.client:
            await self.client.close()

    async def health_check(self) -> bool:
        """Check OpenSearch health"""
        try:
            if not self.client:
                return False
            health = await self.client.cluster.health()
            return health["status"] in ["green", "yellow"]
        except Exception as e:
            logger.error(f"OpenSearch health check failed: {e}")
            return False

    async def _ensure_indices_exist(self):
        """Ensure all required indices exist"""
        indices = [
            (self.media_meta_index, get_media_meta_mapping()),
            (self.chunk_meta_index, get_chunk_meta_mapping()),
            (self.elements_index, get_elements_mapping()),
        ]

        for index_name, mapping in indices:
            if not await self._index_exists(index_name):
                await self._create_index(index_name, mapping)
                logger.info(f"Created index: {index_name}")

    async def _index_exists(self, index_name: str) -> bool:
        """Check if index exists"""
        try:
            if not self.client:
                return False
            return await self.client.indices.exists(index=index_name)
        except Exception:
            return False

    async def _create_index(self, index_name: str, mapping: Dict[str, Any]):
        """Create index with mapping"""
        if not self.client:
            raise RuntimeError("OpenSearch client not initialized")
        await self.client.indices.create(index=index_name, body=mapping)

    async def search_elements(
        self,
        query: str,
        element_types: List[str],
        embeddings: Optional[Dict[str, List[float]]] = None,
        size: int = 10,
        from_: int = 0,
        filters: Optional[Dict[str, Any]] = None,
        element_type_weights: Optional[Dict[str, float]] = None,
    ) -> Dict[str, Any]:
        """Search elements with unified query filtering by element_types"""
        try:
            # Pass all embeddings to the search query builder
            search_query = self._build_search_query(
                query, element_types, embeddings, filters, element_type_weights
            )

            if not self.client:
                raise RuntimeError("OpenSearch client not initialized")

            # Build search body with KNN and query sections
            search_body = {
                "query": search_query, 
                "size": size, 
                "from": from_, 
                "_source": True
            }
            
            # Add KNN section for better vector search performance if embeddings exist
            # Note: Using the query-level KNN approach instead of top-level knn section
            # because OpenSearch may not support multiple KNN searches in array format

            response = await self.client.search(index=self.elements_index, body=search_body)

            # Log unified query results
            hits_count = len(response["hits"]["hits"])
            max_score = response["hits"]["max_score"] if response["hits"]["hits"] else 0.0
            
            # 가중치 및 모달리티 매칭 정보 표시
            weight_info = "weighted" if element_type_weights else "standard"
            modality_info = f"modalities: {','.join(embeddings.keys())}" if embeddings else "text-only"
            logger.info(f"OpenSearch [{','.join(element_types)}] {weight_info} ({modality_info}) → {hits_count} hits (max: {max_score:.4f})")

            # Convert to standard format (score 정보 보존)
            results = []
            for hit in response["hits"]["hits"]:
                result_item = hit["_source"].copy()
                result_item["score"] = hit.get("_score", 0.0)
                result_item["original_score"] = hit.get("_original_score")
                results.append(result_item)

            return {
                "results": results,
                "total_hits": response["hits"]["total"]["value"],
                "max_score": max_score,
                "took_ms": response["took"],
            }

        except Exception as e:
            logger.error(f"Element search failed: {e}")
            raise

    def _build_search_query(
        self,
        query: str,
        element_types: List[str],
        embeddings: Optional[Dict[str, List[float]]],
        filters: Optional[Dict[str, Any]],
        element_type_weights: Optional[Dict[str, float]] = None,
    ) -> Dict[str, Any]:
        """Build hybrid search query combining text and vector search with element_type weights"""
        
        # element_type별 가중치가 있으면 가중치 기반 쿼리 구성, 없으면 기존 방식
        if element_type_weights:
            # 가중치 기반 element_type 필터링 (should 쿼리로 변경)
            element_type_queries = []
            for element_type in element_types:
                weight = element_type_weights.get(element_type, 1.0)
                if weight > 0:  # 가중치가 0인 타입은 제외하지 않고 낮은 boost 적용
                    boost = max(0.1, weight * 10)  # 0.1~10 범위로 변환
                    element_type_queries.append({
                        "term": {
                            "element_type": {
                                "value": element_type,
                                "boost": boost
                            }
                        }
                    })
            
            # Base bool query with weighted element_type matching
            bool_query = {
                "bool": {
                    "must": [],
                    "should": element_type_queries,
                    "minimum_should_match": 1
                }
            }
        else:
            # 기존 방식: 필터로 element_type 제한
            bool_query = {"bool": {"must": [], "filter": [{"terms": {"element_type": element_types}}]}}

        # Add text search
        if query.strip():
            bool_query["bool"]["must"].append(
                {"multi_match": {"query": query, "fields": ["content"], "type": "best_fields", "fuzziness": "AUTO"}}
            )

        # Add vector search if embeddings provided
        if embeddings:
            # Create modality-specific vector queries using bool/should structure
            # This is more compatible across different OpenSearch versions
            vector_queries = []
            
            for modality, embedding_vector in embeddings.items():
                if embedding_vector and len(embedding_vector) > 0:
                    # Use script_score query for vector similarity with element_type filtering
                    base_query = {"term": {"modality": modality}}
                    
                    # Add element_type filtering to vector search as well
                    if element_type_weights:
                        # Create element_type should query with weights for vector search too
                        element_type_queries = []
                        for element_type in element_types:
                            weight = element_type_weights.get(element_type, 1.0)
                            if weight > 0:
                                boost = max(0.1, weight * 10)
                                element_type_queries.append({
                                    "term": {
                                        "element_type": {
                                            "value": element_type,
                                            "boost": boost
                                        }
                                    }
                                })
                        
                        if element_type_queries:
                            base_query = {
                                "bool": {
                                    "must": [{"term": {"modality": modality}}],
                                    "should": element_type_queries,
                                    "minimum_should_match": 1
                                }
                            }
                    
                    # Apply element_type boost to the final script score
                    if element_type_weights:
                        script_source = """
                        double similarity = cosineSimilarity(params.query_vector, doc['embeddings.{modality}']) + 1.0;
                        double element_boost = 1.0;
                        if (params.element_weights.containsKey(doc['element_type'].value)) {{
                            element_boost = params.element_weights[doc['element_type'].value];
                        }}
                        return similarity * Math.max(0.05, element_boost);
                        """.format(modality=modality)
                        
                        vector_query = {
                            "script_score": {
                                "query": {"term": {"modality": modality}},
                                "script": {
                                    "source": script_source,
                                    "params": {
                                        "query_vector": embedding_vector,
                                        "element_weights": element_type_weights
                                    }
                                }
                            }
                        }
                    else:
                        vector_query = {
                            "script_score": {
                                "query": base_query,
                                "script": {
                                    "source": "cosineSimilarity(params.query_vector, doc['embeddings." + modality + "']) + 1.0",
                                    "params": {"query_vector": embedding_vector}
                                }
                            }
                        }
                    vector_queries.append(vector_query)

            # Combine text search with vector searches
            if vector_queries:
                # Configure search type weights based on modalities
                has_image_embedding = any('image' in str(vq) for vq in vector_queries)
                
                if has_image_embedding:
                    # 이미지 검색 시: 이미지 임베딩을 강력히 우선시
                    text_search_boost = 0.3      # BM25 텍스트 검색 가중치 대폭 감소
                    embedding_search_boost = 3.0  # 이미지 임베딩 검색 가중치 대폭 증가 (10배 차이)
                else:
                    # 텍스트만 검색 시: 기존 가중치 유지
                    text_search_boost = 1.0      # BM25 텍스트 검색 가중치
                    embedding_search_boost = 1.5  # 임베딩 벡터 검색 가중치
                
                # Create hybrid query with configurable boosting
                text_query_with_boost = {
                    "bool": {
                        **bool_query["bool"],
                        "boost": text_search_boost
                    }
                }
                
                # Apply embedding boost by wrapping script_score in a bool query with boost
                boosted_vector_queries = []
                for vector_query in vector_queries:
                    boosted_vector_query = {
                        "bool": {
                            "must": [vector_query],
                            "boost": embedding_search_boost
                        }
                    }
                    boosted_vector_queries.append(boosted_vector_query)
                
                all_queries = [text_query_with_boost] + boosted_vector_queries
                
                search_query = {
                    "bool": {
                        "should": all_queries,
                        "minimum_should_match": 1
                    }
                }
            else:
                search_query = bool_query
        else:
            search_query = bool_query

        # Add additional filters
        if filters:
            for key, value in filters.items():
                if isinstance(value, list):
                    # Use terms query for list values
                    bool_query["bool"]["filter"].append({"terms": {key: value}})
                else:
                    # Use term query for single values
                    bool_query["bool"]["filter"].append({"term": {key: value}})

        # Log the complete query structure for debugging
        self._log_search_query(search_query, embeddings, query, element_types, element_type_weights)
        
        return search_query

    def _log_search_query(self, search_query: Dict[str, Any], embeddings: Optional[Dict[str, List[float]]], 
                         text_query: str, element_types: List[str], element_type_weights: Optional[Dict[str, float]]):
        """Log the complete OpenSearch query with embedding descriptions"""
        import json
        import copy
        
        # Create a copy of the query for logging
        log_query = copy.deepcopy(search_query)
        
        # Replace embedding vectors with descriptions
        if embeddings:
            self._replace_embeddings_with_descriptions(log_query, embeddings)
        
        # Create query summary
        query_summary = {
            "text_query": text_query or "None",
            "element_types": element_types,
            "element_type_weights": element_type_weights,
            "embeddings_provided": list(embeddings.keys()) if embeddings else [],
            "query_structure": "hybrid_search" if embeddings else "text_only"
        }
        
        logger.info("=" * 80)
        logger.info("COMPLETE OPENSEARCH QUERY")
        logger.info("=" * 80)
        logger.info("Query Summary:")
        logger.info(json.dumps(query_summary, indent=2, ensure_ascii=False))
        logger.info("-" * 40)
        logger.info("Full OpenSearch Query:")
        logger.info(json.dumps(log_query, indent=2, ensure_ascii=False))
        logger.info("=" * 80)
    
    def _replace_embeddings_with_descriptions(self, query_dict: Dict[str, Any], embeddings: Dict[str, List[float]]):
        """Recursively replace embedding vectors with descriptions"""
        if isinstance(query_dict, dict):
            for key, value in query_dict.items():
                if key == "vector" and isinstance(value, list) and len(value) > 10:
                    # Find the embedding field from the parent context
                    embedding_description = self._find_embedding_context(query_dict, embeddings)
                    query_dict[key] = f"[EMBEDDING_VECTOR: {embedding_description}]"
                elif key == "query_vector" and isinstance(value, list) and len(value) > 10:
                    # Handle script_score query_vector parameter
                    vector_length = len(value)
                    if vector_length == 384:
                        description = "텍스트 임베딩 (384차원)"
                    elif vector_length == 1152:
                        description = "이미지 임베딩 (1152차원)"
                    else:
                        description = f"임베딩 ({vector_length}차원)"
                    query_dict[key] = f"[EMBEDDING_VECTOR: {description}]"
                elif isinstance(value, (dict, list)):
                    self._replace_embeddings_with_descriptions(value, embeddings)
        elif isinstance(query_dict, list):
            for item in query_dict:
                if isinstance(item, (dict, list)):
                    self._replace_embeddings_with_descriptions(item, embeddings)
    
    def _find_embedding_context(self, current_dict: Dict[str, Any], embeddings: Dict[str, List[float]]) -> str:
        """Find embedding context from the current dictionary context"""
        # Look for embeddings.* keys in the current context
        for key in current_dict.keys():
            if key.startswith("embeddings."):
                modality = key.split(".")[-1]
                vector_length = len(embeddings.get(modality, []))
                if vector_length == 384:
                    return "텍스트 임베딩 (384차원)"
                elif vector_length == 1152:
                    return "이미지 임베딩 (1152차원)"
                else:
                    return f"{modality} 임베딩 ({vector_length}차원)"
        
        # Fallback: use the first available embedding and infer from dimension
        if embeddings:
            first_modality = list(embeddings.keys())[0]
            vector_length = len(embeddings[first_modality])
            if vector_length == 384:
                return "텍스트 임베딩 (384차원)"
            elif vector_length == 1152:
                return "이미지 임베딩 (1152차원)"
            else:
                return f"{first_modality} 임베딩 ({vector_length}차원)"
        
        return "임베딩 벡터 (차원 정보 없음)"
    
    def _get_embedding_description_by_dimension(self, declared_modality: str, vector_length: int) -> str:
        """Get embedding description based on vector dimension and declared modality"""
        # Simple dimension-based description for cleaner logs
        if vector_length == 384:
            return "텍스트 임베딩 (384차원)"
        elif vector_length == 1152:
            return "이미지 임베딩 (1152차원)"
        else:
            return f"{declared_modality} 임베딩 ({vector_length}차원)"
    
    def _get_embedding_description(self, knn_query: Dict[str, Any], embeddings: Dict[str, List[float]]) -> str:
        """Get description for embedding based on the KNN query structure"""
        # Recursively search for embedding field name in nested structure
        def find_embedding_field(obj, path=""):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    current_path = f"{path}.{key}" if path else key
                    if key.startswith("embeddings."):
                        return key
                    result = find_embedding_field(value, current_path)
                    if result:
                        return result
            return None
        
        embedding_field = find_embedding_field(knn_query)
        
        if embedding_field:
            declared_modality = embedding_field.split(".")[-1]  # Extract modality from "embeddings.text" or "embeddings.image"
            vector_length = len(embeddings.get(declared_modality, []))
            return self._get_embedding_description_by_dimension(declared_modality, vector_length)
        
        # Fallback: try to guess from available embeddings
        if embeddings:
            first_modality = list(embeddings.keys())[0]
            vector_length = len(embeddings[first_modality])
            return self._get_embedding_description_by_dimension(first_modality, vector_length)
        
        return "임베딩 벡터 (차원 정보 없음)"

    async def get_chunk_meta(self, chunk_id: str) -> Optional[Dict[str, Any]]:
        """Get chunk metadata by chunk_id"""
        try:
            if not self.client:
                return None
            response = await self.client.get(index=self.chunk_meta_index, id=chunk_id)
            return response["_source"]
        except Exception as e:
            logger.warning(f"Chunk meta not found for {chunk_id}: {e}")
            return None

    async def get_media_meta(self, media_id: str) -> Optional[Dict[str, Any]]:
        """Get media metadata by media_id"""
        try:
            if not self.client:
                return None
            response = await self.client.get(index=self.media_meta_index, id=media_id)
            return response["_source"]
        except Exception as e:
            logger.warning(f"Media meta not found for {media_id}: {e}")
            return None
