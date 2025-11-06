import json
import time
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from loguru import logger

from app.core.dependencies import (get_input_validator, get_multimodal_stream_service,
                                   get_search_service)
from app.core.validators import InputValidator
from app.models.opensearch import SearchResponse
from app.services import (FilePreprocessingService, MultimodalStreamService,
                          SearchService)

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
    input_validator: InputValidator = Depends(get_input_validator),
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
async def multimodal_search_and_generate_stream(
    request: Request,
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
    multimodal_stream_service: MultimodalStreamService = Depends(get_multimodal_stream_service),
):
    """멀티모달 검색 및 선택적 AI 답변 생성 스트리밍 엔드포인트
    
    검색만 수행하거나 검색 + LLM 답변 생성을 함께 수행할 수 있습니다.
    generate_answer=True일 때 답변 생성도 함께 실행됩니다.
    """
    logger.info(f"🚀 Stream API: answer={generate_answer}, temp={temperature}, retries={max_retries}")
    
    # 🔧 새로운 로직: 최대 1회 재시도만 허용 (총 2번 시도)
    if max_retries > 1:
        logger.warning(f"⚠️ max_retries {max_retries} exceeded limit, forcing to 1 (total 2 attempts)")
        max_retries = 1
    
    # 파일 전처리
    processed_files, file_processing_errors = await FilePreprocessingService.preprocess_files(
        image=image,
        video=video,
        audio=audio,
        text_file=text_file
    )
    
    # 파일 제공 여부 확인
    files_were_provided = any([image, video, audio, text_file])
    
    # 클라이언트 연결 상태를 체크하는 스트리밍 래퍼
    async def client_aware_stream():
        try:
            async for chunk in multimodal_stream_service.process_multimodal_request(
                text_query=text_query,
                processed_files=processed_files,
                include_chunk_meta=include_chunk_meta,
                include_media_meta=include_media_meta,
                max_results=max_results,
                files_were_provided=files_were_provided,
                generate_answer=generate_answer,
                temperature=temperature,
                max_retries=max_retries,
                file_processing_errors=file_processing_errors,
            ):
                # 클라이언트 연결 상태 체크
                if await request.is_disconnected():
                    logger.info("🔌 Client disconnected, stopping stream")
                    break
                yield chunk
        except Exception as e:
            logger.error(f"Stream error: {e}")
            # 에러 발생 시에도 적절한 종료 신호
            yield f"data: {json.dumps({'step': 'error', 'message': str(e)}, ensure_ascii=False)}\n\n"
    
    # 스트리밍 응답 생성
    return StreamingResponse(
        client_aware_stream(),
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