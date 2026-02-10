from typing import Any, Dict, List, Optional, Tuple

from loguru import logger

from app.clients.llm_client import LLMClient
from app.core.config import weighting_config


class QueryAnalyzer:
    """쿼리 분석 및 검색 쿼리 빌딩을 담당하는 서비스"""

    def __init__(self, llm_client: LLMClient = None):
        self.llm_client = llm_client or LLMClient()

    async def analyze_query_intent(
        self, query: str, available_element_types: List[str], input_modalities: Optional[List[str]] = None
    ) -> Optional[Dict[str, Any]]:
        """쿼리 의도 분석 - 안정적인 fallback 우선 + LLM 보조"""
        # 먼저 안정적인 fallback 분석 실행
        fallback_result = self._fallback_query_analysis(query, available_element_types, input_modalities)
        
        # LLM 분석도 시도해보지만 실패해도 문제없음
        try:
            llm_result = await self.llm_client.analyze_query_intent(query, available_element_types, input_modalities)
            if llm_result and llm_result.get("element_type_weights"):
                # 유의미한 가중치가 있는지 확인
                meaningful_weights = {k: v for k, v in llm_result["element_type_weights"].items() if v > 0.0}
                if meaningful_weights:
                    llm_result["fallback_reasoning"] = fallback_result.get("reasoning", "")
                    logger.info(f"Using LLM query analysis: {len(meaningful_weights)} weighted types")
                    return llm_result
        except Exception as e:
            logger.debug(f"LLM query analysis failed: {e}")
        
        # LLM이 실패하거나 유효하지 않으면 안정적인 fallback 사용
        logger.info("Using enhanced fallback query analysis")
        return fallback_result

    def _fallback_query_analysis(
        self, query: str, available_element_types: List[str], input_modalities: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """간단한 휴리스틱을 사용한 폴백 쿼리 분석 - 가중치 기반"""
        # Define modality-specific element types
        modality_element_mapping = {"text": ["paragraph", "summary"], "image": ["caption", "origin"]}

        # Initialize all weights to 0.0
        element_weights = {element_type: 0.0 for element_type in available_element_types}

        # Filter available_element_types based on input modalities
        relevant_types = set()
        if input_modalities:
            for modality in input_modalities:
                if modality in modality_element_mapping:
                    relevant_types.update(modality_element_mapping[modality])
            # Only consider element types that are both relevant and available
            relevant_available_types = [t for t in available_element_types if t in relevant_types]
        else:
            relevant_available_types = available_element_types

        query_lower = query.lower()

        # 향상된 키워드 기반 휴리스틱으로 가중치 설정
        if input_modalities and "text" in input_modalities:
            # 요약 관련 키워드들 (더 포괄적)
            summary_keywords = ["요약", "summary", "정리", "개요", "핵심", "간략", "압축", "추출", "핵심내용"]
            # 일반 텍스트 내용 키워드들
            content_keywords = ["텍스트", "text", "문서", "document", "내용", "본문", "글", "문단", "전문", "상세"]
            
            # 키워드 매칭 점수 계산
            summary_score = sum(1 for keyword in summary_keywords if keyword in query_lower)
            content_score = sum(1 for keyword in content_keywords if keyword in query_lower)
            
            if summary_score > 0:
                # 요약 관련 쿼리 - summary 우선
                if "summary" in relevant_available_types:
                    element_weights["summary"] = min(1.0, weighting_config.TEXT_SUMMARY_BASE_WEIGHT + (summary_score * weighting_config.TEXT_SUMMARY_BOOST))
                if "paragraph" in relevant_available_types:
                    element_weights["paragraph"] = max(weighting_config.TEXT_MIN_WEIGHT, weighting_config.TEXT_PARAGRAPH_BASE_WEIGHT - (summary_score * weighting_config.TEXT_PARAGRAPH_PENALTY))
            elif content_score > 0:
                # 일반 텍스트 내용 관련 쿼리 - paragraph 우선
                if "paragraph" in relevant_available_types:
                    element_weights["paragraph"] = min(1.0, weighting_config.TEXT_SUMMARY_BASE_WEIGHT + (content_score * weighting_config.TEXT_SUMMARY_BOOST))
                if "summary" in relevant_available_types:
                    element_weights["summary"] = max(weighting_config.TEXT_MIN_WEIGHT, weighting_config.TEXT_PARAGRAPH_BASE_WEIGHT - (content_score * weighting_config.TEXT_PARAGRAPH_PENALTY))
            else:
                # 키워드가 없으면 균등하게 분배하되 paragraph 약간 우선
                if "paragraph" in relevant_available_types:
                    element_weights["paragraph"] = weighting_config.TEXT_PARAGRAPH_DEFAULT
                if "summary" in relevant_available_types:
                    element_weights["summary"] = weighting_config.TEXT_SUMMARY_DEFAULT

        if input_modalities and "image" in input_modalities:
            # 이미지 설명/캡션 관련 키워드들
            caption_keywords = ["설명", "캡션", "caption", "묘사", "describe", "보여주", "나타내", "표현"]
            # 이미지 자체 관련 키워드들
            image_keywords = ["이미지", "image", "사진", "그림", "시각", "picture", "photo", "원본", "origin"]
            
            # 키워드 매칭 점수 계산
            caption_score = sum(1 for keyword in caption_keywords if keyword in query_lower)
            image_score = sum(1 for keyword in image_keywords if keyword in query_lower)
            
            if caption_score > 0:
                # 이미지 설명/캡션 관련 쿼리 - 하지만 여전히 origin을 더 우선시
                if "origin" in relevant_available_types:
                    element_weights["origin"] = weighting_config.IMAGE_ORIGIN_WEIGHT  # origin을 항상 최고 우선순위로
                if "caption" in relevant_available_types:
                    element_weights["caption"] = min(weighting_config.IMAGE_CAPTION_MAX_WEIGHT, weighting_config.IMAGE_CAPTION_BASE_WEIGHT + (caption_score * weighting_config.IMAGE_CAPTION_BOOST))  # caption 가중치 대폭 감소
            elif image_score > 0:
                # 이미지 자체 관련 쿼리 - origin 강력히 우선
                if "origin" in relevant_available_types:
                    element_weights["origin"] = weighting_config.IMAGE_ORIGIN_WEIGHT  # 최대 가중치
                if "caption" in relevant_available_types:
                    element_weights["caption"] = weighting_config.IMAGE_CAPTION_MIN_WEIGHT  # 매우 낮은 가중치
            else:
                # 키워드가 없으면 origin을 강력히 우선시 (이미지 검색의 기본 목적)
                if "origin" in relevant_available_types:
                    element_weights["origin"] = weighting_config.IMAGE_ORIGIN_WEIGHT  # 최대 가중치
                if "caption" in relevant_available_types:
                    element_weights["caption"] = weighting_config.IMAGE_CAPTION_BASE_WEIGHT  # 낮은 가중치

        # 모달리티 정보가 없거나 가중치가 설정되지 않은 경우 기본값 설정
        meaningful_weights = {k: v for k, v in element_weights.items() if v > 0.0}
        if not meaningful_weights:
            if input_modalities:
                for modality in input_modalities:
                    if modality in weighting_config.MODALITY_FALLBACK_WEIGHTS:
                        for element_type, weight in weighting_config.MODALITY_FALLBACK_WEIGHTS[modality].items():
                            if element_type in available_element_types:
                                element_weights[element_type] = weight
            else:
                # 모달리티 정보가 없으면 모든 타입에 균등한 중간 가중치
                for element_type in available_element_types:
                    element_weights[element_type] = weighting_config.UNIVERSAL_DEFAULT_WEIGHT

        # Get selected types for backward compatibility
        selected_types = [k for k, v in element_weights.items() if v > 0.0]

        return {
            "element_type_weights": element_weights,
            "selected_element_types": selected_types,  # backward compatibility
            "reasoning": f"Fallback analysis based on keywords in query: {query[:50]}...",
            "confidence": 0.6,
        }

    def create_default_query_analysis(
        self, available_element_types: List[str], reason: str = "No text query provided"
    ) -> Dict[str, Any]:
        """텍스트 쿼리가 없을 때 기본 쿼리 분석 생성 - 가중치 기반"""
        # 모든 타입에 동일한 중간 가중치 부여
        element_weights = {element_type: weighting_config.UNIVERSAL_DEFAULT_WEIGHT for element_type in available_element_types}
        
        return {
            "element_type_weights": element_weights,
            "selected_element_types": available_element_types,  # backward compatibility
            "reasoning": f"{reason}, using all element types with equal weights",
            "confidence": 0.5,
        }

    async def expand_query(self, query: str, context: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
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
                logger.debug(f"Query expansion successful for: '{query[:50]}...'")
                return result
            else:
                logger.warning("LLM query expansion returned None, using original query only")
                return None
        except Exception as e:
            logger.error(f"Query expansion failed: {e}, using original query only")
            return None

    async def process_query_analysis(
        self, text_query: Optional[str], available_element_types: List[str], input_modalities: Optional[List[str]] = None
    ) -> Tuple[Dict[str, Any], List[str]]:
        """쿼리 확장 및 의도 분석을 통합 처리"""
        if text_query:
            # 쿼리 확장
            expanded_queries, expansion_result = await self._expand_query(text_query)
            # 의도 분석 (입력 모달리티 고려)
            query_analysis = await self._analyze_query_intent(
                expanded_queries, expansion_result, input_modalities, available_element_types
            )
        else:
            query_analysis = self.create_default_query_analysis(available_element_types)
            expanded_queries = ["multimodal search"]

        return query_analysis, expanded_queries

    async def _expand_query(self, text_query: str) -> Tuple[List[str], Optional[Dict[str, Any]]]:
        """쿼리 확장 수행"""
        expansion_result = await self.expand_query(text_query)

        if expansion_result and expansion_result.get("final_queries"):
            final_queries = expansion_result["final_queries"][:3]  # 상위 3개 사용
            expanded_queries = [q["query"] for q in final_queries]

            logger.info(f"Query expansion completed: {len(final_queries)} variants → [{', '.join(expanded_queries)}]")
            return expanded_queries, expansion_result
        else:
            logger.warning(f"Query expansion failed, using original: '{text_query}'")
            return [text_query], None

    async def _analyze_query_intent(
        self,
        expanded_queries: List[str],
        expansion_result: Optional[Dict[str, Any]],
        input_modalities: Optional[List[str]],
        available_element_types: List[str],
    ) -> Dict[str, Any]:
        """의도 분석 수행"""
        primary_query = expanded_queries[0] if expanded_queries else "multimodal search"

        query_analysis = await self.analyze_query_intent(primary_query, available_element_types, input_modalities)

        if not query_analysis:
            logger.warning(f"Query analysis failed for: '{primary_query}'. Using default.")
            query_analysis = self.create_default_query_analysis(available_element_types, "Query analysis failed")

        # 확장 정보를 쿼리 분석에 추가
        if expansion_result:
            query_analysis["expansion_analysis"] = {
                "applied_techniques": expansion_result.get("applied_techniques", []),
                "expansion_summary": expansion_result.get("expansion_summary", ""),
                "has_dependency": expansion_result.get("has_dependency", False),
                "dependency_reason": expansion_result.get("dependency_reason", ""),
            }
            query_analysis["expansion_used"] = len(expanded_queries) > 1

        return query_analysis

    def enrich_query_with_context(self, query: str, context: Dict[str, Any]) -> str:
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

    def extract_context_from_results(self, search_results: Dict[str, Any]) -> Dict[str, Any]:
        """검색 결과에서 다음 쿼리를 위한 컨텍스트 추출"""
        context = {"keywords": [], "entities": [], "concepts": []}

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
                        context["entities"].extend(
                            [e.get("text", e) if isinstance(e, dict) else e for e in features["entities"][:2]]
                        )

        # 중복 제거 및 빈도수 기반 정렬
        context["keywords"] = list(dict.fromkeys(context["keywords"]))[:10]
        context["entities"] = list(dict.fromkeys(context["entities"]))[:5]
        context["concepts"] = list(dict.fromkeys(context["concepts"]))[:5]

        return context
