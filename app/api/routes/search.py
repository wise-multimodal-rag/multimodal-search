import json
import time
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from loguru import logger

from app.core.dependencies import get_answer_generation_service, get_search_service
from app.core.validators import input_validator
from app.models.opensearch import SearchResponse
from app.services import SearchService
from app.services.generation import AnswerGenerationService

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.post("/search/multimodal", response_model=SearchResponse)
async def search_multimodal(
    text_query: Optional[str] = Form(default="쿼리를 입력해주세요", description="텍스트 검색 쿼리"),
    image: Optional[UploadFile] = File(default=None, description="이미지 파일"),
    video: Optional[UploadFile] = File(default=None, description="비디오 파일"),
    audio: Optional[UploadFile] = File(default=None, description="오디오 파일"),
    text_file: Optional[UploadFile] = File(default=None, description="텍스트 파일"),
    include_chunk_meta: bool = Form(default=True, description="Chunk 메타데이터 포함 여부"),
    include_media_meta: bool = Form(default=True, description="Media 메타데이터 포함 여부"),
    max_results: int = Form(default=5, ge=1, le=100, description="최대 결과 수"),
    search_service: SearchService = Depends(get_search_service),
):
    """진정한 멀티모달 검색 엔드포인트 - 텍스트, 이미지, 비디오, 오디오 조합 입력"""
    try:
        # 고급 입력 검증
        request_data = {
            "text_query": text_query,
            "max_results": max_results,
            "include_chunk_meta": include_chunk_meta,
            "include_media_meta": include_media_meta,
        }

        # 파일 데이터 추가 (필요한 경우)
        if image:
            import base64

            image_content = await image.read()
            request_data["image"] = {
                "base64_data": base64.b64encode(image_content).decode("utf-8"),
                "content_type": image.content_type or "image/jpeg",
                "filename": image.filename,
            }

        if video:
            import base64

            video_content = await video.read()
            request_data["video"] = {
                "base64_data": base64.b64encode(video_content).decode("utf-8"),
                "content_type": video.content_type or "video/mp4",
                "filename": video.filename,
            }

        if audio:
            import base64

            audio_content = await audio.read()
            request_data["audio"] = {
                "base64_data": base64.b64encode(audio_content).decode("utf-8"),
                "content_type": audio.content_type or "audio/mp3",
                "filename": audio.filename,
            }

        if text_file:
            import base64

            text_content = await text_file.read()
            request_data["text_file"] = {
                "base64_data": base64.b64encode(text_content).decode("utf-8"),
                "content_type": text_file.content_type or "text/plain",
                "filename": text_file.filename,
            }

        # 통합 검증 실행
        try:
            validated_data = input_validator.validate_search_request(request_data)
        except Exception as validation_error:
            logger.error(f"Input validation failed: {validation_error}")
            # Log request data without base64 content
            debug_data = {}
            for key, value in request_data.items():
                if key in ["image", "video", "audio", "text_file"] and isinstance(value, dict):
                    debug_data[key] = {
                        "content_type": value.get("content_type"),
                        "filename": value.get("filename"),
                        "data_size": len(value.get("base64_data", "")) if "base64_data" in value else 0,
                    }
                else:
                    debug_data[key] = value
            logger.debug(f"Request data: {debug_data}")
            raise

        # 검증된 데이터에서 값 추출
        text_query = validated_data.get("text_query")
        max_results = validated_data["max_results"]
        include_chunk_meta = validated_data["include_chunk_meta"]
        include_media_meta = validated_data["include_media_meta"]

        # 입력 타입 로깅
        input_types = []
        if text_query:
            input_types.append("text")
        if image:
            input_types.append("image")
        if video:
            input_types.append("video")
        if audio:
            input_types.append("audio")
        if text_file:
            input_types.append("text_file")

        # 멀티모달 검색 수행
        result = await search_service.search_multimodal(
            text_query=text_query,
            image_file=image,
            video_file=video,
            audio_file=audio,
            text_file=text_file,
            include_chunk_meta=include_chunk_meta,
            include_media_meta=include_media_meta,
            max_results=max_results,
        )

        return result

    except HTTPException as e:
        logger.warning(f"HTTP {e.status_code} error in multimodal search: {e.detail}")
        raise
    except Exception as e:
        logger.error(f"Multimodal search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/search/multimodal/stream")
async def search_multimodal_stream(
    text_query: Optional[str] = Form(default="쿼리를 입력해주세요", description="텍스트 검색 쿼리"),
    image: Optional[UploadFile] = File(default=None, description="이미지 파일"),
    video: Optional[UploadFile] = File(default=None, description="비디오 파일"),
    audio: Optional[UploadFile] = File(default=None, description="오디오 파일"),
    text_file: Optional[UploadFile] = File(default=None, description="텍스트 파일"),
    include_chunk_meta: bool = Form(default=True, description="Chunk 메타데이터 포함 여부"),
    include_media_meta: bool = Form(default=True, description="Media 메타데이터 포함 여부"),
    max_results: int = Form(default=5, ge=1, le=100, description="최대 결과 수"),
    generate_answer: bool = Form(default=False, description="AI 답변도 함께 생성"),
    temperature: float = Form(default=0.7, ge=0.0, le=2.0, description="답변 생성 온도"),
    max_retries: int = Form(default=2, ge=0, le=5, description="답변 재생성 최대 횟수"),
    search_service: SearchService = Depends(get_search_service),
    generation_service: AnswerGenerationService = Depends(get_answer_generation_service),
):
    """실시간 스트리밍 방식의 멀티모달 검색 엔드포인트"""
    logger.info(f"🚀 Stream API called with generate_answer={generate_answer}, temperature={temperature}, max_retries={max_retries}")
    # 요청 받자마자 즉시 파일들을 읽어서 메모리에 보관
    processed_files = {}
    file_processing_errors = []

    # 파일들을 즉시 처리 (스트림 생성 전에)
    if image:
        try:
            image_content = await image.read()
            logger.info(f"📷 Image: {image.filename} ({len(image_content) if image_content else 0} bytes)")

            if image_content and len(image_content) > 0:
                processed_files["image"] = {
                    "data": image_content,
                    "filename": image.filename or "unknown_image",
                    "content_type": image.content_type or "image/jpeg",
                }
            else:
                error_msg = f"이미지 파일이 비어있습니다: {image.filename}"
                file_processing_errors.append(error_msg)
                logger.error(f"❌ {error_msg}")
        except Exception as e:
            error_msg = f"이미지 파일 읽기 실패: {str(e)}"
            file_processing_errors.append(error_msg)
            logger.error(f"❌ {error_msg}")

    if video:
        try:
            video_content = await video.read()
            logger.info(f"🎥 Video: {video.filename} ({len(video_content) if video_content else 0} bytes)")

            if video_content and len(video_content) > 0:
                processed_files["video"] = {
                    "data": video_content,
                    "filename": video.filename or "unknown_video",
                    "content_type": video.content_type or "video/mp4",
                }
            else:
                error_msg = f"비디오 파일이 비어있습니다: {video.filename}"
                file_processing_errors.append(error_msg)
                logger.error(f"❌ {error_msg}")
        except Exception as e:
            error_msg = f"비디오 파일 읽기 실패: {str(e)}"
            file_processing_errors.append(error_msg)
            logger.error(f"❌ {error_msg}")

    if audio:
        try:
            audio_content = await audio.read()
            logger.info(f"🎵 Audio: {audio.filename} ({len(audio_content) if audio_content else 0} bytes)")

            if audio_content and len(audio_content) > 0:
                processed_files["audio"] = {
                    "data": audio_content,
                    "filename": audio.filename or "unknown_audio",
                    "content_type": audio.content_type or "audio/mp3",
                }
            else:
                error_msg = f"오디오 파일이 비어있습니다: {audio.filename}"
                file_processing_errors.append(error_msg)
                logger.error(f"❌ {error_msg}")
        except Exception as e:
            error_msg = f"오디오 파일 읽기 실패: {str(e)}"
            file_processing_errors.append(error_msg)
            logger.error(f"❌ {error_msg}")

    if text_file:
        try:
            text_content = await text_file.read()
            logger.info(f"📄 Text: {text_file.filename} ({len(text_content) if text_content else 0} bytes)")

            if text_content and len(text_content) > 0:
                processed_files["text_file"] = {
                    "data": text_content,
                    "filename": text_file.filename or "unknown.txt",
                    "content_type": text_file.content_type or "text/plain",
                }
            else:
                error_msg = f"텍스트 파일이 비어있습니다: {text_file.filename}"
                file_processing_errors.append(error_msg)
                logger.error(f"❌ {error_msg}")
        except Exception as e:
            error_msg = f"텍스트 파일 읽기 실패: {str(e)}"
            file_processing_errors.append(error_msg)
            logger.error(f"❌ {error_msg}")

    logger.info(f"📋 Files ready: {len(processed_files)}, errors: {len(file_processing_errors)}")

    async def generate_search_stream():
        try:
            # 파일 처리 오류가 있었다면 스트리밍으로 알림
            if file_processing_errors:
                for error in file_processing_errors:
                    yield f"data: {json.dumps({'step': 'file_read_failed', 'message': error, 'timestamp': time.time()}, ensure_ascii=False)}\\n\\n"

            # 파일이 제공되었는지 확인 (실제 파일 업로드 시도가 있었는지)
            files_were_provided = any([image, video, audio, text_file])

            # 검색 결과를 저장할 변수
            search_results = None
            
            # 처리된 파일 데이터와 함께 스트리밍 검색 시작
            async for step_result in search_service.search_multimodal_stream(
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
                
                # SSE 형식으로 데이터 전송 - 안전한 JSON 직렬화
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
                        yield f"data: {json.dumps(error_data, ensure_ascii=False)}\n\n"
                    else:
                        data_str = f"data: {json_data}\n\n"
                        yield data_str
                        logger.debug(f"✅ SSE data sent: {data_size} bytes for step {step_result.get('step', 'unknown')}")

                except Exception as json_error:
                    logger.error(f"❌ Failed to serialize step result: {json_error}")
                    logger.error(f"❌ Step: {step_result.get('step', 'unknown')}")
                    import traceback

                    logger.error(f"❌ SSE serialization traceback: {traceback.format_exc()}")
                    error_data = {
                        "step": "serialization_error",
                        "message": f"데이터 직렬화 실패: {str(json_error)}",
                        "timestamp": time.time(),
                    }
                    yield f"data: {json.dumps(error_data, ensure_ascii=False)}\n\n"
            
            # 답변 생성이 요청된 경우 추가 처리
            if generate_answer and search_results:
                logger.info("🤖 Starting answer generation")
                
                try:
                    # 검색 결과를 SearchResponse 형태로 변환
                    from app.models.opensearch import SearchResponse
                    search_response = SearchResponse(
                        query=text_query or "",
                        total_hits=len(search_results.get('results', [])),
                        max_score=search_results.get('search_stats', {}).get('max_score', 0.0),
                        results=search_results.get('results', []),
                        took_ms=search_results.get('search_stats', {}).get('took_ms', 0),
                        element_types_used=search_results.get('query_analysis', {}).get('selected_element_types', [])
                    )
                    
                    # 답변 생성 시작 신호
                    yield f"data: {json.dumps({'step': 'answer_generation_start', 'message': 'AI 답변 생성을 시작합니다', 'timestamp': time.time()}, ensure_ascii=False)}\n\n"
                    
                    # 초안 생성 신호
                    yield f"data: {json.dumps({'step': 'draft_generation', 'message': '검색 결과를 분석하여 답변 초안을 생성하고 있습니다', 'timestamp': time.time()}, ensure_ascii=False)}\n\n"
                    
                    # 실제 답변 생성 (블로킹 호출)
                    generation_result = await generation_service.generate_answer(
                        query=text_query or "",
                        search_results=search_response,
                        max_retries=max_retries,
                        temperature=temperature,
                    )
                    
                    # 생성 과정 단계별 전송 - 모든 시도에 대해
                    if generation_result.get('generation_attempts'):
                        for attempt in generation_result['generation_attempts']:
                            attempt_num = attempt.get('attempt', 1)
                            
                            # 답변 초안 생성 완료 - 상세 데이터 포함
                            draft_content = attempt.get('draft_answer', '')  # 올바른 키 사용
                            draft_data = {
                                'attempt_number': attempt_num,
                                'answer_length': len(draft_content),
                                'processing_time_ms': attempt.get('processing_time_ms', 0),
                                'temperature': generation_result.get('temperature', 0.7),
                                'answer_draft': draft_content,  # 전체 초안 내용 추가
                                'draft_preview': draft_content[:100] + '...' if len(draft_content) > 100 else draft_content,
                                'search_context_size': len(search_response.results) if search_response else 0
                            }
                            
                            # 초안 생성 메시지
                            draft_message = f"답변 초안 생성이 완료되었습니다 ({attempt_num}회차)" if attempt_num > 1 else "답변 초안 생성이 완료되었습니다"
                            yield f"data: {json.dumps({'step': 'draft_generated', 'message': draft_message, 'data': draft_data, 'timestamp': time.time()}, ensure_ascii=False)}\n\n"
                            
                            # 품질 검토 시작
                            reflection_message = f"생성된 답변의 품질을 검토하고 있습니다 ({attempt_num}회차)" if attempt_num > 1 else "생성된 답변의 품질을 검토하고 있습니다"
                            yield f"data: {json.dumps({'step': 'reflection', 'message': reflection_message, 'timestamp': time.time()}, ensure_ascii=False)}\n\n"
                            
                            # 품질 검토 완료 - 상세 데이터 포함
                            reflection_data = {
                                'attempt_number': attempt_num,  # 시도 횟수 추가
                                'reflection': attempt.get('reflection', {}),
                                'is_acceptable': attempt.get('is_acceptable', False),
                                'total_score': attempt.get('reflection', {}).get('total_score', 0),
                                'scores': attempt.get('reflection', {}).get('scores', {}),
                                'improvement_suggestions': attempt.get('improvement_suggestions', []),
                                'answer_quality': '우수' if attempt.get('is_acceptable') else '재생성 필요'
                            }
                            
                            # 품질 검토 완료 메시지
                            review_message = f"품질 검토가 완료되었습니다 ({attempt_num}회차)" if attempt_num > 1 else "품질 검토가 완료되었습니다"
                            yield f"data: {json.dumps({'step': 'reflection_completed', 'message': review_message, 'data': reflection_data, 'timestamp': time.time()}, ensure_ascii=False)}\n\n"
                            
                            # 재생성이 필요하고 마지막 시도가 아닌 경우
                            if not attempt.get('is_acceptable') and attempt_num < generation_result.get('total_attempts', 1):
                                yield f"data: {json.dumps({'step': 'regenerating', 'message': f'품질 개선을 위해 답변을 재생성하고 있습니다 ({attempt_num + 1}회차 시도)', 'timestamp': time.time()}, ensure_ascii=False)}\n\n"
                    
                    # 답변 생성 완료
                    yield f"data: {json.dumps({'step': 'answer_completed', 'message': 'AI 답변 생성이 완료되었습니다', 'data': generation_result, 'timestamp': time.time()}, ensure_ascii=False)}\n\n"
                    
                    # 최종 답변 API 레벨에서 로깅 (간단히)
                    if generation_result and generation_result.get("final_answer"):
                        final_answer = generation_result["final_answer"]
                        success = generation_result.get("success", False)
                        total_attempts = generation_result.get("total_attempts", 0)
                        logger.info(f"🌟 API Final Answer: {len(final_answer)} chars, Success: {success}, Attempts: {total_attempts}")
                        logger.info(f"📄 Answer: {final_answer[:150]}...")
                    
                    logger.info("✅ Answer generation completed")
                    
                except Exception as gen_error:
                    logger.error(f"❌ Answer generation failed: {gen_error}")
                    error_data = {
                        "step": "answer_generation_error",
                        "message": f"답변 생성 중 오류가 발생했습니다: {str(gen_error)}",
                        "timestamp": time.time(),
                        "error": str(gen_error)
                    }
                    yield f"data: {json.dumps(error_data, ensure_ascii=False)}\n\n"

            # 스트림 완료 신호
            yield "data: [DONE]\n\n"

        except Exception as e:
            logger.error(f"Streaming search failed: {e}")
            error_result = {"step": "error", "error": str(e), "timestamp": time.time()}
            yield f"data: {json.dumps(error_result, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        generate_search_stream(),
        media_type="text/event-stream; charset=utf-8",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "*",
        },
    )



@router.get("/demo", response_class=HTMLResponse)
async def search_demo_interface(request: Request):
    """Multimodal search demo interface"""
    return templates.TemplateResponse("search.html", {"request": request})
