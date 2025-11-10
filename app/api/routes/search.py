import json
import time
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from loguru import logger

from app.core.common_handlers import execute_multimodal_search
from app.core.dependencies import (get_input_validator, get_multimodal_stream_service,
                                   get_search_service)
from app.core.utils import get_input_types
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
    max_results: int = Form(default=10, ge=1, le=100, description="최대 결과 수"),
    search_service: SearchService = Depends(get_search_service),
    input_validator: InputValidator = Depends(get_input_validator),
):
    """진정한 멀티모달 검색 엔드포인트 - 텍스트, 이미지, 비디오, 오디오 조합 입력"""
    try:
        # 공통 함수를 사용하여 멀티모달 검색 실행
        result = await execute_multimodal_search(
            text_query=text_query,
            image=image,
            video=video,
            audio=audio,
            text_file=text_file,
            include_chunk_meta=include_chunk_meta,
            include_media_meta=include_media_meta,
            max_results=max_results,
            search_service=search_service,
            input_validator=input_validator,
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
    max_results: int = Form(default=10, ge=1, le=100, description="최대 결과 수"),
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