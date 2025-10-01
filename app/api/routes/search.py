from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from loguru import logger

from app.core.dependencies import get_search_service
from app.models.opensearch import SearchResponse
from app.services import SearchService

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.post("/search/multimodal", response_model=SearchResponse)
async def search_multimodal(
        text_query: Optional[str] = Form(default="AI 기술에 대한 문서를 찾아줘", description="텍스트 검색 쿼리"),
        image: Optional[UploadFile] = File(default=None, description="이미지 파일"),
        video: Optional[UploadFile] = File(default=None, description="비디오 파일"),
        audio: Optional[UploadFile] = File(default=None, description="오디오 파일"),
        include_chunk_meta: bool = Form(default=True, description="Chunk 메타데이터 포함 여부"),
        include_media_meta: bool = Form(default=True, description="Media 메타데이터 포함 여부"),
        max_results: int = Form(default=10, ge=1, le=100, description="최대 결과 수"),
        search_service: SearchService = Depends(get_search_service)
):
    """진정한 멀티모달 검색 엔드포인트 - 텍스트, 이미지, 비디오, 오디오 조합 입력"""
    try:
        # 입력 검증
        if not any([text_query, image, video, audio]):
            raise HTTPException(status_code=400, detail="최소 하나의 입력(텍스트, 이미지, 비디오, 오디오)이 필요합니다")

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

        logger.info(f"Multimodal search request with inputs: {', '.join(input_types)}")

        # 멀티모달 검색 수행
        result = await search_service.search_multimodal(
            text_query=text_query,
            image_file=image,
            video_file=video,
            audio_file=audio,
            include_chunk_meta=include_chunk_meta,
            include_media_meta=include_media_meta,
            max_results=max_results
        )

        logger.info(f"Multimodal search completed: {result.total_hits} hits in {result.took_ms}ms")
        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Multimodal search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/demo", response_class=HTMLResponse)
async def search_demo_interface(request: Request):
    """Multimodal search demo interface"""
    return templates.TemplateResponse("search.html", {"request": request})
