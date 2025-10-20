from typing import Any, Dict, List, Optional, Union

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
            # 병렬 임베딩 생성을 위한 태스크 준비
            embedding_tasks = []
            task_names = []
            import base64

            # 1. 텍스트 임베딩
            if "text" in modalities_data:
                text_query = modalities_data["text"]["query"]
                embedding_tasks.append(self.embedding_client.get_text_embedding(text_query))
                task_names.append("text")

            # 2. 이미지 임베딩
            if "image" in modalities_data and "base64_data" in modalities_data["image"]:
                try:
                    image_bytes = base64.b64decode(modalities_data["image"]["base64_data"])
                    embedding_tasks.append(self.embedding_client.get_image_embedding(image_bytes))
                    task_names.append("image")
                except Exception as e:
                    logger.warning(f"Failed to decode image data: {e}")

            # 3. 비디오 임베딩 (첫 프레임 또는 키프레임 사용)
            if "video" in modalities_data and "base64_data" in modalities_data["video"]:
                try:
                    video_bytes = base64.b64decode(modalities_data["video"]["base64_data"])
                    embedding_tasks.append(self.embedding_client.get_video_embedding(video_bytes))
                    task_names.append("video")
                except Exception as e:
                    logger.warning(f"Failed to decode video data: {e}")

            # 4. 오디오 임베딩
            if "audio" in modalities_data and "base64_data" in modalities_data["audio"]:
                try:
                    audio_bytes = base64.b64decode(modalities_data["audio"]["base64_data"])
                    embedding_tasks.append(self.embedding_client.get_audio_embedding(audio_bytes))
                    task_names.append("audio")
                except Exception as e:
                    logger.warning(f"Failed to decode audio data: {e}")

            # 병렬 실행 및 결과 처리
            if embedding_tasks:
                import asyncio
                embedding_results = await asyncio.gather(*embedding_tasks, return_exceptions=True)
                
                for i, result in enumerate(embedding_results):
                    task_name = task_names[i]
                    if isinstance(result, Exception):
                        logger.warning(f"Embedding generation failed for {task_name}: {result}")
                    elif result:
                        embeddings[task_name] = result

            # 5. 추출된 특징들에서 임베딩 생성 (이미 병렬 처리됨)
            if features:
                try:
                    feature_embeddings = await self._generate_feature_embeddings(features)
                    embeddings.update(feature_embeddings)
                except Exception as e:
                    logger.warning(f"Feature embedding generation failed: {e}")

            logger.info(f"Generated embeddings: {len(embeddings)} successful - {list(embeddings.keys())}")
            
            return embeddings

        except Exception as e:
            logger.error(f"Multimodal embedding generation failed: {e}")
            return {}

    async def _generate_feature_embeddings(self, features: MultimodalFeatures) -> Dict[str, List[float]]:
        """추출된 특징들에서 임베딩 생성 (병렬 처리 최적화)"""
        import asyncio
        
        embedding_tasks = []
        task_keys = []

        # 텍스트 특징 임베딩 태스크들 준비
        if features.text:
            if features.text.summary:
                embedding_tasks.append(self.embedding_client.get_text_embedding(features.text.summary))
                task_keys.append("text_summary")

            # 키워드들을 텍스트로 결합하여 임베딩
            if features.text.keywords:
                keywords_text = self._extract_keywords_text(features.text.keywords)
                if keywords_text:
                    embedding_tasks.append(self.embedding_client.get_text_embedding(keywords_text))
                    task_keys.append("text_keywords")

            # 엔티티들을 텍스트로 결합하여 임베딩
            if features.text.entities:
                entities_text = self._extract_entities_text(features.text.entities)
                if entities_text:
                    embedding_tasks.append(self.embedding_client.get_text_embedding(entities_text))
                    task_keys.append("text_entities")

        # 이미지 특징 임베딩 태스크들 준비
        if features.image:
            if features.image.caption:
                embedding_tasks.append(self.embedding_client.get_text_embedding(features.image.caption))
                task_keys.append("image_caption")

            if features.image.objects:
                objects_text = self._extract_objects_text(features.image.objects)
                if objects_text:
                    embedding_tasks.append(self.embedding_client.get_text_embedding(objects_text))
                    task_keys.append("image_objects")

        # 비디오 특징 임베딩 태스크들 준비
        if features.video:
            if features.video.description:
                embedding_tasks.append(self.embedding_client.get_text_embedding(features.video.description))
                task_keys.append("video_description")

            if features.video.scenes:
                scenes_text = " ".join(features.video.scenes)
                embedding_tasks.append(self.embedding_client.get_text_embedding(scenes_text))
                task_keys.append("video_scenes")

            if features.video.activities:
                activities_text = " ".join(features.video.activities)
                embedding_tasks.append(self.embedding_client.get_text_embedding(activities_text))
                task_keys.append("video_activities")

        # 오디오 특징 임베딩 태스크들 준비
        if features.audio:
            if features.audio.transcription:
                embedding_tasks.append(self.embedding_client.get_text_embedding(features.audio.transcription))
                task_keys.append("audio_transcription")

            if features.audio.sounds:
                sounds_text = " ".join(features.audio.sounds)
                embedding_tasks.append(self.embedding_client.get_text_embedding(sounds_text))
                task_keys.append("audio_sounds")

        # 모든 임베딩 태스크를 병렬로 실행
        if embedding_tasks:
            embedding_results = await asyncio.gather(*embedding_tasks, return_exceptions=True)
            
            feature_embeddings = {}
            for i, result in enumerate(embedding_results):
                if isinstance(result, Exception):
                    logger.warning(f"Embedding generation failed for {task_keys[i]}: {result}")
                elif result:
                    feature_embeddings[task_keys[i]] = result
            
            return feature_embeddings
        else:
            return {}

    def _extract_keywords_text(self, keywords_data: Union[List[Dict[str, Any]], Dict[str, Any]]) -> str:
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

