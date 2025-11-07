from typing import Any, Dict, List, Optional

import httpx
from loguru import logger

from app.core.config import settings
from app.core.security import security_manager


class LLMClient:
    def __init__(self):
        self.base_url = settings.litellm_url
        self.api_key = security_manager.get_api_key("LITELLM_API_KEY") or settings.litellm_api_key
        self.model = settings.litellm_model
        self.generation_model = settings.litellm_generation_model
        self.timeout = 60.0

    async def complete(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.3,
        max_tokens: Optional[int] = None,
        force_json: bool = False,
        use_generation_model: bool = False,
    ) -> Optional[str]:
        """Get completion from LLM"""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                model = self.generation_model if use_generation_model else self.model
                payload = {"model": model, "messages": messages, "temperature": temperature}

                if max_tokens:
                    payload["max_tokens"] = max_tokens

                # Gemini-specific settings - only force JSON when explicitly requested
                if "gemini" in model.lower() and force_json:
                    payload["response_format"] = {"type": "json_object"}
                    payload["extra_body"] = {"generationConfig": {"responseMimeType": "application/json"}}

                headers = {}
                if self.api_key and self.api_key != "your-api-key":
                    # LiteLLM might use different auth formats
                    if self.api_key.startswith("Bearer "):
                        headers["Authorization"] = self.api_key
                    else:
                        headers["Authorization"] = f"Bearer {self.api_key}"

                # 간결한 요청 로깅
                logger.debug(
                    f"LLM request: model={payload.get('model')}, messages={len(payload.get('messages', []))}, temp={payload.get('temperature')}"
                )

                response = await client.post(f"{self.base_url}/v1/chat/completions", json=payload, headers=headers)
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
                            
                            # 답변 생성 모드일 때만 상세 내용 로깅
                            if use_generation_model and len(content) > 100:  # 긴 응답만 로깅 (답변 생성 시)
                                logger.info(f"🤖 LLM Raw Response ({payload.get('model')}):")
                                logger.info(f"📝 Content ({len(content)} chars):")
                                logger.info(f"{'*'*50}")
                                logger.info(content)
                                logger.info(f"{'*'*50}")
                            
                            return content
                        elif "content" in message and message["content"] == "":
                            logger.warning(f"LLM returned empty content, finish_reason: {finish_reason}")
                            return None
                        else:
                            logger.error(f"Missing or null content in message: {message}, finish_reason: {finish_reason}")
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
        self, query: str, available_element_types: List[str], input_modalities: Optional[List[str]] = None
    ) -> Optional[Dict[str, Any]]:
        """Analyze query intent to determine relevant element types based on input modalities"""
        # Define modality-specific element types
        modality_element_mapping = {"text": ["paragraph", "summary"], "image": ["caption", "origin"]}

        # 모달리티 제약을 완화 - 텍스트 쿼리에서도 이미지 콘텐츠 검색 가능
        # 예: "헤드폰 이미지"라는 텍스트 쿼리로 이미지 관련 타입 검색 허용
        original_available_types = available_element_types.copy()
        
        # 강제 필터링 제거 - LLM이 쿼리 내용에 따라 자유롭게 가중치 결정
        # if input_modalities:
        #     relevant_types = set()
        #     for modality in input_modalities:
        #         if modality in modality_element_mapping:
        #             relevant_types.update(modality_element_mapping[modality])
        #     # Only keep element types that are both relevant and available
        #     available_element_types = [t for t in available_element_types if t in relevant_types]

        element_types_desc = {
            # Currently active types
            "paragraph": "일반 문단 - 문서의 본문 내용",
            "summary": "AI 요약 - 자동 생성된 요약문",
            "caption": "이미지 설명 - AI가 생성한 이미지 캡션",
            "origin": "원본 이미지 - 최초 업로드된 이미지",
            # Temporarily disabled element types (for future use)
            # Text 모달리티:
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
        element_list = "\n".join(
            [f"- {etype}: {element_types_desc.get(etype, '기타 콘텐츠')}" for etype in available_element_types]
        )

        # Build modality context message
        modality_context = ""
        if input_modalities:
            modality_context = f"""
입력 모달리티: {", ".join(input_modalities)}
"""

        system_message = f"""쿼리 내용을 분석하여 검색에 적합한 element_type별 가중치를 계산하세요.
{modality_context}
사용 가능한 타입:
{element_list}

**중요한 우선순위 규칙**:
- 이미지 관련 쿼리 ("이미지", "사진", "그림" 등):
  → origin (원본 이미지): 1.0 (최고 우선순위)
  → caption (이미지 설명): 0.2-0.3 (매우 낮은 우선순위)
- 요약 관련 쿼리 ("요약", "정리" 등):
  → summary: 1.0, paragraph: 0.5-0.7
- 일반 텍스트 쿼리 ("내용", "문서", "텍스트" 등):
  → paragraph: 1.0, summary: 0.5-0.7

가중치 (0.0~1.0):
- 1.0: 핵심 요구사항 (최고 우선순위)
- 0.7: 관련 높음
- 0.5: 보통 관련
- 0.3: 약간 관련
- 0.2: 매우 낮은 관련성
- 0.0: 관련 없음

JSON만 출력:
{{
    "element_type_weights": {{
        "paragraph": 0.3,
        "summary": 0.5, 
        "caption": 0.2,
        "origin": 1.0
    }},
    "reasoning": "이미지 검색이므로 origin을 최우선으로, caption은 매우 낮게 설정",
    "confidence": 0.9
}}"""

        messages = [{"role": "system", "content": system_message}, {"role": "user", "content": f"검색 쿼리: {query}"}]

        response = await self.complete(messages, temperature=0.2, max_tokens=1500, force_json=False)

        if response:
            try:
                import json

                # Try to extract JSON from response if it contains additional text
                response_cleaned = response.strip()
                logger.debug(f"Cleaning LLM response for JSON parsing: {response_cleaned=}")

                # Look for JSON block between ```json and ``` or { and }
                if "```json" in response_cleaned:
                    start = response_cleaned.find("```json") + 7
                    end = response_cleaned.find("```", start)
                    if end != -1:
                        response_cleaned = response_cleaned[start:end].strip()
                elif response_cleaned.startswith("{"):
                    # Find the complete JSON object, even if truncated
                    brace_count = 0
                    json_end = -1
                    for i, char in enumerate(response_cleaned):
                        if char == '{':
                            brace_count += 1
                        elif char == '}':
                            brace_count -= 1
                            if brace_count == 0:
                                json_end = i + 1
                                break
                    
                    if json_end > 0:
                        response_cleaned = response_cleaned[:json_end]
                    else:
                        # JSON is incomplete, try to fix it
                        response_cleaned = response_cleaned.rstrip(',\n ') + '}'
                else:
                    # Try to find JSON-like structure
                    start = response_cleaned.find("{")
                    if start != -1:
                        # Find matching closing brace
                        brace_count = 0
                        json_end = -1
                        for i in range(start, len(response_cleaned)):
                            char = response_cleaned[i]
                            if char == '{':
                                brace_count += 1
                            elif char == '}':
                                brace_count -= 1
                                if brace_count == 0:
                                    json_end = i + 1
                                    break
                        
                        if json_end > start:
                            response_cleaned = response_cleaned[start:json_end]
                        else:
                            # Incomplete JSON, try to fix
                            response_cleaned = response_cleaned[start:].rstrip(',\n ') + '}'

                logger.debug(f"Attempting to parse JSON, length: {len(response_cleaned)} chars")
                result = json.loads(response_cleaned)

                # Validate element type weights
                element_weights = result.get("element_type_weights", {})
                
                # Filter only available element types and validate weights
                valid_weights = {}
                for element_type, weight in element_weights.items():
                    if element_type in original_available_types:  # 원래 available types 사용
                        # Ensure weight is between 0.0 and 1.0
                        weight = max(0.0, min(1.0, float(weight) if isinstance(weight, (int, float)) else 0.0))
                        valid_weights[element_type] = weight

                # Add missing element types with 0.0 weight
                for element_type in original_available_types:  # 원래 available types 사용
                    if element_type not in valid_weights:
                        valid_weights[element_type] = 0.0

                # Check if any meaningful weights exist (> 0.0)
                meaningful_weights = {k: v for k, v in valid_weights.items() if v > 0.0}
                if not meaningful_weights:
                    logger.warning(f"No meaningful element type weights found in LLM response: {element_weights}")
                    return None

                return {
                    "element_type_weights": valid_weights,
                    "reasoning": result.get("reasoning", "LLM analysis completed"),
                    "confidence": min(1.0, max(0.0, result.get("confidence", 0.7))),
                    # For backward compatibility, also provide selected_element_types
                    "selected_element_types": [k for k, v in meaningful_weights.items()],
                }
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse LLM response as JSON: {e}")
                logger.error(f"Raw response: {response}")
                return None
            except Exception as e:
                logger.error(f"Error processing LLM response: {e}")
                return None

        return None

    async def expand_query(self, query: str, context: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
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

        system_message = f"""검색 쿼리를 분석하여 필요한 경우에만 확장하세요. 원본 쿼리의 의도를 최대한 보존하면서 검색 성능을 개선하는 것이 목표입니다.

{context_info}

적용 가능한 기법:

1. **Query Rewriting (쿼리 재작성)** - 기본적으로 적용:
   - 동의어, 유의어로 재작성
   - 예시: "AI" → "인공지능", "방법" → "how to"

2. **Query Decomposition (쿼리 분해)** - 복합 쿼리일 때만:
   - 2개 이상의 독립적 개념이 명확히 구분되는 경우에만 적용
   - 예시: "파이썬과 자바스크립트 차이점" → "파이썬" + "자바스크립트"

3. **Semantic Expansion (의미적 확장)** - 매우 제한적으로 적용:
   ⚠️ **다음 경우에만 적용**:
   - 쿼리가 너무 추상적이어서 구체적인 검색이 어려운 경우
   - 사용자가 명시적으로 "관련된", "비슷한", "유사한" 등의 확장을 요청한 경우
   - 도메인 전문 용어가 필요한 매우 기술적인 쿼리인 경우
   
   ❌ **적용하지 말아야 할 경우**:
   - 구체적인 제품명, 브랜드명, 고유명사가 포함된 쿼리
   - 이미 충분히 구체적인 쿼리
   - 정확한 매칭이 중요한 쿼리

**원칙**: 의심스러우면 Semantic Expansion을 사용하지 마세요. Query Rewriting만으로도 충분한 경우가 대부분입니다.

간소화된 JSON 형식으로만 응답하세요:
{{
    "original_query": "원본 쿼리",
    "final_queries": [
        {{
            "query": "확장된 쿼리1",
            "priority": 1
        }},
        {{
            "query": "확장된 쿼리2", 
            "priority": 2
        }}
    ],
    "has_dependency": false,
    "dependency_reason": "분해된 쿼리들이 독립적으로 실행 가능",
    "applied_techniques": ["rewriting", "decomposition"],
    "expansion_summary": "Query rewriting and decomposition applied (2 variants generated)"
}}

참고:
- 원본 쿼리는 항상 priority 1로 final_queries에 포함
- 확장 쿼리는 최대 2-3개까지만 생성
- priority가 낮을수록 우선순위가 높음
- applied_techniques: ["rewriting", "decomposition", "semantic_expansion"] 중 사용된 것만
- has_dependency가 true면 순차 검색, false면 병렬 검색"""

        messages = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": f"다음 쿼리를 확장해주세요: {query}"},
        ]

        response = await self.complete(messages, temperature=0.2, max_tokens=2000, force_json=True)

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
                    result["final_queries"] = [{"query": query, "priority": 1}]

                # 기본값 설정
                if "has_dependency" not in result:
                    result["has_dependency"] = False
                if "dependency_reason" not in result:
                    result["dependency_reason"] = "쿼리들이 독립적으로 실행 가능"
                if "applied_techniques" not in result:
                    result["applied_techniques"] = ["original"]
                if "expansion_summary" not in result:
                    result["expansion_summary"] = f"원본 쿼리 사용 ({len(result['final_queries'])} variants)"

                # priority로 정렬
                result["final_queries"] = sorted(result["final_queries"], key=lambda x: x.get("priority", 999))

                logger.debug(f"Query expansion generated {len(result['final_queries'])} expanded queries")
                return result

            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse query expansion JSON: {e}")
                logger.error(f"Raw response: {response}")
                return None
            except Exception as e:
                logger.error(f"Error processing query expansion response: {e}")
                return None

        return None
