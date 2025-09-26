from typing import List, Optional, Dict, Any
import httpx
from loguru import logger

from app.core.config import settings


class EmbeddingClient:
    def __init__(self):
        self.base_url = settings.embedding_api_url
        self.timeout = 30.0
        self.headers = {
            "x-token": settings.multimodal_api_key,
            "Content-Type": "application/json"
        }
        self.file_headers = {
            "x-token": settings.multimodal_api_key
        }

    async def get_text_embedding(self, text: str) -> Optional[List[float]]:
        """Get text embedding"""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(
                    f"{self.base_url}/embedding/text",
                    json={"text": text},
                    headers=self.headers
                )
                response.raise_for_status()
                
                result = response.json()
                # 임베딩 벡터는 길어서 처음 5개 값만 로그에 표시
                if result.get("status") == "success" and "data" in result and "embedding" in result["data"]:
                    embedding = result["data"]["embedding"]
                    logger.debug(f"Text embedding API response: status={result.get('status')}, embedding_dim={len(embedding)}, first_5_values={embedding[:5]}")
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
                response = await client.post(
                    f"{self.base_url}/embedding/image",
                    files=files,
                    headers=self.file_headers
                )
                response.raise_for_status()
                
                result = response.json()
                # 임베딩 벡터는 길어서 처음 5개 값만 로그에 표시
                if result.get("status") == "success" and "data" in result and "embedding" in result["data"]:
                    embedding = result["data"]["embedding"]
                    logger.debug(f"Image embedding API response: status={result.get('status')}, embedding_dim={len(embedding)}, first_5_values={embedding[:5]}")
                    return embedding
                else:
                    logger.debug(f"Image embedding API response: {result}")
                    logger.error(f"Image embedding failed: {result}")
                    return None
                    
            except Exception as e:
                logger.error(f"Image embedding request failed: {e}")
                return None

    async def get_image_embedding_from_storage(self, storage_path: str) -> Optional[List[float]]:
        """Get image embedding from storage path"""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(
                    f"{self.base_url}/embedding/image/storage",
                    json={"storage_path": storage_path},
                    headers=self.headers
                )
                response.raise_for_status()
                
                result = response.json()
                # 임베딩 벡터는 길어서 처음 5개 값만 로그에 표시
                if result.get("status") == "success" and "data" in result and "embedding" in result["data"]:
                    embedding = result["data"]["embedding"]
                    logger.debug(f"Image storage embedding API response: status={result.get('status')}, embedding_dim={len(embedding)}, first_5_values={embedding[:5]}")
                    return embedding
                else:
                    logger.debug(f"Image storage embedding API response: {result}")
                    logger.error(f"Image embedding from storage failed: {result}")
                    return None
                    
            except Exception as e:
                logger.error(f"Image embedding from storage request failed: {e}")
                return None


