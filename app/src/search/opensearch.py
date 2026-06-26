import copy
import json
from typing import Any, Dict, List, Optional

from loguru import logger
from opensearchpy import AsyncOpenSearch

from app.config.config import settings
from app.config.weights import weighting_config
from app.src.embeddings import EmbeddingService
from app.utils.index_mappings import (get_chunk_meta_mapping, get_elements_mapping,
                                      get_media_meta_mapping)


class OpenSearchService:
    def __init__(self, embedding_service: EmbeddingService = None):
        self.client: Optional[AsyncOpenSearch] = None
        self._initialized = False
        self.media_meta_index = settings.opensearch_media_index
        self.chunk_meta_index = settings.opensearch_chunk_index
        self.elements_index = settings.opensearch_elements_index

        # Initialize helper components with dependency injection
        self.embedding_service = embedding_service or EmbeddingService()

    async def _ensure_initialized(self):
        """Ensure OpenSearch client is initialized"""
        if not self._initialized:
            await self.initialize()

    async def initialize(self):
        """Initialize OpenSearch client"""
        if self._initialized:
            return

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
            self._initialized = True
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
        await self._ensure_initialized()

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
            image_caption_tags: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Search elements with unified query filtering by element_types"""
        await self._ensure_initialized()

        try:
            # Pass all embeddings to the search query builder
            search_query = self._build_search_query(
                query, element_types, embeddings, filters, element_type_weights, image_caption_tags
            )

            if not self.client:
                raise RuntimeError("OpenSearch client not initialized")

            # Build search body with KNN and query sections
            search_body = {
                "query": search_query,
                "size": size,
                "from": from_,
                "_source": True,
                "explain": True,
            }

            # Add KNN section for better vector search performance if embeddings exist
            # Note: Using the query-level KNN approach instead of top-level knn section
            # because OpenSearch may not support multiple KNN searches in array format

            # Determine search mode for score breakdown context
            has_image_embedding = bool(embeddings and any('image' in k for k in embeddings.keys()))
            has_text_embedding = bool(embeddings and any(
                k in ('text', 'text_summary', 'text_keywords', 'text_entities',
                      'image_caption', 'image_objects') for k in embeddings.keys()))
            if has_image_embedding and has_text_embedding:
                search_mode = "cross_modal"
            elif has_image_embedding:
                search_mode = "image"
            else:
                search_mode = "text"

            response = await self.client.search(index=self.elements_index, body=search_body)

            # Log unified query results
            hits_count = len(response["hits"]["hits"])
            max_score = response["hits"]["max_score"] if response["hits"]["hits"] else 0.0

            # 가중치 및 모달리티 매칭 정보 표시
            weight_info = "weighted" if element_type_weights else "standard"
            modality_info = f"modalities: {','.join(embeddings.keys())}" if embeddings else "text-only"
            logger.info(
                f"OpenSearch [{','.join(element_types)}] {weight_info} ({modality_info}) → {hits_count} hits (max: {max_score:.4f})")

            # Convert to standard format (score 정보 보존 + explain 파싱)
            results = []
            for hit in response["hits"]["hits"]:
                result_item = hit["_source"].copy()
                result_item["score"] = hit.get("_score", 0.0)
                result_item["original_score"] = hit.get("_original_score")

                # Parse explanation tree for score breakdown
                explanation = hit.get("_explanation")
                if explanation:
                    result_item["score_breakdown"] = self._parse_explanation(explanation, search_mode)

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

    # Active embedding fields for cross-modal search
    # All use Qwen3-VL unified 2048D vector space — cross-modal similarity is valid
    CROSS_MODAL_EMBEDDING_FIELDS = ["text", "image"]

    def _build_search_query(
            self,
            query: str,
            element_types: List[str],
            embeddings: Optional[Dict[str, List[float]]],
            filters: Optional[Dict[str, Any]],
            element_type_weights: Optional[Dict[str, float]] = None,
            image_caption_tags: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Build hybrid search query with cross-modal vector search support.

        Cross-modal: Qwen3-VL produces text/image embeddings in the same 2048D vector space,
        so a text embedding can meaningfully match against image embeddings and vice versa.
        Each query embedding searches ALL active embedding fields (text, image).
        """
        # element_type별 가중치가 있으면 가중치 기반 쿼리 구성, 없으면 기존 방식
        if element_type_weights:
            # 가중치 기반 element_type 필터링 (should 쿼리로 변경)
            element_type_queries = []
            for element_type in element_types:
                weight = element_type_weights.get(element_type, weighting_config.OPENSEARCH_DEFAULT_WEIGHT)
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

        # Add text search (BM25)
        if query.strip():
            # Enhance query with image caption tags if provided
            enhanced_query = self._enhance_query_with_caption_tags(query, image_caption_tags)
            bm25_query = {"multi_match": {"query": enhanced_query, "fields": ["content", "description"],
                                          "type": "best_fields", "fuzziness": "AUTO"}}

            if embeddings:
                # Cross-modal mode: BM25 is a scoring bonus (should), not a requirement (must).
                # This allows vector-only matches (e.g., images) to appear in results.
                if "should" not in bool_query["bool"]:
                    bool_query["bool"]["should"] = []
                bool_query["bool"]["should"].append(bm25_query)
            else:
                # Text-only mode: BM25 is required
                bool_query["bool"]["must"].append(bm25_query)

        # Add cross-modal vector search if embeddings provided
        if embeddings:
            vector_queries = []

            for modality, embedding_vector in embeddings.items():
                if not embedding_vector or len(embedding_vector) == 0:
                    continue

                # Identify source modality (for logging/boost calculation only, NOT for filtering)
                source_modality = self._map_embedding_to_modality(modality)

                # Cross-modal: search against ALL embedding fields
                for target_field in self.CROSS_MODAL_EMBEDDING_FIELDS:
                    # Base query: documents that have this embedding field populated
                    base_query = {"exists": {"field": f"embeddings.{target_field}"}}

                    # Add element_type filtering to vector search
                    if element_type_weights:
                        et_queries = []
                        for element_type in element_types:
                            weight = element_type_weights.get(element_type,
                                                             weighting_config.OPENSEARCH_DEFAULT_WEIGHT)
                            if weight > 0:
                                et_boost = max(0.1, weight * 10)
                                et_queries.append({
                                    "term": {"element_type": {"value": element_type, "boost": et_boost}}
                                })

                        if et_queries:
                            base_query = {
                                "bool": {
                                    "must": [{"exists": {"field": f"embeddings.{target_field}"}}],
                                    "should": et_queries,
                                    "minimum_should_match": 1
                                }
                            }

                    # Build script_score query
                    if element_type_weights:
                        script_source = """
                        double similarity = cosineSimilarity(params.query_vector, doc['embeddings.{target}']) + 1.0;
                        double element_boost = 1.0;
                        if (params.element_weights.containsKey(doc['element_type'].value)) {{
                            element_boost = params.element_weights[doc['element_type'].value];
                        }}
                        return similarity * Math.max(0.05, element_boost);
                        """.format(target=target_field)

                        vector_query = {
                            "script_score": {
                                "query": base_query,
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
                                    "source": f"cosineSimilarity(params.query_vector, doc['embeddings.{target_field}']) + 1.0",
                                    "params": {"query_vector": embedding_vector}
                                }
                            }
                        }

                    vector_queries.append({
                        "query": vector_query,
                        "source_modality": source_modality,
                        "target_field": target_field,
                    })

            # Combine text search with vector searches
            if vector_queries:
                # Configure search type weights based on input modalities
                has_image_embedding = any(vq["source_modality"] == "image" for vq in vector_queries)

                if has_image_embedding:
                    # 이미지 검색 시: 임베딩을 강력히 우선시 (BM25는 보조적)
                    text_search_boost = 0.3
                    embedding_search_boost = 3.0
                else:
                    # 텍스트만 검색 시: 기존 가중치 유지
                    text_search_boost = 1.0
                    embedding_search_boost = 1.5

                # Create hybrid query with configurable boosting
                text_query_with_boost = {
                    "bool": {
                        **bool_query["bool"],
                        "boost": text_search_boost
                    }
                }

                # Apply embedding boost to each vector query
                boosted_vector_queries = []
                for vq_info in vector_queries:
                    vector_query = vq_info["query"]
                    source_modality = vq_info["source_modality"]

                    # Calculate modality-specific boost
                    modality_boost = self._calculate_modality_boost(
                        source_modality, element_type_weights, embedding_search_boost
                    )

                    boosted_vector_query = {
                        "bool": {
                            "must": [vector_query],
                            "boost": modality_boost
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
            if "filter" not in bool_query["bool"]:
                bool_query["bool"]["filter"] = []
            for key, value in filters.items():
                if isinstance(value, list):
                    bool_query["bool"]["filter"].append({"terms": {key: value}})
                else:
                    bool_query["bool"]["filter"].append({"term": {key: value}})

        # Log the complete query structure for debugging
        self._log_search_query(search_query, embeddings, query, element_types, element_type_weights)

        return search_query

    def _enhance_query_with_caption_tags(self, query: str, image_caption_tags: Optional[List[str]]) -> str:
        """Enhance query by appending image caption tags while respecting 1000 character limit"""
        if not image_caption_tags:
            return query

        # Start with original query
        enhanced_query = query.strip()

        # Join tags with space
        tags_text = " ".join(image_caption_tags)

        # Check if adding tags would exceed 1000 character limit
        if len(enhanced_query) + len(tags_text) + 1 <= 1000:  # +1 for space separator
            enhanced_query = f"{enhanced_query} {tags_text}"
        else:
            # Calculate remaining space
            remaining_space = 1000 - len(enhanced_query) - 1  # -1 for space separator
            if remaining_space > 0:
                # Truncate tags text to fit within limit
                truncated_tags = tags_text[:remaining_space]
                enhanced_query = f"{enhanced_query} {truncated_tags}"

        return enhanced_query

    def _map_embedding_to_modality(self, embedding_type: str) -> str:
        """Map embedding type to OpenSearch modality"""
        # Text-based embeddings map to 'text' modality
        text_based_embeddings = {
            "text", "text_summary", "text_keywords", "text_entities",
            "image_caption", "image_tags", "image_objects",
            "video_description", "video_scenes", "video_activities",
            "audio_transcription", "audio_sounds"
        }

        if embedding_type in text_based_embeddings:
            return "text"
        elif embedding_type == "image":
            return "image"
        elif embedding_type == "video":
            return "video"
        elif embedding_type == "audio":
            return "audio"
        else:
            # Fallback to the original embedding type
            return embedding_type

    def _calculate_modality_boost(self, embedding_type: str, element_type_weights: Optional[Dict[str, float]],
                                  base_boost: float) -> float:
        """Calculate modality-specific boost based on element_type_weights"""
        if not element_type_weights:
            return base_boost

        # Map embedding types to their corresponding element types for boost calculation
        embedding_to_element_type = {
            "text": ["paragraph", "summary"],  # Original text embedding targets these types
            "image_caption": ["caption"],  # Image caption embedding targets caption type
            "image": ["origin"],  # Image embedding targets origin type
            # Future mappings
            "text_summary": ["summary"],
            "text_keywords": ["paragraph"],
            "text_entities": ["paragraph"],
            "image_objects": ["origin"],
            "video_description": ["paragraph"],
            "audio_transcription": ["paragraph"],
        }

        relevant_element_types = embedding_to_element_type.get(embedding_type, [])
        if not relevant_element_types:
            return base_boost

        # Calculate weighted average of relevant element types
        total_weight = 0.0
        weight_sum = 0.0

        for element_type in relevant_element_types:
            if element_type in element_type_weights:
                weight = element_type_weights[element_type]
                weight_sum += weight
                total_weight += 1.0

        if total_weight == 0:
            return base_boost

        # Calculate average weight for this embedding type
        avg_weight = weight_sum / total_weight

        # Scale boost based on average weight using config values
        min_multiplier = weighting_config.MODALITY_BOOST_MIN_MULTIPLIER
        boost_range = weighting_config.MODALITY_BOOST_RANGE
        boost_multiplier = min_multiplier + (avg_weight * boost_range)
        final_boost = base_boost * boost_multiplier

        logger.info(
            f"Modality boost calculated: {embedding_type} → avg_weight={avg_weight:.2f}, multiplier={boost_multiplier:.2f}, final_boost={final_boost:.2f}")

        return final_boost

    def _parse_explanation(self, explanation: Dict[str, Any], search_mode: str) -> Dict[str, Any]:
        """Parse OpenSearch _explanation tree to extract BM25 and vector score components.

        The explanation tree structure for a bool/should query:
        - Top level: sum of (should clause scores)
          - Child 0: BM25 text match (with boost)
          - Child 1+: script_score vector queries (with boost)

        Returns a structured breakdown of each scoring component.
        """
        breakdown = {
            "total_score": explanation.get("value", 0.0),
            "search_mode": search_mode,
            "components": [],
        }

        try:
            details = explanation.get("details", [])
            if not details:
                # Single component - no decomposition possible
                breakdown["components"].append({
                    "type": "combined",
                    "score": explanation.get("value", 0.0),
                    "description": explanation.get("description", "")[:100],
                })
                return breakdown

            for detail in details:
                component = self._classify_explanation_node(detail)
                if component:
                    breakdown["components"].append(component)

            # 같은 type의 컴포넌트를 합산 (예: search_boost 2개 → 1개, bm25 여러개 → 1개)
            breakdown["components"] = self._merge_same_type_components(breakdown["components"])

        except Exception as e:
            logger.debug(f"Failed to parse explanation: {e}")
            breakdown["parse_error"] = str(e)

        return breakdown

    def _merge_same_type_components(self, components: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """같은 type의 최상위 컴포넌트를 합산하여 하나로 병합"""
        if not components:
            return components

        # type별 그룹핑
        type_groups: Dict[str, List[Dict[str, Any]]] = {}
        order = []  # 원래 순서 유지
        for comp in components:
            comp_type = comp.get("type", "unknown")
            if comp_type not in type_groups:
                type_groups[comp_type] = []
                order.append(comp_type)
            type_groups[comp_type].append(comp)

        # 합산
        merged = []
        for comp_type in order:
            group = type_groups[comp_type]
            if len(group) == 1:
                merged.append(group[0])
            else:
                # 같은 type 여러 개 → 합산
                total_score = sum(c.get("score", 0) for c in group)
                merged_comp = {
                    "type": comp_type,
                    "score": total_score,
                    "description": group[0].get("description", ""),
                    "details": group[0].get("details", {}),
                }
                # boost_applied가 있으면 유지
                if group[0].get("boost_applied"):
                    merged_comp["boost_applied"] = group[0]["boost_applied"]
                merged.append(merged_comp)

        return merged

    def _classify_explanation_node(self, node: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Classify a single explanation node as BM25, vector, element_type boost, or wrapper."""
        description = node.get("description", "").lower()
        value = node.get("value", 0.0)
        details = node.get("details", [])

        # Skip coord/queryNorm nodes with zero value
        if value == 0.0 and "coord" in description:
            return None

        # Element type term boost detection (before generic BM25)
        # These are "weight(element_type:xxx)" or term queries on element_type with boost
        if "element_type" in description:
            boost = self._extract_boost_value(node)
            return {
                "type": "element_type_boost",
                "score": value,
                "description": "Element Type 가중치",
                "details": {"boost": boost} if boost else {},
            }

        # BM25 text match detection
        if any(keyword in description for keyword in ["weight(", "multi_match", "bm25", "idf", "tf"]):
            return {
                "type": "bm25",
                "score": value,
                "description": "BM25 키워드 매칭",
                "details": self._extract_boost_info(node),
            }

        # Script score (vector similarity) detection
        if "script score" in description or "cosinesimilarity" in description:
            # Try to identify vector type from nested details
            vector_type = self._identify_vector_type(node)
            return {
                "type": f"vector_{vector_type}",
                "score": value,
                "description": f"Vector 유사도 ({vector_type})",
                "details": self._extract_boost_info(node),
            }

        # Bool query with boost (wrapper for sub-components)
        if "bool" in description or "sum of" in description or "max of" in description:
            # Recurse into children to find actual scoring components
            sub_components = []
            for sub_detail in details:
                sub_comp = self._classify_explanation_node(sub_detail)
                if sub_comp:
                    sub_components.append(sub_comp)

            if sub_components:
                # If wrapper has boost, apply it
                boost = self._extract_boost_value(node)
                if boost and boost != 1.0:
                    for comp in sub_components:
                        comp["boost_applied"] = boost

                # If all sub-components are the same type, label the composite accordingly
                if len(sub_components) == 1:
                    return sub_components[0]

                sub_types = set(c.get("type") for c in sub_components)
                if sub_types == {"bm25"}:
                    composite_label = "BM25 텍스트 관련성 (멀티 키워드 합산)"
                    composite_type = "bm25_composite"
                elif sub_types == {"element_type_boost"}:
                    composite_label = "Element Type 가중치 합산"
                    composite_type = "element_type_composite"
                else:
                    composite_label = description[:80]
                    composite_type = "composite"

                return {
                    "type": composite_type,
                    "score": value,
                    "description": composite_label,
                    "sub_components": sub_components,
                }

        # Product/boost wrapper
        if "product of" in description or "boost" in description:
            boost = self._extract_boost_value(node)
            # Find the actual scoring child
            for sub_detail in details:
                sub_comp = self._classify_explanation_node(sub_detail)
                if sub_comp:
                    if boost and boost != 1.0:
                        sub_comp["boost_applied"] = boost
                    sub_comp["score"] = value  # Use the boosted score
                    return sub_comp

        # Boost factor node (e.g., text_search_boost or embedding_search_boost applied at bool level)
        if value > 0.0 and "boost" in description:
            return {
                "type": "search_boost",
                "score": value,
                "description": "검색 유형 가중치 (Boost)",
                "details": {"boost": value},
            }

        # Generic fallback - include it for transparency
        if value > 0.0:
            return {
                "type": "other",
                "score": value,
                "description": description[:80] if description else "unknown",
            }

        return None

    def _identify_vector_type(self, node: Dict[str, Any]) -> str:
        """Identify whether a vector score is for image or text embedding."""
        # Walk the explanation tree looking for modality hints
        node_str = str(node).lower()
        if "embeddings.image" in node_str or "'image'" in node_str:
            return "image"
        elif "embeddings.text" in node_str or "'text'" in node_str:
            return "text"
        elif "image_caption" in node_str:
            return "image_caption"
        return "unknown"

    def _extract_boost_info(self, node: Dict[str, Any]) -> Dict[str, Any]:
        """Extract boost-related information from an explanation node."""
        info = {}
        description = node.get("description", "")

        # Try to extract boost value from description
        boost = self._extract_boost_value(node)
        if boost:
            info["boost"] = boost

        # Check child details for boost info
        for detail in node.get("details", []):
            desc = detail.get("description", "").lower()
            if "boost" in desc:
                info["boost"] = detail.get("value", 1.0)

        return info

    def _extract_boost_value(self, node: Dict[str, Any]) -> Optional[float]:
        """Extract boost value from a node or its children."""
        description = node.get("description", "").lower()

        # Look for boost in description string (e.g., "boost=3.0")
        if "boost" in description:
            import re
            boost_match = re.search(r"boost[=:]\s*([0-9.]+)", description)
            if boost_match:
                return float(boost_match.group(1))

        # Look for boost in child details
        for detail in node.get("details", []):
            desc = detail.get("description", "").lower()
            if "boost" in desc and detail.get("value"):
                return detail.get("value")

        return None

    def _log_search_query(self, search_query: Dict[str, Any], embeddings: Optional[Dict[str, List[float]]],
                          text_query: str, element_types: List[str], element_type_weights: Optional[Dict[str, float]]):
        """Log the complete OpenSearch query with embedding descriptions"""
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

        logger.info("Query Summary:")
        logger.info(json.dumps(query_summary, ensure_ascii=False))
        logger.info("Full OpenSearch Query:")
        logger.info(json.dumps(log_query, ensure_ascii=False))

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
            declared_modality = embedding_field.split(".")[
                -1]  # Extract modality from "embeddings.text" or "embeddings.image"
            vector_length = len(embeddings.get(declared_modality, []))
            return self._get_embedding_description_by_dimension(declared_modality, vector_length)

        # Fallback: try to guess from available embeddings
        if embeddings:
            first_modality = list(embeddings.keys())[0]
            vector_length = len(embeddings[first_modality])
            return self._get_embedding_description_by_dimension(first_modality, vector_length)

        return "임베딩 벡터 (차원 정보 없음)"

    async def search_cross_modal(
            self,
            embeddings: Dict[str, List[float]],
            element_types: List[str],
            size: int = 5,
            element_type_weights: Optional[Dict[str, float]] = None,
    ) -> Dict[str, Any]:
        """Cross-modal vector-only search: query each embedding against OTHER modality fields.

        This is a dedicated cross-modal search that runs without BM25,
        ensuring results from other modalities are not drowned out by text scores.
        No element_type filtering is applied here since cross-modal documents may have
        different element_types (e.g., image docs use 'main', 'sub', 'origin').
        """
        await self._ensure_initialized()

        try:
            if not self.client:
                raise RuntimeError("OpenSearch client not initialized")

            vector_queries = []

            for modality, embedding_vector in embeddings.items():
                if not embedding_vector or len(embedding_vector) == 0:
                    continue

                source_modality = self._map_embedding_to_modality(modality)

                # Only search the OPPOSITE modality fields (cross-modal only)
                for target_field in self.CROSS_MODAL_EMBEDDING_FIELDS:
                    if target_field == source_modality:
                        continue  # Skip same-modal (handled by main search)

                    # No element_type filter for cross-modal — different modalities have different types
                    base_query = {"exists": {"field": f"embeddings.{target_field}"}}

                    vector_query = {
                        "script_score": {
                            "query": base_query,
                            "script": {
                                "source": f"cosineSimilarity(params.query_vector, doc['embeddings.{target_field}']) + 1.0",
                                "params": {"query_vector": embedding_vector}
                            }
                        }
                    }
                    vector_queries.append(vector_query)

            if not vector_queries:
                return {"results": [], "total_hits": 0, "max_score": 0.0, "took_ms": 0}

            # Combine all cross-modal vector queries
            search_query = {
                "bool": {
                    "should": vector_queries,
                    "minimum_should_match": 1
                }
            }

            search_body = {
                "query": search_query,
                "size": size,
                "_source": True,
                "explain": True,
            }

            response = await self.client.search(index=self.elements_index, body=search_body)

            hits_count = len(response["hits"]["hits"])
            max_score = response["hits"]["max_score"] if response["hits"]["hits"] else 0.0
            logger.info(f"Cross-modal search → {hits_count} hits (max: {max_score:.4f})")

            results = []
            for hit in response["hits"]["hits"]:
                result_item = hit["_source"].copy()
                result_item["score"] = hit.get("_score", 0.0)
                result_item["_cross_modal"] = True  # Mark as cross-modal result

                # Parse explanation for score breakdown
                explanation = hit.get("_explanation")
                if explanation:
                    result_item["score_breakdown"] = self._parse_explanation(explanation, "cross_modal")

                results.append(result_item)

            return {
                "results": results,
                "total_hits": response["hits"]["total"]["value"],
                "max_score": max_score,
                "took_ms": response["took"],
            }

        except Exception as e:
            logger.error(f"Cross-modal search failed: {e}")
            return {"results": [], "total_hits": 0, "max_score": 0.0, "took_ms": 0}

    async def get_chunk_meta(self, chunk_id: str) -> Optional[Dict[str, Any]]:
        """Get chunk metadata by chunk_id"""
        await self._ensure_initialized()

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
        await self._ensure_initialized()

        try:
            if not self.client:
                return None
            response = await self.client.get(index=self.media_meta_index, id=media_id)
            return response["_source"]
        except Exception as e:
            logger.warning(f"Media meta not found for {media_id}: {e}")
            return None
