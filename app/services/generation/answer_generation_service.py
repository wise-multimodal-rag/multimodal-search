import asyncio
import json
import time
from typing import Any, AsyncGenerator, Dict, List, Optional

from loguru import logger

from app.clients.llm_client import LLMClient
from app.core.prompt_manager import prompt_manager
from app.models.opensearch import SearchResponse


class AnswerGenerationService:
    """LLM을 활용한 답변 생성 서비스"""

    def __init__(self, llm_client: LLMClient):
        self.llm_client = llm_client
        self.prompt_manager = prompt_manager

    async def generate_answer(
            self,
            query: str,
            search_results: SearchResponse,
            max_retries: int = 2,
            temperature: float = 0.7,
            search_service=None,
    ) -> Dict[str, Any]:
        """검색 결과를 기반으로 질의에 대한 답변을 생성합니다.
        
        Args:
            query: 사용자 질의
            search_results: 멀티모달 검색 결과
            max_retries: 재생성 최대 횟수
            temperature: 생성 온도
            search_service: 재검색을 위한 검색 서비스
            
        Returns:
            Dict containing the final answer and generation metadata
        """
        logger.info(f"Starting answer generation for query: {query}")

        # 검색 결과를 컨텍스트로 변환
        context = await self._prepare_context(search_results)

        generation_attempts = []

        # 새로운 로직: 최대 2회만 시도 (초안 1회 + 재생성 1회)
        max_attempts = 2

        for attempt in range(max_attempts):
            logger.info(f"Generation attempt {attempt + 1}/{max_attempts}")

            # 1. 초안 생성 (이전 시도의 개선 제안 활용)
            previous_improvements = None
            if attempt > 0 and generation_attempts:
                # 이전 시도에서 개선 제안 추출
                previous_attempt = generation_attempts[-1]
                if previous_attempt:
                    previous_improvements = previous_attempt.get("improvement_suggestions", [])
                    logger.info(
                        f"Using {len(previous_improvements) if previous_improvements else 0} improvement suggestions from previous attempt")
                else:
                    logger.warning("Previous attempt is None, skipping improvement suggestions")

            draft_answer = await self._generate_draft(query, context, temperature, previous_improvements)
            if not draft_answer:
                logger.error(f"Failed to generate draft answer in attempt {attempt + 1}")
                continue

            # 생성된 초안 답변 로깅 (간단히)
            logger.info(f"Draft {attempt + 1}: {len(draft_answer)} chars - {draft_answer[:100]}...")

            # 2. Reflection 수행
            reflection_result = await self._perform_reflection(query, draft_answer, context)
            if not reflection_result:
                logger.error(f"Failed to perform reflection in attempt {attempt + 1}")
                continue

            # Reflection 결과 로깅 (간단히)
            total_score = reflection_result.get('total_score', 0) if reflection_result else 0
            is_acceptable = reflection_result.get('is_acceptable', False) if reflection_result else False
            logger.info(f"Reflection {attempt + 1}: {total_score}/50 ({'PASS' if is_acceptable else 'RETRY'})")

            attempt_result = {
                "attempt": attempt + 1,
                "draft_answer": draft_answer,
                "reflection": reflection_result or {},
                "is_acceptable": reflection_result.get("is_acceptable", False) if reflection_result else False,
                "improvement_suggestions": reflection_result.get("improvement_suggestions",
                                                                 []) if reflection_result else [],
            }

            generation_attempts.append(attempt_result)

            # 3. 품질 검증
            total_score = reflection_result.get('total_score', 0) if reflection_result else 0
            is_acceptable = reflection_result.get("is_acceptable", False) if reflection_result else False

            if is_acceptable:
                logger.info(f"Answer accepted in attempt {attempt + 1} - Score: {total_score}/50")
                logger.info(f"FINAL ANSWER: {len(draft_answer)} chars - {draft_answer[:100]}...")
                return {
                    "success": True,
                    "final_answer": draft_answer,
                    "query": query,
                    "total_attempts": attempt + 1,
                    "generation_attempts": generation_attempts,
                    "best_attempt": attempt + 1,
                    "best_score": total_score,
                    "search_context": {
                        "total_results": search_results.total_hits,
                        "element_types_used": search_results.element_types_used,
                    },
                    "completion_reason": "quality_accepted"
                }

            # 마지막 시도인지 확인
            if attempt >= max_attempts - 1:
                logger.info(f"Generation reached max attempts ({attempt + 1}/{max_attempts}), selecting best answer")
                break

            # 재생성 신호 (첫번째 시도가 35점 이하인 경우에만)
            if total_score <= 35:
                logger.info(f"Generation needs retry (score={total_score}), preparing attempt {attempt + 2}")

                # 재검색은 하지 않음 - 동일한 검색 결과 사용
                logger.info("Using same search results for regeneration (no re-search needed)")

                # 다음 시도에서는 약간 다른 온도 사용
                temperature = min(1.0, temperature + 0.1)
            else:
                logger.info(f"Score {total_score}/50 is acceptable, completing generation")
                break

        # 모든 시도 완료 - 가장 점수가 높은 답변 선택
        logger.info(f"Selecting best answer from {len(generation_attempts)} attempts")

        if generation_attempts:
            # 점수가 가장 높은 답변 선택
            best_attempt = max(generation_attempts, key=lambda x: x.get("reflection", {}).get("total_score", 0))
            best_score = best_attempt.get("reflection", {}).get("total_score", 0)
            best_answer = best_attempt["draft_answer"]
            best_attempt_num = best_attempt["attempt"]

            logger.info(f"Selected attempt {best_attempt_num} with score {best_score}/50")
            logger.info(f"BEST ANSWER: {len(best_answer)} chars - {best_answer[:100]}...")

            # 성공 여부 판단 (35점 이상이면 성공)
            is_success = best_score >= 35

            return {
                "success": is_success,
                "final_answer": best_answer,
                "query": query,
                "total_attempts": len(generation_attempts),
                "generation_attempts": generation_attempts,
                "best_attempt": best_attempt_num,
                "best_score": best_score,
                "search_context": {
                    "total_results": search_results.total_hits,
                    "element_types_used": search_results.element_types_used,
                },
                "completion_reason": "best_score_selected"
            }
        else:
            # 예외적인 경우
            logger.error("No generation attempts found")
            return {
                "success": False,
                "final_answer": None,
                "query": query,
                "total_attempts": 0,
                "error": "No generation attempts completed"
            }

    async def _prepare_context(self, search_results: SearchResponse) -> str:
        """검색 결과를 LLM이 사용할 수 있는 컨텍스트로 변환"""
        if not search_results.results:
            return "검색 결과가 없습니다."

        context_parts = []
        context_parts.append(f"검색 결과 (총 {search_results.total_hits}개):")

        # origin 타입 element들의 chunk_id 수집 및 이미 포함된 caption chunk_id 수집
        origin_chunk_ids = []
        existing_caption_chunk_ids = set()

        for result in search_results.results[:10]:
            if result.element.element_type == "origin":
                origin_chunk_ids.append(result.element.chunk_id)
            elif result.element.element_type == "caption":
                existing_caption_chunk_ids.add(result.element.chunk_id)

        # 이미 검색 결과에 포함된 caption은 제외하고 origin 이미지들의 caption 검색
        origin_captions = {}
        if origin_chunk_ids:
            origin_captions = await self._get_captions_for_origins(origin_chunk_ids, existing_caption_chunk_ids)

        for i, result in enumerate(search_results.results[:10], 1):  # 상위 10개만 사용
            element = result.element
            score = result.score

            # 미디어 정보
            media_info = ""
            if result.media_meta:
                media_info = f" [미디어: {result.media_meta.media_type}]"

            # 요소 정보
            element_info = f"[{element.element_type}]"

            # 텍스트 전처리: 공백 정리 및 특수문자 처리
            cleaned_content = self._clean_content_text(element.content)

            # origin 타입인 경우 관련 캡션 추가
            context_content = cleaned_content
            if element.element_type == "origin" and element.chunk_id in origin_captions:
                caption = origin_captions[element.chunk_id]
                cleaned_caption = self._clean_content_text(caption)
                context_content += f"\n   관련 이미지 설명: {cleaned_caption}"

            context_parts.append(
                f"{i}. {element_info}{media_info} (점수: {score:.3f})\n"
                f"   내용: {context_content}"
            )

        # 첨부된 이미지의 캡션 (외부 API로 생성) 추가 - 이미지가 있을 때만
        if (search_results.query_analysis and
                "attached_image_caption" in search_results.query_analysis):
            attached_caption = search_results.query_analysis.get("attached_image_caption", "")
            if attached_caption and attached_caption.strip():
                logger.info(f"Found attached image caption: {attached_caption[:100]}...")
                context_parts.append("\n=== 첨부 이미지 정보 ===")
                context_parts.append("첨부된 이미지 설명:")
                cleaned_attached_caption = self._clean_content_text(attached_caption)
                context_parts.append(f"  - {cleaned_attached_caption}")
                logger.info(f"Added attached image caption to context")
            else:
                logger.info(f"attached_image_caption is empty or whitespace only")
        else:
            logger.debug(f"No attached image caption found")

        return "\n\n".join(context_parts)

    async def _get_captions_for_origins(self, chunk_ids: List[str], existing_caption_chunk_ids: set = None) -> Dict[
        str, str]:
        """Origin element들의 chunk_id로 해당하는 caption을 OpenSearch에서 검색 (중복 제외)"""
        if not chunk_ids:
            return {}

        try:
            # OpenSearch 서비스에 접근하기 위해 dependency injection 사용
            from app.core.dependency_injector import get_opensearch_service
            opensearch_service = get_opensearch_service()

            # chunk_id들로 caption element 검색
            query = {
                "query": {
                    "bool": {
                        "must": [
                            {"terms": {"chunk_id": chunk_ids}},
                            {"term": {"element_type": "caption"}},
                            {"term": {"modality": "text"}}
                        ]
                    }
                },
                "size": len(chunk_ids),
                "_source": ["chunk_id", "content"]
            }

            logger.info(f"Searching captions for {len(chunk_ids)} origin chunks")

            if opensearch_service.client:
                response = await opensearch_service.client.search(
                    index=opensearch_service.elements_index,
                    body=query
                )
            else:
                response = None

            # chunk_id별로 caption 매핑 (이미 검색 결과에 포함된 caption은 제외)
            captions = {}
            excluded_count = 0
            if response and "hits" in response:
                for hit in response["hits"]["hits"]:
                    source = hit["_source"]
                    chunk_id = source["chunk_id"]
                    content = source["content"]

                    # 이미 검색 결과에 포함된 caption은 제외
                    if existing_caption_chunk_ids and chunk_id in existing_caption_chunk_ids:
                        excluded_count += 1
                        logger.debug(f"Skipping duplicate caption for chunk_id: {chunk_id}")
                        continue

                    captions[chunk_id] = content

                logger.info(
                    f"Found {len(captions)} captions for origin images ({excluded_count} duplicates excluded)")
            else:
                logger.info("No captions found for origin images")

            return captions

        except Exception as e:
            logger.error(f"Failed to get captions for origins: {e}")
            return {}

    def _clean_content_text(self, content: str) -> str:
        """텍스트 내용 전처리: 불필요한 공백, 특수문자 정리"""
        if not content:
            return ""

        import re

        # 1. 여러 개의 연속된 공백을 하나로 통합
        content = re.sub(r'\s+', ' ', content)

        # 2. 여러 개의 연속된 줄바꿈을 최대 2개로 제한
        content = re.sub(r'\n{3,}', '\n\n', content)

        # 3. 탭 문자를 공백으로 변환
        content = content.replace('\t', ' ')

        # 4. 특수 구분자들 정리 (표 형태의 구분자들)
        content = re.sub(r'\s*\|\s*\|\s*', ' | ', content)  # | | | -> |
        content = re.sub(r'\s*\|\s*$', '', content, flags=re.MULTILINE)  # 줄 끝의 |
        content = re.sub(r'^\s*\|\s*', '', content, flags=re.MULTILINE)  # 줄 시작의 |

        # 5. 반복되는 특수문자들 정리
        content = re.sub(r'-{3,}', '---', content)  # 긴 대시들
        content = re.sub(r'={3,}', '===', content)  # 긴 등호들
        content = re.sub(r'_{3,}', '___', content)  # 긴 언더스코어들

        # 6. 문장 간 공백 정리 (문장 끝 . 후 공백)
        content = re.sub(r'\.\s+', '. ', content)
        content = re.sub(r',\s+', ', ', content)

        # 7. 시작과 끝의 공백 제거
        content = content.strip()

        # 8. 한글과 영문 사이의 불필요한 공백 정리
        content = re.sub(r'([가-힣])\s+([A-Za-z])', r'\1 \2', content)
        content = re.sub(r'([A-Za-z])\s+([가-힣])', r'\1 \2', content)

        return content

    async def _generate_draft(self, query: str, context: str, temperature: float,
                              previous_improvements: Optional[List[str]] = None) -> Optional[str]:
        """초안 답변 생성"""
        # 이미지 관련 안내문 - 첨부 이미지가 있을 때만 포함 (컨텍스트에서 확인)
        has_attached_image = "=== 첨부 이미지 정보 ===" in context

        # 프롬프트 매니저에서 답변 생성 프롬프트 가져오기
        system_prompt = await self.prompt_manager.get_answer_generation_prompt(
            has_attached_image=has_attached_image,
            previous_improvements=previous_improvements
        )

        user_prompt = f"""질문: {query}

검색 결과:
{context}

위 검색 결과를 바탕으로 질문에 대한 포괄적이고 정확한 답변을 생성해주세요."""

        messages = self.prompt_manager.create_messages(system_prompt, user_prompt)
        logger.debug(f"🧾 Draft generation messages: {messages}")

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
        # 프롬프트 매니저에서 답변 평가 프롬프트 가져오기
        system_prompt = await self.prompt_manager.get_answer_reflection_prompt()

        user_prompt = f"""평가할 답변:
질문: {query}

생성된 답변:
{draft_answer}

참고 검색 결과:
{context}

위 답변을 평가하고 개선점을 제안해주세요."""

        messages = self.prompt_manager.create_messages(system_prompt, user_prompt)

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

                # improvement_suggestions가 없으면 빈 리스트로 설정
                if "improvement_suggestions" not in result:
                    result["improvement_suggestions"] = []
                elif not isinstance(result["improvement_suggestions"], list):
                    logger.warning(
                        f"improvement_suggestions is not a list: {type(result['improvement_suggestions'])}, converting to list")
                    result["improvement_suggestions"] = [str(result["improvement_suggestions"])]

                logger.info(
                    f"Reflection result: improvement_suggestions type={type(result.get('improvement_suggestions'))}, value={result.get('improvement_suggestions')}")
                return result

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse reflection JSON: {e}")
            logger.error(f"Raw response: {response}")
        except Exception as e:
            logger.error(f"Error performing reflection: {e}")

        return None

    async def generate_answer_stream(
            self,
            query: str,
            search_results: SearchResponse,
            max_retries: int = 2,
            temperature: float = 0.7,
            search_service=None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """검색 결과를 기반으로 질의에 대한 답변을 스트리밍으로 생성합니다."""
        start_time = time.time()
        max_generation_time = 300  # 5분 최대 실행 시간
        logger.info(f"Starting streaming answer generation for query: {query} (max_retries={max_retries})")

        # 검색 결과를 컨텍스트로 변환
        context = await self._prepare_context(search_results)
        logger.debug(f"Prepared context: {context}")

        # 답변 생성 시작 신호
        yield {
            'step': 'answer_generation_start',
            'message': 'AI 답변 생성을 시작합니다',
            'timestamp': time.time()
        }

        generation_attempts = []

        # 새로운 로직: 최대 2회만 시도 (초안 1회 + 재생성 1회)
        max_attempts = 2
        logger.info(f"STREAM Starting generation with max_attempts={max_attempts} (1 initial + 1 regeneration)")

        for attempt in range(max_attempts):
            logger.info(f"STREAM Starting attempt {attempt + 1}/{max_attempts}")
            # 취소 요청 체크 및 양보
            try:
                await asyncio.sleep(0.01)  # 취소 체크를 위한 양보 (10ms)
            except asyncio.CancelledError:
                logger.info(f"STREAM Generation cancelled at attempt {attempt + 1}")
                cancel_result = {
                    'step': 'answer_generation_cancelled',
                    'message': '답변 생성이 취소되었습니다',
                    'timestamp': time.time()
                }
                yield cancel_result
                return

            # 시간 제한 체크
            elapsed_time = time.time() - start_time
            if elapsed_time > max_generation_time:
                logger.error(f"STREAM Generation timeout after {elapsed_time:.1f}s, stopping")
                timeout_result = {
                    'step': 'answer_generation_timeout',
                    'message': f'답변 생성이 시간 초과되어 중단되었습니다 ({elapsed_time:.1f}초)',
                    'timestamp': time.time()
                }
                yield timeout_result
                return

            logger.info(
                f"STREAM Generation attempt {attempt + 1}/{max_attempts} (max_retries={max_retries}, elapsed={elapsed_time:.1f}s)")

            # 초안 생성 시작 신호
            yield {
                'step': 'draft_generation',
                'message': f'답변 초안을 생성하고 있습니다 ({attempt + 1}회차)' if attempt > 0 else '검색 결과를 분석하여 답변 초안을 생성하고 있습니다',
                'timestamp': time.time(),
                'attempt_number': attempt + 1
            }

            # 1. 초안 생성 (이전 시도의 개선 제안 활용)
            logger.info(f"STREAM Generating draft for attempt {attempt + 1}")
            previous_improvements = None
            if attempt > 0 and generation_attempts:
                # 이전 시도에서 개선 제안 추출
                previous_attempt = generation_attempts[-1]
                if previous_attempt:
                    previous_improvements = previous_attempt.get("improvement_suggestions", [])
                    logger.info(
                        f"STREAM Using {len(previous_improvements) if previous_improvements else 0} improvement suggestions from previous attempt")
                else:
                    logger.warning("STREAM Previous attempt is None, skipping improvement suggestions")

            try:
                draft_answer = await self._generate_draft(query, context, temperature, previous_improvements)
                if not draft_answer:
                    logger.error(f"STREAM Failed to generate draft answer in attempt {attempt + 1}")
                    continue
                logger.info(f"STREAM Draft generated for attempt {attempt + 1}: {len(draft_answer)} chars")
            except asyncio.CancelledError:
                logger.info(f"STREAM Draft generation cancelled at attempt {attempt + 1}")
                raise

            # 초안 생성 완료 신호
            draft_data = {
                'attempt_number': attempt + 1,
                'answer_length': len(draft_answer),
                'temperature': temperature,
                'answer_draft': draft_answer,
                'draft_preview': draft_answer[:100] + '...' if len(draft_answer) > 100 else draft_answer,
                'search_context_size': len(search_results.results) if search_results else 0
            }

            draft_message = f"답변 초안 생성이 완료되었습니다 ({attempt + 1}회차)" if attempt > 0 else "답변 초안 생성이 완료되었습니다"
            yield {
                'step': 'draft_generated',
                'message': draft_message,
                'data': draft_data,
                'timestamp': time.time()
            }

            # 품질 검토 시작 신호
            reflection_message = f"생성된 답변의 품질을 검토하고 있습니다 ({attempt + 1}회차)" if attempt > 0 else "생성된 답변의 품질을 검토하고 있습니다"
            yield {
                'step': 'reflection',
                'message': reflection_message,
                'timestamp': time.time(),
                'attempt_number': attempt + 1
            }

            # 2. Reflection 수행
            logger.info(f"STREAM Performing reflection for attempt {attempt + 1}")
            try:
                reflection_result = await self._perform_reflection(query, draft_answer, context)
                if not reflection_result:
                    logger.error(f"STREAM Failed to perform reflection in attempt {attempt + 1}")
                    continue
                logger.info(
                    f"STREAM Reflection completed for attempt {attempt + 1}: {reflection_result.get('total_score', 0)}/50")
            except asyncio.CancelledError:
                logger.info(f"STREAM Reflection cancelled at attempt {attempt + 1}")
                raise

            # 품질 검토 완료 신호  
            reflection_data = {
                'attempt_number': attempt + 1,
                'reflection': reflection_result or {},
                'is_acceptable': reflection_result.get('is_acceptable', False) if reflection_result else False,
                'total_score': reflection_result.get('total_score', 0) if reflection_result else 0,
                'scores': reflection_result.get('scores', {}) if reflection_result else {},
                'improvement_suggestions': reflection_result.get('improvement_suggestions',
                                                                 []) if reflection_result else [],
                'answer_quality': '우수' if reflection_result and reflection_result.get('is_acceptable') else '재생성 필요'
            }

            review_message = f"품질 검토가 완료되었습니다 ({attempt + 1}회차)" if attempt > 0 else "품질 검토가 완료되었습니다"
            yield {
                'step': 'reflection_completed',
                'message': review_message,
                'data': reflection_data,
                'timestamp': time.time()
            }

            attempt_result = {
                "attempt": attempt + 1,
                "draft_answer": draft_answer,
                "reflection": reflection_result or {},
                "is_acceptable": reflection_result.get("is_acceptable", False) if reflection_result else False,
                "improvement_suggestions": reflection_result.get("improvement_suggestions",
                                                                 []) if reflection_result else [],
            }

            generation_attempts.append(attempt_result)

            # 3. 품질 검증
            is_acceptable = reflection_result.get("is_acceptable", False) if reflection_result else False
            total_score = reflection_result.get("total_score", 0) if reflection_result else 0
            logger.info(
                f"STREAM Quality check: score={total_score}/50, acceptable={is_acceptable}, attempt={attempt + 1}/{max_attempts}")

            # 품질이 좋으면 바로 완료
            if is_acceptable:
                logger.info(f"STREAM Answer accepted in attempt {attempt + 1}")

                # 최종 결과
                final_result = {
                    "success": True,
                    "final_answer": draft_answer,
                    "query": query,
                    "total_attempts": len(generation_attempts),
                    "generation_attempts": generation_attempts,
                    "search_context": {
                        "total_results": len(search_results.results) if search_results else 0,
                        "element_types": search_results.element_types_used if search_results else []
                    },
                    "temperature": temperature,
                    "is_final": True,
                    "completion_reason": "quality_accepted"
                }

                # 답변 생성 완료 신호
                yield {
                    'step': 'answer_completed',
                    'message': 'AI 답변 생성이 완료되었습니다',
                    'data': final_result,
                    'timestamp': time.time()
                }
                logger.info(f"STREAM Generation completed successfully after {attempt + 1} attempts")
                return

            # 마지막 시도인지 확인 (2회 제한)
            if attempt >= max_attempts - 1:
                logger.info(
                    f"STREAM Generation reached max attempts ({attempt + 1}/{max_attempts}), selecting best answer")
                break

            # 재생성 신호 (첫번째 시도가 35점 이하인 경우에만)
            if total_score <= 35:
                logger.info(f"STREAM Generation needs retry (score={total_score}), preparing attempt {attempt + 2}")

                # 재검색은 하지 않음 - 동일한 검색 결과로 재생성
                logger.info("STREAM Using same search results for regeneration (no re-search needed)")

                yield {
                    'step': 'regenerating',
                    'message': f'이전 개선 제안을 반영하여 답변을 재생성하고 있습니다 (점수: {total_score}/50)',
                    'timestamp': time.time()
                }
                # 다음 시도에서는 약간 다른 온도 사용
                temperature = min(1.0, temperature + 0.1)
            else:
                logger.info(f"STREAM Score {total_score}/50 is acceptable, completing generation")
                break

        # 모든 시도 완료 - 가장 점수가 높은 답변 선택
        logger.info(f"STREAM Selecting best answer from {len(generation_attempts)} attempts")

        if generation_attempts:
            # 점수가 가장 높은 답변 선택
            best_attempt = max(generation_attempts, key=lambda x: x.get("reflection", {}).get("total_score", 0))
            best_score = best_attempt.get("reflection", {}).get("total_score", 0)
            best_answer = best_attempt["draft_answer"]
            best_attempt_num = best_attempt["attempt"]

            logger.info(f"STREAM Selected attempt {best_attempt_num} with score {best_score}/50")

            # 성공 여부 판단 (35점 이상이면 성공)
            is_success = best_score >= 35
            completion_reason = "best_score_selected"

            final_result = {
                "success": is_success,
                "final_answer": best_answer,
                "query": query,
                "total_attempts": len(generation_attempts),
                "max_attempts": max_attempts,
                "generation_attempts": generation_attempts,
                "best_attempt": best_attempt_num,
                "best_score": best_score,
                "search_context": {
                    "total_results": len(search_results.results) if search_results else 0,
                    "element_types": search_results.element_types_used if search_results else []
                },
                "temperature": temperature,
                "is_final": True,
                "completion_reason": completion_reason
            }

            # 답변 생성 완료 신호
            completion_message = f'AI 답변 생성이 완료되었습니다 ({best_attempt_num}차 답변 선택, 점수: {best_score}/50)'
            yield {
                'step': 'answer_completed',
                'message': completion_message,
                'data': final_result,
                'timestamp': time.time()
            }
            logger.info(
                f"STREAM Generation completed - selected best answer from {len(generation_attempts)} attempts")
        else:
            # 예외적인 경우 - 시도가 하나도 없음
            logger.error("STREAM No generation attempts found")
            final_result = {
                "success": False,
                "final_answer": None,
                "query": query,
                "total_attempts": 0,
                "error": "No generation attempts completed",
                "is_final": True
            }
            yield {
                'step': 'answer_completed',
                'message': 'AI 답변 생성에 실패했습니다',
                'data': final_result,
                'timestamp': time.time()
            }

        return
