import json
import time
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, StreamingResponse
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
        text_query: Optional[str] = Form(default="쿼리를 입력해주세요", description="텍스트 검색 쿼리"),
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


@router.post("/search/multimodal/stream")
async def search_multimodal_stream(
        text_query: Optional[str] = Form(default="쿼리를 입력해주세요", description="텍스트 검색 쿼리"),
        image: Optional[UploadFile] = File(default=None, description="이미지 파일"),
        video: Optional[UploadFile] = File(default=None, description="비디오 파일"),
        audio: Optional[UploadFile] = File(default=None, description="오디오 파일"),
        include_chunk_meta: bool = Form(default=True, description="Chunk 메타데이터 포함 여부"),
        include_media_meta: bool = Form(default=True, description="Media 메타데이터 포함 여부"),
        max_results: int = Form(default=10, ge=1, le=100, description="최대 결과 수"),
        search_service: SearchService = Depends(get_search_service)
):
    """실시간 스트리밍 방식의 멀티모달 검색 엔드포인트"""
    # 요청 받자마자 즉시 파일들을 읽어서 메모리에 보관
    processed_files = {}
    file_processing_errors = []
    
    # 파일들을 즉시 처리 (스트림 생성 전에)
    if image:
        try:
            logger.info(f"🔄 Reading image file immediately: {image.filename}")
            image_content = await image.read()
            logger.info(f"📊 Image read result: {len(image_content) if image_content else 0} bytes")
            
            if image_content and len(image_content) > 0:
                processed_files['image'] = {
                    'data': image_content,
                    'filename': image.filename or 'unknown_image',
                    'content_type': image.content_type or 'image/jpeg'
                }
                logger.info(f"✅ Image processing successful: {len(image_content)} bytes")
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
            logger.info(f"🔄 Reading video file immediately: {video.filename}")
            video_content = await video.read()
            logger.info(f"📊 Video read result: {len(video_content) if video_content else 0} bytes")
            
            if video_content and len(video_content) > 0:
                processed_files['video'] = {
                    'data': video_content,
                    'filename': video.filename or 'unknown_video',
                    'content_type': video.content_type or 'video/mp4'
                }
                logger.info(f"✅ Video processing successful: {len(video_content)} bytes")
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
            logger.info(f"🔄 Reading audio file immediately: {audio.filename}")
            audio_content = await audio.read()
            logger.info(f"📊 Audio read result: {len(audio_content) if audio_content else 0} bytes")
            
            if audio_content and len(audio_content) > 0:
                processed_files['audio'] = {
                    'data': audio_content,
                    'filename': audio.filename or 'unknown_audio',
                    'content_type': audio.content_type or 'audio/mp3'
                }
                logger.info(f"✅ Audio processing successful: {len(audio_content)} bytes")
            else:
                error_msg = f"오디오 파일이 비어있습니다: {audio.filename}"
                file_processing_errors.append(error_msg)
                logger.error(f"❌ {error_msg}")
        except Exception as e:
            error_msg = f"오디오 파일 읽기 실패: {str(e)}"
            file_processing_errors.append(error_msg)
            logger.error(f"❌ {error_msg}")
    
    logger.info(f"📋 Pre-processing complete: {len(processed_files)} files ready, {len(file_processing_errors)} errors")
    
    async def generate_search_stream():
        try:
            # 파일 처리 오류가 있었다면 스트리밍으로 알림
            if file_processing_errors:
                for error in file_processing_errors:
                    yield f"data: {json.dumps({'step': 'file_read_failed', 'message': error, 'timestamp': time.time()}, ensure_ascii=False)}\\n\\n"
            
            # 처리된 파일 데이터와 함께 스트리밍 검색 시작
            async for step_result in search_service.search_multimodal_stream(
                text_query=text_query,
                processed_files=processed_files,
                include_chunk_meta=include_chunk_meta,
                include_media_meta=include_media_meta,
                max_results=max_results
            ):
                # SSE 형식으로 데이터 전송
                yield f"data: {json.dumps(step_result, ensure_ascii=False, default=str)}\n\n"
                
        except Exception as e:
            logger.error(f"Streaming search failed: {e}")
            error_result = {
                "step": "error",
                "error": str(e),
                "timestamp": time.time()
            }
            yield f"data: {json.dumps(error_result, ensure_ascii=False)}\n\n"
    
    return StreamingResponse(
        generate_search_stream(),
        media_type="text/plain",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "*",
        }

    )


@router.get("/demo", response_class=HTMLResponse)
async def search_demo_interface(request: Request):
    """Multimodal search demo interface"""
    return templates.TemplateResponse("search.html", {"request": request})
