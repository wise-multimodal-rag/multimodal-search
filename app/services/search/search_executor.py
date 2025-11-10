import asyncio
from typing import Any, Dict, List, Optional

from loguru import logger

from app.core.config import weighting_config
from app.services.analysis.query_analyzer import QueryAnalyzer
from app.services.search.opensearch_service import OpenSearchService


class SearchExecutor:
    """검색 실행 및 결과 통합을 전담하는 서비스"""

    def __init__(self, opensearch_service: OpenSearchService = None, query_analyzer: QueryAnalyzer = None):
        self.opensearch_service = opensearch_service or OpenSearchService()
        self.query_analyzer = query_analyzer or QueryAnalyzer()

    async def execute_expanded_search(
        self,
        expanded_queries: List[str],
        selected_element_types: List[str],
        embeddings: Dict[str, List[float]],
        max_results: int,
        expansion_result: Optional[Dict[str, Any]] = None,
        element_type_weights: Optional[Dict[str, float]] = None,
        image_caption_tags: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """확장 쿼리 검색 실행 (순차/병렬 처리 최적화)"""
        # LLM 결과에서 의존성 확인
        has_dependency = expansion_result.get("has_dependency", False) if expansion_result else False

        if has_dependency:
            logger.debug(f"Sequential search execution for {len(expanded_queries)} dependent queries")
            all_search_results = await self._execute_sequential_search(
                expanded_queries, selected_element_types, embeddings, max_results, expansion_result, element_type_weights, image_caption_tags
            )
        else:
            logger.debug(f"Parallel search execution for {len(expanded_queries)} independent queries")
            all_search_results = await self._execute_parallel_search(
                expanded_queries, selected_element_types, embeddings, max_results, element_type_weights, image_caption_tags
            )

        return self._process_search_results(all_search_results, expanded_queries, max_results)

    async def _execute_parallel_search(
        self,
        expanded_queries: List[str],
        selected_element_types: List[str],
        embeddings: Dict[str, List[float]],
        max_results: int,
        element_type_weights: Optional[Dict[str, float]] = None,
        image_caption_tags: Optional[List[str]] = None,
    ) -> List[Any]:
        """기존 병렬 검색 실행"""
        search_tasks = [
            self._execute_single_query_search(
                expanded_query, i, len(expanded_queries), selected_element_types, embeddings, max_results, element_type_weights, image_caption_tags
            )
            for i, expanded_query in enumerate(expanded_queries)
        ]

        # 모든 검색을 병렬로 실행
        return await asyncio.gather(*search_tasks, return_exceptions=True)

    async def _execute_sequential_search(
        self,
        expanded_queries: List[str],
        selected_element_types: List[str],
        embeddings: Dict[str, List[float]],
        max_results: int,
        expansion_result: Optional[Dict[str, Any]],
        element_type_weights: Optional[Dict[str, float]] = None,
        image_caption_tags: Optional[List[str]] = None,
    ) -> List[Any]:
        """순차적 의존성 처리를 위한 검색"""
        accumulated_context = {}
        all_results = []

        dependency_reason = expansion_result.get("dependency_reason", "") if expansion_result else ""
        logger.info(f"Sequential execution reason: {dependency_reason}")

        for i, query in enumerate(expanded_queries):
            # 이전 결과를 컨텍스트로 활용
            if i > 0 and accumulated_context:
                enriched_query = self.query_analyzer.enrich_query_with_context(query, accumulated_context)
                logger.debug(f"Query {i + 1} enriched with context: '{query}' → '{enriched_query}'")
            else:
                enriched_query = query

            # 단일 쿼리 검색 실행
            result = await self._execute_single_query_search(
                enriched_query, i, len(expanded_queries), selected_element_types, embeddings, max_results, element_type_weights, image_caption_tags
            )

            if not isinstance(result, Exception) and result is not None:
                all_results.append(result)
                # 다음 쿼리를 위한 컨텍스트 추출
                new_context = self.query_analyzer.extract_context_from_results(result)
                accumulated_context.update(new_context)
                logger.debug(f"Context extracted from query {i + 1}: {list(new_context.keys())}")
            else:
                logger.warning(f"Query {i + 1} failed, continuing with existing context")
                all_results.append(result)  # 실패한 결과도 포함 (후에 필터링됨)

        return all_results

    async def _execute_single_query_search(
        self,
        expanded_query: str,
        query_index: int,
        total_queries: int,
        selected_element_types: List[str],
        embeddings: Dict[str, List[float]],
        max_results: int,
        element_type_weights: Optional[Dict[str, float]] = None,
        image_caption_tags: Optional[List[str]] = None,
    ) -> Any:
        """단일 쿼리 검색 실행"""
        weight = 1.0 - (query_index * weighting_config.QUERY_WEIGHT_DECAY)  # 설정값에 따라 감소
        search_size = max_results // total_queries + (max_results % total_queries if query_index == 0 else 0)

        search_results = await self.opensearch_service.search_elements(
            query=expanded_query,
            element_types=selected_element_types,
            embeddings=embeddings,
            size=search_size,
            from_=0,
            filters=None,
            element_type_weights=element_type_weights,
            image_caption_tags=image_caption_tags,
        )

        # 쿼리별 가중치 적용
        self._apply_query_weight(search_results, weight, expanded_query)
        
        # element_type별 가중치는 OpenSearch에서 이미 적용됨 (후처리 불필요)

        return search_results

    def _apply_query_weight(self, search_results: Dict[str, Any], weight: float, expanded_query: str):
        """쿼리별 가중치 적용"""
        if search_results and isinstance(search_results, dict) and "results" in search_results:
            weighted_count = 0
            for result in search_results["results"]:
                if isinstance(result, dict) and "score" in result:
                    result["score"] *= weight  # 가중치 적용
                    result["query_used"] = expanded_query  # 어떤 쿼리로 검색됐는지 기록
                    result["query_weight_applied"] = weight  # 적용된 쿼리 가중치 기록
                    weighted_count += 1


    def _process_search_results(
        self, all_search_results: List[Any], expanded_queries: List[str], max_results: int
    ) -> Dict[str, Any]:
        """검색 결과 처리 및 검증"""
        # 예외가 발생한 결과는 필터링하고 상세 로깅
        valid_results = []
        failed_queries = []

        for i, result in enumerate(all_search_results):
            if isinstance(result, Exception):
                query = expanded_queries[i] if i < len(expanded_queries) else f"query_{i}"
                logger.warning(f"Search query {i + 1} '{query}' failed: {type(result).__name__}: {result}")
                failed_queries.append((i + 1, query, str(result)))
            elif result is None:
                query = expanded_queries[i] if i < len(expanded_queries) else f"query_{i}"
                logger.warning(f"Search query {i + 1} '{query}' returned no results")
                failed_queries.append((i + 1, query, "No results"))
            else:
                valid_results.append(result)

        # 실패 통계 로깅
        if failed_queries:
            logger.warning(f"Search failures: {len(failed_queries)}/{len(expanded_queries)} queries failed")

        # 유효한 결과가 없는 경우 처리
        if not valid_results:
            logger.error("All search queries failed")
            return {"results": [], "total_hits": 0, "max_score": 0.0, "took_ms": 0}

        # 결과 통합
        combined_results = self._combine_search_results(valid_results, max_results)

        return combined_results

    def _combine_search_results(self, all_search_results: List[Any], max_results: int) -> Dict[str, Any]:
        """검색 결과 통합"""
        if not all_search_results:
            return {"results": [], "total_hits": 0, "max_score": 0.0, "took_ms": 0}

        # 가장 좋은 결과를 기본으로 사용
        search_results = all_search_results[0] if all_search_results else None

        if len(all_search_results) > 1:
            # 여러 검색 결과를 통합
            combined_results = []
            for sr in all_search_results:
                if sr and isinstance(sr, dict) and "results" in sr:
                    combined_results.extend(sr["results"])

            # 점수순으로 정렬하고 중복 제거
            combined_results.sort(key=lambda x: x.get("score", 0), reverse=True)
            unique_results = []
            seen_ids = set()
            for result in combined_results:
                result_id = result.get("id") or result.get("_id") or result.get("element_id")
                if result_id and result_id not in seen_ids:
                    seen_ids.add(result_id)
                    unique_results.append(result)
                    if len(unique_results) >= max_results:
                        break

            # 통합된 결과로 search_results 업데이트
            if search_results and isinstance(search_results, dict):
                search_results["results"] = unique_results[:max_results]
                search_results["total_hits"] = len(unique_results)
                if unique_results:
                    search_results["max_score"] = max(r.get("score", 0) for r in unique_results)
            else:
                # search_results가 None이거나 잘못된 형태인 경우 기본 구조 생성
                search_results = {
                    "results": unique_results[:max_results],
                    "total_hits": len(unique_results),
                    "max_score": max(r.get("score", 0) for r in unique_results) if unique_results else 0.0,
                    "took_ms": 0,
                }

        # search_results가 여전히 None인 경우 기본 구조 반환
        if not search_results:
            search_results = {"results": [], "total_hits": 0, "max_score": 0.0, "took_ms": 0}

        return search_results
