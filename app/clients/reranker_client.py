"""
Qwen3-Reranker HTTP 클라이언트 (vLLM 직접 호출)

vLLM 서버의 /classify 엔드포인트를 직접 호출합니다.
Qwen3-VL-Reranker-2B 모델의 프롬프트 형식에 맞춰 query-document 쌍을 구성합니다.
실패 시 None을 반환하여 graceful degradation을 지원합니다.

환경변수:
  RERANKER_API_URL: vLLM reranker 서버 URL (비어있으면 reranker 비활성)
"""

from typing import Any, Dict, List, Optional

import httpx
from loguru import logger

from app.config.config import settings

# Qwen3-Reranker 프롬프트 템플릿
_SYSTEM_PROMPT = (
    "Judge whether the Document meets the requirements based on the Query "
    "and the Instruct provided. Note that the answer can only be \"yes\" or \"no\"."
)
_DEFAULT_INSTRUCT = "Given a web search query, retrieve relevant passages that answer the query."


class RerankerClient:
    """Qwen3-Reranker를 vLLM /classify로 직접 호출하는 HTTP 클라이언트"""

    def __init__(self):
        self.base_url = settings.reranker_api_url.rstrip("/") if settings.reranker_api_url else ""
        self.timeout = settings.reranker_timeout
        self.headers = {"Content-Type": "application/json"}
        self._available = bool(self.base_url)

        if not self._available:
            logger.info("RerankerClient: RERANKER_API_URL not configured, reranker disabled")

    @property
    def available(self) -> bool:
        """Reranker 사용 가능 여부"""
        return self._available and settings.reranker_enabled

    async def rerank(
        self,
        query: str,
        documents: List[Dict[str, str]],
        top_k: Optional[int] = None,
        instruct: Optional[str] = None,
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Reranker API를 호출하여 문서를 재정렬합니다.

        Args:
            query: 검색 쿼리
            documents: 재정렬할 문서 목록 [{"id": str, "content": str}, ...]
            top_k: 반환할 상위 문서 수 (None이면 settings 값 사용)
            instruct: 커스텀 instruct (None이면 기본값 사용)

        Returns:
            재정렬된 결과 리스트 [{"index": int, "score": float}, ...]
            실패 시 None (graceful degradation)
        """
        if not self.available:
            return None

        if not documents:
            return []

        if top_k is None:
            top_k = settings.reranker_top_k

        if instruct is None:
            instruct = _DEFAULT_INSTRUCT

        # vLLM /classify 페이로드 구성
        inputs = self._build_inputs(query, documents, instruct)

        payload = {
            "model": "qwen3-vl-reranker-2b",
            "input": inputs,
            "use_activation": True,
            "add_special_tokens": False,
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/classify",
                    json=payload,
                    headers=self.headers,
                )
                response.raise_for_status()

                result = response.json()
                return self._parse_vllm_response(result, top_k)

        except httpx.TimeoutException:
            logger.warning(
                f"Reranker timeout ({self.timeout}s) for query: '{query[:50]}...' "
                f"with {len(documents)} documents"
            )
            return None
        except httpx.HTTPStatusError as e:
            logger.warning(
                f"Reranker HTTP error {e.response.status_code}: "
                f"{e.response.text[:200]}"
            )
            return None
        except httpx.RequestError as e:
            logger.warning(f"Reranker request failed: {e}")
            return None
        except Exception as e:
            logger.warning(f"Reranker unexpected error: {e}")
            return None

    def _build_inputs(
        self,
        query: str,
        documents: List[Dict[str, str]],
        instruct: str,
    ) -> List[str]:
        """Qwen3-Reranker 형식의 input 문자열 리스트를 구성합니다.

        형식:
        <|im_start|>system
        {system_prompt}<|im_end|>
        <|im_start|>user
        <instruct>{instruct}
        <query>{query}
        <document>{document}<|im_end|>
        <|im_start|>assistant
        """
        inputs = []
        for doc in documents:
            content = doc.get("content", "")[:2000]  # 문서 길이 제한
            prompt = (
                f"<|im_start|>system\n{_SYSTEM_PROMPT}<|im_end|>\n"
                f"<|im_start|>user\n"
                f"<instruct>{instruct}\n"
                f"<query>{query}\n"
                f"<document>{content}<|im_end|>\n"
                f"<|im_start|>assistant\n"
            )
            inputs.append(prompt)
        return inputs

    def _parse_vllm_response(
        self,
        result: Dict[str, Any],
        top_k: int,
    ) -> Optional[List[Dict[str, Any]]]:
        """
        vLLM /classify 응답을 파싱합니다.

        vLLM 응답 형식 (num_classes=1, sigmoid score):
        {
            "id": "classify-...",
            "object": "list",
            "data": [
                {"index": 0, "label": "LABEL_0", "probs": [0.7311], "num_classes": 1},
                {"index": 1, "label": "LABEL_0", "probs": [0.1529], "num_classes": 1},
            ]
        }

        probs[0] = relevance score (sigmoid 적용된 값, 0~1 범위)
        num_classes=1인 경우 probs[0]이 직접 relevance score입니다.
        num_classes=2인 경우 probs[1]이 "yes" (relevant) 확률입니다.
        """
        data = result.get("data", [])
        if not data:
            logger.warning("Reranker returned empty data")
            return None

        # 각 문서의 relevance score 추출
        scored = []
        for item in data:
            index = item.get("index", 0)
            probs = item.get("probs", [])
            num_classes = item.get("num_classes", 1)

            if not probs:
                score = 0.0
            elif num_classes == 1:
                # sigmoid score — probs[0]이 직접 relevance score
                score = probs[0]
            elif len(probs) >= 2:
                # 2-class — probs[1]이 "yes" (relevant) 확률
                score = probs[1]
            else:
                score = probs[0]

            scored.append({"index": index, "score": score})

        # score 순으로 정렬하여 top_k 반환
        scored.sort(key=lambda x: x["score"], reverse=True)
        top_results = scored[:top_k]

        # 모든 점수가 동일한지 체크 (이슈 감지)
        unique_scores = set(round(item["score"], 6) for item in scored)
        if len(unique_scores) <= 1 and len(scored) > 1:
            logger.warning(
                f"Reranker returned identical scores ({unique_scores}), "
                f"model may not be scoring correctly"
            )
            return None  # 의미 없는 결과이므로 None 반환 → graceful degradation

        if top_results:
            logger.info(
                f"Reranker returned {len(top_results)} results "
                f"(top_score={top_results[0]['score']:.4f}, "
                f"bottom_score={top_results[-1]['score']:.4f})"
            )

        return top_results if top_results else None

    async def health_check(self) -> bool:
        """Reranker 서버 상태 확인"""
        if not self.base_url:
            return False

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(
                    f"{self.base_url}/health",
                    headers=self.headers,
                )
                return response.status_code == 200
        except Exception:
            return False
