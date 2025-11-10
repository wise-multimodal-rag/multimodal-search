import time
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from loguru import logger

from app.core.common_handlers import execute_multimodal_search
from app.core.dependencies import get_answer_generation_service, get_search_service
from app.models.generation import GenerationResponse
from app.services import SearchService
from app.services.generation import AnswerGenerationService

router = APIRouter()


@router.post("/generate/multimodal", response_model=GenerationResponse)
async def generate_multimodal_answer(
        text_query: str = Form(description="텍스트 검색 쿼리"),
        image: Optional[UploadFile] = File(default=None, description="이미지 파일"),
        video: Optional[UploadFile] = File(default=None, description="비디오 파일"),
        audio: Optional[UploadFile] = File(default=None, description="오디오 파일"),
        text_file: Optional[UploadFile] = File(default=None, description="텍스트 파일"),
        include_chunk_meta: bool = Form(default=True, description="Chunk 메타데이터 포함 여부"),
        include_media_meta: bool = Form(default=True, description="Media 메타데이터 포함 여부"),
        max_results: int = Form(default=10, ge=1, le=100, description="최대 검색 결과 수"),
        temperature: float = Form(default=0.7, ge=0.0, le=2.0, description="생성 온도"),
        max_retries: int = Form(default=2, ge=0, le=5, description="재생성 최대 횟수"),
        search_service: SearchService = Depends(get_search_service),
        generation_service: AnswerGenerationService = Depends(get_answer_generation_service),
):
    """멀티모달 검색 결과를 기반으로 LLM 답변을 생성하는 엔드포인트"""
    start_time = time.time()

    try:
        logger.info(f"Starting multimodal answer generation for query: {text_query}")

        # 1. 공통 함수를 사용하여 멀티모달 검색 수행
        search_result = await execute_multimodal_search(
            text_query=text_query,
            image=image,
            video=video,
            audio=audio,
            text_file=text_file,
            include_chunk_meta=include_chunk_meta,
            include_media_meta=include_media_meta,
            max_results=max_results,
            search_service=search_service,
            input_validator=None,  # generation endpoint는 검증 생략
        )

        logger.info(f"Search completed, found {search_result.total_hits} results")

        # 2. 검색 결과를 기반으로 답변 생성
        generation_result = await generation_service.generate_answer(
            query=text_query,
            search_results=search_result,
            max_retries=max_retries,
            temperature=temperature,
            search_service=search_service,
        )

        # 3. 처리 시간 계산
        processing_time_ms = int((time.time() - start_time) * 1000)
        generation_result["processing_time_ms"] = processing_time_ms

        logger.info(f"Answer generation completed in {processing_time_ms}ms")

        return GenerationResponse(**generation_result)

    except HTTPException as e:
        logger.warning(f"HTTP {e.status_code} error in multimodal answer generation: {e.detail}")
        raise
    except Exception as e:
        logger.error(f"Multimodal answer generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
