from typing import Any, Dict, List, Optional

from loguru import logger
from opensearchpy import AsyncOpenSearch

from app.core.config import settings
from app.core.index_mappings import (get_chunk_meta_mapping, get_elements_mapping,
                                     get_media_meta_mapping)
from app.services.embeddings.embedding_service import EmbeddingService
from app.services.search.rrf_reranker import RRFReranker


class OpenSearchService:
    def __init__(self):
        self.client: Optional[AsyncOpenSearch] = None
        self.media_meta_index = "multimodal_rag_media"
        self.chunk_meta_index = "multimodal_rag_chunk"
        self.elements_index = "multimodal_rag_element"

        # Initialize helper components
        self.rrf_reranker = RRFReranker()
        self.embedding_service = EmbeddingService()

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
            (self.media_meta_index, get_media_meta_mapping()),
            (self.chunk_meta_index, get_chunk_meta_mapping()),
            (self.elements_index, get_elements_mapping())
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
            filters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Search elements by running separate queries per element_type and aggregating results"""
        all_results = []
        total_took = 0

        try:
            # Run separate query for each element_type
            for element_type in element_types:
                response = await self._execute_single_query(query, element_type, embeddings, filters, size)

                # Log query results
                self._log_query_results(element_type, response)

                # Add element_type info and collect results
                for hit in response["hits"]["hits"]:
                    hit["_element_type_query"] = element_type

                all_results.extend(response["hits"]["hits"])
                total_took += response["took"]

            # Rerank and return results
            aggregated_response = self.rrf_reranker.rerank_results(all_results, size, from_, total_took)
            self.rrf_reranker.log_reranking_summary(aggregated_response)

            return aggregated_response

        except Exception as e:
            logger.error(f"Element search failed: {e}")
            raise

    async def _execute_single_query(
            self,
            query: str,
            element_type: str,
            embeddings: Optional[Dict[str, List[float]]],
            filters: Optional[Dict[str, Any]],
            size: int
    ) -> Dict[str, Any]:
        """Execute search query for single element type"""
        selected_embedding = self.embedding_service.select_for_element_type(element_type, embeddings)
        search_query = self._build_search_query(query, [element_type], selected_embedding, filters)

        if not self.client:
            raise RuntimeError("OpenSearch client not initialized")
        return await self.client.search(
            index=self.elements_index,
            body={
                "query": search_query,
                "size": size,
                "from": 0,
                "_source": True
            }
        )

    def _log_query_results(self, element_type: str, response: Dict[str, Any]) -> None:
        """Log compact query results"""
        hits_count = len(response["hits"]["hits"])
        max_score = response["hits"]["max_score"] if response["hits"]["hits"] else 0.0

        # Get top 3 results summary
        top_results = []
        if hits_count > 0:
            for hit in response["hits"]["hits"][:3]:
                element_id = hit["_source"].get("element_id", "unknown")
                score = hit["_score"]
                top_results.append(f"{element_id}({score:.3f})")

        results_summary = ", ".join(top_results) if top_results else "no results"
        logger.info(f"[{element_type}] query → {hits_count} hits (max: {max_score:.4f}) → top3: [{results_summary}]")

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

    async def get_chunk_meta(self, chunk_id: str) -> Optional[Dict[str, Any]]:
        """Get chunk metadata by chunk_id"""
        try:
            if not self.client:
                return None
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
            if not self.client:
                return None
            response = await self.client.get(
                index=self.media_meta_index,
                id=media_id
            )
            return response["_source"]
        except Exception as e:
            logger.warning(f"Media meta not found for {media_id}: {e}")
            return None
