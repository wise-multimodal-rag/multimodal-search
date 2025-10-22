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
        llm_client: LLMClient = None
    ):
        self.feature_extraction_client = feature_extraction_client or FeatureExtractionClient()
        self.embedding_client = embedding_client or EmbeddingClient()
        self.llm_client = llm_client or LLMClient()

    async def extract_features(
        self, 
        modalities_data: Dict[str, Any], 
        element_types: List[str]
    ) -> MultimodalFeatures:
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
                text=text_features,
                image=image_features,
                video=video_features,
                audio=audio_features
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

    async def _extract_text_features(
        self, 
        text_data: Dict[str, Any], 
        element_types: List[str]
    ) -> Optional[TextFeatures]:
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
                    classification=None  # TODO: 추후 텍스트 분류 기능 추가 예정
                )
            return None

        except Exception as e:
            logger.error(f"Text feature extraction failed: {e}")
            return None

    async def _extract_image_features(
        self, 
        image_data: Dict[str, Any], 
        element_types: List[str]
    ) -> Optional[ImageFeatures]:
        """이미지 모달리티에서 특징 추출 - element_type별로 개별 처리"""
        try:
            # 이미지 관련 element_types가 선택된 경우에만 분석 수행 (현재 활성: caption, origin)
            if not any(t in element_types for t in ["caption", "origin"]):
                # 비활성화된 타입: "cropped", "detected_object", "chart", "diagram"
                return None

            if "base64_data" not in image_data:
                return None

            base64_image = image_data["base64_data"]
            import base64
            image_bytes = base64.b64decode(base64_image)
            
            # element_type별로 개별 feature 추출
            caption_text = None
            origin_data = None
            
            # caption: 이미지 캡션 생성
            if "caption" in element_types:
                caption_result = await self.embedding_client.generate_image_caption(image_bytes)
                if caption_result and "caption" in caption_result:
                    caption_text = caption_result["caption"]
            
            # origin: OpenSearch에서 검색용이므로 별도 임베딩 불필요 (원본 image 임베딩 사용)
            # if "origin" in element_types:
            #     origin_data = base64_image  # 원본 base64 데이터
            
            # 비활성화된 기능들:
            # 객체 탐지 (detected_object), 잘린 이미지 (cropped), 차트 (chart), 다이어그램 (diagram)
            
            # 추출된 feature가 있는 경우만 반환
            if caption_text:
                return ImageFeatures(
                    caption=caption_text,
                    objects=None  # origin은 원본 image와 동일하므로 중복 제거
                )
            return None

        except Exception as e:
            logger.error(f"Image feature extraction failed: {e}")
            return None

    async def _extract_video_features(
        self, 
        video_data: Dict[str, Any], 
        element_types: List[str]
    ) -> Optional[VideoFeatures]:
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
                    keywords=keywords,
                    scenes=scenes,
                    objects=objects,
                    activities=activities,
                    description=description
                )
            return None

        except Exception as e:
            logger.error(f"Video feature extraction failed: {e}")
            return None

    async def _extract_audio_features(
        self, 
        audio_data: Dict[str, Any], 
        element_types: List[str]
    ) -> Optional[AudioFeatures]:
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
                    keywords=keywords,
                    entities=entities,
                    sounds=sounds,
                    audio_type=audio_type,
                    transcription=transcription
                )
            return None

        except Exception as e:
            logger.error(f"Audio feature extraction failed: {e}")
            return None

    async def _analyze_video_with_llm(self, base64_video: str, content_type: str) -> Optional[Dict[str, Any]]:
        """LLM을 통한 비디오 분석"""
        try:
            VIDEO_ANALYSIS_PROMPT = """이 비디오를 분석하여 다음 정보를 JSON 형식으로 제공하세요:
{
    "description": "비디오에 대한 간단한 설명",
    "key_scenes": ["장면1 설명", "장면2 설명"],
    "detected_objects": ["객체1", "객체2"],
    "activities": ["활동1", "활동2"],
    "dominant_colors": ["색상1", "색상2"],
    "estimated_duration": "추정 길이(초)"
}"""

            messages = [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": VIDEO_ANALYSIS_PROMPT},
                        {
                            "type": "video_url",
                            "video_url": {
                                "url": f"data:{content_type};base64,{base64_video}"
                            }
                        }
                    ]
                }
            ]

            response = await self.llm_client.complete(messages, temperature=0.3, max_tokens=1000)
            if response:
                import json
                try:
                    return json.loads(response.strip())
                except json.JSONDecodeError:
                    return {"description": response, "analysis_type": "text_only"}
            return None

        except Exception as e:
            logger.error(f"Video analysis with LLM failed: {e}")
            return None

    async def _analyze_audio_with_llm(self, base64_audio: str, content_type: str) -> Optional[Dict[str, Any]]:
        """LLM을 통한 오디오 분석"""
        try:
            AUDIO_ANALYSIS_PROMPT = """이 오디오를 분석하여 다음 정보를 JSON 형식으로 제공하세요:
{
    "transcription": "음성 내용 (있다면)",
    "type": "speech|music|sound_effect|ambient|mixed",
    "detected_sounds": ["소리1", "소리2"],
    "language": "언어 (있다면)",
    "quality": "음질 평가",
    "duration_estimate": "추정 길이(초)"
}"""

            messages = [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": AUDIO_ANALYSIS_PROMPT},
                        {
                            "type": "audio_url",
                            "audio_url": {
                                "url": f"data:{content_type};base64,{base64_audio}"
                            }
                        }
                    ]
                }
            ]

            response = await self.llm_client.complete(messages, temperature=0.3, max_tokens=1000)
            if response:
                import json
                try:
                    return json.loads(response.strip())
                except json.JSONDecodeError:
                    return {"description": response, "analysis_type": "text_only"}
            return None

        except Exception as e:
            logger.error(f"Audio analysis with LLM failed: {e}")
            return None