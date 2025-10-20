from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from loguru import logger

from app.core.dependencies import get_search_service
from app.core.validators import input_validator
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
        # 고급 입력 검증
        request_data = {
            'text_query': text_query,
            'max_results': max_results,
            'include_chunk_meta': include_chunk_meta,
            'include_media_meta': include_media_meta
        }
        
        # 파일 데이터 추가 (필요한 경우)
        if image:
            import base64
            image_content = await image.read()
            request_data['image'] = {
                'base64_data': base64.b64encode(image_content).decode('utf-8'),
                'content_type': image.content_type or 'image/jpeg',
                'filename': image.filename
            }
        
        if video:
            import base64
            video_content = await video.read()
            request_data['video'] = {
                'base64_data': base64.b64encode(video_content).decode('utf-8'),
                'content_type': video.content_type or 'video/mp4',
                'filename': video.filename
            }
        
        if audio:
            import base64
            audio_content = await audio.read()
            request_data['audio'] = {
                'base64_data': base64.b64encode(audio_content).decode('utf-8'),
                'content_type': audio.content_type or 'audio/mp3',
                'filename': audio.filename
            }
        
        # 통합 검증 실행
        try:
            validated_data = input_validator.validate_search_request(request_data)
        except Exception as validation_error:
            logger.error(f"Input validation failed: {validation_error}")
            # Log request data without base64 content
            debug_data = {}
            for key, value in request_data.items():
                if key in ['image', 'video', 'audio'] and isinstance(value, dict):
                    debug_data[key] = {
                        'content_type': value.get('content_type'),
                        'filename': value.get('filename'),
                        'data_size': len(value.get('base64_data', '')) if 'base64_data' in value else 0
                    }
                else:
                    debug_data[key] = value
            logger.debug(f"Request data: {debug_data}")
            raise
        
        # 검증된 데이터에서 값 추출
        text_query = validated_data.get('text_query')
        max_results = validated_data['max_results']
        include_chunk_meta = validated_data['include_chunk_meta']
        include_media_meta = validated_data['include_media_meta']

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

        return result

    except HTTPException as e:
        logger.warning(f"HTTP {e.status_code} error in multimodal search: {e.detail}")
        raise
    except Exception as e:
        logger.error(f"Multimodal search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/demo", response_class=HTMLResponse)
async def search_demo_interface(request: Request):
    """Multimodal search demo interface"""
    return templates.TemplateResponse("search.html", {"request": request})
