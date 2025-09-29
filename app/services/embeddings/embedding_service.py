from typing import Any, Dict, List, Optional

from loguru import logger

from app.clients.embedding_client import EmbeddingClient
from app.models.features import MultimodalFeatures


class EmbeddingService:
    """임베딩 생성 및 선택을 담당하는 서비스"""

    def __init__(self, embedding_client: EmbeddingClient = None):
        self.embedding_client = embedding_client or EmbeddingClient()
        
        # Define element_type to modality mapping for embedding selection
        self.text_element_types = [
            "paragraph", "title", "summary", "stt", "caption", 
            "scene", "ocr", "table", "translation"
        ]
        self.image_element_types = [
            "origin", "cropped", "detected_object", "chart", 
            "diagram", "keyframe", "thumbnail"
        ]
        self.video_element_types = ["clip", "segment"]
        self.audio_element_types = ["speech", "music", "sound_effect", "ambient"]

    async def generate_multimodal_embeddings(
            self,
            modalities_data: Dict[str, Any],
            features: MultimodalFeatures = None
    ) -> Dict[str, List[float]]:
        """모든 모달리티와 추출된 특징들에서 임베딩 생성"""
        embeddings = {}

        try:
            # 1. 텍스트 임베딩
            if "text" in modalities_data:
                text_query = modalities_data["text"]["query"]
                text_embedding = await self.embedding_client.get_text_embedding(text_query)
                if text_embedding:
                    embeddings["text"] = text_embedding

            # 2. 이미지 임베딩
            if "image" in modalities_data and "base64_data" in modalities_data["image"]:
                import base64
                image_bytes = base64.b64decode(modalities_data["image"]["base64_data"])
                image_embedding = await self.embedding_client.get_image_embedding(image_bytes)
                if image_embedding:
                    embeddings["image"] = image_embedding

            # 3. 비디오 임베딩 (첫 프레임 또는 키프레임 사용)
            if "video" in modalities_data and "base64_data" in modalities_data["video"]:
                import base64
                video_bytes = base64.b64decode(modalities_data["video"]["base64_data"])
                video_embedding = await self.embedding_client.get_video_embedding(video_bytes)
                if video_embedding:
                    embeddings["video"] = video_embedding

            # 4. 오디오 임베딩
            if "audio" in modalities_data and "base64_data" in modalities_data["audio"]:
                import base64
                audio_bytes = base64.b64decode(modalities_data["audio"]["base64_data"])
                audio_embedding = await self.embedding_client.get_audio_embedding(audio_bytes)
                if audio_embedding:
                    embeddings["audio"] = audio_embedding

            # 5. 추출된 특징들에서 임베딩 생성
            if features:
                feature_embeddings = await self._generate_feature_embeddings(features)
                embeddings.update(feature_embeddings)

            logger.debug(f"Generated embeddings for: {list(embeddings.keys())}")
            return embeddings

        except Exception as e:
            logger.error(f"Multimodal embedding generation failed: {e}")
            return {}

    async def _generate_feature_embeddings(self, features: MultimodalFeatures) -> Dict[str, List[float]]:
        """추출된 특징들에서 임베딩 생성"""
        feature_embeddings = {}

        try:
            # 텍스트 특징 임베딩
            if features.text:
                if features.text.summary:
                    summary_embedding = await self.embedding_client.get_text_embedding(features.text.summary)
                    if summary_embedding:
                        feature_embeddings["text_summary"] = summary_embedding

                # 키워드들을 텍스트로 결합하여 임베딩
                if features.text.keywords:
                    keywords_text = self._extract_keywords_text(features.text.keywords)
                    if keywords_text:
                        keywords_embedding = await self.embedding_client.get_text_embedding(keywords_text)
                        if keywords_embedding:
                            feature_embeddings["text_keywords"] = keywords_embedding

                # 엔티티들을 텍스트로 결합하여 임베딩
                if features.text.entities:
                    entities_text = self._extract_entities_text(features.text.entities)
                    if entities_text:
                        entities_embedding = await self.embedding_client.get_text_embedding(entities_text)
                        if entities_embedding:
                            feature_embeddings["text_entities"] = entities_embedding

            # 이미지 특징 임베딩
            if features.image:
                if features.image.caption:
                    caption_embedding = await self.embedding_client.get_text_embedding(features.image.caption)
                    if caption_embedding:
                        feature_embeddings["image_caption"] = caption_embedding

                if features.image.objects:
                    objects_text = self._extract_objects_text(features.image.objects)
                    if objects_text:
                        objects_embedding = await self.embedding_client.get_text_embedding(objects_text)
                        if objects_embedding:
                            feature_embeddings["image_objects"] = objects_embedding

            # 비디오 특징 임베딩
            if features.video:
                if features.video.description:
                    video_desc_embedding = await self.embedding_client.get_text_embedding(features.video.description)
                    if video_desc_embedding:
                        feature_embeddings["video_description"] = video_desc_embedding

                if features.video.scenes:
                    scenes_text = " ".join(features.video.scenes)
                    scenes_embedding = await self.embedding_client.get_text_embedding(scenes_text)
                    if scenes_embedding:
                        feature_embeddings["video_scenes"] = scenes_embedding

                if features.video.activities:
                    activities_text = " ".join(features.video.activities)
                    activities_embedding = await self.embedding_client.get_text_embedding(activities_text)
                    if activities_embedding:
                        feature_embeddings["video_activities"] = activities_embedding

            # 오디오 특징 임베딩
            if features.audio:
                if features.audio.transcription:
                    transcription_embedding = await self.embedding_client.get_text_embedding(
                        features.audio.transcription)
                    if transcription_embedding:
                        feature_embeddings["audio_transcription"] = transcription_embedding

                if features.audio.sounds:
                    sounds_text = " ".join(features.audio.sounds)
                    sounds_embedding = await self.embedding_client.get_text_embedding(sounds_text)
                    if sounds_embedding:
                        feature_embeddings["audio_sounds"] = sounds_embedding

            return feature_embeddings

        except Exception as e:
            logger.error(f"Feature embedding generation failed: {e}")
            return {}

    def _extract_keywords_text(self, keywords_data: List[Dict[str, Any]]) -> str:
        """키워드 데이터에서 텍스트 추출"""
        try:
            if isinstance(keywords_data, dict) and "keywords" in keywords_data:
                keywords_list = keywords_data["keywords"]
            else:
                keywords_list = keywords_data

            keywords = []
            for kw in keywords_list[:10]:  # 상위 10개만 사용
                if isinstance(kw, dict) and "word" in kw:
                    keywords.append(kw["word"])
                elif isinstance(kw, str):
                    keywords.append(kw)

            return " ".join(keywords)
        except Exception:
            return ""

    def _extract_entities_text(self, entities_data: List[Dict[str, Any]]) -> str:
        """엔티티 데이터에서 텍스트 추출"""
        try:
            entities = []
            for entity in entities_data[:10]:  # 상위 10개만 사용
                if isinstance(entity, dict) and "text" in entity:
                    entities.append(entity["text"])
                elif isinstance(entity, dict) and "name" in entity:
                    entities.append(entity["name"])
                elif isinstance(entity, str):
                    entities.append(entity)

            return " ".join(entities)
        except Exception:
            return ""

    def _extract_objects_text(self, objects_data: List[Dict[str, Any]]) -> str:
        """객체 데이터에서 텍스트 추출"""
        try:
            objects = []
            for obj in objects_data[:10]:  # 상위 10개만 사용
                if isinstance(obj, dict) and "name" in obj:
                    objects.append(obj["name"])
                elif isinstance(obj, dict) and "label" in obj:
                    objects.append(obj["label"])
                elif isinstance(obj, str):
                    objects.append(obj)

            return " ".join(objects)
        except Exception:
            return ""

    async def generate_enhanced_embeddings(
            self,
            query: str,
            features: MultimodalFeatures
    ) -> Dict[str, List[float]]:
        """특징을 활용한 향상된 임베딩 생성"""
        embeddings = {}

        try:
            # 기본 텍스트 임베딩 생성
            text_embedding = await self.embedding_client.get_text_embedding(query)
            if text_embedding:
                embeddings["text"] = text_embedding

            # 추출된 특징을 사용한 향상된 임베딩 생성
            if features.has_any_features():
                enhanced_query = self._build_enhanced_query_text(query, features)
                if enhanced_query and enhanced_query != query:
                    enhanced_embedding = await self.embedding_client.get_text_embedding(enhanced_query)
                    if enhanced_embedding:
                        # 향상된 임베딩이 있으면 사용, 없으면 기본 임베딩 유지
                        embeddings["text"] = enhanced_embedding

            logger.debug(f"Generated enhanced embeddings for modalities: {list(embeddings.keys())}")
            return embeddings

        except Exception as e:
            logger.error(f"Enhanced embedding generation failed: {e}")
            return {}

    def _build_enhanced_query_text(self, query: str, features: MultimodalFeatures) -> str:
        """특징을 활용하여 향상된 쿼리 텍스트 생성"""
        enhanced_parts = [query]

        # 텍스트 특징에서 키워드 추출
        if features.text and features.text.keywords:
            keywords_list = features.text.keywords.get("keywords", []) if isinstance(features.text.keywords,
                                                                                     dict) else []
            keywords_text = " ".join([kw.get("word", "") for kw in keywords_list[:5] if isinstance(kw, dict)])
            if keywords_text:
                enhanced_parts.append(keywords_text)

        # 이미지 캡션 추가
        if features.image and features.image.caption:
            enhanced_parts.append(features.image.caption[:100])  # 캡션이 너무 길지 않도록 제한

        # 비디오 설명 추가
        if features.video and features.video.description:
            enhanced_parts.append(features.video.description[:100])

        # 오디오 전사 추가
        if features.audio and features.audio.transcription:
            enhanced_parts.append(features.audio.transcription[:100])

        enhanced_query = " ".join(enhanced_parts)

        # 너무 길어지지 않도록 제한
        if len(enhanced_query) > 500:
            enhanced_query = enhanced_query[:500]

        return enhanced_query

    def select_for_element_type(
        self, 
        element_type: str, 
        embeddings: Optional[Dict[str, List[float]]]
    ) -> Optional[Dict[str, List[float]]]:
        """Select appropriate embedding based on element_type"""
        if not embeddings:
            return None
        
        # Select embedding based on element_type with fallback priority
        if element_type in self.text_element_types:
            return self._select_with_fallback(embeddings, ["text", "image", "video", "audio"])
        elif element_type in self.image_element_types:
            return self._select_with_fallback(embeddings, ["image", "text", "video", "audio"])
        elif element_type in self.video_element_types:
            return self._select_with_fallback(embeddings, ["video", "image", "text", "audio"])
        elif element_type in self.audio_element_types:
            return self._select_with_fallback(embeddings, ["audio", "text", "image", "video"])
        
        # If no match, return first available embedding
        for key, value in embeddings.items():
            return {key: value}
        
        return None
    
    def _select_with_fallback(
        self, 
        embeddings: Dict[str, List[float]], 
        priority_order: List[str]
    ) -> Optional[Dict[str, List[float]]]:
        """Select embedding with fallback priority"""
        for key in priority_order:
            if key in embeddings:
                return {key: embeddings[key]}
        return None
