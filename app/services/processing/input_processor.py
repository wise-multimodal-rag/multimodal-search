import base64
from typing import Any, Dict, Optional

from fastapi import UploadFile
from loguru import logger


class InputProcessor:
    """멀티모달 입력 처리를 담당하는 서비스"""

    async def process_multimodal_inputs(
        self,
        text_query: Optional[str],
        image_file: Optional[UploadFile],
        video_file: Optional[UploadFile],
        audio_file: Optional[UploadFile],
        text_file: Optional[UploadFile] = None
    ) -> Dict[str, Any]:
        """멀티모달 입력을 base64로 인코딩하여 구조화된 데이터로 변환"""
        logger.info(f"처리할 입력들: text_query={bool(text_query)}, image_file={bool(image_file)}, video_file={bool(video_file)}, audio_file={bool(audio_file)}, text_file={bool(text_file)}")
        if text_file:
            logger.info(f"텍스트 파일 정보: filename={text_file.filename}, content_type={text_file.content_type}")
        
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

        # 텍스트 파일 처리
        if text_file:
            logger.info(f"텍스트 파일 처리 시작: {text_file.filename}")
            text_file_data = await self._process_text_file(text_file)
            logger.info(f"텍스트 파일 처리 결과: {text_file_data is not None}")
            if text_file_data:
                modalities_data["text_file"] = text_file_data
                logger.info(f"텍스트 파일이 modalities_data에 추가됨: {text_file_data.get('filename', 'unknown')}")
            else:
                logger.warning("텍스트 파일 처리 실패")
        else:
            logger.info("텍스트 파일이 전달되지 않음")

        logger.info(f"최종 modalities_data 키들: {list(modalities_data.keys())}")
        return modalities_data

    async def process_multimodal_inputs_from_processed(
        self,
        text_query: Optional[str],
        processed_files: Optional[Dict[str, Dict[str, Any]]]
    ) -> Dict[str, Any]:
        """이미 처리된 파일 데이터에서 멀티모달 입력을 구성"""
        modalities_data = {}
        processing_errors = []

        # 텍스트 처리
        if text_query:
            modalities_data["text"] = {
                "query": text_query,
                "type": "text"
            }

        # 처리된 파일 데이터 사용
        if processed_files:
            # 이미지 처리
            if "image" in processed_files:
                try:
                    image_info = processed_files["image"]
                    image_data = self._process_processed_file(
                        image_info["data"], 
                        image_info["filename"], 
                        image_info["content_type"],
                        "image"
                    )
                    if image_data and "error" not in image_data:
                        modalities_data["image"] = image_data
                    else:
                        error_msg = image_data.get("error", "Unknown image processing error") if image_data else "Image data is None"
                        processing_errors.append(f"이미지 처리 실패: {error_msg}")
                        logger.warning(f"Image processing failed: {error_msg}")
                except Exception as e:
                    processing_errors.append(f"이미지 처리 중 예외 발생: {str(e)}")
                    logger.error(f"Exception during image processing: {e}")

            # 비디오 처리
            if "video" in processed_files:
                try:
                    video_info = processed_files["video"]
                    video_data = self._process_processed_file(
                        video_info["data"], 
                        video_info["filename"], 
                        video_info["content_type"],
                        "video"
                    )
                    if video_data and "error" not in video_data:
                        modalities_data["video"] = video_data
                    else:
                        error_msg = video_data.get("error", "Unknown video processing error") if video_data else "Video data is None"
                        processing_errors.append(f"비디오 처리 실패: {error_msg}")
                        logger.warning(f"Video processing failed: {error_msg}")
                except Exception as e:
                    processing_errors.append(f"비디오 처리 중 예외 발생: {str(e)}")
                    logger.error(f"Exception during video processing: {e}")

            # 오디오 처리
            if "audio" in processed_files:
                try:
                    audio_info = processed_files["audio"]
                    audio_data = self._process_processed_file(
                        audio_info["data"], 
                        audio_info["filename"], 
                        audio_info["content_type"],
                        "audio"
                    )
                    if audio_data and "error" not in audio_data:
                        modalities_data["audio"] = audio_data
                    else:
                        error_msg = audio_data.get("error", "Unknown audio processing error") if audio_data else "Audio data is None"
                        processing_errors.append(f"오디오 처리 실패: {error_msg}")
                        logger.warning(f"Audio processing failed: {error_msg}")
                except Exception as e:
                    processing_errors.append(f"오디오 처리 중 예외 발생: {str(e)}")
                    logger.error(f"Exception during audio processing: {e}")

        # 처리 오류가 있었다면 로깅
        if processing_errors:
            logger.warning(f"File processing completed with {len(processing_errors)} errors")
            for error in processing_errors:
                logger.warning(f"Processing error: {error}")

        # 텍스트만 있고 파일 처리가 모두 실패한 경우 경고
        if text_query and len(modalities_data) == 1 and "text" in modalities_data and processed_files:
            logger.warning("All file processing failed, continuing with text-only search")

        return modalities_data

    def _process_processed_file(
        self, 
        file_data: bytes, 
        filename: str, 
        content_type: str, 
        file_type: str
    ) -> Optional[Dict[str, Any]]:
        """이미 읽힌 파일 데이터를 base64로 인코딩"""
        try:
            # 파일을 base64로 인코딩
            base64_data = base64.b64encode(file_data).decode('utf-8')
            
            result = {
                "filename": filename,
                "content_type": content_type,
                "size": len(file_data),
                "base64_data": base64_data,
                "type": file_type
            }
            
            logger.info(f"Processed {file_type}: {filename} ({len(file_data)} bytes)")
            return result
            
        except Exception as e:
            logger.error(f"Failed to process {file_type}: {e}")
            return {"error": str(e), "type": file_type}

    async def _process_image_file(self, image_file: UploadFile) -> Optional[Dict[str, Any]]:
        """이미지 파일을 base64로 인코딩"""
        try:
            # 파일 포인터를 시작점으로 리셋 시도
            try:
                await image_file.seek(0)
            except Exception:
                # seek이 실패해도 계속 진행
                pass
                
            image_data = await image_file.read()
            
            # 데이터가 비어있는 경우 처리
            if not image_data:
                logger.warning(f"Image file {image_file.filename} is empty or already read")
                return {"error": "File is empty or already processed", "type": "image"}
            
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
            # 파일 포인터를 시작점으로 리셋 시도
            try:
                await video_file.seek(0)
            except Exception:
                pass
                
            video_data = await video_file.read()
            
            # 데이터가 비어있는 경우 처리
            if not video_data:
                logger.warning(f"Video file {video_file.filename} is empty or already read")
                return {"error": "File is empty or already processed", "type": "video"}
            
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
            # 파일 포인터를 시작점으로 리셋 시도
            try:
                await audio_file.seek(0)
            except Exception:
                pass
                
            audio_data = await audio_file.read()
            
            # 데이터가 비어있는 경우 처리
            if not audio_data:
                logger.warning(f"Audio file {audio_file.filename} is empty or already read")
                return {"error": "File is empty or already processed", "type": "audio"}
            
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

    async def _process_text_file(self, text_file: UploadFile) -> Dict[str, Any]:
        """텍스트 파일을 처리하여 base64로 인코딩"""
        try:
            logger.info(f"_process_text_file 시작: {text_file.filename}, content_type: {text_file.content_type}")
            
            # 텍스트 파일 읽기
            text_data = await text_file.read()
            logger.info(f"텍스트 파일 읽기 완료: {len(text_data) if text_data else 0} bytes")
            
            # 데이터가 비어있는 경우 처리
            if not text_data:
                logger.warning(f"Text file {text_file.filename} is empty or already read")
                return {"error": "File is empty or already processed", "type": "text_file"}
            
            # 텍스트 파일을 base64로 인코딩  
            base64_text = base64.b64encode(text_data).decode('utf-8')
            
            # 텍스트 내용도 추출 (UTF-8로 디코딩 시도)
            try:
                text_content = text_data.decode('utf-8')
            except UnicodeDecodeError:
                # UTF-8 디코딩 실패시 다른 인코딩 시도
                try:
                    text_content = text_data.decode('latin-1')
                except:
                    text_content = "텍스트 디코딩 실패"
            
            result = {
                "filename": text_file.filename,
                "content_type": text_file.content_type or "text/plain",
                "size": len(text_data),
                "base64_data": base64_text,
                "text_content": text_content[:10000],  # 처음 10KB만 저장
                "type": "text_file"
            }
            
            logger.info(f"_process_text_file 완료: {text_file.filename} ({len(text_data)} bytes)")
            logger.info(f"반환할 result: {result.get('type', 'unknown')} type")
            return result
            
        except Exception as e:
            logger.error(f"Failed to process text file: {e}")
            return {"error": str(e), "type": "text_file"}

    def validate_inputs(
        self,
        text_query: Optional[str],
        image_file: Optional[UploadFile],
        video_file: Optional[UploadFile],
        audio_file: Optional[UploadFile],
        text_file: Optional[UploadFile] = None
    ) -> bool:
        """입력 검증 - 최소 하나의 입력이 있는지 확인"""
        return any([text_query, image_file, video_file, audio_file, text_file])

    def get_input_types(
        self,
        text_query: Optional[str],
        image_file: Optional[UploadFile],
        video_file: Optional[UploadFile],
        audio_file: Optional[UploadFile],
        text_file: Optional[UploadFile] = None
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
        if text_file:
            input_types.append("text_file")
        return input_types