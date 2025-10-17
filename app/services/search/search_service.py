from typing import Optional

from fastapi import UploadFile
from loguru import logger

from app.models.opensearch import SearchResponse
from app.services.analysis.multimodal_feature_extractor import \
    MultimodalFeatureExtractor
from app.services.analysis.query_analyzer import QueryAnalyzer
from app.services.embeddings.embedding_service import EmbeddingService
from app.services.processing.input_processor import InputProcessor
from app.services.search.opensearch_service import OpenSearchService
from app.services.search.result_enricher import ResultEnricher


class SearchService:
    """메인 검색 오케스트레이션 서비스"""

    def __init__(
            self,
            opensearch_service: OpenSearchService = None,
            input_processor: InputProcessor = None,
            feature_extractor: MultimodalFeatureExtractor = None,
            query_analyzer: QueryAnalyzer = None,
            embedding_service: EmbeddingService = None,
            result_enricher: ResultEnricher = None
    ):
        # Define available element types for the system
        self.available_element_types = [
            # Text modality
            "paragraph", "title", "summary", "stt", "caption", "scene",
            "ocr", "table", "translation",
            # Image modality  
            "origin", "cropped", "detected_object", "chart", "diagram",
            "keyframe", "thumbnail",
            # Video modality
            "clip", "segment",
            # Audio modality
            "speech", "music", "sound_effect", "ambient"
        ]

        # Use dependency injection or fallback to defaults
        self.opensearch_service = opensearch_service or OpenSearchService()
        self.input_processor = input_processor or InputProcessor()
        self.feature_extractor = feature_extractor or MultimodalFeatureExtractor()
        self.query_analyzer = query_analyzer or QueryAnalyzer()
        self.embedding_service = embedding_service or EmbeddingService()
        self.result_enricher = result_enricher or ResultEnricher(self.opensearch_service)

    async def search_multimodal(
            self,
            text_query: Optional[str] = None,
            image_file: Optional[UploadFile] = None,
            video_file: Optional[UploadFile] = None,
            audio_file: Optional[UploadFile] = None,
            include_chunk_meta: bool = True,
            include_media_meta: bool = True,
            max_results: int = 10
    ) -> SearchResponse:
        """멀티모달 검색 오케스트레이션"""
        logger.info("Processing multimodal search request")
        start_time = self._get_current_time_ms()

        try:
            # 입력 검증
            if not self.input_processor.validate_inputs(text_query, image_file, video_file, audio_file):
                raise ValueError("최소 하나의 입력(텍스트, 이미지, 비디오, 오디오)이 필요합니다")

            input_types = self.input_processor.get_input_types(text_query, image_file, video_file, audio_file)
            logger.info(f"Multimodal search request with inputs: {', '.join(input_types)}")

            # Step 1: 멀티모달 입력 처리
            logger.info("[Step 1: 멀티모달 입력 처리] Processing multimodal inputs")
            modalities_data = await self.input_processor.process_multimodal_inputs(
                text_query, image_file, video_file, audio_file
            )

            # Step 2: 쿼리 확장 및 의도 분석 (복잡한 로직이므로 함수 분리)
            query_analysis, expanded_queries = await self._expand_and_analyze_query(text_query)

            # Step 3: 멀티모달 특징 추출
            logger.info("[Step 3: 멀티모달 특징 추출] Extracting multimodal features")
            extracted_features = await self.feature_extractor.extract_features(modalities_data,
                                                                               query_analysis["selected_element_types"])

            # Step 4: 임베딩 생성
            logger.info("[Step 4: 임베딩 생성] Generating embeddings")
            embeddings = await self.embedding_service.generate_multimodal_embeddings(
                modalities_data, extracted_features
            )

            # Step 5: 확장 쿼리 검색 실행 (복잡한 로직이므로 함수 분리)
            search_results = await self._execute_expanded_search(
                expanded_queries, query_analysis["selected_element_types"], embeddings, max_results
            )

            # Step 6: 결과 enrichment
            logger.info("[Step 6: 결과 enrichment] Enriching search results")
            enriched_results = await self.result_enricher.enrich_search_results(
                search_results, include_chunk_meta, include_media_meta
            )

            # Step 7: 응답 생성
            return self._generate_search_response(
                text_query, input_types, expanded_queries, query_analysis,
                enriched_results, search_results, start_time
            )

        except Exception as e:
            logger.error(f"Multimodal search failed: {e}")
            raise

    async def _expand_and_analyze_query(self, text_query):
        """Step 2: 쿼리 확장 및 의도 분석"""
        logger.info("[Step 2: 쿼리 확장 및 의도 분석] Expanding query and analyzing intent")

        if text_query:
            # 쿼리 확장
            expanded_queries, expansion_result = await self._expand_query(text_query)
            # 의도 분석
            query_analysis = await self._analyze_query_intent(expanded_queries, expansion_result)
        else:
            logger.warning("[Step 2: 쿼리 분석] No text query provided. Using all element types as fallback.")
            query_analysis = self.query_analyzer.create_default_query_analysis(self.available_element_types)
            expanded_queries = ["multimodal search"]

        selected_element_types = query_analysis["selected_element_types"]
        logger.info(f"[Step 2-2: 의도 분석] Selected element types: {selected_element_types}")
        logger.info(f"[Step 2: 완료] Final expanded queries: {expanded_queries}")

        return query_analysis, expanded_queries

    async def _expand_query(self, text_query):
        """쿼리 확장 수행"""
        logger.info(f"[Step 2-1: 쿼리 확장] Expanding query: '{text_query}'")
        expansion_result = await self.query_analyzer.expand_query(text_query)

        if expansion_result and expansion_result.get("final_queries"):
            final_queries = expansion_result["final_queries"][:3]  # 상위 3개 사용
            expanded_queries = [q["query"] for q in final_queries]

            self._log_expansion_results(final_queries, expansion_result)
            return expanded_queries, expansion_result
        else:
            logger.warning(f"[Step 2-1: 쿼리 확장] ❌ Query expansion failed, using original query: '{text_query}'")
            return [text_query], None

    def _log_expansion_results(self, final_queries, expansion_result):
        """쿼리 확장 결과 로깅"""
        logger.info(f"[Step 2-1: 쿼리 확장] ✅ Generated {len(final_queries)} expanded queries:")
        for i, query_info in enumerate(final_queries, 1):
            priority = query_info.get("priority", i)
            confidence = query_info.get("confidence", 0.0)
            strategy = query_info.get("search_strategy", "unknown")
            query_text = query_info.get("query", "")
            logger.info(f"  [{priority}] '{query_text}' (신뢰도: {confidence:.2f}, 전략: {strategy})")

        # 적용된 기법 로깅
        applied_techniques = expansion_result.get("applied_techniques", [])
        if applied_techniques:
            logger.info(f"[Step 2-1: 적용 기법] 🔧 {', '.join(applied_techniques)}")

        # 분해 적용 여부 로깅
        decomposition = expansion_result.get("decomposition", {})
        if decomposition.get("applied", False):
            main_concepts = decomposition.get("main_concepts", [])
            logger.info(f"[Step 2-1: 쿼리 분해] ✂️  주요 개념: {', '.join(main_concepts)}")
        else:
            reason = decomposition.get("reason", "분해 불필요")
            logger.info(f"[Step 2-1: 쿼리 분해] ⏭️  건너뜀 - {reason}")

        # 쿼리 분석 정보 로깅
        if expansion_result.get("query_analysis"):
            analysis = expansion_result["query_analysis"]
            intent = analysis.get("intent", "")
            complexity = analysis.get("complexity", "")
            domain = analysis.get("domain", "")
            if intent or complexity or domain:
                logger.info(f"[Step 2-1: 쿼리 분석] 📝 의도: {intent}, 복잡도: {complexity}, 도메인: {domain}")

    async def _analyze_query_intent(self, expanded_queries, expansion_result):
        """의도 분석 수행"""
        logger.info("[Step 2-2: 의도 분석] Analyzing intent based on expanded queries")
        primary_query = expanded_queries[0] if expanded_queries else "multimodal search"

        query_analysis = await self.query_analyzer.analyze_query_intent(
            primary_query, self.available_element_types)

        if not query_analysis:
            logger.warning(
                f"[Step 2-2: 의도 분석] Query analysis failed for expanded query: '{primary_query}'. Falling back to default behavior.")
            query_analysis = self.query_analyzer.create_default_query_analysis(
                self.available_element_types, "Query analysis failed"
            )

        # 확장 정보를 쿼리 분석에 추가
        if expansion_result:
            query_analysis["expansion_analysis"] = expansion_result.get("query_analysis", {})
            query_analysis["expansion_used"] = len(expanded_queries) > 1

        return query_analysis

    async def _execute_expanded_search(self, expanded_queries, selected_element_types, embeddings, max_results):
        """Step 5: 확장 쿼리 검색 실행"""
        logger.info(f"[Step 5: OpenSearch 검색 실행] Executing search with {len(expanded_queries)} expanded queries")

        # 각 확장된 쿼리로 검색 수행
        all_search_results = []
        for i, expanded_query in enumerate(expanded_queries):
            search_result = await self._execute_single_query_search(
                expanded_query, i, len(expanded_queries), selected_element_types, embeddings, max_results
            )
            all_search_results.append(search_result)

        # 결과 통합
        combined_results = self._combine_search_results(all_search_results, max_results)
        self._log_final_search_results(combined_results, len(expanded_queries))

        return combined_results

    async def _execute_single_query_search(self, expanded_query, query_index, total_queries,
                                           selected_element_types, embeddings, max_results):
        """단일 쿼리 검색 실행"""
        weight = 1.0 - (query_index * 0.1)  # 0.1씩 감소
        search_size = max_results // total_queries + (max_results % total_queries if query_index == 0 else 0)

        logger.info(
            f"[Step 5: 검색 {query_index + 1}/{total_queries}] 🔍 Query: '{expanded_query}' (가중치: {weight:.1f}, size: {search_size})")

        search_results = await self.opensearch_service.search_elements(
            query=expanded_query,
            element_types=selected_element_types,
            embeddings=embeddings,
            size=search_size,
            from_=0,
            filters=None
        )

        # 검색 결과 로깅
        if search_results and isinstance(search_results, dict):
            total_hits = search_results.get('total_hits', 0)
            max_score = search_results.get('max_score', 0.0)
            results_count = len(search_results.get('results', []))
            logger.info(
                f"[Step 5: 검색 {query_index + 1} 결과] 📊 {results_count}개 결과 (총 {total_hits}개 히트, 최고점수: {max_score:.4f})")

        # 가중치 적용
        self._apply_query_weight(search_results, weight, expanded_query)

        return search_results

    def _apply_query_weight(self, search_results, weight, expanded_query):
        """쿼리별 가중치 적용"""
        if search_results and isinstance(search_results, dict) and 'results' in search_results:
            weighted_count = 0
            for result in search_results['results']:
                if isinstance(result, dict) and 'score' in result:
                    result['score'] *= weight  # 가중치 적용
                    result['query_used'] = expanded_query  # 어떤 쿼리로 검색됐는지 기록
                    result['weight_applied'] = weight  # 적용된 가중치 기록
                    weighted_count += 1

            if weighted_count > 0:
                logger.info(f"[Step 5: 가중치 적용] ⚖️  {weighted_count}개 결과에 가중치 {weight:.1f} 적용 완료")

    def _combine_search_results(self, all_search_results, max_results):
        """검색 결과 통합"""
        if not all_search_results:
            return None

        # 가장 좋은 결과를 기본으로 사용
        search_results = all_search_results[0] if all_search_results else None

        if len(all_search_results) > 1:
            # 여러 검색 결과를 통합
            combined_results = []
            for sr in all_search_results:
                if sr and isinstance(sr, dict) and 'results' in sr:
                    combined_results.extend(sr['results'])

            # 점수순으로 정렬하고 중복 제거
            combined_results.sort(key=lambda x: x.get('score', 0), reverse=True)
            unique_results = []
            seen_ids = set()
            for result in combined_results:
                result_id = result.get('id') or result.get('_id') or result.get('element_id')
                if result_id and result_id not in seen_ids:
                    seen_ids.add(result_id)
                    unique_results.append(result)
                    if len(unique_results) >= max_results:
                        break

            # 통합된 결과로 search_results 업데이트
            if search_results and isinstance(search_results, dict):
                search_results['results'] = unique_results[:max_results]
                search_results['total_hits'] = len(unique_results)
                if unique_results:
                    search_results['max_score'] = max(r.get('score', 0) for r in unique_results)

        return search_results

    def _log_final_search_results(self, search_results, query_count):
        """최종 검색 결과 로깅"""
        if search_results and isinstance(search_results, dict):
            final_total = search_results.get('total_hits', 0)
            final_count = len(search_results.get('results', []))
            final_max_score = search_results.get('max_score', 0.0)
            logger.info(
                f"[Step 5: 검색 완료] 🎯 통합 완료: {final_count}개 최종 결과 (총 히트: {final_total}, 최고점수: {final_max_score:.4f})")

            # 상위 3개 결과의 쿼리 사용 현황 로깅
            if 'results' in search_results and search_results['results']:
                logger.info("[Step 5: 상위 결과] 📋 Top 3 results:")
                for idx, result in enumerate(search_results['results'][:3], 1):
                    if isinstance(result, dict):
                        element_id = result.get('element_id', result.get('id', 'unknown'))
                        score = result.get('score', 0.0)
                        query_used = result.get('query_used', 'unknown')[:30] + '...' if len(
                            result.get('query_used', '')) > 30 else result.get('query_used', 'unknown')
                        weight = result.get('weight_applied', 1.0)
                        logger.info(f"  {idx}. {element_id} (점수: {score:.4f}, 가중치: {weight:.1f}, 쿼리: '{query_used}')")
        else:
            logger.warning(f"[Step 5: 검색 완료] ⚠️  No valid search results from {query_count} queries")

    def _generate_search_response(self, text_query, input_types, expanded_queries, query_analysis,
                                  enriched_results, search_results, start_time):
        """Step 7: 응답 생성"""
        logger.info("[Step 7: 응답 생성] Generating response")
        end_time = self._get_current_time_ms()
        stats = self.result_enricher.calculate_search_statistics(search_results)

        logger.info(
            f"[Step 7: 응답 생성] Multimodal search completed: {stats['total_hits']} hits in {end_time - start_time}ms")

        # 응답에 확장된 쿼리 정보 포함
        display_query = text_query or f"Multimodal search ({', '.join(input_types)})"
        if len(expanded_queries) > 1:
            display_query += f" (expanded to {len(expanded_queries)} queries)"

        # query_analysis에 확장 정보 추가
        if query_analysis:
            query_analysis["expanded_queries"] = expanded_queries
            query_analysis["expansion_used"] = len(expanded_queries) > 1

        return SearchResponse(
            query=display_query,
            total_hits=stats["total_hits"],
            max_score=stats["max_score"],
            results=enriched_results,
            took_ms=end_time - start_time,
            element_types_used=query_analysis["selected_element_types"],
            query_analysis=query_analysis
        )

    def _get_current_time_ms(self) -> int:
        """현재 시간을 밀리초로 반환"""
        import time
        return int(time.time() * 1000)
