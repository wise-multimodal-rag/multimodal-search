import asyncio
from typing import List, Dict, Optional, Any

from loguru import logger

from app.config.config import settings
from app.config.weights import weighting_config
from app.clients.reranker_client import RerankerClient
from app.src.search.opensearch import OpenSearchService
from app.src.search.analyzers import QueryAnalyzer


class SearchExecutor:
    """검색 실행 및 결과 통합을 전담하는 서비스

    RERANKER_ENABLED=true (기본):
        기존 하이브리드 검색 oversample → Qwen3-Reranker 재정렬 → 모달리티 보강 슬롯
    RERANKER_ENABLED=false:
        기존 하이브리드 검색 (BM25+Vector boost 합산) 그대로 동작
    """

    def __init__(
        self,
        opensearch_service: OpenSearchService = None,
        query_analyzer: QueryAnalyzer = None,
        reranker_client: Optional[RerankerClient] = None,
    ):
        self.opensearch_service = opensearch_service or OpenSearchService()
        self.query_analyzer = query_analyzer or QueryAnalyzer()
        self.reranker_client = reranker_client

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
        """확장 쿼리 검색 실행

        RERANKER_ENABLED=true + RerankerClient available:
            oversample 검색 후 Reranker 재정렬 + 모달리티 보강
        그 외:
            기존 하이브리드 검색
        """
        if settings.reranker_enabled and self.reranker_client and self.reranker_client.available:
            return await self._execute_with_reranker(
                expanded_queries, selected_element_types, embeddings,
                max_results, expansion_result, element_type_weights, image_caption_tags
            )
        else:
            return await self._execute_hybrid_search(
                expanded_queries, selected_element_types, embeddings,
                max_results, expansion_result, element_type_weights, image_caption_tags
            )

    # =========================================================================
    # Reranker 적용 검색 (기본)
    # =========================================================================

    async def _execute_with_reranker(
            self,
            expanded_queries: List[str],
            selected_element_types: List[str],
            embeddings: Dict[str, List[float]],
            max_results: int,
            expansion_result: Optional[Dict[str, Any]] = None,
            element_type_weights: Optional[Dict[str, float]] = None,
            image_caption_tags: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Oversample 검색 후 Reranker 재정렬 + 모달리티 보강 슬롯"""
        oversample_size = max_results * settings.reranker_oversample

        # 1. 기존 하이브리드 검색으로 oversample
        base_results = await self._execute_hybrid_search(
            expanded_queries, selected_element_types, embeddings,
            oversample_size, expansion_result, element_type_weights, image_caption_tags
        )

        results = base_results.get("results", [])
        if not results:
            return base_results

        # 2. 전체 결과(모든 모달리티)를 Reranker에 전달
        query_text = " ".join(expanded_queries)
        reranked_results = await self._apply_reranking(
            query=query_text,
            results=results,
            max_results=oversample_size,
        )

        # 3. 모달리티 보강 슬롯 적용 (RERANKER_MODALITY_BOOST=true일 때)
        if settings.reranker_modality_boost:
            final_results = self._apply_modality_boost(reranked_results, results, max_results)
        else:
            final_results = reranked_results[:max_results]

        return {
            "results": final_results,
            "total_hits": base_results.get("total_hits", len(final_results)),
            "max_score": max(r.get("score", 0) for r in final_results) if final_results else 0.0,
            "took_ms": base_results.get("took_ms", 0),
            "reranker_applied": any(r.get("reranker_score") is not None for r in final_results),
        }

    # =========================================================================
    # Reranker 호출
    # =========================================================================

    async def _apply_reranking(
            self,
            query: str,
            results: List[Dict[str, Any]],
            max_results: int,
    ) -> List[Dict[str, Any]]:
        """Reranker를 적용하여 결과를 재정렬합니다.

        실패 시 원본 순서를 유지합니다 (graceful degradation).
        """
        if not self.reranker_client or not results:
            return results[:max_results]

        # Reranker에 보낼 문서 구성
        documents = []
        for r in results:
            content = r.get("content", "") or ""
            # 이미지/미디어: URL 대신 설명 텍스트를 Reranker에 전달
            if content.startswith("http"):
                # 우선순위: description > 같은 청크 라벨 > 파일명
                content = (
                    r.get("description")
                    or r.get("chunk_label")
                    or r.get("media_title")
                    or content
                )
            doc_id = r.get("element_id", r.get("id", ""))
            documents.append({"id": doc_id, "content": content[:1000]})

        # Reranker 호출
        reranker_results = await self.reranker_client.rerank(
            query=query,
            documents=documents,
            top_k=min(max_results, len(documents)),
        )

        if reranker_results is None:
            logger.warning("Reranker failed, using original order (graceful degradation)")
            return results[:max_results]

        # Reranker 점수로 재정렬
        reranked = []
        for rr in reranker_results:
            idx = rr["index"]
            if idx < len(results):
                result = results[idx].copy()
                result["reranker_score"] = rr["score"]
                result["original_score"] = result.get("score", 0.0)
                result["score"] = rr["score"]
                if "score_breakdown" not in result:
                    result["score_breakdown"] = {}
                result["score_breakdown"]["reranker"] = {
                    "score": rr["score"],
                    "model": "qwen3-reranker",
                }
                reranked.append(result)

        # Reranker가 반환하지 않은 결과는 뒤에 추가
        reranked_indices = set(rr["index"] for rr in reranker_results)
        for i, result in enumerate(results):
            if i not in reranked_indices:
                reranked.append(result)

        return reranked[:max_results]

    # =========================================================================
    # 모달리티 보강 슬롯
    # =========================================================================

    def _apply_modality_boost(
            self,
            reranked_results: List[Dict[str, Any]],
            oversample_results: List[Dict[str, Any]],
            max_results: int,
    ) -> List[Dict[str, Any]]:
        """Reranker 재정렬 후 부족한 모달리티를 보강합니다.

        Reranker가 텍스트 위주로 정렬하더라도, oversample 후보에 존재하는
        다른 모달리티(image, video, audio) 결과를 최소한 보장합니다.
        """
        # 상위 max_results개에서 모달리티 분포 확인
        top_results = reranked_results[:max_results]
        top_modalities = set(r.get("modality") for r in top_results if r.get("modality"))

        # 시스템 지원 모달리티
        all_supported_modalities = {"text", "image", "video", "audio"}

        # oversample 후보에 존재하는 모달리티 확인
        available_modalities = set(r.get("modality") for r in oversample_results if r.get("modality"))

        # 보강 대상: oversample에 있지만 top_results에 빠진 모달리티
        missing_modalities = (available_modalities & all_supported_modalities) - top_modalities

        if not missing_modalities:
            return top_results

        # 보강 슬롯 수 계산: 부족 모달리티당 최소 1개, 상한 max_results의 30%
        boost_slots = min(
            len(missing_modalities) * 2,
            max_results * 3 // 10,
        )

        # 보강할 문서 수집 (reranked_results에서 max_results 이후 + oversample에서)
        seen_ids = set(
            r.get("element_id") or r.get("id") or r.get("_id")
            for r in top_results
        )

        boost_candidates = []
        # reranked에서 max_results 밖에 있는 부족 모달리티 문서
        for r in reranked_results[max_results:]:
            if r.get("modality") in missing_modalities:
                rid = r.get("element_id") or r.get("id") or r.get("_id")
                if rid and rid not in seen_ids:
                    boost_candidates.append(r)
                    seen_ids.add(rid)

        # oversample 원본에서도 추가 탐색
        if len(boost_candidates) < boost_slots:
            for r in oversample_results:
                if r.get("modality") in missing_modalities:
                    rid = r.get("element_id") or r.get("id") or r.get("_id")
                    if rid and rid not in seen_ids:
                        boost_candidates.append(r)
                        seen_ids.add(rid)
                        if len(boost_candidates) >= boost_slots:
                            break

        if not boost_candidates:
            return top_results

        # 메인 슬롯 축소 + 보강 슬롯 추가
        actual_boost = min(len(boost_candidates), boost_slots)
        main_slots = max_results - actual_boost
        final_results = top_results[:main_slots] + boost_candidates[:actual_boost]

        # 점수순 최종 정렬
        final_results.sort(key=lambda x: x.get("score", 0), reverse=True)

        logger.info(
            f"Modality boost: added {actual_boost} results for missing modalities {missing_modalities} "
            f"(main={main_slots}, boost={actual_boost})"
        )

        return final_results[:max_results]

    # =========================================================================
    # 기존 하이브리드 검색 (RERANKER_ENABLED=false 시 사용)
    # =========================================================================

    async def _execute_hybrid_search(
            self,
            expanded_queries: List[str],
            selected_element_types: List[str],
            embeddings: Dict[str, List[float]],
            max_results: int,
            expansion_result: Optional[Dict[str, Any]] = None,
            element_type_weights: Optional[Dict[str, float]] = None,
            image_caption_tags: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """기존 하이브리드 검색 (BM25+Vector boost 합산 + cross-modal)"""
        has_dependency = expansion_result.get("has_dependency", False) if expansion_result else False

        if has_dependency:
            logger.debug(f"Sequential search execution for {len(expanded_queries)} dependent queries")
            all_search_results = await self._execute_sequential_search(
                expanded_queries, selected_element_types, embeddings, max_results, expansion_result,
                element_type_weights, image_caption_tags
            )
        else:
            logger.debug(f"Parallel search execution for {len(expanded_queries)} independent queries")
            all_search_results = await self._execute_parallel_search(
                expanded_queries, selected_element_types, embeddings, max_results, element_type_weights,
                image_caption_tags
            )

        # Cross-modal: 별도의 벡터 전용 cross-modal 검색
        if embeddings:
            cross_modal_size = max(3, max_results // 3)
            cross_modal_results = await self.opensearch_service.search_cross_modal(
                embeddings=embeddings,
                element_types=selected_element_types,
                size=cross_modal_size,
                element_type_weights=element_type_weights,
            )
            if cross_modal_results and cross_modal_results.get("results"):
                all_search_results.append(cross_modal_results)
                logger.info(f"Cross-modal search added {len(cross_modal_results['results'])} results")

        return self._process_search_results(all_search_results, expanded_queries, max_results)

    # =========================================================================
    # 내부 검색 메서드
    # =========================================================================

    async def _execute_parallel_search(
            self,
            expanded_queries: List[str],
            selected_element_types: List[str],
            embeddings: Dict[str, List[float]],
            max_results: int,
            element_type_weights: Optional[Dict[str, float]] = None,
            image_caption_tags: Optional[List[str]] = None,
    ) -> List[Any]:
        """병렬 검색 실행"""
        search_tasks = [
            self._execute_single_query_search(
                expanded_query, i, len(expanded_queries), selected_element_types, embeddings, max_results,
                element_type_weights, image_caption_tags
            )
            for i, expanded_query in enumerate(expanded_queries)
        ]
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
            if i > 0 and accumulated_context:
                enriched_query = self.query_analyzer.enrich_query_with_context(query, accumulated_context)
                logger.debug(f"Query {i + 1} enriched with context: '{query}' → '{enriched_query}'")
            else:
                enriched_query = query

            result = await self._execute_single_query_search(
                enriched_query, i, len(expanded_queries), selected_element_types, embeddings, max_results,
                element_type_weights, image_caption_tags
            )

            if not isinstance(result, Exception) and result is not None:
                all_results.append(result)
                new_context = self.query_analyzer.extract_context_from_results(result)
                accumulated_context.update(new_context)
                logger.debug(f"Context extracted from query {i + 1}: {list(new_context.keys())}")
            else:
                logger.warning(f"Query {i + 1} failed, continuing with existing context")
                all_results.append(result)

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
        weight = 1.0 - (query_index * weighting_config.QUERY_WEIGHT_DECAY)
        base_size = max_results // total_queries + (max_results % total_queries if query_index == 0 else 0)

        if embeddings:
            search_size = min(base_size * 3, max_results)
        else:
            search_size = base_size

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

        self._apply_query_weight(search_results, weight, expanded_query)
        return search_results

    def _apply_query_weight(self, search_results: Dict[str, Any], weight: float, expanded_query: str):
        """쿼리별 가중치 적용"""
        if search_results and isinstance(search_results, dict) and "results" in search_results:
            for result in search_results["results"]:
                if isinstance(result, dict) and "score" in result:
                    result["score"] *= weight
                    result["query_used"] = expanded_query
                    result["query_weight_applied"] = weight

    def _process_search_results(
            self, all_search_results: List[Any], expanded_queries: List[str], max_results: int
    ) -> Dict[str, Any]:
        """검색 결과 처리 및 검증"""
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

        if failed_queries:
            logger.warning(f"Search failures: {len(failed_queries)}/{len(expanded_queries)} queries failed")

        if not valid_results:
            logger.error("All search queries failed")
            return {"results": [], "total_hits": 0, "max_score": 0.0, "took_ms": 0}

        return self._combine_search_results(valid_results, max_results)

    def _combine_search_results(self, all_search_results: List[Any], max_results: int) -> Dict[str, Any]:
        """검색 결과 통합 (cross-modal 점수 정규화 포함)"""
        if not all_search_results:
            return {"results": [], "total_hits": 0, "max_score": 0.0, "took_ms": 0}

        search_results = all_search_results[0] if all_search_results else None

        if len(all_search_results) > 1:
            main_results = []
            cross_modal_results = []

            for sr in all_search_results:
                if sr and isinstance(sr, dict) and "results" in sr:
                    for r in sr["results"]:
                        if r.get("_cross_modal"):
                            cross_modal_results.append(r)
                        else:
                            main_results.append(r)

            # Cross-modal 점수 정규화
            if cross_modal_results and main_results:
                main_scores = sorted([r.get("score", 0) for r in main_results if r.get("score", 0) > 0],
                                     reverse=True)
                if main_scores:
                    target_rank = max(0, len(main_scores) // 3)
                    target_score = main_scores[target_rank]
                    cross_max = max(r.get("score", 0) for r in cross_modal_results)

                    if cross_max > 0:
                        scale_factor = target_score / cross_max
                        for r in cross_modal_results:
                            raw_score = r.get("score", 0.0)
                            r["original_score"] = raw_score
                            r["score"] = raw_score * scale_factor

                            if r.get("score_breakdown"):
                                r["score_breakdown"]["normalized_score"] = raw_score * scale_factor
                                r["score_breakdown"]["normalization"] = {
                                    "raw_vector_score": raw_score,
                                    "scale_factor": round(scale_factor, 2),
                                    "final_score": round(raw_score * scale_factor, 4),
                                    "method": "cross-modal score normalization (상위 1/3 target)",
                                }
                                r["score_breakdown"]["total_score"] = raw_score * scale_factor

                        logger.info(
                            f"Cross-modal score normalization: scale={scale_factor:.2f} "
                            f"(target_score={target_score:.2f}, cross_max={cross_max:.2f})")

            # 메인 결과 정렬 + 중복 제거
            main_results.sort(key=lambda x: x.get("score", 0), reverse=True)
            unique_main = []
            seen_ids = set()
            for result in main_results:
                result_id = result.get("id") or result.get("_id") or result.get("element_id")
                if result_id and result_id not in seen_ids:
                    seen_ids.add(result_id)
                    unique_main.append(result)

            # Cross-modal 슬롯 할당
            main_modalities = [r.get("modality") for r in unique_main]
            main_modality_set = set(main_modalities)
            all_supported_modalities = {"text", "image"}
            missing_modalities = all_supported_modalities - main_modality_set

            if missing_modalities:
                cross_modal_slots = min(
                    len(cross_modal_results),
                    max(len(missing_modalities), 2),
                    max_results * 3 // 10
                )
            else:
                cross_modal_slots = min(len(cross_modal_results), max(2, max_results // 4))

            main_slots = max_results - cross_modal_slots
            unique_main = unique_main[:main_slots]

            # Cross-modal 결과 우선순위
            cross_modal_results.sort(key=lambda x: x.get("score", 0), reverse=True)
            cross_underrepresented = [r for r in cross_modal_results if r.get("modality") in missing_modalities]
            cross_others = [r for r in cross_modal_results if r.get("modality") not in missing_modalities]
            prioritized_cross = cross_underrepresented + cross_others

            unique_cross = []
            for result in prioritized_cross:
                result_id = result.get("id") or result.get("_id") or result.get("element_id")
                if result_id and result_id not in seen_ids:
                    seen_ids.add(result_id)
                    unique_cross.append(result)
                    if len(unique_cross) >= cross_modal_slots:
                        break

            unique_results = unique_main + unique_cross
            unique_results.sort(key=lambda x: x.get("score", 0), reverse=True)

            if unique_cross:
                cross_modalities = set(r.get("modality") for r in unique_cross)
                logger.info(
                    f"Cross-modal slots: {len(unique_cross)}/{cross_modal_slots} "
                    f"(main: {len(unique_main)}/{main_slots}, "
                    f"missing_modalities: {missing_modalities or 'none'}, "
                    f"cross_modalities_filled: {cross_modalities})")

            if search_results and isinstance(search_results, dict):
                search_results["results"] = unique_results[:max_results]
                search_results["total_hits"] = len(unique_results)
                if unique_results:
                    search_results["max_score"] = max(r.get("score", 0) for r in unique_results)
            else:
                search_results = {
                    "results": unique_results[:max_results],
                    "total_hits": len(unique_results),
                    "max_score": max(r.get("score", 0) for r in unique_results) if unique_results else 0.0,
                    "took_ms": 0,
                }

        if not search_results:
            search_results = {"results": [], "total_hits": 0, "max_score": 0.0, "took_ms": 0}

        return search_results
