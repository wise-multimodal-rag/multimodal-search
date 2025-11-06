import asyncio
import json
from typing import Any, Dict, List, Optional

from loguru import logger

from app.clients.llm_client import LLMClient
from app.models.opensearch import SearchResponse


class AnswerGenerationService:
    """LLM을 활용한 답변 생성 서비스"""

    def __init__(self, llm_client: LLMClient):
        self.llm_client = llm_client

    async def generate_answer(
        self,
        query: str,
        search_results: SearchResponse,
        max_retries: int = 2,
        temperature: float = 0.7,
    ) -> Dict[str, Any]:
        """검색 결과를 기반으로 질의에 대한 답변을 생성합니다.
        
        Args:
            query: 사용자 질의
            search_results: 멀티모달 검색 결과
            max_retries: 재생성 최대 횟수
            temperature: 생성 온도
            
        Returns:
            Dict containing the final answer and generation metadata
        """
        logger.info(f"Starting answer generation for query: {query}")
        
        # 검색 결과를 컨텍스트로 변환
        context = self._prepare_context(search_results)
        
        generation_attempts = []
        
        for attempt in range(max_retries + 1):
            logger.info(f"Generation attempt {attempt + 1}/{max_retries + 1}")
            
            # 1. 초안 생성
            draft_answer = await self._generate_draft(query, context, temperature)
            if not draft_answer:
                logger.error(f"Failed to generate draft answer in attempt {attempt + 1}")
                continue
            
            # 생성된 초안 답변 로깅 (간단히)
            logger.info(f"📝 Draft {attempt + 1}: {len(draft_answer)} chars - {draft_answer[:100]}...")
            
            # 2. Reflection 수행
            reflection_result = await self._perform_reflection(query, draft_answer, context)
            if not reflection_result:
                logger.error(f"Failed to perform reflection in attempt {attempt + 1}")
                continue
            
            # Reflection 결과 로깅 (간단히)
            total_score = reflection_result.get('total_score', 0)
            is_acceptable = reflection_result.get('is_acceptable', False)
            logger.info(f"🔍 Reflection {attempt + 1}: {total_score}/50 ({'PASS' if is_acceptable else 'RETRY'})")
            
            attempt_result = {
                "attempt": attempt + 1,
                "draft_answer": draft_answer,
                "reflection": reflection_result,
                "is_acceptable": reflection_result.get("is_acceptable", False),
                "improvement_suggestions": reflection_result.get("improvement_suggestions", []),
            }
            
            generation_attempts.append(attempt_result)
            
            # 3. 품질 검증
            if reflection_result.get("is_acceptable", False):
                logger.info(f"✅ Answer accepted in attempt {attempt + 1} - Score: {reflection_result.get('total_score', 0)}/50")
                logger.info(f"🎉 FINAL ANSWER: {len(draft_answer)} chars - {draft_answer[:100]}...")
                return {
                    "success": True,
                    "final_answer": draft_answer,
                    "query": query,
                    "total_attempts": attempt + 1,
                    "generation_attempts": generation_attempts,
                    "search_context": {
                        "total_results": search_results.total_hits,
                        "element_types_used": search_results.element_types_used,
                    },
                }
            
            # 재생성이 필요한 경우, 개선 사항을 반영하여 다음 시도 준비
            if attempt < max_retries:
                logger.info(f"Answer needs improvement, preparing retry {attempt + 2}")
                # 다음 시도에서는 약간 다른 온도 사용
                temperature = min(1.0, temperature + 0.1)
        
        # 모든 시도가 실패한 경우, 마지막 생성된 답변을 반환
        logger.warning(f"❌ All attempts failed quality check, using best attempt")
        if generation_attempts:
            last_answer = generation_attempts[-1]["draft_answer"]
            last_score = generation_attempts[-1]["reflection"].get("total_score", 0)
            logger.info(f"🔶 FALLBACK: {len(last_answer)} chars - Score: {last_score}/50 - {last_answer[:100]}...")
        return {
            "success": False,
            "final_answer": generation_attempts[-1]["draft_answer"] if generation_attempts else None,
            "query": query,
            "total_attempts": len(generation_attempts),
            "generation_attempts": generation_attempts,
            "search_context": {
                "total_results": search_results.total_hits,
                "element_types_used": search_results.element_types_used,
            },
            "error": "All generation attempts failed quality requirements",
        }

    def _prepare_context(self, search_results: SearchResponse) -> str:
        """검색 결과를 LLM이 사용할 수 있는 컨텍스트로 변환"""
        if not search_results.results:
            return "검색 결과가 없습니다."
        
        context_parts = []
        context_parts.append(f"검색 결과 (총 {search_results.total_hits}개):")
        
        for i, result in enumerate(search_results.results[:10], 1):  # 상위 10개만 사용
            element = result.element
            score = result.score
            
            # 미디어 정보
            media_info = ""
            if result.media_meta:
                media_info = f" [미디어: {result.media_meta.media_type}]"
            
            # 요소 정보
            element_info = f"[{element.element_type}]"
            
            context_parts.append(
                f"{i}. {element_info}{media_info} (점수: {score:.3f})\n"
                f"   내용: {element.content[:500]}{'...' if len(element.content) > 500 else ''}"
            )
        
        return "\n\n".join(context_parts)

    async def _generate_draft(self, query: str, context: str, temperature: float) -> Optional[str]:
        """초안 답변 생성"""
        system_prompt = """당신은 멀티모달 검색 결과를 바탕으로 정확하고 유용한 답변을 생성하는 AI 어시스턴트입니다.

다음 원칙을 따라 답변을 생성하세요:

1. **정확성**: 제공된 검색 결과에 기반하여 정확한 정보만 제공
2. **완성도**: 질문에 대해 포괄적이고 완전한 답변 제공
3. **명확성**: 이해하기 쉽고 구체적인 설명
4. **구조화**: 논리적 순서와 명확한 구조로 답변 구성
5. **출처 표시**: 검색 결과의 어떤 부분을 참고했는지 명시

답변 형식:
- 질문에 직접적으로 답변하는 내용으로 시작
- 필요시 배경 설명이나 맥락 정보 제공
- 구체적인 예시나 세부사항 포함
- 관련된 추가 정보나 주의사항 언급

검색 결과에 없는 정보에 대해서는 추측하지 말고, 검색 결과의 한계를 명시하세요."""

        user_prompt = f"""질문: {query}

검색 결과:
{context}

위 검색 결과를 바탕으로 질문에 대한 포괄적이고 정확한 답변을 생성해주세요."""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        try:
            response = await self.llm_client.complete(
                messages=messages,
                temperature=temperature,
                max_tokens=2000,
                use_generation_model=True
            )
            return response
        except Exception as e:
            logger.error(f"Error generating draft answer: {e}")
            return None

    async def _perform_reflection(self, query: str, draft_answer: str, context: str) -> Optional[Dict[str, Any]]:
        """생성된 답변에 대한 reflection 수행"""
        system_prompt = """당신은 생성된 답변의 품질을 평가하고 개선점을 제안하는 전문가입니다.

다음 기준으로 답변을 평가하세요:

1. **정확성** (0-10): 검색 결과와 일치하는 정보 제공 여부
2. **완성도** (0-10): 질문에 대한 포괄적인 답변 제공 여부  
3. **명확성** (0-10): 이해하기 쉽고 구체적인 설명 여부
4. **구조** (0-10): 논리적 구성과 읽기 쉬운 형태 여부
5. **관련성** (0-10): 질문과의 직접적인 연관성

전체 점수가 35점 이상(평균 7점)이면 is_acceptable: true로 설정하세요.

JSON 형식으로만 응답하세요:
{
    "scores": {
        "accuracy": 8,
        "completeness": 7,
        "clarity": 9,
        "structure": 8,
        "relevance": 9
    },
    "total_score": 41,
    "is_acceptable": true,
    "strengths": ["명확한 설명", "좋은 구조"],
    "improvement_suggestions": ["더 구체적인 예시 필요"],
    "overall_assessment": "전반적으로 우수한 답변이나 예시가 더 필요함"
}"""

        user_prompt = f"""평가할 답변:
질문: {query}

생성된 답변:
{draft_answer}

참고 검색 결과:
{context}

위 답변을 평가하고 개선점을 제안해주세요."""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        try:
            response = await self.llm_client.complete(
                messages=messages,
                temperature=0.3,
                max_tokens=1000,
                force_json=True,
                use_generation_model=True
            )
            
            if response:
                # JSON 파싱
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
                
                result = json.loads(response_cleaned)
                
                # 기본값 설정
                if "is_acceptable" not in result:
                    total_score = result.get("total_score", 0)
                    result["is_acceptable"] = total_score >= 35
                
                return result
                
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse reflection JSON: {e}")
            logger.error(f"Raw response: {response}")
        except Exception as e:
            logger.error(f"Error performing reflection: {e}")
        
        return None