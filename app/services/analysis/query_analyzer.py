from typing import Any, Dict, List, Optional, Tuple

from loguru import logger

from app.clients.llm_client import LLMClient


class QueryAnalyzer:
    """쿼리 분석 및 검색 쿼리 빌딩을 담당하는 서비스"""
    
    def __init__(self, llm_client: LLMClient = None):
        self.llm_client = llm_client or LLMClient()

    async def analyze_query_intent(
        self, 
        query: str, 
        available_element_types: List[str],
        input_modalities: Optional[List[str]] = None
    ) -> Optional[Dict[str, Any]]:
        """LLM을 사용하여 쿼리 의도 분석"""
        try:
            result = await self.llm_client.analyze_query_intent(query, available_element_types, input_modalities)
            if result:
                return result
            else:
                logger.warning("LLM query analysis returned None, using fallback strategy")
                return self._fallback_query_analysis(query, available_element_types, input_modalities)
        except Exception as e:
            logger.error(f"Query intent analysis failed: {e}, using fallback strategy")
            return self._fallback_query_analysis(query, available_element_types, input_modalities)

    def _fallback_query_analysis(
        self, 
        query: str, 
        available_element_types: List[str],
        input_modalities: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """간단한 휴리스틱을 사용한 폴백 쿼리 분석"""
        # Define modality-specific element types
        modality_element_mapping = {
            "text": ["paragraph", "summary"],
            "image": ["caption", "origin"]
        }
        
        # Filter available_element_types based on input modalities
        if input_modalities:
            relevant_types = set()
            for modality in input_modalities:
                if modality in modality_element_mapping:
                    relevant_types.update(modality_element_mapping[modality])
            # Only keep element types that are both relevant and available
            available_element_types = [t for t in available_element_types if t in relevant_types]
        
        query_lower = query.lower()
        selected_types = []

        # 키워드 기반 휴리스틱 (모달리티 고려)
        if input_modalities and "text" in input_modalities:
            # 텍스트 모달리티 전용 키워드
            if any(word in query_lower for word in ["요약", "summary", "정리"]):
                selected_types.extend(["summary", "paragraph"])
            elif any(word in query_lower for word in ["텍스트", "text", "문서", "document", "내용"]):
                selected_types.extend(["paragraph", "summary"])
            else:
                # 기본적으로 paragraph 우선
                selected_types.append("paragraph")
        
        if input_modalities and "image" in input_modalities:
            # 이미지 모달리티 전용 키워드
            if any(word in query_lower for word in ["이미지", "image", "사진", "그림", "시각"]):
                selected_types.extend(["origin", "caption"])
            elif any(word in query_lower for word in ["설명", "캡션", "caption"]):
                selected_types.extend(["caption", "origin"])
            else:
                # 기본적으로 origin 우선
                selected_types.extend(["origin", "caption"])

        # 특정 타입이 식별되지 않으면 모달리티별 기본값 사용
        if not selected_types:
            if input_modalities:
                if "text" in input_modalities:
                    selected_types.extend(["paragraph", "summary"])
                if "image" in input_modalities:
                    selected_types.extend(["origin", "caption"])
            else:
                # 모달리티 정보가 없으면 모든 가능한 타입 사용
                selected_types = ["paragraph", "summary", "origin", "caption"]

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
                logger.debug(f"Query expansion successful for: '{query[:50]}...'")
                return result
            else:
                logger.warning("LLM query expansion returned None, using original query only")
                return None
        except Exception as e:
            logger.error(f"Query expansion failed: {e}, using original query only")
            return None

    async def process_query_analysis(
        self, 
        text_query: Optional[str], 
        available_element_types: List[str],
        input_modalities: Optional[List[str]] = None
    ) -> Tuple[Dict[str, Any], List[str]]:
        """쿼리 확장 및 의도 분석을 통합 처리"""
        if text_query:
            # 쿼리 확장
            expanded_queries, expansion_result = await self._expand_query(text_query)
            # 의도 분석 (입력 모달리티 고려)
            query_analysis = await self._analyze_query_intent(expanded_queries, expansion_result, input_modalities, available_element_types)
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
        available_element_types: List[str]
    ) -> Dict[str, Any]:
        """의도 분석 수행"""
        primary_query = expanded_queries[0] if expanded_queries else "multimodal search"

        query_analysis = await self.analyze_query_intent(
            primary_query, available_element_types, input_modalities)

        if not query_analysis:
            logger.warning(f"Query analysis failed for: '{primary_query}'. Using default.")
            query_analysis = self.create_default_query_analysis(
                available_element_types, "Query analysis failed"
            )

        # 확장 정보를 쿼리 분석에 추가
        if expansion_result:
            query_analysis["expansion_analysis"] = {
                "applied_techniques": expansion_result.get("applied_techniques", []),
                "expansion_summary": expansion_result.get("expansion_summary", ""),
                "has_dependency": expansion_result.get("has_dependency", False),
                "dependency_reason": expansion_result.get("dependency_reason", "")
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
        context = {
            "keywords": [],
            "entities": [],
            "concepts": []
        }
        
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
                        context["entities"].extend([e.get("text", e) if isinstance(e, dict) else e for e in features["entities"][:2]])
        
        # 중복 제거 및 빈도수 기반 정렬
        context["keywords"] = list(dict.fromkeys(context["keywords"]))[:10]
        context["entities"] = list(dict.fromkeys(context["entities"]))[:5]
        context["concepts"] = list(dict.fromkeys(context["concepts"]))[:5]
        
        return context

