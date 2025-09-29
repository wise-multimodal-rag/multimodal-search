from typing import Dict, Any, Optional
import base64
from fastapi import UploadFile
from loguru import logger


class InputProcessor:
    """멀티모달 입력 처리를 담당하는 서비스"""

    async def process_multimodal_inputs(
        self,
        text_query: Optional[str],
        image_file: Optional[UploadFile],
        video_file: Optional[UploadFile],
        audio_file: Optional[UploadFile]
    ) -> Dict[str, Any]:
        """멀티모달 입력을 base64로 인코딩하여 구조화된 데이터로 변환"""
        modalities_data = {}

        # 텍스트 처리
        if text_query:
            modalities_data["text"] = {
                "query": text_query,
                "type": "text"
            }

        # 이미지 처리 (인코딩만)
        if image_file:
            image_data = await self._process_image_file(image_file)
            if image_data:
                modalities_data["image"] = image_data

        # 비디오 처리 (인코딩만)
        if video_file:
            video_data = await self._process_video_file(video_file)
            if video_data:
                modalities_data["video"] = video_data

        # 오디오 처리 (인코딩만)
        if audio_file:
            audio_data = await self._process_audio_file(audio_file)
            if audio_data:
                modalities_data["audio"] = audio_data

        return modalities_data

    async def _process_image_file(self, image_file: UploadFile) -> Optional[Dict[str, Any]]:
        """이미지 파일을 base64로 인코딩"""
        try:
            image_data = await image_file.read()
            
            # 이미지를 base64로 인코딩
            base64_image = base64.b64encode(image_data).decode('utf-8')
            
            result = {
                "filename": image_file.filename,
                "content_type": image_file.content_type,
                "size": len(image_data),
                "base64_data": base64_image,
                "type": "image"
            }
            
            logger.info(f"Processed image: {image_file.filename} ({len(image_data)} bytes)")
            return result
            
        except Exception as e:
            logger.error(f"Failed to process image: {e}")
            return {"error": str(e), "type": "image"}

    async def _process_video_file(self, video_file: UploadFile) -> Optional[Dict[str, Any]]:
        """비디오 파일을 base64로 인코딩"""
        try:
            video_data = await video_file.read()
            
            # 비디오를 base64로 인코딩
            base64_video = base64.b64encode(video_data).decode('utf-8')
            
            result = {
                "filename": video_file.filename,
                "content_type": video_file.content_type,
                "size": len(video_data),
                "base64_data": base64_video,
                "type": "video"
            }
            
            logger.info(f"Processed video: {video_file.filename} ({len(video_data)} bytes)")
            return result
            
        except Exception as e:
            logger.error(f"Failed to process video: {e}")
            return {"error": str(e), "type": "video"}

    async def _process_audio_file(self, audio_file: UploadFile) -> Optional[Dict[str, Any]]:
        """오디오 파일을 base64로 인코딩"""
        try:
            audio_data = await audio_file.read()
            
            # 오디오를 base64로 인코딩  
            base64_audio = base64.b64encode(audio_data).decode('utf-8')
            
            result = {
                "filename": audio_file.filename,
                "content_type": audio_file.content_type,
                "size": len(audio_data),
                "base64_data": base64_audio,
                "type": "audio"
            }
            
            logger.info(f"Processed audio: {audio_file.filename} ({len(audio_data)} bytes)")
            return result
            
        except Exception as e:
            logger.error(f"Failed to process audio: {e}")
            return {"error": str(e), "type": "audio"}

    def validate_inputs(
        self,
        text_query: Optional[str],
        image_file: Optional[UploadFile],
        video_file: Optional[UploadFile],
        audio_file: Optional[UploadFile]
    ) -> bool:
        """입력 검증 - 최소 하나의 입력이 있는지 확인"""
        return any([text_query, image_file, video_file, audio_file])

    def get_input_types(
        self,
        text_query: Optional[str],
        image_file: Optional[UploadFile],
        video_file: Optional[UploadFile],
        audio_file: Optional[UploadFile]
    ) -> list[str]:
        """입력된 모달리티 타입들을 반환"""
        input_types = []
        if text_query:
            input_types.append("text")
        if image_file:
            input_types.append("image")
        if video_file:
            input_types.append("video")
        if audio_file:
            input_types.append("audio")
        return input_types