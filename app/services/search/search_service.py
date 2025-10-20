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
        start_time = self._get_current_time_ms()

        try:
            # 입력 검증
            if not self.input_processor.validate_inputs(text_query, image_file, video_file, audio_file):
                raise ValueError("최소 하나의 입력(텍스트, 이미지, 비디오, 오디오)이 필요합니다")

            input_types = self.input_processor.get_input_types(text_query, image_file, video_file, audio_file)

            # Step 1: 멀티모달 입력 처리
            modalities_data = await self.input_processor.process_multimodal_inputs(
                text_query, image_file, video_file, audio_file
            )

            # Step 2: 쿼리 확장 및 의도 분석 (복잡한 로직이므로 함수 분리)
            query_analysis, expanded_queries = await self._expand_and_analyze_query(text_query)

            # Step 3: 멀티모달 특징 추출
            extracted_features = await self.feature_extractor.extract_features(modalities_data,
                                                                               query_analysis["selected_element_types"])

            # Step 4: 임베딩 생성
            embeddings = await self.embedding_service.generate_multimodal_embeddings(
                modalities_data, extracted_features
            )

            # Step 5: 확장 쿼리 검색 실행 (복잡한 로직이므로 함수 분리)  
            expansion_result = query_analysis.get("expansion_analysis") if "expansion_analysis" in query_analysis else None
            search_results = await self._execute_expanded_search(
                expanded_queries, query_analysis["selected_element_types"], embeddings, max_results, expansion_result
            )

            # Step 6: 결과 enrichment
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
        if text_query:
            # 쿼리 확장
            expanded_queries, expansion_result = await self._expand_query(text_query)
            # 의도 분석
            query_analysis = await self._analyze_query_intent(expanded_queries, expansion_result)
        else:
            query_analysis = self.query_analyzer.create_default_query_analysis(self.available_element_types)
            expanded_queries = ["multimodal search"]

        return query_analysis, expanded_queries

    async def _expand_query(self, text_query):
        """쿼리 확장 수행"""
        expansion_result = await self.query_analyzer.expand_query(text_query)

        if expansion_result and expansion_result.get("final_queries"):
            final_queries = expansion_result["final_queries"][:3]  # 상위 3개 사용
            expanded_queries = [q["query"] for q in final_queries]

            logger.info(f"Query expanded: {len(final_queries)} variants generated")
            return expanded_queries, expansion_result
        else:
            logger.warning(f"Query expansion failed, using original: '{text_query}'")
            return [text_query], None


    async def _analyze_query_intent(self, expanded_queries, expansion_result):
        """의도 분석 수행"""
        primary_query = expanded_queries[0] if expanded_queries else "multimodal search"

        query_analysis = await self.query_analyzer.analyze_query_intent(
            primary_query, self.available_element_types)

        if not query_analysis:
            logger.warning(f"Query analysis failed for: '{primary_query}'. Using default.")
            query_analysis = self.query_analyzer.create_default_query_analysis(
                self.available_element_types, "Query analysis failed"
            )

        # 확장 정보를 쿼리 분석에 추가
        if expansion_result:
            query_analysis["expansion_analysis"] = expansion_result.get("query_analysis", {})
            query_analysis["expansion_used"] = len(expanded_queries) > 1

        return query_analysis

    async def _execute_expanded_search(self, expanded_queries, selected_element_types, embeddings, max_results, expansion_result=None):
        """Step 5: 확장 쿼리 검색 실행 (순차/병렬 처리 최적화)"""
        # LLM 결과에서 의존성 확인
        has_dependency = expansion_result.get("has_dependency", False) if expansion_result else False
        
        if has_dependency:
            logger.info(f"Sequential search execution for {len(expanded_queries)} dependent queries")
            all_search_results = await self._execute_sequential_search(
                expanded_queries, selected_element_types, embeddings, max_results, expansion_result
            )
        else:
            logger.info(f"Parallel search execution for {len(expanded_queries)} independent queries")
            all_search_results = await self._execute_parallel_search(
                expanded_queries, selected_element_types, embeddings, max_results
            )
        
        return self._process_search_results(all_search_results, expanded_queries, max_results)

    async def _execute_parallel_search(self, expanded_queries, selected_element_types, embeddings, max_results):
        """기존 병렬 검색 실행"""
        import asyncio
        search_tasks = [
            self._execute_single_query_search(
                expanded_query, i, len(expanded_queries), selected_element_types, embeddings, max_results
            )
            for i, expanded_query in enumerate(expanded_queries)
        ]
        
        # 모든 검색을 병렬로 실행
        return await asyncio.gather(*search_tasks, return_exceptions=True)

    async def _execute_sequential_search(self, expanded_queries, selected_element_types, embeddings, max_results, expansion_result):
        """순차적 의존성 처리를 위한 검색"""
        accumulated_context = {}
        all_results = []
        
        dependency_reason = expansion_result.get("dependency_reason", "") if expansion_result else ""
        logger.info(f"Sequential execution reason: {dependency_reason}")
        
        for i, query in enumerate(expanded_queries):
            # 이전 결과를 컨텍스트로 활용
            if i > 0 and accumulated_context:
                enriched_query = await self._enrich_query_with_context(query, accumulated_context)
                logger.info(f"Query {i+1} enriched with context: '{query}' → '{enriched_query}'")
            else:
                enriched_query = query
                
            # 단일 쿼리 검색 실행
            result = await self._execute_single_query_search(
                enriched_query, i, len(expanded_queries), selected_element_types, embeddings, max_results
            )
            
            if not isinstance(result, Exception) and result is not None:
                all_results.append(result)
                # 다음 쿼리를 위한 컨텍스트 추출
                new_context = self._extract_context_from_results(result)
                accumulated_context.update(new_context)
                logger.debug(f"Context extracted from query {i+1}: {list(new_context.keys())}")
            else:
                logger.warning(f"Query {i+1} failed, continuing with existing context")
                all_results.append(result)  # 실패한 결과도 포함 (후에 필터링됨)
        
        return all_results

    def _process_search_results(self, all_search_results, expanded_queries, max_results):
        """검색 결과 처리 및 검증"""
        # 예외가 발생한 결과는 필터링하고 상세 로깅
        valid_results = []
        failed_queries = []
        
        for i, result in enumerate(all_search_results):
            if isinstance(result, Exception):
                query = expanded_queries[i] if i < len(expanded_queries) else f"query_{i}"
                logger.warning(f"Search query {i+1} '{query}' failed: {type(result).__name__}: {result}")
                failed_queries.append((i+1, query, str(result)))
            elif result is None:
                query = expanded_queries[i] if i < len(expanded_queries) else f"query_{i}"
                logger.warning(f"Search query {i+1} '{query}' returned no results")
                failed_queries.append((i+1, query, "No results"))
            else:
                valid_results.append(result)

        # 실패 통계 로깅
        if failed_queries:
            logger.warning(f"Search failures: {len(failed_queries)}/{len(expanded_queries)} queries failed")
        
        # 유효한 결과가 없는 경우 처리
        if not valid_results:
            logger.error("All search queries failed")
            return {
                'results': [],
                'total_hits': 0,
                'max_score': 0.0,
                'took_ms': 0
            }

        # 결과 통합
        combined_results = self._combine_search_results(valid_results, max_results)
        
        return combined_results

    async def _execute_single_query_search(self, expanded_query, query_index, total_queries,
                                           selected_element_types, embeddings, max_results):
        """단일 쿼리 검색 실행"""
        weight = 1.0 - (query_index * 0.1)  # 0.1씩 감소
        search_size = max_results // total_queries + (max_results % total_queries if query_index == 0 else 0)


        search_results = await self.opensearch_service.search_elements(
            query=expanded_query,
            element_types=selected_element_types,
            embeddings=embeddings,
            size=search_size,
            from_=0,
            filters=None
        )


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
            else:
                # search_results가 None이거나 잘못된 형태인 경우 기본 구조 생성
                search_results = {
                    'results': unique_results[:max_results],
                    'total_hits': len(unique_results),
                    'max_score': max(r.get('score', 0) for r in unique_results) if unique_results else 0.0,
                    'took_ms': 0
                }

        # search_results가 여전히 None인 경우 기본 구조 반환
        if not search_results:
            search_results = {
                'results': [],
                'total_hits': 0,
                'max_score': 0.0,
                'took_ms': 0
            }

        return search_results


    def _generate_search_response(self, text_query, input_types, expanded_queries, query_analysis,
                                  enriched_results, search_results, start_time):
        """Step 7: 응답 생성"""
        end_time = self._get_current_time_ms()
        stats = self.result_enricher.calculate_search_statistics(search_results)

        logger.info(f"Search completed: {stats['total_hits']} hits in {end_time - start_time}ms")

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

    async def _enrich_query_with_context(self, query: str, context: dict) -> str:
        """이전 검색 결과 컨텍스트를 활용하여 쿼리 보강"""
        if not context:
            return query
            
        # 컨텍스트에서 핵심 키워드 추출
        keywords = context.get("keywords", [])
        entities = context.get("entities", [])
        concepts = context.get("concepts", [])
        
        # 쿼리에 컨텍스트 정보 추가
        enriched_parts = [query]
        
        if keywords:
            # 상위 3개 키워드만 사용
            top_keywords = keywords[:3]
            enriched_parts.extend(top_keywords)
            
        if entities:
            # 상위 2개 엔티티만 사용  
            top_entities = entities[:2]
            enriched_parts.extend(top_entities)
            
        if concepts:
            # 상위 2개 개념만 사용
            top_concepts = concepts[:2]
            enriched_parts.extend(top_concepts)
        
        # 중복 제거 및 조합
        unique_parts = list(dict.fromkeys(enriched_parts))
        enriched_query = " ".join(unique_parts)
        
        # 너무 길어지면 원본 쿼리와 핵심 키워드만 사용
        if len(enriched_query) > 200:
            enriched_query = f"{query} {' '.join(keywords[:2])}"
            
        return enriched_query
    
    def _extract_context_from_results(self, search_results: dict) -> dict:
        """검색 결과에서 다음 쿼리를 위한 컨텍스트 추출"""
        context = {
            "keywords": [],
            "entities": [],
            "concepts": []
        }
        
        if not search_results or not search_results.get("results"):
            return context
            
        # 상위 5개 결과에서 컨텍스트 추출
        top_results = search_results["results"][:5]
        
        for result in top_results:
            # content에서 키워드 추출 (간단한 방식)
            content = result.get("content", "")
            if content:
                # 공백으로 분리된 단어들 중 의미있는 것 추출
                words = content.split()
                meaningful_words = [
                    word.strip(".,!?()[]{}\"'")
                    for word in words 
                    if len(word) > 2 and not word.isnumeric() and word.isalpha()
                ]
                context["keywords"].extend(meaningful_words[:3])
            
            # 메타데이터에서 추가 정보 추출
            if "features" in result:
                features = result["features"]
                if isinstance(features, dict):
                    # 키워드가 있다면 추가
                    if "keywords" in features and isinstance(features["keywords"], list):
                        context["keywords"].extend(features["keywords"][:3])
                    
                    # 엔티티가 있다면 추가
                    if "entities" in features and isinstance(features["entities"], list):
                        context["entities"].extend([e.get("text", e) if isinstance(e, dict) else e for e in features["entities"][:2]])
        
        # 중복 제거 및 빈도수 기반 정렬
        context["keywords"] = list(dict.fromkeys(context["keywords"]))[:10]
        context["entities"] = list(dict.fromkeys(context["entities"]))[:5]
        context["concepts"] = list(dict.fromkeys(context["concepts"]))[:5]
        
        return context

    def _get_current_time_ms(self) -> int:
        """현재 시간을 밀리초로 반환"""
        import time
        return int(time.time() * 1000)
