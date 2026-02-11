from typing import Any, Dict, List, Optional

import httpx
from loguru import logger

from app.config.config import settings
from app.utils.authentication import security_manager


class EmbeddingClient:
    def __init__(self):
        self.base_url = settings.embedding_api_url
        self.timeout = 30.0
        api_key = security_manager.get_api_key("MULTIMODAL_API_KEY") or settings.multimodal_api_key
        self.headers = {"x-token": api_key, "Content-Type": "application/json"}
        self.file_headers = {"x-token": api_key}

    async def get_text_embedding(self, text: str) -> Optional[List[float]]:
        """Get text embedding"""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(f"{self.base_url}/embedding/text", json={"text": text}, headers=self.headers)
                response.raise_for_status()

                result = response.json()
                # 임베딩 벡터는 길어서 처음 5개 값만 로그에 표시
                if result.get("status") == "success" and "data" in result and "embedding" in result["data"]:
                    embedding = result["data"]["embedding"]
                    logger.info(
                        f"Text embedding API response: status={result.get('status')}, embedding_dim={len(embedding)}"
                    )
                    return embedding
                else:
                    logger.debug(f"Text embedding API response: {result}")
                    logger.error(f"Text embedding failed: {result}")
                    return None

            except Exception as e:
                logger.error(f"Text embedding request failed: {e}")
                return None

    async def get_image_embedding(self, image_data: bytes) -> Optional[List[float]]:
        """Get image embedding from binary data"""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                files = {"image": ("image.jpg", image_data, "image/jpeg")}
                response = await client.post(f"{self.base_url}/embedding/image", files=files, headers=self.file_headers)
                response.raise_for_status()

                result = response.json()
                # 임베딩 벡터는 길어서 처음 5개 값만 로그에 표시
                if result.get("status") == "success" and "data" in result and "embedding" in result["data"]:
                    embedding = result["data"]["embedding"]
                    logger.info(
                        f"Image embedding API response: status={result.get('status')}, embedding_dim={len(embedding)}"
                    )
                    return embedding
                else:
                    logger.debug(f"Image embedding API response: {result}")
                    logger.error(f"Image embedding failed: {result}")
                    return None

            except Exception as e:
                logger.error(f"Image embedding request failed: {e}")
                return None

    async def get_video_embedding(self, video_data: bytes) -> Optional[List[float]]:
        """Get video embedding from binary data"""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                files = {"video": ("video.mp4", video_data, "video/mp4")}
                response = await client.post(f"{self.base_url}/embedding/video", files=files, headers=self.file_headers)
                response.raise_for_status()

                result = response.json()
                if result.get("status") == "success" and "data" in result and "embedding" in result["data"]:
                    embedding = result["data"]["embedding"]
                    logger.debug(
                        f"Video embedding API response: status={result.get('status')}, embedding_dim={len(embedding)}, first_5_values={embedding[:5]}"
                    )
                    return embedding
                else:
                    logger.debug(f"Video embedding API response: {result}")
                    logger.error(f"Video embedding failed: {result}")
                    return None

            except Exception as e:
                logger.error(f"Video embedding request failed: {e}")
                return None

    async def get_audio_embedding(self, audio_data: bytes) -> Optional[List[float]]:
        """Get audio embedding from binary data"""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                files = {"audio": ("audio.wav", audio_data, "audio/wav")}
                response = await client.post(f"{self.base_url}/embedding/audio", files=files, headers=self.file_headers)
                response.raise_for_status()

                result = response.json()
                if result.get("status") == "success" and "data" in result and "embedding" in result["data"]:
                    embedding = result["data"]["embedding"]
                    logger.debug(
                        f"Audio embedding API response: status={result.get('status')}, embedding_dim={len(embedding)}, first_5_values={embedding[:5]}"
                    )
                    return embedding
                else:
                    logger.debug(f"Audio embedding API response: {result}")
                    logger.error(f"Audio embedding failed: {result}")
                    return None

            except Exception as e:
                logger.error(f"Audio embedding request failed: {e}")
                return None

    async def detect_objects(self, image_data: bytes) -> Optional[Dict[str, Any]]:
        """Detect objects in image using YOLO11"""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                files = {"image": ("image.jpg", image_data, "image/jpeg")}
                response = await client.post(
                    f"{self.base_url}/analysis/image/detection", files=files, headers=self.file_headers
                )
                response.raise_for_status()

                result = response.json()
                logger.debug(f"Object detection API response: {result}")
                if result.get("status") == "success":
                    return result["data"]
                else:
                    logger.error(f"Object detection failed: {result}")
                    return None

            except Exception as e:
                logger.error(f"Object detection request failed: {e}")
                return None

    async def generate_image_caption(self, image_data: bytes) -> Optional[Dict[str, Any]]:
        """Generate image caption"""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                files = {"image_file": ("image.jpg", image_data, "image/jpeg")}
                response = await client.post(
                    f"{self.base_url}/analysis/image/captioning", files=files, headers=self.file_headers
                )
                response.raise_for_status()

                result = response.json()
                logger.debug(f"Image caption API response: {result}")
                if result.get("status") == "success":
                    return result["data"]
                else:
                    logger.error(f"Image caption generation failed: {result}")
                    return None

            except Exception as e:
                logger.error(f"Image caption request failed: {e}")
                return None
