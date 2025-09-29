from typing import Dict, List, Any
from loguru import logger

from app.clients.embedding_client import EmbeddingClient
from app.models.features import MultimodalFeatures


class EmbeddingService:
    """임베딩 생성을 담당하는 서비스"""
    
    def __init__(self, embedding_client: EmbeddingClient = None):
        self.embedding_client = embedding_client or EmbeddingClient()

    async def generate_multimodal_embeddings(
        self, 
        modalities_data: Dict[str, Any]
    ) -> Dict[str, List[float]]:
        """멀티모달 데이터에서 임베딩 생성"""
        embeddings = {}

        try:
            # 텍스트 임베딩
            if "text" in modalities_data:
                text_query = modalities_data["text"]["query"]
                text_embedding = await self.embedding_client.get_text_embedding(text_query)
                if text_embedding:
                    embeddings["text"] = text_embedding

            # 멀티모달 임베딩은 특징 추출 단계에서 분석된 결과를 활용
            # 여기서는 단순히 텍스트 기반 임베딩만 생성

            logger.debug(f"Generated embeddings for modalities: {list(embeddings.keys())}")
            return embeddings

        except Exception as e:
            logger.error(f"Multimodal embedding generation failed: {e}")
            return {}

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
            keywords_list = features.text.keywords.get("keywords", []) if isinstance(features.text.keywords, dict) else []
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