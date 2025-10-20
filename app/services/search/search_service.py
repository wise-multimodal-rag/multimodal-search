import time
from typing import AsyncGenerator, Dict, Any, Optional

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

    async def search_multimodal_stream(
        self,
        text_query: Optional[str] = None,
        processed_files: Optional[Dict[str, Dict[str, Any]]] = None,
        include_chunk_meta: bool = True,
        include_media_meta: bool = True,
        max_results: int = 10
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """스트리밍 방식의 멀티모달 검색 오케스트레이션"""
        
        start_time = time.time()
        
        try:
            # Step 0: 검색 시작 알림
            input_types = []
            if text_query:
                input_types.append("text")
            if processed_files:
                input_types.extend(processed_files.keys())
                
            yield {
                "step": "start",
                "message": "멀티모달 검색을 시작합니다...",
                "timestamp": time.time(),
                "data": {
                    "input_types": input_types,
                    "has_text": bool(text_query),
                    "has_image": bool(processed_files and 'image' in processed_files),
                    "has_video": bool(processed_files and 'video' in processed_files),
                    "has_audio": bool(processed_files and 'audio' in processed_files)
                }
            }
            
            # 입력 검증 - 파일 처리에 실패해도 텍스트 쿼리가 있으면 계속 진행
            if not text_query and (not processed_files or len(processed_files) == 0):
                raise ValueError("파일 읽기에 실패했고 텍스트 쿼리도 없습니다. 텍스트 쿼리를 입력하거나 파일을 다시 업로드해주세요.")
            
            # 파일 처리 실패 시 텍스트 전용 모드로 전환
            if processed_files is None or len(processed_files) == 0:
                if text_query:
                    logger.warning("No files processed successfully, continuing with text-only search")
                    yield {
                        "step": "file_read_failed",
                        "message": "파일 처리에 실패했지만 텍스트 쿼리로 검색을 계속 진행합니다",
                        "timestamp": time.time(),
                        "data": {"fallback_mode": "text_only"}
                    }
            
            # Step 1: 입력 처리
            yield {
                "step": "input_processing",
                "message": "멀티모달 입력을 처리하고 있습니다...",
                "timestamp": time.time()
            }
            
            modalities_data = await self.input_processor.process_multimodal_inputs_from_processed(
                text_query, processed_files
            )
            
            # 파일 정보 수집
            file_info = {}
            if processed_files:
                for file_type, file_data in processed_files.items():
                    file_info[file_type] = {
                        "filename": file_data["filename"],
                        "content_type": file_data["content_type"]
                    }
            
            yield {
                "step": "input_processed", 
                "message": "입력 처리가 완료되었습니다",
                "timestamp": time.time(),
                "data": {
                    "modalities": list(modalities_data.keys()),
                    "text_query": text_query,
                    "file_info": file_info
                }
            }
            
            # Step 2: 쿼리 분석 및 확장
            yield {
                "step": "query_analysis",
                "message": "쿼리 의도를 분석하고 확장하고 있습니다...",
                "timestamp": time.time()
            }
            
            query_analysis, expanded_queries = await self._expand_and_analyze_query(text_query)
            
            yield {
                "step": "query_analyzed",
                "message": "쿼리 분석이 완료되었습니다",
                "timestamp": time.time(),
                "data": {
                    "original_query": text_query,
                    "selected_element_types": query_analysis["selected_element_types"],
                    "expanded_queries": expanded_queries,
                    "reasoning": query_analysis.get("reasoning", ""),
                    "confidence": query_analysis.get("confidence", 0.0),
                    "expansion_used": len(expanded_queries) > 1,
                    "total_queries": len(expanded_queries)
                }
            }
            
            # Step 3: 특징 추출
            yield {
                "step": "feature_extraction",
                "message": "멀티모달 특징을 추출하고 있습니다...",
                "timestamp": time.time()
            }
            
            extracted_features = await self.feature_extractor.extract_features(
                modalities_data, query_analysis["selected_element_types"]
            )
            
            # 특징 추출 결과 데이터 준비
            feature_data = {
                "extraction_success": {
                    "text": extracted_features.text is not None,
                    "image": extracted_features.image is not None,
                    "video": extracted_features.video is not None,
                    "audio": extracted_features.audio is not None
                }
            }
            
            # 각 모달리티별 특징 정보 추가 (실제 값 포함)
            if extracted_features.text:
                text_feature_data = {
                    "keywords_count": len(extracted_features.text.keywords) if extracted_features.text.keywords else 0,
                    "entities_count": len(extracted_features.text.entities) if extracted_features.text.entities else 0,
                    "has_summary": bool(extracted_features.text.summary),
                    "has_classification": bool(extracted_features.text.classification)
                }
                
                # 실제 특징 값들 추가 (안전한 직렬화)
                if extracted_features.text.keywords:
                    text_feature_data["keywords"] = self._safely_serialize_feature(extracted_features.text.keywords)
                if extracted_features.text.entities:
                    text_feature_data["entities"] = self._safely_serialize_feature(extracted_features.text.entities)
                if extracted_features.text.summary:
                    text_feature_data["summary"] = self._safely_serialize_feature(extracted_features.text.summary)
                if extracted_features.text.classification:
                    text_feature_data["classification"] = self._safely_serialize_feature(extracted_features.text.classification)
                if hasattr(extracted_features.text, 'sentiment') and extracted_features.text.sentiment:
                    text_feature_data["sentiment"] = self._safely_serialize_feature(extracted_features.text.sentiment)
                if hasattr(extracted_features.text, 'topics') and extracted_features.text.topics:
                    text_feature_data["topics"] = self._safely_serialize_feature(extracted_features.text.topics)
                    
                feature_data["text_features"] = text_feature_data
                
            if extracted_features.image:
                image_feature_data = {
                    "has_caption": bool(extracted_features.image.caption),
                    "objects_count": len(extracted_features.image.objects) if extracted_features.image.objects else 0
                }
                
                # 실제 특징 값들 추가 (안전한 직렬화)
                if extracted_features.image.caption:
                    image_feature_data["caption"] = self._safely_serialize_feature(extracted_features.image.caption)
                if extracted_features.image.objects:
                    image_feature_data["objects"] = self._safely_serialize_feature(extracted_features.image.objects)
                if hasattr(extracted_features.image, 'tags') and extracted_features.image.tags:
                    image_feature_data["tags"] = self._safely_serialize_feature(extracted_features.image.tags)
                if hasattr(extracted_features.image, 'colors') and extracted_features.image.colors:
                    image_feature_data["colors"] = self._safely_serialize_feature(extracted_features.image.colors)
                if hasattr(extracted_features.image, 'scene_analysis') and extracted_features.image.scene_analysis:
                    image_feature_data["scene_analysis"] = self._safely_serialize_feature(extracted_features.image.scene_analysis)
                    
                feature_data["image_features"] = image_feature_data
                
            if extracted_features.video:
                video_feature_data = {
                    "has_description": bool(extracted_features.video.description),
                    "scenes_count": len(extracted_features.video.scenes) if extracted_features.video.scenes else 0,
                    "activities_count": len(extracted_features.video.activities) if extracted_features.video.activities else 0
                }
                
                # 실제 특징 값들 추가 (안전한 직렬화)
                if extracted_features.video.description:
                    video_feature_data["description"] = self._safely_serialize_feature(extracted_features.video.description)
                if extracted_features.video.scenes:
                    video_feature_data["scenes"] = self._safely_serialize_feature(extracted_features.video.scenes)
                if extracted_features.video.activities:
                    video_feature_data["activities"] = self._safely_serialize_feature(extracted_features.video.activities)
                if hasattr(extracted_features.video, 'keyframes') and extracted_features.video.keyframes:
                    video_feature_data["keyframes"] = self._safely_serialize_feature(extracted_features.video.keyframes)
                if hasattr(extracted_features.video, 'motion_analysis') and extracted_features.video.motion_analysis:
                    video_feature_data["motion_analysis"] = self._safely_serialize_feature(extracted_features.video.motion_analysis)
                    
                feature_data["video_features"] = video_feature_data
                
            if extracted_features.audio:
                audio_feature_data = {
                    "has_transcription": bool(extracted_features.audio.transcription),
                    "sounds_count": len(extracted_features.audio.sounds) if extracted_features.audio.sounds else 0,
                    "audio_type": extracted_features.audio.audio_type
                }
                
                # 실제 특징 값들 추가 (안전한 직렬화)
                if extracted_features.audio.transcription:
                    audio_feature_data["transcription"] = self._safely_serialize_feature(extracted_features.audio.transcription)
                if extracted_features.audio.sounds:
                    audio_feature_data["sounds"] = self._safely_serialize_feature(extracted_features.audio.sounds)
                if hasattr(extracted_features.audio, 'emotions') and extracted_features.audio.emotions:
                    audio_feature_data["emotions"] = self._safely_serialize_feature(extracted_features.audio.emotions)
                if hasattr(extracted_features.audio, 'speaker_info') and extracted_features.audio.speaker_info:
                    audio_feature_data["speaker_info"] = self._safely_serialize_feature(extracted_features.audio.speaker_info)
                if hasattr(extracted_features.audio, 'acoustic_features') and extracted_features.audio.acoustic_features:
                    audio_feature_data["acoustic_features"] = self._safely_serialize_feature(extracted_features.audio.acoustic_features)
                    
                feature_data["audio_features"] = audio_feature_data
            
            yield {
                "step": "features_extracted",
                "message": "특징 추출이 완료되었습니다",
                "timestamp": time.time(),
                "data": feature_data
            }
            
            # Step 4: 임베딩 생성
            yield {
                "step": "embedding_generation",
                "message": "임베딩을 생성하고 있습니다...",
                "timestamp": time.time()
            }
            
            embeddings = await self.embedding_service.generate_multimodal_embeddings(
                modalities_data, extracted_features
            )
            
            # 임베딩 통계 계산
            embedding_stats = {}
            for modality, vector in embeddings.items():
                if vector:
                    embedding_stats[modality] = {
                        "dimension": len(vector),
                        "vector_norm": sum(x*x for x in vector)**0.5 if vector else 0.0
                    }
            
            yield {
                "step": "embeddings_generated",
                "message": "임베딩 생성이 완료되었습니다",
                "timestamp": time.time(),
                "data": {
                    "embedding_types": list(embeddings.keys()),
                    "embedding_stats": embedding_stats,
                    "total_embeddings": len(embeddings)
                }
            }
            
            # Step 5: 검색 실행
            yield {
                "step": "search_execution",
                "message": "OpenSearch에서 검색을 실행하고 있습니다...",
                "timestamp": time.time()
            }
            
            expansion_result = query_analysis.get("expansion_analysis")
            search_results = await self._execute_expanded_search(
                expanded_queries, query_analysis["selected_element_types"], 
                embeddings, max_results, expansion_result
            )
            
            # 검색 실행 통계
            search_stats = {
                "total_hits": search_results.get("total_hits", 0),
                "max_score": search_results.get("max_score", 0.0),
                "result_count": len(search_results.get("results", [])),
                "took_ms": search_results.get("took_ms", 0),
                "queries_executed": len(expanded_queries)
            }
            
            yield {
                "step": "search_executed",
                "message": "검색 실행이 완료되었습니다",
                "timestamp": time.time(),
                "data": search_stats
            }
            
            # Step 6: 결과 enrichment
            yield {
                "step": "result_enrichment",
                "message": "검색 결과를 보강하고 있습니다...",
                "timestamp": time.time()
            }
            
            enriched_results = await self.result_enricher.enrich_search_results(
                search_results, include_chunk_meta, include_media_meta
            )
            
            yield {
                "step": "result_enriched",
                "message": "결과 보강이 완료되었습니다",
                "timestamp": time.time(),
                "data": {
                    "enriched_count": len(enriched_results),
                    "chunk_meta_included": include_chunk_meta,
                    "media_meta_included": include_media_meta
                }
            }
            
            # Step 7: 최종 결과
            total_time = time.time() - start_time
            final_stats = self.result_enricher.calculate_search_statistics(search_results)
            
            yield {
                "step": "completed",
                "message": f"검색이 완료되었습니다 ({total_time:.2f}초)",
                "timestamp": time.time(),
                "data": {
                    "results": [result.model_dump() if hasattr(result, 'model_dump') else result for result in enriched_results],
                    "search_stats": final_stats,
                    "total_time_ms": total_time * 1000,
                    "processing_steps": 7,
                    "query_analysis": query_analysis,
                    "expanded_queries": expanded_queries
                }
            }
            
        except Exception as e:
            logger.error(f"Streaming search failed: {e}")
            yield {
                "step": "error",
                "error": str(e),
                "timestamp": time.time()
            }

    def _safely_serialize_feature(self, feature_value):
        """특징 값을 안전하게 직렬화 가능한 형태로 변환"""
        if feature_value is None:
            return None
            
        # Pydantic 모델인 경우
        if hasattr(feature_value, 'model_dump'):
            return feature_value.model_dump()
        
        # 기본 JSON 직렬화 가능한 타입들
        if isinstance(feature_value, (list, dict, str, int, float, bool)):
            # 리스트인 경우 각 요소도 재귀적으로 처리
            if isinstance(feature_value, list):
                return [self._safely_serialize_feature(item) for item in feature_value]
            # 딕셔너리인 경우 각 값을 재귀적으로 처리
            elif isinstance(feature_value, dict):
                return {key: self._safely_serialize_feature(value) for key, value in feature_value.items()}
            else:
                return feature_value
        
        # 그 외의 경우 문자열로 변환
        return str(feature_value)

    def _get_current_time_ms(self) -> int:
        """현재 시간을 밀리초로 반환"""
        import time
        return int(time.time() * 1000)
