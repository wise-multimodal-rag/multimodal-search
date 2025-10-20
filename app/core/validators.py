"""Input validation utilities for multimodal search."""

import base64
import re
from typing import Any, Dict, List, Optional, Tuple
from fastapi import HTTPException, status
from loguru import logger


class InputValidator:
    """사용자 입력 검증 클래스"""
    
    # 제한 설정
    MAX_TEXT_LENGTH = 10000  # 10KB
    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
    MAX_RESULTS = 1000
    MIN_RESULTS = 1
    
    ALLOWED_IMAGE_TYPES = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
    ALLOWED_VIDEO_TYPES = ['video/mp4', 'video/webm', 'video/avi', 'video/mov']
    ALLOWED_AUDIO_TYPES = ['audio/mp3', 'audio/wav', 'audio/ogg', 'audio/m4a']
    
    @classmethod
    def validate_text_query(cls, text: Optional[str]) -> Optional[str]:
        """텍스트 쿼리 검증"""
        if not text:
            return None
            
        text = text.strip()
        if not text:
            return None
            
        if len(text) > cls.MAX_TEXT_LENGTH:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Text query too long. Maximum {cls.MAX_TEXT_LENGTH} characters allowed."
            )
        
        # 악성 패턴 검사 (기본적인 XSS 방지)
        dangerous_patterns = [
            r'<script.*?>.*?</script>',
            r'javascript:',
            r'on\w+\s*=',
            r'<iframe.*?>.*?</iframe>'
        ]
        
        for pattern in dangerous_patterns:
            if re.search(pattern, text, re.IGNORECASE | re.DOTALL):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Text contains potentially dangerous content"
                )
        
        return text
    
    @classmethod
    def validate_max_results(cls, max_results: Optional[int]) -> int:
        """결과 수 제한 검증"""
        if max_results is None:
            return 50  # 기본값
            
        if not isinstance(max_results, int):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="max_results must be an integer"
            )
            
        if max_results < cls.MIN_RESULTS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"max_results must be at least {cls.MIN_RESULTS}"
            )
            
        if max_results > cls.MAX_RESULTS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"max_results cannot exceed {cls.MAX_RESULTS}"
            )
        
        return max_results
    
    @classmethod
    def validate_base64_file(cls, base64_data: str, file_type: str, allowed_types: List[str]) -> Tuple[bytes, int]:
        """Base64 파일 데이터 검증"""
        try:
            # Base64 디코딩
            file_data = base64.b64decode(base64_data)
            file_size = len(file_data)
            
            # 파일 크기 검사
            if file_size > cls.MAX_FILE_SIZE:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"File too large. Maximum {cls.MAX_FILE_SIZE // (1024*1024)}MB allowed."
                )
            
            if file_size == 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Empty file data"
                )
            
            # MIME 타입 검사
            if file_type not in allowed_types:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Unsupported file type: {file_type}. Allowed types: {allowed_types}"
                )
            
            # 파일 시그니처 검사 (간단한 검증)
            if not cls._validate_file_signature(file_data, file_type):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="File data does not match declared type"
                )
            
            return file_data, file_size
            
        except base64.binascii.Error:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid base64 data"
            )
    
    @classmethod
    def _validate_file_signature(cls, file_data: bytes, file_type: str) -> bool:
        """파일 시그니처 검증 - 더 유연한 검증"""
        if len(file_data) < 4:
            return False
            
        # 파일 시그니처 매핑 (처음 몇 바이트)
        signatures = {
            'image/jpeg': [
                b'\xff\xd8\xff\xe0',  # JFIF
                b'\xff\xd8\xff\xe1',  # EXIF
                b'\xff\xd8\xff\xdb',  # JPEG raw
                b'\xff\xd8\xff\xc0',  # JPEG baseline
                b'\xff\xd8\xff\xc2',  # JPEG progressive
                b'\xff\xd8\xff'       # General JPEG
            ],
            'image/png': [b'\x89PNG\r\n\x1a\n'],
            'image/gif': [b'GIF87a', b'GIF89a'],
            'image/webp': [b'RIFF'],  # WEBP는 RIFF로 시작
            'video/mp4': [b'ftyp', b'moov', b'\x00\x00\x00'],
            'video/webm': [b'\x1a\x45\xdf\xa3'],
            'video/avi': [b'RIFF'],
            'video/mov': [b'ftyp', b'moov'],
            'audio/mp3': [b'ID3', b'\xff\xfb', b'\xff\xf3', b'\xff\xf2'],
            'audio/wav': [b'RIFF'],
            'audio/m4a': [b'ftyp'],
            'audio/ogg': [b'OggS']
        }
        
        expected_signatures = signatures.get(file_type, [])
        if not expected_signatures:
            return True  # 알 수 없는 타입은 통과
            
        # 더 유연한 검증 - 처음 16바이트 내에서 시그니처 찾기
        search_area = file_data[:16]
        
        for signature in expected_signatures:
            # 정확한 시작 매치
            if file_data.startswith(signature):
                return True
            # 처음 16바이트 내 어디든 포함
            if signature in search_area:
                return True
            # WebP의 경우 RIFF 후 WEBP 확인
            if file_type == 'image/webp' and b'RIFF' in search_area[:8] and b'WEBP' in file_data[8:16]:
                return True
                
        # 특별 케이스들
        if file_type.startswith('image/') and len(file_data) > 100:
            # 이미지 파일이면서 최소 크기가 있으면 통과 (너무 작은 파일 제외)
            return True
            
        return False
    
    @classmethod
    def validate_search_request(cls, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """전체 검색 요청 검증"""
        validated = {}
        
        # 텍스트 쿼리 검증
        if 'text_query' in request_data:
            validated['text_query'] = cls.validate_text_query(request_data['text_query'])
        
        # 결과 수 제한 검증
        validated['max_results'] = cls.validate_max_results(request_data.get('max_results'))
        
        # 파일 데이터 검증
        if 'image' in request_data:
            image_data = request_data['image']
            if isinstance(image_data, dict) and 'base64_data' in image_data and 'content_type' in image_data:
                file_data, file_size = cls.validate_base64_file(
                    image_data['base64_data'], 
                    image_data['content_type'], 
                    cls.ALLOWED_IMAGE_TYPES
                )
                validated['image'] = {
                    'base64_data': image_data['base64_data'],
                    'content_type': image_data['content_type'],
                    'file_size': file_size
                }
        
        if 'video' in request_data:
            video_data = request_data['video']
            if isinstance(video_data, dict) and 'base64_data' in video_data and 'content_type' in video_data:
                file_data, file_size = cls.validate_base64_file(
                    video_data['base64_data'], 
                    video_data['content_type'], 
                    cls.ALLOWED_VIDEO_TYPES
                )
                validated['video'] = {
                    'base64_data': video_data['base64_data'],
                    'content_type': video_data['content_type'],
                    'file_size': file_size
                }
        
        if 'audio' in request_data:
            audio_data = request_data['audio']
            if isinstance(audio_data, dict) and 'base64_data' in audio_data and 'content_type' in audio_data:
                file_data, file_size = cls.validate_base64_file(
                    audio_data['base64_data'], 
                    audio_data['content_type'], 
                    cls.ALLOWED_AUDIO_TYPES
                )
                validated['audio'] = {
                    'base64_data': audio_data['base64_data'],
                    'content_type': audio_data['content_type'],
                    'file_size': file_size
                }
        
        # 옵션 검증
        validated['include_chunk_meta'] = bool(request_data.get('include_chunk_meta', False))
        validated['include_media_meta'] = bool(request_data.get('include_media_meta', False))
        
        # 최소한 하나의 입력이 있는지 확인
        has_input = (
            validated.get('text_query') or 
            'image' in validated or 
            'video' in validated or 
            'audio' in validated
        )
        
        if not has_input:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least one input (text_query, image, video, or audio) is required"
            )
        
        return validated


# 전역 검증 인스턴스
input_validator = InputValidator()