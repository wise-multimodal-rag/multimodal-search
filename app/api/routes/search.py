from fastapi import APIRouter, HTTPException, Form, File, UploadFile, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi import Request
from typing import Optional, List
from loguru import logger

from app.models.requests import MultimodalSearchRequest
from app.models.opensearch import SearchResponse
from app.services.search_service import SearchService
from app.core.dependencies import get_search_service

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.post("/search/multimodal", response_model=SearchResponse)
async def search_multimodal(
    text_query: Optional[str] = Form(default=None, description="텍스트 검색 쿼리"),
    image: Optional[UploadFile] = File(default=None, description="이미지 파일"),
    video: Optional[UploadFile] = File(default=None, description="비디오 파일"),
    audio: Optional[UploadFile] = File(default=None, description="오디오 파일"),
    include_chunk_meta: bool = Form(default=True, description="Chunk 메타데이터 포함 여부"),
    include_media_meta: bool = Form(default=True, description="Media 메타데이터 포함 여부"),
    max_results: int = Form(default=10, ge=1, le=100, description="최대 결과 수"),
    offset: int = Form(default=0, ge=0, description="결과 오프셋"),
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
            max_results=max_results,
            offset=offset
        )
        
        logger.info(f"Multimodal search completed: {result.total_hits} hits in {result.took_ms}ms")
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Multimodal search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))



@router.get("/chatbot", response_class=HTMLResponse)
async def chatbot_interface(request: Request):
    """Simple chatbot interface"""
    return templates.TemplateResponse("chatbot.html", {"request": request})


@router.get("/element-types")
async def get_available_element_types(
    search_service: SearchService = Depends(get_search_service)
):
    """Get available element types"""
    return {
        "element_types": search_service.available_element_types,
        "descriptions": {
            # Text modality
            "paragraph": "일반 문단 - 문서의 본문 내용",
            "title": "제목 - 문서/섹션 제목",
            "summary": "AI 요약 - 자동 생성된 요약문",
            "stt": "음성→텍스트 - 음성인식 결과",
            "caption": "이미지 설명 - AI가 생성한 이미지 캡션",
            "scene": "비디오 장면 설명 - 비디오 장면에 대한 텍스트 설명",
            "ocr": "이미지→텍스트 - OCR로 추출한 텍스트",
            "table": "표 데이터 - JSON 형태의 구조화된 표",
            "translation": "번역 결과 - 다른 언어로 번역된 텍스트",
            
            # Image modality
            "origin": "원본 이미지 - 최초 업로드된 이미지",
            "cropped": "잘린 이미지 - 특정 영역을 추출한 이미지",
            "detected_object": "감지된 객체 - 객체 감지로 추출한 영역",
            "chart": "차트/그래프 - 데이터 시각화 이미지",
            "diagram": "다이어그램 - 구조도, 플로우차트 등",
            "keyframe": "키 프레임 - 비디오에서 추출한 대표 프레임 이미지",
            "thumbnail": "썸네일 - 비디오의 썸네일 이미지",
            
            # Video modality
            "clip": "비디오 클립 - 특정 시간 구간의 영상",
            "segment": "비디오 구간 - 의미적으로 구분된 비디오 구간",
            
            # Audio modality
            "speech": "사람의 발화 구간 - 특정 화자의 발언 부분",
            "music": "배경음악이나 음악 콘텐츠 - 인트로 음악, 배경음 등",
            "sound_effect": "특수 효과음 - 박수소리, 벨소리, 알림음",
            "ambient": "주변 환경음 - 에어컨 소리, 발걸음, 잡음"
        }
    }