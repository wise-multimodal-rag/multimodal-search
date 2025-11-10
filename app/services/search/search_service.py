import time
from typing import Any, AsyncGenerator, Dict, List, Optional

from fastapi import UploadFile
from loguru import logger

from app.core.config import weighting_config
from app.models.opensearch import SearchResponse
from app.services.analysis.multimodal_feature_extractor import \
    MultimodalFeatureExtractor
from app.services.analysis.query_analyzer import QueryAnalyzer
from app.services.embeddings.embedding_service import EmbeddingService
from app.services.processing.input_processor import InputProcessor
from app.services.search.opensearch_service import OpenSearchService
from app.services.search.result_enricher import ResultEnricher
from app.services.search.search_executor import SearchExecutor


class SearchService:
    """메인 검색 오케스트레이션 서비스"""

    def __init__(
        self,
        opensearch_service: OpenSearchService,
        input_processor: InputProcessor,
        feature_extractor: MultimodalFeatureExtractor,
        query_analyzer: QueryAnalyzer,
        embedding_service: EmbeddingService,
        result_enricher: ResultEnricher,
        search_executor: SearchExecutor,
    ):
        # Define available element types for the system
        # Currently active types
        self.available_element_types = [
            "paragraph",  # 일반 문단 - 문서의 본문 내용
            "summary",  # AI 요약 - 자동 생성된 요약문
            "caption",  # 이미지 설명 - AI가 생성한 이미지 캡션
            "origin",  # 원본 이미지 - 최초 업로드된 이미지
        ]

        # Temporarily disabled element types (for future use)
        # Text modality:
        # "title": "제목 - 문서/섹션 제목",
        # "stt": "음성→텍스트 - 음성인식 결과",
        # "scene": "비디오 장면 설명 - 비디오 장면에 대한 텍스트 설명",
        # "ocr": "이미지→텍스트 - OCR로 추출한 텍스트",
        # "table": "표 데이터 - JSON 형태의 구조화된 표",
        # "translation": "번역 결과 - 다른 언어로 번역된 텍스트",
        # Image modality:
        # "cropped": "잘린 이미지 - 특정 영역을 추출한 이미지",
        # "detected_object": "감지된 객체 - 객체 감지로 추출한 영역",
        # "chart": "차트/그래프 - 데이터 시각화 이미지",
        # "diagram": "다이어그램 - 구조도, 플로우차트 등",
        # "keyframe": "키 프레임 - 비디오에서 추출한 대표 프레임 이미지",
        # "thumbnail": "썸네일 - 비디오의 썸네일 이미지",
        # Video modality:
        # "clip": "비디오 클립 - 특정 시간 구간의 영상",
        # "segment": "비디오 구간 - 의미적으로 구분된 비디오 구간",
        # Audio modality:
        # "speech": "사람의 발화 구간 - 특정 화자의 발언 부분",
        # "music": "배경음악이나 음악 콘텐츠 - 인트로 음악, 배경음 등",
        # "sound_effect": "특수 효과음 - 박수소리, 벨소리, 알림음",
        # "ambient": "주변 환경음 - 에어컨 소리, 발걸음, 잡음"

        # Strict dependency injection - no fallbacks
        self.opensearch_service = opensearch_service
        self.input_processor = input_processor
        self.feature_extractor = feature_extractor
        self.query_analyzer = query_analyzer
        self.embedding_service = embedding_service
        self.result_enricher = result_enricher
        self.search_executor = search_executor

    async def search_multimodal(
        self,
        text_query: Optional[str] = None,
        image_file: Optional[UploadFile] = None,
        video_file: Optional[UploadFile] = None,
        audio_file: Optional[UploadFile] = None,
        text_file: Optional[UploadFile] = None,
        include_chunk_meta: bool = True,
        include_media_meta: bool = True,
        max_results: int = 10,
    ) -> SearchResponse:
        """멀티모달 검색 오케스트레이션"""
        start_time = self._get_current_time_ms()

        try:
            # 입력 검증
            if not self.input_processor.validate_inputs(text_query, image_file, video_file, audio_file, text_file):
                raise ValueError("최소 하나의 입력(텍스트, 이미지, 비디오, 오디오, 텍스트 파일)이 필요합니다")

            input_types = self.input_processor.get_input_types(text_query, image_file, video_file, audio_file, text_file)

            # Step 1: 멀티모달 입력 처리
            modalities_data = await self.input_processor.process_multimodal_inputs(
                text_query, image_file, video_file, audio_file, text_file
            )

            # Step 2: 쿼리 확장 및 의도 분석 (QueryAnalyzer 사용)
            query_analysis, expanded_queries = await self.query_analyzer.process_query_analysis(
                text_query,
                self.available_element_types,
                self._extract_input_modalities(modalities_data) if modalities_data else None,
            )

            # Step 3: 멀티모달 특징 추출
            extracted_features = await self.feature_extractor.extract_features(
                modalities_data, query_analysis.get("selected_element_types", []) if query_analysis else []
            )

            # Step 4: 임베딩 생성
            embeddings = await self.embedding_service.generate_multimodal_embeddings(modalities_data, extracted_features)

            # Step 5: 확장 쿼리 검색 실행 (SearchExecutor 사용)
            expansion_result = query_analysis.get("expansion_analysis") if "expansion_analysis" in query_analysis else None
            element_type_weights = query_analysis.get("element_type_weights")
            
            # 가중치가 0인 element types는 검색에서 제외 (단, 캡션은 무조건 생성했지만 검색엔 가중치에 따라)
            filtered_element_types = self._filter_element_types_by_weight(
                query_analysis.get("selected_element_types", []) if query_analysis else [], 
                element_type_weights
            )
            
            # Extract image caption tags if available
            image_caption_tags = None
            if extracted_features and extracted_features.image and hasattr(extracted_features.image, 'tags'):
                image_caption_tags = getattr(extracted_features.image, 'tags')
                logger.info(f"🏷️ Using image caption tags for search enhancement: {image_caption_tags}")
            
            search_results = await self.search_executor.execute_expanded_search(
                expanded_queries, filtered_element_types, embeddings, max_results, expansion_result, element_type_weights, image_caption_tags
            )

            # Step 6: 결과 enrichment
            enriched_results = await self.result_enricher.enrich_search_results(
                search_results, include_chunk_meta, include_media_meta
            )

            # Step 7: 응답 생성 (첨부 이미지 캡션 포함)
            return self._generate_search_response(
                text_query, input_types, expanded_queries, query_analysis, enriched_results, search_results, start_time, extracted_features
            )

        except Exception as e:
            logger.error(f"Multimodal search failed: {e}")
            raise

    def _extract_input_modalities(self, modalities_data):
        """Extract input modalities from modalities_data"""
        input_modalities = []

        if modalities_data.get("text"):
            input_modalities.append("text")
        if modalities_data.get("image"):
            input_modalities.append("image")
        if modalities_data.get("video"):
            input_modalities.append("video")
        if modalities_data.get("audio"):
            input_modalities.append("audio")
        if modalities_data.get("text_file"):
            input_modalities.append("text_file")

        return input_modalities

    def _filter_element_types_by_weight(
        self, selected_element_types: List[str], element_type_weights: Optional[Dict[str, float]]
    ) -> List[str]:
        """가중치가 0인 element types를 검색에서 제외"""
        if not element_type_weights:
            return selected_element_types
        
        # 가중치가 0보다 큰 element types만 필터링
        filtered_types = [
            element_type for element_type in selected_element_types
            if element_type_weights.get(element_type, 0.0) > 0.0
        ]
        
        if len(filtered_types) != len(selected_element_types):
            excluded_types = [t for t in selected_element_types if t not in filtered_types]
            logger.info(f"🚫 Excluding element types with zero weight from search: {excluded_types}")
            logger.info(f"✅ Using element types for search: {filtered_types}")
        
        return filtered_types

    def _generate_search_response(
        self, text_query, input_types, expanded_queries, query_analysis, enriched_results, search_results, start_time, extracted_features=None
    ):
        """Step 7: 응답 생성"""
        end_time = self._get_current_time_ms()
        stats = self.result_enricher.calculate_search_statistics(search_results)

        logger.info(f"Search completed: {stats['total_hits']} hits in {end_time - start_time}ms")

        # 응답에 확장된 쿼리 정보 포함
        display_query = text_query or f"Multimodal search ({', '.join(input_types)})"
        if len(expanded_queries) > 1:
            display_query += f" (expanded to {len(expanded_queries)} queries)"

        # query_analysis에 확장 정보 및 첨부 이미지 캡션 추가
        if query_analysis:
            query_analysis["expanded_queries"] = expanded_queries
            query_analysis["expansion_used"] = len(expanded_queries) > 1
            
            # 첨부된 이미지의 캡션 정보 추가
            if extracted_features and extracted_features.image and extracted_features.image.caption:
                query_analysis["attached_image_caption"] = extracted_features.image.caption
                logger.info(f"🖼️ Added attached image caption to query_analysis: {extracted_features.image.caption[:100]}...")
            else:
                logger.info(f"🚫 No image caption found in extracted_features. Image features: {extracted_features.image is not None if extracted_features else 'No features'}")

        return SearchResponse(
            query=display_query,
            total_hits=stats["total_hits"],
            max_score=stats["max_score"],
            results=enriched_results,
            took_ms=end_time - start_time,
            element_types_used=query_analysis["selected_element_types"],
            query_analysis=query_analysis,
        )

    async def search_multimodal_stream(
        self,
        text_query: Optional[str] = None,
        processed_files: Optional[Dict[str, Dict[str, Any]]] = None,
        include_chunk_meta: bool = True,
        include_media_meta: bool = True,
        max_results: int = 10,
        files_were_provided: bool = False,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """스트리밍 방식의 멀티모달 검색 오케스트레이션"""
        start_time = time.time()

        try:
            # Step 0: 검색 시작 및 입력 검증
            async for step_data in self._stream_step_0_start_and_validate(
                text_query, processed_files, files_were_provided
            ):
                yield step_data

            # Step 1: 입력 처리
            modalities_data = None
            async for step_data in self._stream_step_1_input_processing(text_query, processed_files):
                if step_data.get("step") == "modalities_data":
                    modalities_data = step_data.get("data")
                yield step_data

            # Step 2: 쿼리 확장 및 의도 분석
            query_analysis, expanded_queries = None, None
            async for step_data in self._stream_step_2_query_analysis(text_query, modalities_data):
                if step_data.get("step") == "query_analysis_result":
                    result_data = step_data.get("data", {})
                    query_analysis = result_data.get("query_analysis")
                    expanded_queries = result_data.get("expanded_queries")
                yield step_data

            # Step 3: 특징 추출
            yield {"step": "feature_extraction", "message": "멀티모달 특징을 추출하고 있습니다...", "timestamp": time.time()}

            extracted_features = await self.feature_extractor.extract_features(
                modalities_data, query_analysis.get("selected_element_types", []) if query_analysis else []
            )

            # 텍스트 기반 element types 체크
            text_based_types = {"paragraph", "title", "heading", "list_item", "table_cell", "text"}
            has_text_elements = bool(set(query_analysis.get("selected_element_types", []) if query_analysis else []) & text_based_types)

            # 특징 추출 결과 데이터 준비 - 더 정확한 상태 구분
            feature_data = {
                "extraction_success": {
                    "text": "success"
                    if (extracted_features.text is not None or (text_query and has_text_elements))
                    else ("no_data" if not text_query and not has_text_elements else "failed"),
                    "image": "success"
                    if extracted_features.image is not None
                    else ("no_data" if not (modalities_data and modalities_data.get("image")) else "failed"),
                    "video": "success"
                    if extracted_features.video is not None
                    else ("no_data" if not (modalities_data and modalities_data.get("video")) else "failed"),
                    "audio": "success"
                    if extracted_features.audio is not None
                    else ("no_data" if not (modalities_data and modalities_data.get("audio")) else "failed"),
                }
            }

            # 각 모달리티별 특징 정보 추가 (실제 값 포함)
            if extracted_features.text or (text_query and has_text_elements):
                if extracted_features.text:
                    text_feature_data = {
                        "keywords_count": len(extracted_features.text.keywords) if extracted_features.text.keywords else 0,
                        "entities_count": len(extracted_features.text.entities) if extracted_features.text.entities else 0,
                        "has_summary": bool(extracted_features.text.summary),
                        "has_classification": bool(extracted_features.text.classification),
                    }

                    # 실제 특징 값들 추가 (안전한 직렬화)
                    if extracted_features.text.keywords:
                        text_feature_data["keywords"] = self._safely_serialize_feature(extracted_features.text.keywords)
                    if extracted_features.text.entities:
                        text_feature_data["entities"] = self._safely_serialize_feature(extracted_features.text.entities)
                    if extracted_features.text.summary:
                        text_feature_data["summary"] = self._safely_serialize_feature(extracted_features.text.summary)
                    if extracted_features.text.classification:
                        text_feature_data["classification"] = self._safely_serialize_feature(
                            extracted_features.text.classification
                        )
                    if hasattr(extracted_features.text, "sentiment") and getattr(extracted_features.text, "sentiment", None):
                        text_feature_data["sentiment"] = self._safely_serialize_feature(
                            getattr(extracted_features.text, "sentiment")
                        )
                    if hasattr(extracted_features.text, "topics") and getattr(extracted_features.text, "topics", None):
                        text_feature_data["topics"] = self._safely_serialize_feature(
                            getattr(extracted_features.text, "topics")
                        )
                else:
                    # 텍스트 쿼리가 있고 텍스트 기반 element type이 있는 경우 (paragraph 등)
                    text_feature_data = {
                        "source": "원본 텍스트 쿼리",
                        "query": text_query,
                        "element_types": [t for t in (query_analysis.get("selected_element_types", []) if query_analysis else []) if t in text_based_types],
                        "note": "별도 특징 추출 없이 원본 텍스트가 임베딩 생성에 사용됨",
                    }

                feature_data["text_features"] = text_feature_data

            if extracted_features.image:
                image_feature_data = {
                    "has_caption": bool(extracted_features.image.caption),
                    "objects_count": len(extracted_features.image.objects) if extracted_features.image.objects else 0,
                }

                # 실제 특징 값들 추가 (안전한 직렬화)
                if extracted_features.image.caption:
                    image_feature_data["caption"] = self._safely_serialize_feature(extracted_features.image.caption)
                if extracted_features.image.objects:
                    image_feature_data["objects"] = self._safely_serialize_feature(extracted_features.image.objects)
                if hasattr(extracted_features.image, "tags") and getattr(extracted_features.image, "tags", None):
                    image_feature_data["tags"] = self._safely_serialize_feature(getattr(extracted_features.image, "tags"))
                if hasattr(extracted_features.image, "colors") and getattr(extracted_features.image, "colors", None):
                    image_feature_data["colors"] = self._safely_serialize_feature(
                        getattr(extracted_features.image, "colors")
                    )
                if hasattr(extracted_features.image, "scene_analysis") and getattr(
                    extracted_features.image, "scene_analysis", None
                ):
                    image_feature_data["scene_analysis"] = self._safely_serialize_feature(
                        getattr(extracted_features.image, "scene_analysis")
                    )

                feature_data["image_features"] = image_feature_data

            if extracted_features.video:
                video_feature_data = {
                    "has_description": bool(extracted_features.video.description),
                    "scenes_count": len(extracted_features.video.scenes) if extracted_features.video.scenes else 0,
                    "activities_count": len(extracted_features.video.activities)
                    if extracted_features.video.activities
                    else 0,
                }

                # 실제 특징 값들 추가 (안전한 직렬화)
                if extracted_features.video.description:
                    video_feature_data["description"] = self._safely_serialize_feature(extracted_features.video.description)
                if extracted_features.video.scenes:
                    video_feature_data["scenes"] = self._safely_serialize_feature(extracted_features.video.scenes)
                if extracted_features.video.activities:
                    video_feature_data["activities"] = self._safely_serialize_feature(extracted_features.video.activities)
                if hasattr(extracted_features.video, "keyframes") and getattr(extracted_features.video, "keyframes", None):
                    video_feature_data["keyframes"] = self._safely_serialize_feature(
                        getattr(extracted_features.video, "keyframes")
                    )
                if hasattr(extracted_features.video, "motion_analysis") and getattr(
                    extracted_features.video, "motion_analysis", None
                ):
                    video_feature_data["motion_analysis"] = self._safely_serialize_feature(
                        getattr(extracted_features.video, "motion_analysis")
                    )

                feature_data["video_features"] = video_feature_data

            if extracted_features.audio:
                audio_feature_data = {
                    "has_transcription": bool(extracted_features.audio.transcription),
                    "sounds_count": len(extracted_features.audio.sounds) if extracted_features.audio.sounds else 0,
                    "audio_type": extracted_features.audio.audio_type,
                }

                # 실제 특징 값들 추가 (안전한 직렬화)
                if extracted_features.audio.transcription:
                    audio_feature_data["transcription"] = self._safely_serialize_feature(
                        extracted_features.audio.transcription
                    )
                if extracted_features.audio.sounds:
                    audio_feature_data["sounds"] = self._safely_serialize_feature(extracted_features.audio.sounds)
                if hasattr(extracted_features.audio, "emotions") and getattr(extracted_features.audio, "emotions", None):
                    audio_feature_data["emotions"] = self._safely_serialize_feature(
                        getattr(extracted_features.audio, "emotions")
                    )
                if hasattr(extracted_features.audio, "speaker_info") and getattr(
                    extracted_features.audio, "speaker_info", None
                ):
                    audio_feature_data["speaker_info"] = self._safely_serialize_feature(
                        getattr(extracted_features.audio, "speaker_info")
                    )
                if hasattr(extracted_features.audio, "acoustic_features") and getattr(
                    extracted_features.audio, "acoustic_features", None
                ):
                    audio_feature_data["acoustic_features"] = self._safely_serialize_feature(
                        getattr(extracted_features.audio, "acoustic_features")
                    )

                feature_data["audio_features"] = audio_feature_data

            yield {
                "step": "features_extracted",
                "message": "특징 추출이 완료되었습니다",
                "timestamp": time.time(),
                "data": feature_data,
            }

            # Step 4: 임베딩 생성
            yield {"step": "embedding_generation", "message": "임베딩을 생성하고 있습니다...", "timestamp": time.time()}

            embeddings = await self.embedding_service.generate_multimodal_embeddings(modalities_data, extracted_features)

            # 임베딩 통계 계산
            embedding_stats = {}
            for modality, vector in embeddings.items():
                if vector:
                    embedding_stats[modality] = {
                        "dimension": len(vector),
                        "vector_norm": sum(x * x for x in vector) ** 0.5 if vector else 0.0,
                    }

            yield {
                "step": "embeddings_generated",
                "message": "임베딩 생성이 완료되었습니다",
                "timestamp": time.time(),
                "data": {
                    "embedding_types": list(embeddings.keys()),
                    "embedding_stats": embedding_stats,
                    "total_embeddings": len(embeddings),
                },
            }

            # Step 5: 검색 실행
            yield {
                "step": "search_execution",
                "message": "OpenSearch에서 검색을 실행하고 있습니다...",
                "timestamp": time.time(),
            }

            expansion_result = query_analysis.get("expansion_analysis") if query_analysis else None
            element_type_weights = query_analysis.get("element_type_weights") if query_analysis else None
            
            # 가중치가 0인 element types는 검색에서 제외 (단, 캡션은 무조건 생성했지만 검색엔 가중치에 따라)
            filtered_element_types = self._filter_element_types_by_weight(
                query_analysis.get("selected_element_types", []) if query_analysis else [], 
                element_type_weights
            )
            
            # Extract image caption tags if available
            image_caption_tags = None
            if extracted_features and extracted_features.image and hasattr(extracted_features.image, 'tags'):
                image_caption_tags = getattr(extracted_features.image, 'tags')
                logger.info(f"🏷️ [STREAM] Using image caption tags for search enhancement: {image_caption_tags}")
            
            search_results = await self.search_executor.execute_expanded_search(
                expanded_queries, filtered_element_types, embeddings, max_results, expansion_result, element_type_weights, image_caption_tags
            )

            # 검색 실행 상세 통계
            executed_queries_info = []
            for i, query in enumerate(expanded_queries):
                weight = 1.0 - (i * weighting_config.QUERY_WEIGHT_DECAY)
                executed_queries_info.append({"index": i + 1, "query": query, "weight": weight, "priority": i + 1})

            # OpenSearch 쿼리 정보 (예시 - 실제로는 더 복잡)
            opensearch_query_info = {
                "index_used": "elements",
                "query_type": "hybrid_search",
                "search_fields": ["content"],
                "element_types_filter": query_analysis.get("selected_element_types", []) if query_analysis else [],
                "has_vector_search": bool(embeddings),
                "vector_modalities": list(embeddings.keys()) if embeddings else [],
                "modality_matching": "Each element's modality matched with appropriate embedding" if embeddings else "N/A",
                "fuzziness": "AUTO",
                "weighting_applied": "element_type weights applied directly to OpenSearch query",
            }

            search_stats = {
                "total_hits": search_results.get("total_hits", 0) if search_results else 0,
                "max_score": search_results.get("max_score", 0.0) if search_results else 0.0,
                "result_count": len(search_results.get("results", [])) if search_results else 0,
                "took_ms": search_results.get("took_ms", 0) if search_results else 0,
                "queries_executed": len(expanded_queries),
                "executed_queries": executed_queries_info,
                "opensearch_query": opensearch_query_info,
            }

            yield {
                "step": "search_executed",
                "message": "검색 실행이 완료되었습니다",
                "timestamp": time.time(),
                "data": search_stats,
            }

            # Step 6: 결과 enrichment
            yield {"step": "result_enrichment", "message": "검색 결과를 보강하고 있습니다...", "timestamp": time.time()}

            logger.info("🔄 Starting result enrichment...")
            enriched_results = await self.result_enricher.enrich_search_results(
                search_results, include_chunk_meta, include_media_meta
            )
            logger.info(f"✅ Result enrichment completed: {len(enriched_results)} results")

            # 보강된 결과의 상세 정보 계산
            element_types_in_results = {}
            for result in enriched_results:
                element_type = result.element.element_type
                element_types_in_results[element_type] = element_types_in_results.get(element_type, 0) + 1

            # 메타데이터 보강 통계
            chunk_meta_added = sum(1 for result in enriched_results if result.chunk_meta is not None)
            media_meta_added = sum(1 for result in enriched_results if result.media_meta is not None)

            yield {
                "step": "result_enriched",
                "message": f"결과 보강이 완료되었습니다 ({len(enriched_results)}개 결과)",
                "timestamp": time.time(),
                "data": {
                    "enriched_count": len(enriched_results),
                    "chunk_meta_included": include_chunk_meta,
                    "media_meta_included": include_media_meta,
                    "chunk_meta_added": chunk_meta_added,
                    "media_meta_added": media_meta_added,
                    "element_types_distribution": element_types_in_results,
                    "enrichment_options": {
                        "chunk_metadata": "포함됨" if include_chunk_meta else "제외됨",
                        "media_metadata": "포함됨" if include_media_meta else "제외됨",
                    },
                },
            }

            # Step 7: 최종 결과
            logger.info("🔄 Starting final result processing...")
            total_time = time.time() - start_time

            try:
                final_stats = self.result_enricher.calculate_search_statistics(search_results)
                logger.info("✅ Search statistics calculated")
            except Exception as e:
                logger.error(f"❌ Failed to calculate search statistics: {e}")
                final_stats = {}

            # 안전한 결과 직렬화
            logger.info(f"🔄 Starting serialization of {len(enriched_results)} results...")
            results_data = []
            total_bytes = 0
            failed_count = 0

            for i, result in enumerate(enriched_results):
                try:
                    if hasattr(result, "model_dump"):
                        serialized = result.model_dump()
                        # 직렬화된 데이터 크기 확인
                        import json

                        size_check = len(json.dumps(serialized, default=str))
                        total_bytes += size_check
                    elif hasattr(result, "dict"):
                        serialized = result.dict()
                    elif isinstance(result, dict):
                        serialized = result
                    else:
                        serialized = str(result)

                    results_data.append(serialized)

                except Exception as e:
                    failed_count += 1
                    logger.error(f"❌ Failed to serialize result {i}: {type(e).__name__}: {e}")
                    results_data.append({"error": f"Serialization failed: {str(e)}", "result_index": i})

            # 요약 로그
            if failed_count > 0:
                logger.warning(
                    f"✅ Serialization completed: {len(results_data) - failed_count}/{len(enriched_results)} successful, {failed_count} failed, {total_bytes:,} bytes total"
                )
            else:
                logger.info(f"✅ Serialization completed: {len(results_data)} results, {total_bytes:,} bytes total")

            try:
                logger.info("🔄 Creating completed data...")

                # 첨부 이미지 캡션 추가
                attached_image_caption = None
                if extracted_features and extracted_features.image and extracted_features.image.caption:
                    attached_image_caption = extracted_features.image.caption
                    logger.info(f"🖼️ [STREAM] Found attached image caption: {attached_image_caption[:100]}...")
                else:
                    logger.info(f"🚫 [STREAM] No image caption found. Image features: {extracted_features.image is not None if extracted_features else 'No features'}")

                # 데이터 크기 체크를 위한 임시 생성
                temp_completed_data = {
                    "results": results_data,
                    "search_stats": {
                        "total_hits": final_stats.get("total_hits", 0),
                        "max_score": final_stats.get("max_score", 0.0),
                        "result_count": len(results_data),
                    },
                    "total_time_ms": total_time * 1000,
                    "processing_steps": 7,
                    "query_analysis": {
                        "selected_element_types": query_analysis.get("selected_element_types", []) if query_analysis else [],
                        "confidence": query_analysis.get("confidence", 0.0) if query_analysis else 0.0,
                        "attached_image_caption": attached_image_caption,
                    },
                    "expanded_queries": [
                        q.get("query", str(q)) if isinstance(q, dict) else str(q) for q in (expanded_queries or [])
                    ],
                }

                # 전체 데이터 크기 확인
                import json

                temp_json = json.dumps(temp_completed_data, default=str)
                data_size = len(temp_json)
                logger.info(f"📊 Completed data size: {data_size} bytes ({data_size / 1024 / 1024:.2f} MB)")

                # 크기가 너무 크면 간소화
                if data_size > 5 * 1024 * 1024:  # 5MB 초과시
                    logger.warning(f"⚠️ Data too large ({data_size / 1024 / 1024:.2f} MB), simplifying...")
                    completed_data = {
                        "results": results_data[:5],  # 처음 5개만
                        "search_stats": temp_completed_data["search_stats"],
                        "total_time_ms": temp_completed_data["total_time_ms"],
                        "processing_steps": 7,
                        "message": f"결과가 너무 커서 {len(results_data)}개 중 5개만 표시합니다",
                    }
                else:
                    completed_data = temp_completed_data

                logger.info("✅ Completed data created successfully")

                logger.info("🔄 Yielding completed step...")
                yield {
                    "step": "completed",
                    "message": f"검색이 완료되었습니다 ({total_time:.2f}초)",
                    "timestamp": time.time(),
                    "data": completed_data,
                }
                logger.info("✅ Completed step yielded successfully")

                # 프론트엔드가 completed 이벤트를 처리할 시간을 확보하기 위한 짧은 지연
                import asyncio

                await asyncio.sleep(0.1)

                # 스트림 완료 확인 로그
                logger.info("🏁 Stream processing completed - search_multimodal_stream ending")

            except Exception as e:
                logger.error(f"❌ Failed to create completed data: {e}")
                # 최소한의 완료 메시지라도 전송
                yield {
                    "step": "completed",
                    "message": f"검색이 완료되었습니다 ({total_time:.2f}초)",
                    "timestamp": time.time(),
                    "data": {
                        "results": [],
                        "search_stats": {"total_results": 0},
                        "total_time_ms": total_time * 1000,
                        "processing_steps": 7,
                        "error": f"Data serialization failed: {str(e)}",
                    },
                }

        except Exception as e:
            import traceback

            logger.error(f"❌ Streaming search failed: {e}")
            logger.error(f"❌ Traceback: {traceback.format_exc()}")

            yield {"step": "error", "error": str(e), "timestamp": time.time()}

    def _safely_serialize_feature(self, feature_value):
        """특징 값을 안전하게 직렬화 가능한 형태로 변환"""
        if feature_value is None:
            return None

        # Pydantic 모델인 경우
        if hasattr(feature_value, "model_dump"):
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

    # === 스트리밍 검색 단계별 메서드들 ===
    
    async def _stream_step_0_start_and_validate(
        self, text_query: Optional[str], processed_files: Optional[Dict[str, Dict[str, Any]]], files_were_provided: bool
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Step 0: 검색 시작 알림 및 입력 검증"""
        # 입력 타입 확인
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
                "has_image": bool(processed_files and "image" in processed_files),
                "has_video": bool(processed_files and "video" in processed_files),
                "has_audio": bool(processed_files and "audio" in processed_files),
            },
        }

        # 입력 검증
        if not text_query and (not processed_files or len(processed_files) == 0):
            raise ValueError(
                "파일 읽기에 실패했고 텍스트 쿼리도 없습니다. 텍스트 쿼리를 입력하거나 파일을 다시 업로드해주세요."
            )

        # 파일 처리 실패 알림
        if files_were_provided and (processed_files is None or len(processed_files) == 0):
            if text_query:
                logger.warning("Files were provided but processing failed, continuing with text-only search")
                yield {
                    "step": "file_read_failed",
                    "message": "파일 처리에 실패했지만 텍스트 쿼리로 검색을 계속 진행합니다",
                    "timestamp": time.time(),
                    "data": {"fallback_mode": "text_only"},
                }

    async def _stream_step_1_input_processing(
        self, text_query: Optional[str], processed_files: Optional[Dict[str, Dict[str, Any]]]
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Step 1: 멀티모달 입력 처리"""
        yield {"step": "input_processing", "message": "멀티모달 입력을 처리하고 있습니다...", "timestamp": time.time()}

        modalities_data = await self.input_processor.process_multimodal_inputs_from_processed(
            text_query, processed_files
        )

        # 파일 정보 수집
        file_info = {}
        if processed_files:
            for file_type, file_data in processed_files.items():
                file_info[file_type] = {"filename": file_data["filename"], "content_type": file_data["content_type"]}

        logger.info(f"스트리밍 응답용 modalities_data 키들: {list(modalities_data.keys())}")
        yield {
            "step": "input_processed",
            "message": "입력 처리가 완료되었습니다",
            "timestamp": time.time(),
            "data": {"modalities": list(modalities_data.keys()), "text_query": text_query, "file_info": file_info},
        }

        yield {
            "step": "modalities_data",
            "message": "모달리티 데이터 준비 완료",
            "timestamp": time.time(),
            "data": modalities_data,
        }

    async def _stream_step_2_query_analysis(
        self, text_query: Optional[str], modalities_data: Dict[str, Any]
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Step 2: 쿼리 확장 및 의도 분석"""
        yield {"step": "query_analysis", "message": "쿼리를 분석하고 있습니다...", "timestamp": time.time()}

        input_modalities = self._extract_input_modalities(modalities_data) if modalities_data else None
        query_analysis, expanded_queries = await self.query_analyzer.process_query_analysis(
            text_query, self.available_element_types, input_modalities
        )

        # 분석 결과 데이터 생성
        element_weights = query_analysis.get("element_type_weights", {})
        analysis_data = self._prepare_query_analysis_data(query_analysis, expanded_queries, element_weights, text_query, modalities_data)
        
        yield {
            "step": "query_analyzed",
            "message": f"쿼리 의도 분석 완료 - {analysis_data['analysis_method']} 사용",
            "timestamp": time.time(),
            "data": analysis_data,
        }

        yield {
            "step": "query_analysis_result",
            "message": "쿼리 분석 결과",
            "timestamp": time.time(),
            "data": {"query_analysis": query_analysis, "expanded_queries": expanded_queries},
        }

    def _prepare_query_analysis_data(self, query_analysis, expanded_queries, element_weights, text_query, modalities_data=None):
        """쿼리 분석 결과 데이터 준비"""
        highest_weight_type = max(element_weights.items(), key=lambda x: x[1]) if element_weights else ("none", 0.0)
        meaningful_weights = {k: v for k, v in element_weights.items() if v > 0.0}
        analysis_method = "Advanced Fallback Analysis" if "fallback_reasoning" in query_analysis else "LLM Analysis"
        
        # 가중치 분포 세부 정보
        weight_distribution_details = {
            "high_priority": {k: v for k, v in meaningful_weights.items() if v >= weighting_config.HIGH_PRIORITY_THRESHOLD},
            "medium_priority": {k: v for k, v in meaningful_weights.items() if weighting_config.MEDIUM_PRIORITY_THRESHOLD <= v < weighting_config.HIGH_PRIORITY_THRESHOLD},
            "low_priority": {k: v for k, v in meaningful_weights.items() if weighting_config.LOW_PRIORITY_THRESHOLD < v < weighting_config.MEDIUM_PRIORITY_THRESHOLD},
            "excluded": {k: v for k, v in element_weights.items() if v == weighting_config.LOW_PRIORITY_THRESHOLD}
        }
        
        return {
            "original_query": text_query,
            "expanded_queries": expanded_queries,
            "expansion_used": len(expanded_queries) > 1,
            "total_queries": len(expanded_queries),
            
            # Element type 정보
            "selected_element_types": query_analysis["selected_element_types"],
            "element_type_weights": element_weights,
            "meaningful_weights": meaningful_weights,
            "weight_distribution_details": weight_distribution_details,
            "highest_priority_type": highest_weight_type[0],
            "highest_weight_score": highest_weight_type[1],
            "total_weighted_types": len(meaningful_weights),
            "zero_weight_types": len(weight_distribution_details["excluded"]),
            
            # 분석 정보
            "analysis_method": analysis_method,
            "reasoning": query_analysis.get("reasoning", ""),
            "confidence": query_analysis.get("confidence", 0.0),
            "element_types_count": len(query_analysis["selected_element_types"]),
            "expansion_analysis": query_analysis.get("expansion_analysis"),
            "weighting_system_enabled": query_analysis.get("element_type_weights") is not None,
            "fallback_reasoning": query_analysis.get("fallback_reasoning", ""),
            
            # 요약 정보
            "summary": {
                "query_intent": f"'{text_query or 'multimodal query'}'에서 '{highest_weight_type[0]}' 타입을 우선 검색 (가중치: {highest_weight_type[1]:.1f})",
                "weight_distribution": f"높은 우선순위: {len(weight_distribution_details['high_priority'])}개, " +
                                     f"중간 우선순위: {len(weight_distribution_details['medium_priority'])}개, " +
                                     f"낮은 우선순위: {len(weight_distribution_details['low_priority'])}개",
                "expansion_status": f"{len(expanded_queries)}개 쿼리로 확장" if len(expanded_queries) > 1 else "확장 없음",
                "opensearch_weighting": "OpenSearch 쿼리 레벨에서 가중치 적용됨"
            },
            
            # 디버그 정보
            "debug_info": {
                "llm_success": analysis_method == "LLM Analysis",
                "fallback_used": analysis_method == "Advanced Fallback Analysis",
                "input_modalities": self._extract_input_modalities(modalities_data) if modalities_data else None,
                "available_element_types": self.available_element_types
            }
        }
