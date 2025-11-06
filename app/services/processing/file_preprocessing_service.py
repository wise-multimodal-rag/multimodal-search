"""파일 전처리 서비스
업로드된 파일들을 읽고 검증하는 기능을 담당
"""
from typing import Dict, List, Optional, Tuple

from fastapi import UploadFile
from loguru import logger


class FilePreprocessingService:
    """파일 전처리 서비스"""

    @staticmethod
    async def preprocess_files(
        image: Optional[UploadFile] = None,
        video: Optional[UploadFile] = None,
        audio: Optional[UploadFile] = None,
        text_file: Optional[UploadFile] = None,
    ) -> Tuple[Dict[str, Dict], List[str]]:
        """업로드된 파일들을 전처리합니다.
        
        Args:
            image: 이미지 파일
            video: 비디오 파일
            audio: 오디오 파일
            text_file: 텍스트 파일
            
        Returns:
            Tuple[processed_files, file_processing_errors]
        """
        processed_files = {}
        file_processing_errors = []

        # 이미지 파일 처리
        if image:
            try:
                image_content = await image.read()
                logger.info(f"📷 Image: {image.filename} ({len(image_content) if image_content else 0} bytes)")

                if image_content and len(image_content) > 0:
                    processed_files["image"] = {
                        "data": image_content,
                        "filename": image.filename or "unknown_image",
                        "content_type": image.content_type or "image/jpeg",
                    }
                else:
                    error_msg = f"이미지 파일이 비어있습니다: {image.filename}"
                    file_processing_errors.append(error_msg)
                    logger.error(f"❌ {error_msg}")
            except Exception as e:
                error_msg = f"이미지 파일 읽기 실패: {str(e)}"
                file_processing_errors.append(error_msg)
                logger.error(f"❌ {error_msg}")

        # 비디오 파일 처리
        if video:
            try:
                video_content = await video.read()
                logger.info(f"🎥 Video: {video.filename} ({len(video_content) if video_content else 0} bytes)")

                if video_content and len(video_content) > 0:
                    processed_files["video"] = {
                        "data": video_content,
                        "filename": video.filename or "unknown_video",
                        "content_type": video.content_type or "video/mp4",
                    }
                else:
                    error_msg = f"비디오 파일이 비어있습니다: {video.filename}"
                    file_processing_errors.append(error_msg)
                    logger.error(f"❌ {error_msg}")
            except Exception as e:
                error_msg = f"비디오 파일 읽기 실패: {str(e)}"
                file_processing_errors.append(error_msg)
                logger.error(f"❌ {error_msg}")

        # 오디오 파일 처리
        if audio:
            try:
                audio_content = await audio.read()
                logger.info(f"🎵 Audio: {audio.filename} ({len(audio_content) if audio_content else 0} bytes)")

                if audio_content and len(audio_content) > 0:
                    processed_files["audio"] = {
                        "data": audio_content,
                        "filename": audio.filename or "unknown_audio",
                        "content_type": audio.content_type or "audio/mp3",
                    }
                else:
                    error_msg = f"오디오 파일이 비어있습니다: {audio.filename}"
                    file_processing_errors.append(error_msg)
                    logger.error(f"❌ {error_msg}")
            except Exception as e:
                error_msg = f"오디오 파일 읽기 실패: {str(e)}"
                file_processing_errors.append(error_msg)
                logger.error(f"❌ {error_msg}")

        # 텍스트 파일 처리
        if text_file:
            try:
                text_content = await text_file.read()
                logger.info(f"📄 Text: {text_file.filename} ({len(text_content) if text_content else 0} bytes)")

                if text_content and len(text_content) > 0:
                    processed_files["text_file"] = {
                        "data": text_content,
                        "filename": text_file.filename or "unknown.txt",
                        "content_type": text_file.content_type or "text/plain",
                    }
                else:
                    error_msg = f"텍스트 파일이 비어있습니다: {text_file.filename}"
                    file_processing_errors.append(error_msg)
                    logger.error(f"❌ {error_msg}")
            except Exception as e:
                error_msg = f"텍스트 파일 읽기 실패: {str(e)}"
                file_processing_errors.append(error_msg)
                logger.error(f"❌ {error_msg}")

        logger.info(f"📋 Files ready: {len(processed_files)}, errors: {len(file_processing_errors)}")

        return processed_files, file_processing_errors