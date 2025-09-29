from typing import Any, Dict, List, Optional

from loguru import logger

from app.models.opensearch import ChunkMeta, Element, MediaMeta, SearchResult
from app.services.search.opensearch_service import OpenSearchService


class ResultEnricher:
    """검색 결과 enrichment를 담당하는 서비스"""
    
    def __init__(self, opensearch_service: OpenSearchService = None):
        self.opensearch_service = opensearch_service or OpenSearchService()

    async def enrich_search_results(
        self,
        search_results: Dict[str, Any],
        include_chunk_meta: bool,
        include_media_meta: bool
    ) -> List[SearchResult]:
        """검색 결과에 chunk 및 media 메타데이터 추가"""
        enriched_results = []

        try:
            for hit in search_results["hits"]["hits"]:
                element_data = hit["_source"]
                element = Element(**element_data)

                chunk_meta = None
                media_meta = None

                # chunk 메타데이터 가져오기 (요청된 경우)
                if include_chunk_meta:
                    chunk_meta = await self._get_chunk_metadata(element.chunk_id)

                # media 메타데이터 가져오기 (요청된 경우)
                if include_media_meta:
                    media_meta = await self._get_media_metadata(element.media_id)

                result = SearchResult(
                    element=element,
                    chunk_meta=chunk_meta,
                    media_meta=media_meta,
                    score=hit["_score"]
                )

                enriched_results.append(result)

            logger.debug(f"Enriched {len(enriched_results)} search results")
            return enriched_results

        except Exception as e:
            logger.error(f"Result enrichment failed: {e}")
            return []

    async def _get_chunk_metadata(self, chunk_id: str) -> Optional[ChunkMeta]:
        """Chunk 메타데이터 조회"""
        try:
            chunk_data = await self.opensearch_service.get_chunk_meta(chunk_id)
            if chunk_data:
                return ChunkMeta(**chunk_data)
            return None
        except Exception as e:
            logger.error(f"Failed to get chunk metadata for {chunk_id}: {e}")
            return None

    async def _get_media_metadata(self, media_id: str) -> Optional[MediaMeta]:
        """Media 메타데이터 조회"""
        try:
            media_data = await self.opensearch_service.get_media_meta(media_id)
            if media_data:
                return MediaMeta(**media_data)
            return None
        except Exception as e:
            logger.error(f"Failed to get media metadata for {media_id}: {e}")
            return None

    def calculate_search_statistics(self, search_results: Dict[str, Any]) -> Dict[str, Any]:
        """검색 결과 통계 계산"""
        try:
            hits = search_results.get("hits", {})
            total = hits.get("total", {})
            
            return {
                "total_hits": total.get("value", 0),
                "max_score": hits.get("max_score", 0.0) or 0.0,
                "result_count": len(hits.get("hits", []))
            }
        except Exception as e:
            logger.error(f"Failed to calculate search statistics: {e}")
            return {
                "total_hits": 0,
                "max_score": 0.0,
                "result_count": 0
            }