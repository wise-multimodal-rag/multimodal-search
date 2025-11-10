from typing import Any, Dict, List, Optional

from loguru import logger

from app.clients.embedding_client import EmbeddingClient
from app.clients.feature_extraction_client import FeatureExtractionClient
from app.clients.llm_client import LLMClient
from app.models.features import (AudioFeatures, ImageFeatures, MultimodalFeatures,
                                 TextFeatures, VideoFeatures)


class MultimodalFeatureExtractor:
    """멀티모달 특징 추출을 담당하는 서비스"""

    def __init__(
        self,
        feature_extraction_client: FeatureExtractionClient = None,
        embedding_client: EmbeddingClient = None,
        llm_client: LLMClient = None,
    ):
        self.feature_extraction_client = feature_extraction_client or FeatureExtractionClient()
        self.embedding_client = embedding_client or EmbeddingClient()
        self.llm_client = llm_client or LLMClient()

    async def extract_features(self, modalities_data: Dict[str, Any], element_types: List[str]) -> MultimodalFeatures:
        """모든 모달리티에서 특징 추출"""
        text_features = None
        image_features = None
        video_features = None
        audio_features = None

        try:
            # 각 모달리티별로 특징 추출
            if "text" in modalities_data:
                # summary element_type의 경우 원본 텍스트로 충분하므로 특징 추출 건너뛰기
                # text_features = await self._extract_text_features(modalities_data["text"], element_types)
                text_features = None  # 원본 텍스트 쿼리를 직접 사용

            if "image" in modalities_data:
                image_features = await self._extract_image_features(modalities_data["image"], element_types)

            if "video" in modalities_data:
                video_features = await self._extract_video_features(modalities_data["video"], element_types)

            if "audio" in modalities_data:
                audio_features = await self._extract_audio_features(modalities_data["audio"], element_types)

            features = MultimodalFeatures(
                text=text_features, image=image_features, video=video_features, audio=audio_features
            )

            logger.debug(
                f"Extracted multimodal features: text={text_features is not None}, "
                f"image={image_features is not None}, video={video_features is not None}, "
                f"audio={audio_features is not None}"
            )
            return features

        except Exception as e:
            logger.error(f"Multimodal feature extraction failed: {e}")
            return MultimodalFeatures()

    async def _extract_text_features(self, text_data: Dict[str, Any], element_types: List[str]) -> Optional[TextFeatures]:
        """텍스트 모달리티에서 특징 추출 - element_type별로 개별 처리"""
        try:
            text_query = text_data["query"]

            # element_type별로 개별 feature 추출
            paragraph_text = None
            summary_text = None

            # paragraph: OpenSearch에서 검색용이므로 별도 임베딩 불필요 (원본 text 임베딩 사용)
            # if "paragraph" in element_types:
            #     paragraph_text = text_query

            # summary: 텍스트 요약 추출
            if "summary" in element_types:
                summary_result = await self.feature_extraction_client.extract_text_summary(text_query)
                if summary_result and "summary" in summary_result:
                    summary_text = summary_result["summary"]

            # caption은 이미지 모달리티에서 처리하므로 여기서 제외
            # 비활성화된 타입: "title", "stt", "scene", "ocr", "table", "translation"

            # 추출된 feature가 있는 경우만 반환
            if summary_text:
                return TextFeatures(
                    keywords=None,  # TODO: 추후 키워드 추출 기능 추가 예정
                    entities=None,  # TODO: 추후 엔티티 추출 기능 추가 예정
                    summary=summary_text,
                    classification=None,  # TODO: 추후 텍스트 분류 기능 추가 예정
                )
            return None

        except Exception as e:
            logger.error(f"Text feature extraction failed: {e}")
            return None

    async def _extract_image_features(self, image_data: Dict[str, Any], element_types: List[str]) -> Optional[ImageFeatures]:
        """이미지 모달리티에서 특징 추출 - 이미지가 첨부되면 무조건 캡션 생성"""
        try:
            if "base64_data" not in image_data:
                return None

            base64_image = image_data["base64_data"]
            import base64

            image_bytes = base64.b64decode(base64_image)

            # 이미지가 첨부되면 무조건 캡션 생성 (검색 사용 여부는 별도 결정)
            caption_text = None
            caption_tags = None
            logger.info(f"🖼️ Image attached - generating caption unconditionally")
            
            caption_result = await self.embedding_client.generate_image_caption(image_bytes)
            if caption_result and "caption" in caption_result:
                caption_text = caption_result["caption"]
                logger.info(f"✅ Image caption generated: {caption_text[:100]}...")
                
                # Extract tags if available
                if "tags" in caption_result:
                    caption_tags = caption_result["tags"]
                    logger.info(f"🏷️ Image caption tags extracted: {caption_tags}")
            else:
                logger.warning(f"🚫 Image caption generation failed or returned no caption")

            # 캡션이 생성된 경우 ImageFeatures 반환
            if caption_text:
                return ImageFeatures(
                    caption=caption_text,
                    objects=None,
                    tags=caption_tags,
                )
            return None

        except Exception as e:
            logger.error(f"Image feature extraction failed: {e}")
            return None

    async def _extract_video_features(self, video_data: Dict[str, Any], element_types: List[str]) -> Optional[VideoFeatures]:
        """비디오 모달리티에서 특징 추출"""
        try:
            # 비디오 관련 element_types 모두 비활성화됨
            # 비활성화된 타입: "scene", "clip", "segment", "keyframe", "thumbnail"
            return None
            # if not any(t in element_types for t in ["scene", "clip", "segment", "keyframe", "thumbnail"]):
            #     return None

            if "base64_data" not in video_data:
                return None

            base64_video = video_data["base64_data"]
            content_type = video_data["content_type"]

            keywords = None
            scenes = None
            objects = None
            activities = None
            description = None

            # LLM을 통한 비디오 분석
            video_analysis = await self._analyze_video_with_llm(base64_video, content_type)

            if video_analysis:
                # 비디오 설명에서 키워드 추출
                if "description" in video_analysis:
                    description = video_analysis["description"]
                    video_keywords = await self.feature_extraction_client.extract_keywords(description)
                    if video_keywords:
                        keywords = video_keywords

                # 비디오 특징 정보 직접 활용
                if "key_scenes" in video_analysis:
                    scenes = video_analysis["key_scenes"]
                if "detected_objects" in video_analysis:
                    objects = video_analysis["detected_objects"]
                if "activities" in video_analysis:
                    activities = video_analysis["activities"]

            # 최소 하나의 feature가 추출된 경우만 VideoFeatures 반환
            if any([keywords, scenes, objects, activities, description]):
                return VideoFeatures(
                    keywords=keywords, scenes=scenes, objects=objects, activities=activities, description=description
                )
            return None

        except Exception as e:
            logger.error(f"Video feature extraction failed: {e}")
            return None

    async def _extract_audio_features(self, audio_data: Dict[str, Any], element_types: List[str]) -> Optional[AudioFeatures]:
        """오디오 모달리티에서 특징 추출"""
        try:
            # 오디오 관련 element_types 모두 비활성화됨
            # 비활성화된 타입: "speech", "stt", "music", "sound_effect", "ambient"
            return None
            # if not any(t in element_types for t in ["speech", "stt", "music", "sound_effect", "ambient"]):
            #     return None

            if "base64_data" not in audio_data:
                return None

            base64_audio = audio_data["base64_data"]
            content_type = audio_data["content_type"]

            keywords = None
            entities = None
            sounds = None
            audio_type = None
            transcription = None

            # LLM을 통한 오디오 분석
            audio_analysis = await self._analyze_audio_with_llm(base64_audio, content_type)

            if audio_analysis:
                # STT 결과에서 키워드 추출
                if "transcription" in audio_analysis and audio_analysis["transcription"]:
                    transcription = audio_analysis["transcription"]

                    stt_keywords = await self.feature_extraction_client.extract_keywords(transcription)
                    if stt_keywords:
                        keywords = stt_keywords

                    # STT 결과에서 엔티티 추출
                    stt_entities = await self.feature_extraction_client.extract_entities(transcription)
                    if stt_entities:
                        entities = stt_entities

                # 오디오 특징 정보 직접 활용
                if "detected_sounds" in audio_analysis:
                    sounds = audio_analysis["detected_sounds"]
                if "type" in audio_analysis:
                    audio_type = audio_analysis["type"]

            # 최소 하나의 feature가 추출된 경우만 AudioFeatures 반환
            if any([keywords, entities, sounds, audio_type, transcription]):
                return AudioFeatures(
                    keywords=keywords, entities=entities, sounds=sounds, audio_type=audio_type, transcription=transcription
                )
            return None

        except Exception as e:
            logger.error(f"Audio feature extraction failed: {e}")
            return None

    async def _analyze_video_with_llm(self, base64_video: str, content_type: str) -> Optional[Dict[str, Any]]:
        """LLM을 통한 비디오 분석 - llm_client로 통합됨"""
        return await self.llm_client.analyze_video_features(base64_video, content_type)

    async def _analyze_audio_with_llm(self, base64_audio: str, content_type: str) -> Optional[Dict[str, Any]]:
        """LLM을 통한 오디오 분석 - llm_client로 통합됨"""
        return await self.llm_client.analyze_audio_features(base64_audio, content_type)
