from typing import Any, Dict, List, Optional

import httpx
from loguru import logger

from app.core.config import settings
from app.core.security import security_manager


class LLMClient:
    def __init__(self):
        self.base_url = settings.litellm_url
        self.api_key = security_manager.get_api_key('LITELLM_API_KEY') or settings.litellm_api_key
        self.model = settings.litellm_model
        self.timeout = 60.0

    async def complete(
            self,
            messages: List[Dict[str, str]],
            temperature: float = 0.7,
            max_tokens: Optional[int] = None,
            force_json: bool = False
    ) -> Optional[str]:
        """Get completion from LLM"""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                payload = {
                    "model": self.model,
                    "messages": messages,
                    "temperature": temperature
                }

                if max_tokens:
                    payload["max_tokens"] = max_tokens

                # Gemini-specific settings - only force JSON when explicitly requested
                if "gemini" in self.model.lower() and force_json:
                    payload["response_format"] = {"type": "json_object"}
                    payload["extra_body"] = {
                        "generationConfig": {
                            "responseMimeType": "application/json"
                        }
                    }

                headers = {}
                if self.api_key and self.api_key != "your-api-key":
                    # LiteLLM might use different auth formats
                    if self.api_key.startswith("Bearer "):
                        headers["Authorization"] = self.api_key
                    else:
                        headers["Authorization"] = f"Bearer {self.api_key}"

                # 간결한 요청 로깅
                logger.debug(f"LLM request: model={payload.get('model')}, messages={len(payload.get('messages', []))}, temp={payload.get('temperature')}")

                response = await client.post(
                    f"{self.base_url}/v1/chat/completions",
                    json=payload,
                    headers=headers
                )
                response.raise_for_status()

                result = response.json()
                logger.debug(f"LLM API response keys: {list(result.keys())}")

                # Check for various possible response structures
                if "choices" in result and len(result["choices"]) > 0:
                    choice = result["choices"][0]

                    # Check finish_reason for truncated responses
                    finish_reason = choice.get("finish_reason", "unknown")
                    if finish_reason == "length":
                        logger.warning(f"LLM response was truncated due to length limit")

                    if "message" in choice:
                        message = choice["message"]
                        if "content" in message and message["content"]:
                            content = message["content"]
                            logger.debug(f"LLM response received, length: {len(content)} chars")
                            return content
                        elif "content" in message and message["content"] == "":
                            logger.warning(f"LLM returned empty content, finish_reason: {finish_reason}")
                            return None
                        else:
                            logger.error(
                                f"Missing or null content in message: {message}, finish_reason: {finish_reason}")
                            return None
                    else:
                        logger.error(f"Missing message in choice: {choice}")
                        return None
                elif "content" in result:
                    # Some APIs return content directly
                    content = result["content"]
                    logger.debug(f"LLM response received (direct), length: {len(content)} chars")
                    return content
                elif "text" in result:
                    # Some APIs use 'text' field
                    content = result["text"]
                    logger.debug(f"LLM response received (text field), length: {len(content)} chars")
                    return content
                else:
                    logger.error(f"Unexpected LLM response structure: {result}")
                    return None

            except Exception as e:
                logger.error(f"LLM completion request failed: {e}")
                logger.error(f"Response status: {response.status_code if 'response' in locals() else 'N/A'}")
                logger.error(f"Response text: {response.text if 'response' in locals() else 'N/A'}")
                return None

    async def analyze_query_intent(
            self,
            query: str,
            available_element_types: List[str]
    ) -> Optional[Dict[str, Any]]:
        """Analyze query intent to determine relevant element types"""
        element_types_desc = {
            # Currently active types
            "paragraph": "일반 문단 - 문서의 본문 내용",
            "summary": "AI 요약 - 자동 생성된 요약문", 
            "caption": "이미지 설명 - AI가 생성한 이미지 캡션",
            "origin": "원본 이미지 - 최초 업로드된 이미지"
            
            # Temporarily disabled element types (for future use)
            # Text 모달리티:
            # "title": "제목 - 문서/섹션 제목",
            # "stt": "음성→텍스트 - 음성인식 결과", 
            # "scene": "비디오 장면 설명 - 비디오 장면에 대한 텍스트 설명",
            # "ocr": "이미지→텍스트 - OCR로 추출한 텍스트",
            # "table": "표 데이터 - JSON 형태의 구조화된 표",
            # "translation": "번역 결과 - 다른 언어로 번역된 텍스트",
            # Image 모달리티:
            # "cropped": "잘린 이미지 - 특정 영역을 추출한 이미지",
            # "detected_object": "감지된 객체 - 객체 감지로 추출한 영역", 
            # "chart": "차트/그래프 - 데이터 시각화 이미지",
            # "diagram": "다이어그램 - 구조도, 플로우차트 등",
            # "keyframe": "키 프레임 - 비디오에서 추출한 대표 프레임 이미지",
            # "thumbnail": "썸네일 - 비디오의 썸네일 이미지",
            # Video 모달리티:
            # "clip": "비디오 클립 - 특정 시간 구간의 영상",
            # "segment": "비디오 구간 - 의미적으로 구분된 비디오 구간",
            # Audio 모달리티:
            # "speech": "사람의 발화 구간 - 특정 화자의 발언 부분",
            # "music": "배경음악이나 음악 콘텐츠 - 인트로 음악, 배경음 등",
            # "sound_effect": "특수 효과음 - 박수소리, 벨소리, 알림음",
            # "ambient": "주변 환경음 - 에어컨 소리, 발걸음, 잡음"
        }

        # element_types_desc를 사용하여 정확한 선택 가능하도록 함
        element_list = "\n".join([
            f"- {etype}: {element_types_desc.get(etype, '기타 콘텐츠')}"
            for etype in available_element_types
        ])

        system_message = f"""검색 쿼리를 분석하여 관련성이 높은 element_type들을 선택하세요.
현재 활성화된 타입만 사용 가능합니다.

사용 가능한 타입:
{element_list}

중요한 제약사항:
- summary: 최소 50자 이상의 텍스트에서만 의미있는 요약을 생성할 수 있습니다. 짧은 쿼리의 경우 summary를 선택하지 마세요!

쿼리 의도에 맞는 1-3개 타입을 선택하고, JSON으로만 답변하세요:
{{
    "selected_element_types": ["type1", "type2", "type3"],
    "reasoning": "선택 이유",
    "confidence": 0.85
}}"""

        messages = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": f"검색 쿼리: {query}"}
        ]

        response = await self.complete(messages, temperature=0.3, max_tokens=3000, force_json=True)

        if response:
            try:
                import json

                # Try to extract JSON from response if it contains additional text
                response_cleaned = response.strip()

                # Look for JSON block between ```json and ``` or { and }
                if "```json" in response_cleaned:
                    start = response_cleaned.find("```json") + 7
                    end = response_cleaned.find("```", start)
                    if end != -1:
                        response_cleaned = response_cleaned[start:end].strip()
                elif response_cleaned.startswith("{") and response_cleaned.endswith("}"):
                    # Already looks like pure JSON
                    pass
                else:
                    # Try to find JSON-like structure
                    start = response_cleaned.find("{")
                    end = response_cleaned.rfind("}") + 1
                    if start != -1 and end > start:
                        response_cleaned = response_cleaned[start:end]

                logger.debug(f"Attempting to parse JSON, length: {len(response_cleaned)} chars")
                result = json.loads(response_cleaned)

                # Validate selected types are in available types
                selected = result.get("selected_element_types", [])
                valid_selected = [t for t in selected if t in available_element_types]

                if not valid_selected:
                    logger.warning(f"No valid element types found in LLM response: {selected}")
                    return None

                return {
                    "selected_element_types": valid_selected,
                    "reasoning": result.get("reasoning", "LLM analysis completed"),
                    "confidence": min(1.0, max(0.0, result.get("confidence", 0.7)))
                }
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse LLM response as JSON: {e}")
                logger.error(f"Raw response: {response}")
                return None
            except Exception as e:
                logger.error(f"Error processing LLM response: {e}")
                return None

        return None

    async def expand_query(
            self,
            query: str,
            context: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """Comprehensive query expansion using Query Decomposition, Query Rewriting, and Semantic Expansion
        
        Args:
            query: Original user query
            context: Optional context information (search domain, user preferences, etc.)
            
        Returns:
            Dictionary containing expanded queries and analysis
        """
        context_info = ""
        if context:
            domain = context.get("domain", "")
            user_type = context.get("user_type", "")
            search_scope = context.get("search_scope", "")
            if domain:
                context_info += f"검색 도메인: {domain}\n"
            if user_type:
                context_info += f"사용자 유형: {user_type}\n"
            if search_scope:
                context_info += f"검색 범위: {search_scope}\n"

        system_message = f"""당신은 검색 쿼리 확장 전문가입니다. 주어진 쿼리의 특성을 분석하여 필요한 기법만 선택적으로 적용해 더 효과적인 검색 쿼리들을 생성하세요.

{context_info}

다음 기법들 중 쿼리에 적합한 것만 선택하여 적용하세요:

1. **Query Decomposition (쿼리 분해)** - 복잡한 복합 쿼리에만 적용:
   ✅ 적용 조건: 2개 이상의 독립적 개념이 AND/OR로 연결된 경우
   ✅ 예시: "파이썬 머신러닝과 데이터 시각화" → "파이썬 머신러닝" + "데이터 시각화"
   ❌ 불필요한 경우: 단일 개념, 단순한 키워드 검색
   - 복합적인 쿼리를 논리적 구성 요소로 분해
   - 각 하위 개념을 독립적으로 검색 가능한 단위로 변환
   
   **의존성 판단**: 분해된 쿼리들이 순차적으로 실행되어야 하는지 결정
   - has_dependency = true: "최신 파이썬 라이브러리와 그 사용법" (1차에서 라이브러리 식별 → 2차에서 해당 라이브러리 사용법)
   - has_dependency = false: "머신러닝과 데이터 시각화" (각각 독립적으로 검색 가능)

2. **Query Rewriting (쿼리 재작성)** - 대부분의 쿼리에 유용:
   ✅ 적용 조건: 동의어, 표현 변경으로 검색 품질 향상 가능
   ✅ 예시: "AI" → "인공지능", "튜토리얼" → "가이드", "방법" → "how to"
   - 원본 쿼리를 다양한 표현 방식으로 재작성
   - 동의어, 유의어, 관련 용어 활용
   - 질문형 → 키워드형, 구어체 → 표준어 등 형식 변환

3. **Semantic Expansion (의미적 확장)** - 검색 범위 확대가 필요할 때:
   ✅ 적용 조건: 관련 개념, 상하위 개념으로 검색 범위 확장이 도움되는 경우
   ✅ 예시: "파이썬" → "pandas numpy matplotlib", "데이터 분석" → "통계 분석 시각화"
   ❌ 불필요한 경우: 매우 구체적인 검색, 정확한 매칭이 중요한 경우
   - 쿼리의 의미적 맥락을 확장
   - 상위/하위 개념, 연관 개념 추가
   - 도메인 특화 용어 및 전문 용어 포함

**중요**: 각 기법의 적용 여부를 먼저 판단하고, 필요한 기법만 사용하세요. 모든 기법을 사용할 필요는 없습니다.

JSON 형식으로만 응답하세요:
{{
    "original_query": "원본 쿼리",
    "query_analysis": {{
        "intent": "검색 의도 분석",
        "complexity": "simple|moderate|complex",
        "domain": "추정 도메인",
        "query_type": "factual|procedural|navigational|transactional",
        "requires_decomposition": false,
        "requires_rewriting": true,
        "requires_expansion": true
    }},
    "applied_techniques": ["rewriting", "semantic_expansion"],
    "has_dependency": false,
    "dependency_reason": "분해된 쿼리들이 독립적으로 실행 가능",
    "decomposition": {{
        "applied": false,
        "reason": "단일 개념으로 분해 불필요",
        "main_concepts": [],
        "sub_queries": []
    }},
    "rewritten_queries": [
        {{
            "query": "재작성된 쿼리1",
            "type": "synonym|paraphrase|format_change|register_change",
            "rationale": "재작성 이유"
        }}
    ],
    "semantic_expansions": [
        {{
            "query": "의미적으로 확장된 쿼리1",
            "expansion_type": "hypernym|hyponym|related_concept|domain_specific",
            "added_concepts": ["추가된 개념1", "추가된 개념2"]
        }}
    ],
    "final_queries": [
        {{
            "query": "최종 확장 쿼리1",
            "priority": 1,
            "search_strategy": "hybrid|semantic|keyword|multimodal",
            "confidence": 0.95,
            "source_technique": "rewriting|expansion|decomposition|original"
        }}
    ],
    "search_suggestions": {{
        "boolean_query": "Boolean 검색 쿼리",
        "filters": ["추천 필터1", "추천 필터2"],
        "query_operators": ["AND", "OR", "NEAR", "WILDCARD"]
    }}
}}

참고: 
- decomposition.applied가 false면 sub_queries는 빈 배열
- rewritten_queries는 적용된 경우에만 항목 포함
- semantic_expansions는 적용된 경우에만 항목 포함
- applied_techniques에는 실제 사용된 기법만 나열"""

        messages = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": f"다음 쿼리를 확장해주세요: {query}"}
        ]

        response = await self.complete(messages, temperature=0.7, max_tokens=4000, force_json=True)

        if response:
            try:
                import json

                # JSON 추출 로직
                response_cleaned = response.strip()
                if "```json" in response_cleaned:
                    start = response_cleaned.find("```json") + 7
                    end = response_cleaned.find("```", start)
                    if end != -1:
                        response_cleaned = response_cleaned[start:end].strip()
                elif response_cleaned.startswith("{") and response_cleaned.endswith("}"):
                    pass
                else:
                    start = response_cleaned.find("{")
                    end = response_cleaned.rfind("}") + 1
                    if start != -1 and end > start:
                        response_cleaned = response_cleaned[start:end]

                logger.debug(f"Parsing query expansion JSON, length: {len(response_cleaned)} chars")
                result = json.loads(response_cleaned)

                # 결과 검증 및 기본값 설정
                if not isinstance(result.get("final_queries"), list):
                    result["final_queries"] = []
                
                # 최소한 원본 쿼리라도 포함
                if not result["final_queries"]:
                    result["final_queries"] = [{
                        "query": query,
                        "priority": 1,
                        "search_strategy": "hybrid",
                        "confidence": 0.8
                    }]

                # priority로 정렬
                result["final_queries"] = sorted(
                    result["final_queries"], 
                    key=lambda x: x.get("priority", 999)
                )

                logger.info(f"Query expansion generated {len(result['final_queries'])} expanded queries")
                return result

            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse query expansion JSON: {e}")
                logger.error(f"Raw response: {response}")
                return None
            except Exception as e:
                logger.error(f"Error processing query expansion response: {e}")
                return None

        return None
