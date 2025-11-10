"""공통 유틸리티 함수들"""
import base64
from typing import Any, Dict, Optional

from fastapi import UploadFile
from loguru import logger


async def process_upload_file_to_base64(file: UploadFile, file_type: str) -> Dict[str, Any]:
    """UploadFile을 base64로 인코딩하여 구조화된 데이터로 변환
    
    Args:
        file: FastAPI UploadFile 객체
        file_type: 파일 타입 (image, video, audio, text_file)
        
    Returns:
        파일 정보와 base64 데이터를 포함한 딕셔너리
    """
    try:
        # 파일 포인터를 시작점으로 리셋 시도
        try:
            await file.seek(0)
        except Exception:
            # seek이 실패해도 계속 진행
            pass

        # 파일 읽기
        file_content = await file.read()
        
        # 데이터가 비어있는 경우 처리
        if not file_content:
            logger.warning(f"{file_type} file {file.filename} is empty or already read")
            return {
                "error": "File is empty or already processed",
                "type": file_type
            }

        # Base64 인코딩
        base64_data = base64.b64encode(file_content).decode("utf-8")
        
        # 기본 content_type 설정
        default_content_types = {
            "image": "image/jpeg",
            "video": "video/mp4", 
            "audio": "audio/mp3",
            "text_file": "text/plain"
        }
        
        result = {
            "base64_data": base64_data,
            "content_type": file.content_type or default_content_types.get(file_type, "application/octet-stream"),
            "filename": file.filename,
            "size": len(file_content),
            "type": file_type
        }
        
        logger.info(f"Processed {file_type}: {file.filename} ({len(file_content)} bytes)")
        return result
        
    except Exception as e:
        logger.error(f"Failed to process {file_type} file {file.filename}: {e}")
        return {
            "error": str(e),
            "type": file_type
        }


def encode_bytes_to_base64(data: bytes) -> str:
    """바이트 데이터를 base64 문자열로 인코딩
    
    Args:
        data: 인코딩할 바이트 데이터
        
    Returns:
        base64 인코딩된 문자열
    """
    return base64.b64encode(data).decode("utf-8")


def decode_base64_to_bytes(base64_str: str) -> bytes:
    """base64 문자열을 바이트 데이터로 디코딩
    
    Args:
        base64_str: 디코딩할 base64 문자열
        
    Returns:
        디코딩된 바이트 데이터
    """
    return base64.b64decode(base64_str)


async def prepare_multimodal_request_data(
    text_query: Optional[str],
    image: Optional[UploadFile],
    video: Optional[UploadFile], 
    audio: Optional[UploadFile],
    text_file: Optional[UploadFile],
    max_results: int,
    include_chunk_meta: bool,
    include_media_meta: bool,
) -> Dict[str, Any]:
    """멀티모달 요청 데이터를 준비하는 공통 함수
    
    Args:
        text_query: 텍스트 쿼리
        image: 이미지 파일
        video: 비디오 파일
        audio: 오디오 파일
        text_file: 텍스트 파일
        max_results: 최대 결과 수
        include_chunk_meta: 청크 메타데이터 포함 여부
        include_media_meta: 미디어 메타데이터 포함 여부
        
    Returns:
        준비된 요청 데이터
    """
    request_data = {
        "text_query": text_query,
        "max_results": max_results,
        "include_chunk_meta": include_chunk_meta,
        "include_media_meta": include_media_meta,
    }

    # 파일들 처리
    file_mappings = [
        (image, "image"),
        (video, "video"),
        (audio, "audio"), 
        (text_file, "text_file")
    ]
    
    for file_obj, file_type in file_mappings:
        if file_obj:
            file_data = await process_upload_file_to_base64(file_obj, file_type)
            if "error" not in file_data:
                request_data[file_type] = file_data
            else:
                logger.warning(f"Failed to process {file_type}: {file_data['error']}")

    return request_data


def get_input_types(
    text_query: Optional[str],
    image: Optional[UploadFile],
    video: Optional[UploadFile],
    audio: Optional[UploadFile],
    text_file: Optional[UploadFile] = None,
) -> list[str]:
    """입력된 모달리티 타입들을 반환하는 공통 함수
    
    Args:
        text_query: 텍스트 쿼리
        image: 이미지 파일
        video: 비디오 파일  
        audio: 오디오 파일
        text_file: 텍스트 파일
        
    Returns:
        입력된 모달리티 타입 리스트
    """
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
    return input_types