"""Input validation utilities for multimodal search."""

import base64
import binascii
import re
from typing import Any, Dict, List, Optional, Tuple

from app.exceptions.base import ValidationException


class InputValidator:
    """사용자 입력 검증 클래스"""

    # 제한 설정
    MAX_TEXT_LENGTH = 10000  # 10KB
    MAX_FILE_SIZE = 20 * 1024 * 1024  # 20MB (이미지, 비디오, 오디오)
    MAX_DOCUMENT_SIZE = 512 * 1024 * 1024  # 512MB (문서 파일)
    MAX_RESULTS = 1000
    MIN_RESULTS = 1

    ALLOWED_IMAGE_TYPES = ["image/jpeg", "image/png", "image/gif", "image/webp"]
    ALLOWED_VIDEO_TYPES = ["video/mp4", "video/webm", "video/avi", "video/mov"]
    ALLOWED_AUDIO_TYPES = ["audio/mp3", "audio/wav", "audio/ogg", "audio/m4a"]
    ALLOWED_TEXT_TYPES = [
        "text/plain",
        "text/markdown",
        "text/csv",
        "text/json",
        "application/json",
        "text/xml",
        "application/xml",
        "text/html",
        "application/pdf",
    ]

    @classmethod
    def validate_text_query(cls, text: Optional[str]) -> Optional[str]:
        """텍스트 쿼리 검증"""
        if not text:
            return None

        text = text.strip()
        if not text:
            return None

        if len(text) > cls.MAX_TEXT_LENGTH:
            raise ValidationException(
                f"Text query too long. Maximum {cls.MAX_TEXT_LENGTH} characters allowed.",
                field="text_query"
            )

        # 악성 패턴 검사 (기본적인 XSS 방지)
        dangerous_patterns = [r"<script.*?>.*?</script>", r"javascript:", r"on\w+\s*=", r"<iframe.*?>.*?</iframe>"]

        for pattern in dangerous_patterns:
            if re.search(pattern, text, re.IGNORECASE | re.DOTALL):
                raise ValidationException(
                    "Text contains potentially dangerous content",
                    field="text_query"
                )

        return text

    @classmethod
    def validate_max_results(cls, max_results: Optional[int]) -> int:
        """결과 수 제한 검증"""
        if max_results is None:
            return 50  # 기본값

        if not isinstance(max_results, int):
            raise ValidationException("max_results must be an integer", field="max_results")

        if max_results < cls.MIN_RESULTS:
            raise ValidationException(
                f"max_results must be at least {cls.MIN_RESULTS}",
                field="max_results"
            )

        if max_results > cls.MAX_RESULTS:
            raise ValidationException(
                f"max_results cannot exceed {cls.MAX_RESULTS}",
                field="max_results"
            )

        return max_results

    @classmethod
    def validate_base64_file(cls, base64_data: str, file_type: str, allowed_types: List[str],
                             is_document: bool = False) -> Tuple[bytes, int]:
        """Base64 파일 데이터 검증"""
        try:
            # Base64 디코딩
            file_data = base64.b64decode(base64_data)
            file_size = len(file_data)

            # 파일 크기 검사 - 문서 파일과 미디어 파일 구분
            max_size = cls.MAX_DOCUMENT_SIZE if is_document else cls.MAX_FILE_SIZE
            max_size_mb = max_size // (1024 * 1024)

            if file_size > max_size:
                raise ValidationException(
                    f"File too large. Maximum {max_size_mb}MB allowed.",
                    field="file_size"
                )

            if file_size == 0:
                raise ValidationException("Empty file data", field="file_data")

            # MIME 타입 검사
            if file_type not in allowed_types:
                raise ValidationException(
                    f"Unsupported file type: {file_type}. Allowed types: {allowed_types}",
                    field="file_type"
                )

            # 파일 시그니처 검사 (간단한 검증)
            if not cls._validate_file_signature(file_data, file_type):
                raise ValidationException("File data does not match declared type", field="file_signature")

            return file_data, file_size

        except binascii.Error:
            raise ValidationException("Invalid base64 data", field="file_data")

    @classmethod
    def _validate_file_signature(cls, file_data: bytes, file_type: str) -> bool:
        """파일 시그니처 검증 - 더 유연한 검증"""
        if len(file_data) < 4:
            return False

        # 파일 시그니처 매핑 (처음 몇 바이트)
        signatures = {
            "image/jpeg": [
                b"\xff\xd8\xff\xe0",  # JFIF
                b"\xff\xd8\xff\xe1",  # EXIF
                b"\xff\xd8\xff\xdb",  # JPEG raw
                b"\xff\xd8\xff\xc0",  # JPEG baseline
                b"\xff\xd8\xff\xc2",  # JPEG progressive
                b"\xff\xd8\xff",  # General JPEG
            ],
            "image/png": [b"\x89PNG\r\n\x1a\n"],
            "image/gif": [b"GIF87a", b"GIF89a"],
            "image/webp": [b"RIFF"],  # WEBP는 RIFF로 시작
            "video/mp4": [b"ftyp", b"moov", b"\x00\x00\x00"],
            "video/webm": [b"\x1a\x45\xdf\xa3"],
            "video/avi": [b"RIFF"],
            "video/mov": [b"ftyp", b"moov"],
            "audio/mp3": [b"ID3", b"\xff\xfb", b"\xff\xf3", b"\xff\xf2"],
            "audio/wav": [b"RIFF"],
            "audio/m4a": [b"ftyp"],
            "audio/ogg": [b"OggS"],
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
            if file_type == "image/webp" and b"RIFF" in search_area[:8] and b"WEBP" in file_data[8:16]:
                return True

        # 특별 케이스들
        if file_type.startswith("image/") and len(file_data) > 100:
            # 이미지 파일이면서 최소 크기가 있으면 통과 (너무 작은 파일 제외)
            return True

        return False

    @classmethod
    def validate_search_request(cls, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """전체 검색 요청 검증"""
        validated = {}

        # 텍스트 쿼리 검증
        if "text_query" in request_data:
            validated["text_query"] = cls.validate_text_query(request_data["text_query"])

        # 결과 수 제한 검증
        validated["max_results"] = cls.validate_max_results(request_data.get("max_results"))

        # 파일 데이터 검증
        if "image" in request_data:
            image_data = request_data["image"]
            if isinstance(image_data, dict) and "base64_data" in image_data and "content_type" in image_data:
                file_data, file_size = cls.validate_base64_file(
                    image_data["base64_data"], image_data["content_type"], cls.ALLOWED_IMAGE_TYPES
                )
                validated["image"] = {
                    "base64_data": image_data["base64_data"],
                    "content_type": image_data["content_type"],
                    "file_size": file_size,
                }

        if "video" in request_data:
            video_data = request_data["video"]
            if isinstance(video_data, dict) and "base64_data" in video_data and "content_type" in video_data:
                file_data, file_size = cls.validate_base64_file(
                    video_data["base64_data"], video_data["content_type"], cls.ALLOWED_VIDEO_TYPES
                )
                validated["video"] = {
                    "base64_data": video_data["base64_data"],
                    "content_type": video_data["content_type"],
                    "file_size": file_size,
                }

        if "audio" in request_data:
            audio_data = request_data["audio"]
            if isinstance(audio_data, dict) and "base64_data" in audio_data and "content_type" in audio_data:
                file_data, file_size = cls.validate_base64_file(
                    audio_data["base64_data"], audio_data["content_type"], cls.ALLOWED_AUDIO_TYPES
                )
                validated["audio"] = {
                    "base64_data": audio_data["base64_data"],
                    "content_type": audio_data["content_type"],
                    "file_size": file_size,
                }

        if "text_file" in request_data:
            text_data = request_data["text_file"]
            if isinstance(text_data, dict) and "base64_data" in text_data and "content_type" in text_data:
                file_data, file_size = cls.validate_base64_file(
                    text_data["base64_data"], text_data["content_type"], cls.ALLOWED_TEXT_TYPES, is_document=True
                )
                validated["text_file"] = {
                    "base64_data": text_data["base64_data"],
                    "content_type": text_data["content_type"],
                    "file_size": file_size,
                    "filename": text_data.get("filename", "unknown.txt"),
                }

        # 옵션 검증
        validated["include_chunk_meta"] = bool(request_data.get("include_chunk_meta", False))
        validated["include_media_meta"] = bool(request_data.get("include_media_meta", False))

        # 최소한 하나의 입력이 있는지 확인
        has_input = (
                validated.get("text_query")
                or "image" in validated
                or "video" in validated
                or "audio" in validated
                or "text_file" in validated
        )

        if not has_input:
            raise ValidationException(
                "At least one input (text_query, image, video, audio, or text_file) is required",
                field="input"
            )

        return validated
