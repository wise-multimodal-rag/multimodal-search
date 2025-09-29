from typing import Dict, List, Optional, Any

from loguru import logger
from opensearchpy import AsyncOpenSearch

from app.core.config import settings


class OpenSearchService:
    def __init__(self):
        self.client: Optional[AsyncOpenSearch] = None
        self.media_meta_index = "multimodal_rag_media"
        self.chunk_meta_index = "multimodal_rag_chunk"
        self.elements_index = "multimodal_rag_element"

    async def initialize(self):
        """Initialize OpenSearch client"""
        try:
            self.client = AsyncOpenSearch(
                hosts=[{
                    'host': settings.opensearch_host,
                    'port': settings.opensearch_port
                }],
                http_auth=(
                    settings.opensearch_username,
                    settings.opensearch_password) if settings.opensearch_username else None,
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
            return health['status'] in ['green', 'yellow']
        except Exception as e:
            logger.error(f"OpenSearch health check failed: {e}")
            return False

    async def _ensure_indices_exist(self):
        """Ensure all required indices exist"""
        indices = [
            (self.media_meta_index, self._get_media_meta_mapping()),
            (self.chunk_meta_index, self._get_chunk_meta_mapping()),
            (self.elements_index, self._get_elements_mapping())
        ]

        for index_name, mapping in indices:
            if not await self._index_exists(index_name):
                await self._create_index(index_name, mapping)
                logger.info(f"Created index: {index_name}")

    async def _index_exists(self, index_name: str) -> bool:
        """Check if index exists"""
        try:
            return await self.client.indices.exists(index=index_name)
        except Exception:
            return False

    async def _create_index(self, index_name: str, mapping: Dict[str, Any]):
        """Create index with mapping"""
        await self.client.indices.create(index=index_name, body=mapping)

    def _get_media_meta_mapping(self) -> Dict[str, Any]:
        """Get media_meta index mapping"""
        return {
            "settings": {
                "index": {"number_of_shards": 1, "number_of_replicas": 1}
            },
            "mappings": {
                "dynamic": "false",
                "properties": {
                    "media_id": {"type": "keyword"},
                    "media_type": {"type": "keyword"},
                    "mime_type": {"type": "keyword"},
                    "title": {"type": "text", "analyzer": "standard"},
                    "source_uri": {"type": "keyword"},
                    "file_size_bytes": {"type": "long"},
                    "duration_seconds": {"type": "float"},
                    "width_pixels": {"type": "integer"},
                    "height_pixels": {"type": "integer"},
                    "language_primary": {"type": "keyword"},
                    "chunk_count": {"type": "integer"},
                    "element_count": {"type": "integer"},
                    "metadata_flat": {"type": "object", "enabled": False},
                    "owner": {"type": "keyword"},
                    "visibility": {"type": "keyword"},
                    "tags": {"type": "keyword"},
                    "created_at": {"type": "date"},
                    "updated_at": {"type": "date"}
                }
            }
        }

    def _get_chunk_meta_mapping(self) -> Dict[str, Any]:
        """Get chunk_meta index mapping"""
        return {
            "settings": {
                "index": {"number_of_shards": 2, "number_of_replicas": 1}
            },
            "mappings": {
                "dynamic": "false",
                "properties": {
                    "chunk_id": {"type": "keyword"},
                    "media_id": {"type": "keyword"},
                    "chunk_seq": {"type": "integer"},
                    "chunk_type": {"type": "keyword"},
                    "modality_set": {"type": "keyword"},
                    "element_count": {"type": "integer"},
                    "label": {"type": "text"},
                    "tags": {"type": "keyword"},
                    "created_at": {"type": "date"},
                    "updated_at": {"type": "date"}
                }
            }
        }

    def _get_elements_mapping(self) -> Dict[str, Any]:
        """Get elements index mapping"""
        return {
            "settings": {
                "index": {
                    "knn": True,
                    "number_of_shards": 3,
                    "number_of_replicas": 1
                },
                "analysis": {
                    "analyzer": {
                        "ko_en": {
                            "type": "custom",
                            "tokenizer": "nori_tokenizer",
                            "filter": ["lowercase", "nori_part_of_speech", "nori_number"]
                        }
                    }
                }
            },
            "mappings": {
                "dynamic": "false",
                "properties": {
                    "element_id": {"type": "keyword"},
                    "chunk_id": {"type": "keyword"},
                    "media_id": {"type": "keyword"},
                    "description": {"type": "text", "analyzer": "ko_en"},
                    "modality": {"type": "keyword"},
                    "element_type": {"type": "keyword"},
                    "content_type": {"type": "keyword"},
                    "content": {
                        "type": "text",
                        "analyzer": "ko_en",
                        "fields": {
                            "exact": {"type": "keyword", "ignore_above": 2048}
                        }
                    },
                    "embeddings": {
                        "properties": {
                            "text": {
                                "type": "knn_vector",
                                "dimension": 384,
                                "method": {"name": "hnsw", "space_type": "cosinesimil"}
                            },
                            "image": {
                                "type": "knn_vector",
                                "dimension": 512,
                                "method": {"name": "hnsw", "space_type": "cosinesimil"}
                            },
                            "video": {
                                "type": "knn_vector",
                                "dimension": 512,
                                "method": {"name": "hnsw", "space_type": "cosinesimil"}
                            },
                            "audio": {
                                "type": "knn_vector",
                                "dimension": 512,
                                "method": {"name": "hnsw", "space_type": "cosinesimil"}
                            }
                        }
                    },
                    "quality_scores": {
                        "properties": {
                            "combined_static": {"type": "rank_feature"}
                        }
                    },
                    "element_seq": {"type": "integer"},
                    "language": {"type": "keyword"},
                    "tags": {"type": "keyword"},
                    "created_at": {"type": "date"},
                    "updated_at": {"type": "date"}
                }
            }
        }

    async def search_elements(
            self,
            query: str,
            element_types: List[str],
            embeddings: Optional[Dict[str, List[float]]] = None,
            size: int = 10,
            from_: int = 0,
            filters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Search elements by running separate queries per element_type and aggregating results"""
        
        all_results = []
        total_took = 0
        
        try:
            # Run separate query for each element_type
            for element_type in element_types:
                # Select appropriate embedding for this element_type
                selected_embedding = self._select_embedding_for_element_type(element_type, embeddings)
                
                # Build query for single element_type
                search_query = self._build_search_query(query, [element_type], selected_embedding, filters)
                
                response = await self.client.search(
                    index=self.elements_index,
                    body={
                        "query": search_query,
                        "size": size,
                        "from": 0,  # Always start from 0 for individual queries
                        "_source": True
                    }
                )
                
                # Add element_type info to each hit
                for hit in response["hits"]["hits"]:
                    hit["_element_type_query"] = element_type
                    
                all_results.extend(response["hits"]["hits"])
                total_took += response["took"]
            
            # Aggregate and rerank results
            aggregated_response = self._aggregate_and_rerank_results(all_results, size, from_, total_took)
            return aggregated_response
            
        except Exception as e:
            logger.error(f"Element search failed: {e}")
            raise

    def _build_search_query(
            self,
            query: str,
            element_types: List[str],
            embeddings: Optional[Dict[str, List[float]]],
            filters: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Build hybrid search query combining text and vector search"""

        # Base bool query
        bool_query = {
            "bool": {
                "must": [],
                "filter": [
                    {"terms": {"element_type": element_types}}
                ]
            }
        }

        # Add text search
        if query.strip():
            bool_query["bool"]["must"].append({
                "multi_match": {
                    "query": query,
                    "fields": ["content^2", "description"],
                    "type": "best_fields",
                    "fuzziness": "AUTO"
                }
            })

        # Add vector search if embeddings provided
        if embeddings:
            knn_queries = []
            for modality, embedding_vector in embeddings.items():
                if embedding_vector:
                    knn_queries.append({
                        "knn": {
                            f"embeddings.{modality}": {
                                "vector": embedding_vector,
                                "k": 10
                            }
                        }
                    })

            # Combine text and vector queries
            if knn_queries:
                if len(knn_queries) == 1:
                    # Single vector query
                    search_query = {
                        "bool": {
                            "should": [
                                bool_query,
                                knn_queries[0]
                            ],
                            "minimum_should_match": 1
                        }
                    }
                else:
                    # Multiple vector queries
                    search_query = {
                        "bool": {
                            "should": [
                                bool_query,
                                {"bool": {"should": knn_queries, "minimum_should_match": 1}}
                            ],
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
                    bool_query["bool"]["filter"].append({
                        "terms": {key: value}
                    })
                else:
                    # Use term query for single values
                    bool_query["bool"]["filter"].append({
                        "term": {key: value}
                    })

        return search_query

    def _select_embedding_for_element_type(
            self, 
            element_type: str, 
            embeddings: Optional[Dict[str, List[float]]]
    ) -> Optional[Dict[str, List[float]]]:
        """Select appropriate embedding based on element_type"""
        if not embeddings:
            return None
            
        # Define element_type to modality mapping
        text_element_types = ["paragraph", "title", "summary", "stt", "caption", "scene", "ocr", "table", "translation"]
        image_element_types = ["origin", "cropped", "detected_object", "chart", "diagram", "keyframe", "thumbnail"]
        video_element_types = ["clip", "segment"]
        audio_element_types = ["speech", "music", "sound_effect", "ambient"]
        
        # Select embedding based on element_type
        if element_type in text_element_types:
            # Prefer text embedding, fallback to others
            for key in ["text", "image", "video", "audio"]:
                if key in embeddings:
                    return {key: embeddings[key]}
        elif element_type in image_element_types:
            # Prefer image embedding, fallback to others  
            for key in ["image", "text", "video", "audio"]:
                if key in embeddings:
                    return {key: embeddings[key]}
        elif element_type in video_element_types:
            # Prefer video embedding, fallback to others
            for key in ["video", "image", "text", "audio"]:
                if key in embeddings:
                    return {key: embeddings[key]}
        elif element_type in audio_element_types:
            # Prefer audio embedding, fallback to others
            for key in ["audio", "text", "image", "video"]:
                if key in embeddings:
                    return {key: embeddings[key]}
        
        # If no match, return first available embedding
        for key, value in embeddings.items():
            return {key: value}
            
        return None

    def _aggregate_and_rerank_results(
            self, 
            all_results: List[Dict], 
            size: int, 
            from_: int, 
            total_took: int
    ) -> Dict[str, Any]:
        """Aggregate results from multiple queries and rerank"""
        
        # Remove duplicates based on element_id
        unique_results = {}
        for hit in all_results:
            element_id = hit["_source"]["element_id"]
            if element_id not in unique_results or hit["_score"] > unique_results[element_id]["_score"]:
                unique_results[element_id] = hit
        
        # Convert back to list and sort by score
        results_list = list(unique_results.values())
        results_list.sort(key=lambda x: x["_score"], reverse=True)
        
        # Apply pagination
        paginated_results = results_list[from_:from_ + size]
        
        # Build response in OpenSearch format
        return {
            "took": total_took,
            "timed_out": False,
            "hits": {
                "total": {"value": len(results_list), "relation": "eq"},
                "max_score": results_list[0]["_score"] if results_list else 0.0,
                "hits": paginated_results
            }
        }

    async def get_chunk_meta(self, chunk_id: str) -> Optional[Dict[str, Any]]:
        """Get chunk metadata by chunk_id"""
        try:
            response = await self.client.get(
                index=self.chunk_meta_index,
                id=chunk_id
            )
            return response["_source"]
        except Exception as e:
            logger.warning(f"Chunk meta not found for {chunk_id}: {e}")
            return None

    async def get_media_meta(self, media_id: str) -> Optional[Dict[str, Any]]:
        """Get media metadata by media_id"""
        try:
            response = await self.client.get(
                index=self.media_meta_index,
                id=media_id
            )
            return response["_source"]
        except Exception as e:
            logger.warning(f"Media meta not found for {media_id}: {e}")
            return None
