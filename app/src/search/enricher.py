import asyncio
import traceback
from typing import Dict, Any, List, Optional

from loguru import logger

from app.api.schemas import SearchResult, Element, ChunkMeta, MediaMeta
from app.src.search.opensearch import OpenSearchService


class ResultEnricher:
    """검색 결과 enrichment를 담당하는 서비스"""

    def __init__(self, opensearch_service: OpenSearchService = None):
        self.opensearch_service = opensearch_service or OpenSearchService()

    async def enrich_search_results(
            self, search_results: Dict[str, Any], include_chunk_meta: bool, include_media_meta: bool
    ) -> List[SearchResult]:
        """검색 결과에 chunk 및 media 메타데이터 추가"""
        enriched_results = []

        logger.info(f"Starting enrich_search_results with {len(search_results)} keys")
        logger.info(f"Search results structure: {list(search_results.keys())}")

        try:
            # 데이터 구조 확인 및 정규화
            if "hits" in search_results and "hits" in search_results["hits"]:
                # OpenSearch 원본 구조
                results_data = search_results["hits"]["hits"]
            elif "results" in search_results:
                # 내부 변환된 구조
                results_data = search_results["results"]
            else:
                logger.warning(f"Unknown search results structure: {list(search_results.keys())}")
                return []

            # 전체 결과에 대해 병렬 처리

            enrichment_tasks = [
                self._enrich_single_result(item, include_chunk_meta, include_media_meta) for item in results_data
            ]

            enriched_results = await asyncio.gather(*enrichment_tasks, return_exceptions=True)

            # 예외 처리 및 필터링
            valid_results = []
            for i, result in enumerate(enriched_results):
                if isinstance(result, Exception):
                    logger.warning(f"Failed to enrich result {i}: {result}")
                elif result:
                    valid_results.append(result)

            return valid_results

        except Exception as e:

            logger.error(f"Result enrichment failed: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            logger.error(
                f"Search results structure: {list(search_results.keys()) if isinstance(search_results, dict) else type(search_results)}"
            )
            return []

    async def _enrich_single_result(
            self, item: Dict[str, Any], include_chunk_meta: bool, include_media_meta: bool
    ) -> Optional[SearchResult]:
        """단일 검색 결과 enrichment"""
        try:
            # 데이터 구조에 따라 element_data와 score 추출
            if "_source" in item:
                # OpenSearch 원본 형태
                element_data = item["_source"]
                score = item.get("_score", 0.0)
                original_score = item.get("_original_score")
                score_breakdown = item.get("_explanation")
            else:
                # 이미 변환된 형태
                element_data = item
                score = item.get("score", 0.0)
                original_score = item.get("original_score")
                score_breakdown = item.get("score_breakdown")

            element = Element(**element_data)

            # 메타데이터 병렬 조회

            metadata_tasks = []

            if include_chunk_meta:
                metadata_tasks.append(self._get_chunk_metadata(element.chunk_id))
            else:
                metadata_tasks.append(asyncio.create_task(asyncio.sleep(0, result=None)))

            if include_media_meta:
                metadata_tasks.append(self._get_media_metadata(element.media_id))
            else:
                metadata_tasks.append(asyncio.create_task(asyncio.sleep(0, result=None)))

            # 병렬 실행
            chunk_meta, media_meta = await asyncio.gather(*metadata_tasks, return_exceptions=True)

            # 예외 처리
            if isinstance(chunk_meta, Exception):
                logger.warning(f"Failed to get chunk metadata for {element.chunk_id}: {chunk_meta}")
                chunk_meta = None

            if isinstance(media_meta, Exception):
                logger.warning(f"Failed to get media metadata for {element.media_id}: {media_meta}")
                media_meta = None

            return SearchResult(
                element=element, chunk_meta=chunk_meta, media_meta=media_meta, score=score,
                original_score=original_score, score_breakdown=score_breakdown
            )

        except Exception as e:
            logger.error(f"Failed to enrich single result: {e}")
            return None

    async def _get_chunk_metadata(self, chunk_id: str) -> Optional[ChunkMeta]:
        """Chunk 메타데이터 조회"""
        try:
            chunk_data = await self.opensearch_service.get_chunk_meta(chunk_id)
            if chunk_data:
                return ChunkMeta(**chunk_data)
            return None
        except Exception as e:
            logger.warning(f"Failed to get chunk metadata for {chunk_id}: {e}")
            return None

    async def _get_media_metadata(self, media_id: str) -> Optional[MediaMeta]:
        """Media 메타데이터 조회"""
        try:
            media_data = await self.opensearch_service.get_media_meta(media_id)
            if media_data:
                # Handle None values for required fields by providing defaults
                media_data = {
                    **media_data,
                    'media_type': media_data.get('media_type') or 'other',
                    'mime_type': media_data.get('mime_type') or 'application/octet-stream',
                    'source_uri': media_data.get('source_uri') or f'unknown://{media_id}',
                }
                return MediaMeta(**media_data)
            return None
        except Exception as e:
            logger.warning(f"Failed to get media metadata for {media_id}: {e}")
            return None

    def calculate_search_statistics(self, search_results: Dict[str, Any]) -> Dict[str, Any]:
        """검색 결과 통계 계산"""
        logger.info(f"Calculating search statistics for: {list(search_results.keys())}")
        try:
            # 데이터 구조 확인 및 정규화
            if "hits" in search_results and "hits" in search_results["hits"]:
                # OpenSearch 원본 구조
                hits = search_results["hits"]
                total = hits.get("total", {})
                return {
                    "total_hits": total.get("value", 0),
                    "max_score": hits.get("max_score", 0.0) or 0.0,
                    "result_count": len(hits.get("hits", [])),
                }
            elif "results" in search_results:
                # 내부 변환된 구조
                return {
                    "total_hits": search_results.get("total_hits", 0),
                    "max_score": search_results.get("max_score", 0.0) or 0.0,
                    "result_count": len(search_results.get("results", [])),
                }
            else:
                return {"total_hits": 0, "max_score": 0.0, "result_count": 0}
        except Exception as e:
            logger.error(f"Failed to calculate search statistics: {e}")
            return {"total_hits": 0, "max_score": 0.0, "result_count": 0}
