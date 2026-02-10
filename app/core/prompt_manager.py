"""Langfuse 기반 프롬프트 매니저

이 모듈은 Langfuse에서 프롬프트를 가져오고, 실패 시 디폴트 프롬프트로 fallback하는
프롬프트 관리 시스템을 제공합니다.
"""

import asyncio
from typing import Dict, List, Any, Optional

from loguru import logger

from app.core.config import settings
from app.core.prompts import PromptIds, DefaultPrompts, PromptTemplates

try:
    from langfuse import Langfuse
except ImportError:
    logger.warning("Langfuse not installed. Using default prompts only.")
    Langfuse = None


class PromptManager:
    """Langfuse 프롬프트 매니저

    Langfuse에서 프롬프트를 가져오고, 실패 시 fallback으로 디폴트 프롬프트를 사용합니다.
    """

    def __init__(self):
        self._langfuse_client: Optional[Any] = None
        self._cache: Dict[str, Any] = {}  # 프롬프트 캐시
        self._cache_ttl: int = 300  # 5분 캐시
        self._last_cache_time: Dict[str, float] = {}

        # Langfuse 클라이언트 초기화
        self._initialize_langfuse()

    def _initialize_langfuse(self):
        """Langfuse 클라이언트 초기화"""
        if not settings.langfuse_enabled:
            logger.info("Langfuse disabled in settings. Using default prompts only.")
            return

        if not Langfuse:
            logger.warning("Langfuse package not available. Using default prompts only.")
            return

        if not settings.langfuse_public_key or not settings.langfuse_secret_key:
            logger.warning("Langfuse credentials not configured. Using default prompts only.")
            return

        try:
            self._langfuse_client = Langfuse(
                public_key=settings.langfuse_public_key,
                secret_key=settings.langfuse_secret_key,
                host=settings.langfuse_host
            )
            logger.info(f"Langfuse client initialized with host: {settings.langfuse_host}")
        except Exception as e:
            logger.error(f"Failed to initialize Langfuse client: {e}")
            self._langfuse_client = None

    def _is_cache_valid(self, prompt_id: str) -> bool:
        """캐시가 유효한지 확인"""
        import time
        if prompt_id not in self._cache:
            return False
        last_time = self._last_cache_time.get(prompt_id, 0)
        return (time.time() - last_time) < self._cache_ttl

    def _set_cache(self, prompt_id: str, prompt_data: Any):
        """캐시에 프롬프트 저장"""
        import time
        self._cache[prompt_id] = prompt_data
        self._last_cache_time[prompt_id] = time.time()

    async def _get_prompt_from_langfuse(self, prompt_id: str) -> Optional[str]:
        """Langfuse에서 프롬프트 가져오기 (비동기)"""
        if not self._langfuse_client:
            return None

        # 캐시 확인
        if self._is_cache_valid(prompt_id):
            logger.debug(f"Using cached prompt for {prompt_id}")
            return self._cache[prompt_id]

        try:
            # Langfuse는 동기 라이브러리이므로 executor에서 실행
            if self._langfuse_client is None:
                return None

            loop = asyncio.get_event_loop()
            prompt_data = await loop.run_in_executor(
                None,
                lambda: self._langfuse_client.get_prompt(prompt_id)  # type: ignore
            )

            if prompt_data and hasattr(prompt_data, 'prompt') and prompt_data is not None:
                prompt_text = prompt_data.prompt
                self._set_cache(prompt_id, prompt_text)
                logger.info(f"Successfully fetched prompt from Langfuse: {prompt_id}")
                return prompt_text
            else:
                logger.warning(f"Prompt data empty or invalid format from Langfuse: {prompt_id}")
                return None

        except Exception as e:
            logger.error(f"Failed to fetch prompt from Langfuse ({prompt_id}): {e}")
            return None

    async def get_query_intent_analysis_prompt(
            self,
            modality_context: str = "",
            element_list: str = ""
    ) -> str:
        """쿼리 의도 분석 프롬프트 가져오기"""
        langfuse_prompt = await self._get_prompt_from_langfuse(PromptIds.QUERY_INTENT_ANALYSIS)

        if langfuse_prompt:
            # Langfuse 프롬프트에서 변수 치환
            return langfuse_prompt.format(
                modality_context=modality_context,
                element_list=element_list
            )

        # Fallback to default
        logger.info("Using default query intent analysis prompt")
        return DefaultPrompts.get_query_intent_analysis_prompt(modality_context, element_list)

    async def get_query_expansion_prompt(self, context_info: str = "") -> str:
        """쿼리 확장 프롬프트 가져오기"""
        langfuse_prompt = await self._get_prompt_from_langfuse(PromptIds.QUERY_EXPANSION)

        if langfuse_prompt:
            return langfuse_prompt.format(context_info=context_info)

        # Fallback to default
        logger.info("Using default query expansion prompt")
        return DefaultPrompts.get_query_expansion_prompt(context_info)

    async def get_video_analysis_prompt(self) -> str:
        """비디오 분석 프롬프트 가져오기"""
        langfuse_prompt = await self._get_prompt_from_langfuse(PromptIds.VIDEO_ANALYSIS)

        if langfuse_prompt:
            return langfuse_prompt

        # Fallback to default
        logger.info("Using default video analysis prompt")
        return DefaultPrompts.get_video_analysis_prompt()

    async def get_audio_analysis_prompt(self) -> str:
        """오디오 분석 프롬프트 가져오기"""
        langfuse_prompt = await self._get_prompt_from_langfuse(PromptIds.AUDIO_ANALYSIS)

        if langfuse_prompt:
            return langfuse_prompt

        # Fallback to default
        logger.info("Using default audio analysis prompt")
        return DefaultPrompts.get_audio_analysis_prompt()

    async def get_answer_generation_prompt(
            self,
            has_attached_image: bool = False,
            previous_improvements: Optional[List[str]] = None
    ) -> str:
        """답변 생성 프롬프트 가져오기"""
        langfuse_prompt = await self._get_prompt_from_langfuse(PromptIds.ANSWER_GENERATION)

        if langfuse_prompt:
            # Langfuse 프롬프트 사용 시 동적 구성 처리
            image_guidance = await self.get_answer_image_guidance_prompt() if has_attached_image else ""
            improvement_section = ""
            if previous_improvements:
                improvement_text = "\n".join([f"- {suggestion}" for suggestion in previous_improvements])
                improvement_section = await self.get_answer_improvement_section_prompt(improvement_text)

            return langfuse_prompt.format(
                image_guidance=image_guidance,
                improvement_section=improvement_section
            )

        # Fallback to default - 기존 로직 사용
        logger.info("Using default answer generation prompt")
        base_prompt = DefaultPrompts.get_answer_generation_base_prompt()

        if has_attached_image:
            base_prompt += await self.get_answer_image_guidance_prompt()

        base_prompt += """
- 질문에 직접적으로 답변하는 내용으로 시작"""

        if has_attached_image:
            base_prompt += """
- 이미지 관련 질문이면 첨부 이미지 캡션 정보를 활용하여 구체적으로 설명"""

        base_prompt += """
- 필요시 배경 설명이나 맥락 정보 제공
- 구체적인 예시나 세부사항 포함
- 관련된 추가 정보나 주의사항 언급

검색 결과에 없는 정보에 대해서는 추측하지 말고, 검색 결과의 한계를 명시하세요."""

        if previous_improvements:
            improvement_text = "\n".join([f"- {suggestion}" for suggestion in previous_improvements])
            base_prompt += await self.get_answer_improvement_section_prompt(improvement_text)

        return base_prompt

    async def get_answer_reflection_prompt(self) -> str:
        """답변 품질 평가 프롬프트 가져오기"""
        langfuse_prompt = await self._get_prompt_from_langfuse(PromptIds.ANSWER_REFLECTION)

        if langfuse_prompt:
            return langfuse_prompt

        # Fallback to default
        logger.info("Using default answer reflection prompt")
        return DefaultPrompts.get_answer_reflection_prompt()

    async def get_answer_image_guidance_prompt(self) -> str:
        """이미지 가이드 프롬프트 가져오기 (Langfuse에서 가져오기 시도, 실패 시 기본값 사용)"""
        langfuse_prompt = await self._get_prompt_from_langfuse(PromptIds.ANSWER_IMAGE_GUIDANCE)

        if langfuse_prompt:
            return langfuse_prompt

        # Fallback to default
        logger.info("Using default answer image guidance prompt")
        return DefaultPrompts.get_answer_generation_image_guidance()

    async def get_answer_improvement_section_prompt(self, improvement_text: str) -> str:
        """개선 섹션 프롬프트 가져오기 (Langfuse에서 가져오기 시도, 실패 시 기본값 사용)"""
        langfuse_prompt = await self._get_prompt_from_langfuse(PromptIds.ANSWER_IMPROVEMENT_SECTION)

        if langfuse_prompt:
            # Langfuse 프롬프트에 improvement_text 변수 치환
            return langfuse_prompt.format(improvement_text=improvement_text)

        # Fallback to default
        logger.info("Using default answer improvement section prompt")
        return DefaultPrompts.get_answer_generation_improvement_section(improvement_text)

    def create_messages(self, system_prompt: str, user_prompt: str) -> List[Dict[str, Any]]:
        """메시지 리스트 생성"""
        return PromptTemplates.create_messages(system_prompt, user_prompt)

    def create_multimodal_messages(
            self,
            prompt_text: str,
            content_list: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """멀티모달 메시지 생성 (비디오/오디오 분석용)"""
        return PromptTemplates.create_multimodal_messages(prompt_text, content_list)

    async def health_check(self) -> Dict[str, Any]:
        """프롬프트 매니저 상태 확인"""
        status = {
            "langfuse_enabled": settings.langfuse_enabled,
            "langfuse_client_initialized": self._langfuse_client is not None,
            "langfuse_host": settings.langfuse_host,
            "cache_size": len(self._cache),
            "fallback_available": True  # 항상 디폴트 프롬프트 사용 가능
        }

        # Langfuse 연결 테스트
        if self._langfuse_client:
            try:
                # 간단한 프롬프트 요청으로 연결 테스트
                test_prompt = await self._get_prompt_from_langfuse("test-connection")
                status["langfuse_connection_test"] = "success"
            except Exception as e:
                status["langfuse_connection_test"] = f"failed: {str(e)}"
        else:
            status["langfuse_connection_test"] = "client not initialized"

        return status

    def clear_cache(self):
        """프롬프트 캐시 클리어"""
        self._cache.clear()
        self._last_cache_time.clear()
        logger.info("Prompt cache cleared")


# 싱글톤 인스턴스
prompt_manager = PromptManager()
