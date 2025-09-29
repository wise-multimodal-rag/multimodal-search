from typing import Any, Dict, List, Optional

from loguru import logger

from app.clients.llm_client import LLMClient
from app.models.features import MultimodalFeatures


class QueryAnalyzer:
    """쿼리 분석 및 검색 쿼리 빌딩을 담당하는 서비스"""
    
    def __init__(self, llm_client: LLMClient = None):
        self.llm_client = llm_client or LLMClient()

    async def analyze_query_intent(
        self, 
        query: str, 
        available_element_types: List[str]
    ) -> Optional[Dict[str, Any]]:
        """LLM을 사용하여 쿼리 의도 분석"""
        try:
            result = await self.llm_client.analyze_query_intent(query, available_element_types)
            if result:
                return result
            else:
                logger.warning("LLM query analysis returned None, using fallback strategy")
                return self._fallback_query_analysis(query, available_element_types)
        except Exception as e:
            logger.error(f"Query intent analysis failed: {e}, using fallback strategy")
            return self._fallback_query_analysis(query, available_element_types)

    def _fallback_query_analysis(
        self, 
        query: str, 
        available_element_types: List[str]
    ) -> Dict[str, Any]:
        """간단한 휴리스틱을 사용한 폴백 쿼리 분석"""
        query_lower = query.lower()
        selected_types = []

        # 키워드 기반 휴리스틱
        if any(word in query_lower for word in ["요약", "summary", "정리"]):
            selected_types.extend(["summary", "paragraph"])
        if any(word in query_lower for word in ["표", "table", "데이터", "data"]):
            selected_types.append("table")
        if any(word in query_lower for word in ["이미지", "image", "사진", "그림"]):
            selected_types.extend(["origin", "cropped", "detected_object", "chart", "diagram"])
        if any(word in query_lower for word in ["비디오", "video", "영상", "동영상"]):
            selected_types.extend(["clip", "segment", "keyframe", "thumbnail"])
        if any(word in query_lower for word in ["음성", "audio", "소리", "오디오"]):
            selected_types.extend(["speech", "music", "sound_effect"])
        if any(word in query_lower for word in ["텍스트", "text", "문서", "document"]):
            selected_types.extend(["paragraph", "title", "ocr"])

        # 특정 타입이 식별되지 않으면 합리적인 기본값 사용
        if not selected_types:
            selected_types = ["paragraph", "title", "summary", "origin", "chart"]

        # available_element_types에 있는 것만 필터링하고 중복 제거
        selected_types = [t for t in selected_types if t in available_element_types]
        selected_types = list(dict.fromkeys(selected_types))

        return {
            "selected_element_types": selected_types,
            "reasoning": f"Fallback analysis based on keywords in query: {query[:50]}...",
            "confidence": 0.6
        }

    async def build_enhanced_query(
        self,
        original_query: str,
        element_types: List[str],
        features: MultimodalFeatures
    ) -> Optional[str]:
        """LLM을 사용하여 향상된 검색 쿼리 빌드"""
        try:
            return await self.llm_client.build_search_query(original_query, element_types, features)
        except Exception as e:
            logger.error(f"Enhanced query building failed: {e}")
            return None

    def create_default_query_analysis(
        self, 
        available_element_types: List[str], 
        reason: str = "No text query provided"
    ) -> Dict[str, Any]:
        """텍스트 쿼리가 없을 때 기본 쿼리 분석 생성"""
        return {
            "selected_element_types": available_element_types,
            "reasoning": f"{reason}, using all element types",
            "confidence": 0.5
        }