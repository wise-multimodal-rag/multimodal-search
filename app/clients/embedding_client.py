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
        """Get text embedding via /embedding/multimodal endpoint"""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                payload = {"modality": "text", "data": text}
                response = await client.post(
                    f"{self.base_url}/embedding/multimodal",
                    json=payload,
                    headers=self.headers,
                )
                response.raise_for_status()

                result = response.json()
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

    async def get_image_embedding(self, image_base64: str) -> Optional[List[float]]:
        """Get image embedding from base64 string via /embedding/multimodal endpoint"""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                payload = {"modality": "image", "data": image_base64}
                response = await client.post(
                    f"{self.base_url}/embedding/multimodal",
                    json=payload,
                    headers=self.headers,
                )
                response.raise_for_status()

                result = response.json()
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
        """Get video embedding - currently not supported, returns None"""
        logger.warning("Video embedding is not supported by current embedding service")
        return None

    async def get_audio_embedding(self, audio_data: bytes) -> Optional[List[float]]:
        """Get audio embedding - currently not supported, returns None"""
        logger.warning("Audio embedding is not supported by current embedding service")
        return None

    async def generate_image_caption(self, image_data: bytes) -> Optional[Dict[str, Any]]:
        """Generate image caption via /analysis/data2text endpoint"""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                files = {"image_file": ("image.jpg", image_data, "image/jpeg")}
                data = {"provider": "vlm"}
                response = await client.post(
                    f"{self.base_url}/analysis/data2text",
                    files=files,
                    data=data,
                    headers=self.file_headers,
                )
                response.raise_for_status()

                result = response.json()
                logger.debug(f"Image caption API response: {result}")

                if result.get("status") == "success" and "data" in result:
                    caption_data = result["data"]
                    return {
                        "caption": caption_data.get("content", ""),
                        "tags": caption_data.get("keywords", []),
                    }
                else:
                    logger.error(f"Image caption generation failed: {result}")
                    return None

            except Exception as e:
                logger.error(f"Image caption request failed: {e}")
                return None
