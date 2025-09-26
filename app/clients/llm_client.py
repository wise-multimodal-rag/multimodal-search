from typing import Dict, List, Any, Optional
import httpx
from loguru import logger

from app.core.config import settings


class LLMClient:
    def __init__(self):
        self.base_url = settings.litellm_url
        self.api_key = settings.litellm_api_key
        self.model = settings.litellm_model
        self.timeout = 60.0

    async def complete(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None
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
                
                # Gemini-specific settings to avoid reasoning tokens
                if "gemini" in self.model.lower():
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
                
                logger.debug(f"LLM request: {payload}")
                
                response = await client.post(
                    f"{self.base_url}/v1/chat/completions",
                    json=payload,
                    headers=headers
                )
                response.raise_for_status()
                
                result = response.json()
                logger.debug(f"LLM API response structure: {result}")
                
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
                            logger.debug(f"LLM response content: {content[:100]}...")
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
                    logger.debug(f"LLM response content (direct): {content[:100]}...")
                    return content
                elif "text" in result:
                    # Some APIs use 'text' field
                    content = result["text"]
                    logger.debug(f"LLM response content (text field): {content[:100]}...")
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
            # Text 모달리티
            "paragraph": "일반 문단 - 문서의 본문 내용",
            "title": "제목 - 문서/섹션 제목",
            "summary": "AI 요약 - 자동 생성된 요약문",
            "stt": "음성→텍스트 - 음성인식 결과",
            "caption": "이미지 설명 - AI가 생성한 이미지 캡션",
            "scene": "비디오 장면 설명 - 비디오 장면에 대한 텍스트 설명",
            "ocr": "이미지→텍스트 - OCR로 추출한 텍스트",
            "table": "표 데이터 - JSON 형태의 구조화된 표",
            "translation": "번역 결과 - 다른 언어로 번역된 텍스트",
            
            # Image 모달리티
            "origin": "원본 이미지 - 최초 업로드된 이미지",
            "cropped": "잘린 이미지 - 특정 영역을 추출한 이미지",
            "detected_object": "감지된 객체 - 객체 감지로 추출한 영역",
            "chart": "차트/그래프 - 데이터 시각화 이미지",
            "diagram": "다이어그램 - 구조도, 플로우차트 등",
            "keyframe": "키 프레임 - 비디오에서 추출한 대표 프레임 이미지",
            "thumbnail": "썸네일 - 비디오의 썸네일 이미지",
            
            # Video 모달리티
            "clip": "비디오 클립 - 특정 시간 구간의 영상",
            "segment": "비디오 구간 - 의미적으로 구분된 비디오 구간",
            
            # Audio 모달리티
            "speech": "사람의 발화 구간 - 특정 화자의 발언 부분",
            "music": "배경음악이나 음악 콘텐츠 - 인트로 음악, 배경음 등",
            "sound_effect": "특수 효과음 - 박수소리, 벨소리, 알림음",
            "ambient": "주변 환경음 - 에어컨 소리, 발걸음, 잡음"
        }
        
        # element_types_desc를 사용하여 정확한 선택 가능하도록 함
        element_list = "\n".join([
            f"- {etype}: {element_types_desc.get(etype, '기타 콘텐츠')}"
            for etype in available_element_types
        ])
        
        system_message = f"""검색 쿼리를 분석하여 관련성이 높은 element_type들을 선택하세요.

사용 가능한 타입:
{element_list}

쿼리 의도에 맞는 2-5개 타입을 선택하고, JSON으로만 답변하세요:
{{
    "selected_element_types": ["type1", "type2", "type3"],
    "reasoning": "선택 이유",
    "confidence": 0.85
}}"""

        messages = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": f"검색 쿼리: {query}"}
        ]
        
        response = await self.complete(messages, temperature=0.3, max_tokens=3000)
        
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
                
                logger.debug(f"Attempting to parse JSON: {response_cleaned[:200]}...")
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

    async def build_search_query(
        self,
        original_query: str,
        element_types: List[str],
        extracted_features: Dict[str, Any]
    ) -> Optional[str]:
        """Build enhanced search query using LLM"""
        
        system_message = """검색 쿼리를 최적화하세요.
- 원본 의도 유지
- 키워드/개체명 활용  
- 동의어 추가
- 간결하게 작성

최적화된 검색 쿼리만 답변하세요."""

        features_text = ""
        
        # 텍스트 특징 처리
        for key_prefix in ["text_", ""]:  # 기존 키워드와 새로운 텍스트 키워드 모두 처리
            keywords_key = f"{key_prefix}keywords" if key_prefix else "keywords"
            if keywords_key in extracted_features:
                keywords_data = extracted_features[keywords_key]
                if isinstance(keywords_data, dict) and "keywords" in keywords_data:
                    keywords = [kw.get("word", "") for kw in keywords_data["keywords"][:5]]
                    features_text += f"텍스트 키워드: {', '.join(keywords)}\n"
                    break  # 첫 번째 키워드만 사용
        
        # 텍스트 엔티티
        if "text_entities" in extracted_features:
            entities_data = extracted_features["text_entities"]
            if isinstance(entities_data, dict) and "entities" in entities_data:
                entities = [ent.get("text", "") for ent in entities_data["entities"][:3]]
                features_text += f"텍스트 개체명: {', '.join(entities)}\n"
        
        # 이미지 특징
        if "image_keywords" in extracted_features:
            img_keywords_data = extracted_features["image_keywords"]
            if isinstance(img_keywords_data, dict) and "keywords" in img_keywords_data:
                img_keywords = [kw.get("word", "") for kw in img_keywords_data["keywords"][:3]]
                features_text += f"이미지 키워드: {', '.join(img_keywords)}\n"
        
        if "image_objects" in extracted_features:
            objects = extracted_features["image_objects"][:3]  # 최대 3개 객체
            features_text += f"감지된 객체: {', '.join(objects)}\n"
        
        # 비디오 특징
        if "video_keywords" in extracted_features:
            vid_keywords_data = extracted_features["video_keywords"]
            if isinstance(vid_keywords_data, dict) and "keywords" in vid_keywords_data:
                vid_keywords = [kw.get("word", "") for kw in vid_keywords_data["keywords"][:3]]
                features_text += f"비디오 키워드: {', '.join(vid_keywords)}\n"
        
        if "video_activities" in extracted_features:
            activities = extracted_features["video_activities"][:3]
            features_text += f"비디오 활동: {', '.join(activities)}\n"
        
        # 오디오 특징
        if "audio_keywords" in extracted_features:
            aud_keywords_data = extracted_features["audio_keywords"]
            if isinstance(aud_keywords_data, dict) and "keywords" in aud_keywords_data:
                aud_keywords = [kw.get("word", "") for kw in aud_keywords_data["keywords"][:3]]
                features_text += f"오디오 키워드: {', '.join(aud_keywords)}\n"
        
        if "audio_type" in extracted_features:
            features_text += f"오디오 타입: {extracted_features['audio_type']}\n"

        user_message = f"""원본 쿼리: {original_query}
대상 콘텐츠 유형: {', '.join(element_types)}

{features_text}

위 정보를 바탕으로 최적화된 검색 쿼리를 생성해주세요."""

        messages = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": user_message}
        ]
        
        return await self.complete(messages, temperature=0.5, max_tokens=500)


