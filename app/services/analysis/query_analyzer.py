from typing import Any, Dict, List, Optional

from loguru import logger

from app.clients.llm_client import LLMClient


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

    async def expand_query(
        self, 
        query: str, 
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """텍스트 쿼리를 확장하여 더 효과적인 검색 쿼리들을 생성.
        
        Query Decomposition, Query Rewriting, Semantic Expansion을 동시에 수행
        
        Args:
            query: 원본 사용자 쿼리
            context: 검색 컨텍스트 정보 (도메인, 사용자 유형 등)
            
        Returns:
            확장된 쿼리들과 분석 결과를 포함한 딕셔너리
        """
        try:
            result = await self.llm_client.expand_query(query, context)
            if result:
                logger.info(f"Query expansion successful for: '{query[:50]}...'")
                return result
            else:
                logger.warning("LLM query expansion returned None, using original query only")
                return None
        except Exception as e:
            logger.error(f"Query expansion failed: {e}, using original query only")
            return None

