"""멀티모달 스트리밍 통합 서비스

검색과 선택적 답변 생성을 통합하여 처리하는 서비스
"""
import json
import time
from typing import Any, AsyncGenerator, Dict, List, Optional

from loguru import logger

from app.models.opensearch import SearchResponse
from app.services import SearchService
from app.services.generation import AnswerGenerationService


class MultimodalStreamService:
    """멀티모달 검색 + 선택적 답변 생성 통합 서비스"""

    def __init__(self, search_service: SearchService, generation_service: AnswerGenerationService):
        self.search_service = search_service
        self.generation_service = generation_service

    async def process_multimodal_request(
            self,
            text_query: Optional[str],
            processed_files: Dict[str, Any],
            include_chunk_meta: bool = True,
            include_media_meta: bool = True,
            max_results: int = 10,
            files_were_provided: bool = False,
            generate_answer: bool = False,
            temperature: float = 0.7,
            max_retries: int = 2,
            file_processing_errors: List[str] = None,
    ) -> AsyncGenerator[str, None]:
        """멀티모달 요청을 처리하여 스트리밍 응답을 생성합니다.
        
        Args:
            text_query: 텍스트 검색 쿼리
            processed_files: 전처리된 파일 데이터
            include_chunk_meta: 청크 메타데이터 포함 여부
            include_media_meta: 미디어 메타데이터 포함 여부
            max_results: 최대 결과 수
            files_were_provided: 파일 업로드 시도 여부
            generate_answer: AI 답변 생성 여부
            temperature: 답변 생성 온도
            max_retries: 답변 재생성 최대 횟수
            file_processing_errors: 파일 처리 오류 목록
        
        Yields:
            SSE 형식의 스트리밍 데이터
        """
        search_results = None

        try:
            # 파일 처리 오류가 있었다면 스트리밍으로 알림
            if file_processing_errors:
                for error in file_processing_errors:
                    yield f"data: {json.dumps({'step': 'file_read_failed', 'message': error, 'timestamp': time.time()}, ensure_ascii=False)}\n\n"

            # 1단계: 멀티모달 검색 실행
            logger.info("🔍 Starting multimodal search")
            async for step_result in self.search_service.search_multimodal_stream(
                    text_query=text_query,
                    processed_files=processed_files,
                    include_chunk_meta=include_chunk_meta,
                    include_media_meta=include_media_meta,
                    max_results=max_results,
                    files_were_provided=files_were_provided,
            ):
                # 검색 완료 단계에서 결과 저장
                if step_result.get('step') == 'completed' and step_result.get('data'):
                    search_results = step_result.get('data')

                # SSE 형식으로 데이터 전송
                yield self._format_sse_data(step_result)

            # 2단계: 답변 생성 (요청된 경우)
            if generate_answer and search_results:
                logger.info("🤖 Starting answer generation")
                answer_step_count = 0
                max_answer_steps = 50  # 무한루프 방지용 최대 스텝 수

                try:
                    # 직접 스트리밍 (태스크 생성 없이)
                    answer_completed = False
                    async for answer_step in self._generate_answer_stream(
                            text_query, search_results, temperature, max_retries
                    ):
                        answer_step_count += 1
                        logger.debug(
                            f"📡 Answer step {answer_step_count}: {answer_step[:100] if isinstance(answer_step, str) else 'data'}")

                        # answer_completed가 포함된 스텝인지 확인
                        if isinstance(answer_step, str) and 'answer_completed' in answer_step:
                            logger.info(f"🏁 STREAM Detected answer_completed in step {answer_step_count}")
                            answer_completed = True
                            yield answer_step
                            break

                        yield answer_step

                        # 무한루프 방지
                        if answer_step_count >= max_answer_steps:
                            logger.error(
                                f"🚨 Answer generation exceeded max steps ({max_answer_steps}), forcing termination")
                            # 강제 완료 신호 생성
                            forced_completion_data = {
                                "step": "answer_completed",
                                "message": f"답변 생성이 {max_answer_steps}단계 후 강제 완료되었습니다",
                                "data": {
                                    "forced_completion": True,
                                    "is_final": True,
                                    "total_steps": answer_step_count,
                                    "max_steps": max_answer_steps
                                },
                                "timestamp": time.time()
                            }
                            yield f"data: {json.dumps(forced_completion_data, ensure_ascii=False)}\n\n"
                            answer_completed = True
                            break

                except Exception as answer_error:
                    logger.error(f"🚨 Answer generation stream failed: {answer_error}")
                    error_data = {
                        "step": "answer_generation_error",
                        "message": f"답변 생성 중 오류 발생: {str(answer_error)}",
                        "timestamp": time.time()
                    }
                    yield f"data: {json.dumps(error_data, ensure_ascii=False)}\n\n"

                logger.info(f"🏁 Answer generation completed after {answer_step_count} steps")

            # 스트림 완료 신호 (무조건 전송)
            logger.info("📡 Sending [DONE] signal")
            yield "data: [DONE]\n\n"

        except Exception as e:
            logger.error(f"Multimodal stream processing failed: {e}")
            error_result = {"step": "error", "error": str(e), "timestamp": time.time()}
            yield f"data: {json.dumps(error_result, ensure_ascii=False)}\n\n"

    async def _generate_answer_stream(
            self,
            text_query: Optional[str],
            search_results: Dict[str, Any],
            temperature: float,
            max_retries: int
    ) -> AsyncGenerator[str, None]:
        """답변 생성 과정을 스트리밍으로 처리"""
        try:
            # query_analysis에서 첨부 이미지 캡션 확인
            query_analysis = search_results.get('query_analysis', {}) or {}
            if query_analysis and 'attached_image_caption' in query_analysis:
                attached_caption = query_analysis.get('attached_image_caption', '')
                if attached_caption:
                    logger.info(
                        f"🖼️ [STREAM] Found attached_image_caption in search_results: {attached_caption[:100]}...")
                else:
                    logger.info(f"🚫 [STREAM] attached_image_caption is empty")
            else:
                logger.info(
                    f"🚫 [STREAM] No attached_image_caption in search_results. query_analysis keys: {list(query_analysis.keys()) if query_analysis else 'None'}")

            # 검색 결과를 SearchResponse 형태로 변환
            search_response = SearchResponse(
                query=text_query or "",
                total_hits=len(search_results.get('results', [])),
                max_score=search_results.get('search_stats', {}).get('max_score', 0.0),
                results=search_results.get('results', []),
                took_ms=search_results.get('search_stats', {}).get('took_ms', 0),
                element_types_used=query_analysis.get('selected_element_types', []),
                query_analysis=query_analysis  # query_analysis 전체 전달
            )

            # 실제 스트리밍 답변 생성
            async for step_data in self.generation_service.generate_answer_stream(
                    query=text_query or "",
                    search_results=search_response,
                    max_retries=max_retries,
                    temperature=temperature,
                    search_service=self.search_service,
            ):
                # 각 단계 결과를 SSE 형식으로 전송
                yield f"data: {json.dumps(step_data, ensure_ascii=False)}\n\n"

            logger.info("✅ Answer generation completed")

        except Exception as gen_error:
            import traceback
            logger.error(f"❌ Answer generation failed: {gen_error}")
            logger.error(f"❌ Full traceback: {traceback.format_exc()}")
            error_data = {
                "step": "answer_generation_error",
                "message": f"답변 생성 중 오류가 발생했습니다: {str(gen_error)}",
                "timestamp": time.time(),
                "error": str(gen_error),
                "traceback": traceback.format_exc()
            }
            yield f"data: {json.dumps(error_data, ensure_ascii=False)}\n\n"

    def _format_sse_data(self, step_result: Dict[str, Any]) -> str:
        """SSE 형식으로 데이터 포맷팅"""
        try:
            json_data = json.dumps(step_result, ensure_ascii=False, default=str)
            data_size = len(json_data)

            # 크기 체크
            if data_size > 10 * 1024 * 1024:  # 10MB 초과
                logger.warning(
                    f"⚠️ SSE data too large: {data_size / 1024 / 1024:.2f} MB for step {step_result.get('step', 'unknown')}"
                )
                # 간소화된 에러 메시지 전송
                error_data = {
                    "step": step_result.get("step", "unknown"),
                    "message": f"데이터가 너무 커서 전송할 수 없습니다 ({data_size / 1024 / 1024:.2f} MB)",
                    "timestamp": time.time(),
                    "error": "data_too_large",
                }
                return f"data: {json.dumps(error_data, ensure_ascii=False)}\n\n"
            else:
                data_str = f"data: {json_data}\n\n"
                logger.debug(f"✅ SSE data sent: {data_size} bytes for step {step_result.get('step', 'unknown')}")
                return data_str

        except Exception as json_error:
            logger.error(f"❌ Failed to serialize step result: {json_error}")
            logger.error(f"❌ Step: {step_result.get('step', 'unknown')}")
            error_data = {
                "step": "serialization_error",
                "message": f"데이터 직렬화 실패: {str(json_error)}",
                "timestamp": time.time(),
            }
            return f"data: {json.dumps(error_data, ensure_ascii=False)}\n\n"
