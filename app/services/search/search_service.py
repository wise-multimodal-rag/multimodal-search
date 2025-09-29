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
            max_results: int = 10,
            offset: int = 0
    ) -> SearchResponse:
        """멀티모달 검색 오케스트레이션"""
        logger.info("Processing multimodal search request")
        start_time = self._get_current_time_ms()

        try:
            # 입력 검증
            if not self.input_processor.validate_inputs(text_query, image_file, video_file, audio_file):
                raise ValueError("최소 하나의 입력(텍스트, 이미지, 비디오, 오디오)이 필요합니다")

            # 입력 타입 로깅
            input_types = self.input_processor.get_input_types(text_query, image_file, video_file, audio_file)
            logger.info(f"Multimodal search request with inputs: {', '.join(input_types)}")

            # Step 1: 멀티모달 입력 처리
            modalities_data = await self.input_processor.process_multimodal_inputs(
                text_query, image_file, video_file, audio_file
            )

            # Step 2: 쿼리 의도 분석
            query_analysis = None
            if text_query:
                query_analysis = await self.query_analyzer.analyze_query_intent(
                    text_query, self.available_element_types)
                if not query_analysis:
                    logger.warning(
                        f"Query analysis failed for text query: '{text_query}'. Falling back to default behavior.")
                    query_analysis = self.query_analyzer.create_default_query_analysis(
                        self.available_element_types, "Query analysis failed"
                    )
            else:
                logger.warning("No text query provided. Using all element types as fallback.")
                query_analysis = self.query_analyzer.create_default_query_analysis(self.available_element_types)

            selected_element_types = query_analysis["selected_element_types"]
            logger.info(f"Selected element types: {selected_element_types}")

            # Step 3: 멀티모달 특징 추출
            extracted_features = await self.feature_extractor.extract_features(modalities_data, selected_element_types)

            # Step 4: 임베딩 생성 (모든 모달리티와 특징들)
            embeddings = await self.embedding_service.generate_multimodal_embeddings(
                modalities_data, extracted_features
            )

            # Step 5: OpenSearch 검색 실행
            search_query = text_query or "multimodal search"
            search_results = await self.opensearch_service.search_elements(
                query=search_query,
                element_types=selected_element_types,
                embeddings=embeddings,
                size=max_results,
                from_=offset,
                filters=None
            )

            # Step 6: 결과 enrichment
            enriched_results = await self.result_enricher.enrich_search_results(
                search_results, include_chunk_meta, include_media_meta
            )

            # Step 7: 응답 생성
            end_time = self._get_current_time_ms()
            stats = self.result_enricher.calculate_search_statistics(search_results)

            logger.info(f"Multimodal search completed: {stats['total_hits']} hits in {end_time - start_time}ms")

            return SearchResponse(
                query=f"Multimodal search ({', '.join(input_types)}): {search_query}",
                total_hits=stats["total_hits"],
                max_score=stats["max_score"],
                results=enriched_results,
                took_ms=end_time - start_time,
                element_types_used=selected_element_types,
                query_analysis=query_analysis
            )

        except Exception as e:
            logger.error(f"Multimodal search failed: {e}")
            raise

    def _get_current_time_ms(self) -> int:
        """현재 시간을 밀리초로 반환"""
        import time
        return int(time.time() * 1000)
