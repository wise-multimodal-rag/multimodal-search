"""공통 핸들러 함수들"""
from typing import Optional

from fastapi import UploadFile
from loguru import logger

from app.core.utils import get_input_types
from app.core.validators import InputValidator
from app.models.opensearch import SearchResponse
from app.services import SearchService


async def execute_multimodal_search(
    text_query: Optional[str],
    image: Optional[UploadFile],
    video: Optional[UploadFile],
    audio: Optional[UploadFile],
    text_file: Optional[UploadFile],
    include_chunk_meta: bool,
    include_media_meta: bool,
    max_results: int,
    search_service: SearchService,
    input_validator: Optional[InputValidator] = None,
) -> SearchResponse:
    """멀티모달 검색을 실행하는 공통 함수
    
    Args:
        text_query: 텍스트 쿼리
        image: 이미지 파일
        video: 비디오 파일
        audio: 오디오 파일
        text_file: 텍스트 파일
        include_chunk_meta: 청크 메타데이터 포함 여부
        include_media_meta: 미디어 메타데이터 포함 여부
        max_results: 최대 결과 수
        search_service: 검색 서비스
        input_validator: 입력 검증기 (선택적)
        
    Returns:
        검색 결과
        
    Raises:
        HTTPException: 검증 실패 또는 검색 실패 시
    """
    # 입력 검증 (제공된 경우에만)
    if input_validator:
        from app.core.utils import prepare_multimodal_request_data
        
        request_data = await prepare_multimodal_request_data(
            text_query=text_query,
            image=image,
            video=video,
            audio=audio,
            text_file=text_file,
            max_results=max_results,
            include_chunk_meta=include_chunk_meta,
            include_media_meta=include_media_meta,
        )
        
        try:
            validated_data = input_validator.validate_search_request(request_data)
            # 검증된 데이터에서 값 업데이트
            text_query = validated_data.get("text_query")
            max_results = validated_data["max_results"]
            include_chunk_meta = validated_data["include_chunk_meta"]
            include_media_meta = validated_data["include_media_meta"]
        except Exception as validation_error:
            logger.error(f"Input validation failed: {validation_error}")
            # 디버그용 데이터 로깅 (base64 제외)
            debug_data = _prepare_debug_data(request_data)
            logger.debug(f"Request data: {debug_data}")
            raise

    # 입력 타입 로깅
    input_types = get_input_types(text_query, image, video, audio, text_file)
    logger.info(f"Input types: {input_types}")

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

    logger.info(f"Search completed with {result.total_hits} results")
    return result


def _prepare_debug_data(request_data: dict) -> dict:
    """디버깅용 데이터 준비 (base64 데이터 제외)"""
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
    return debug_data