"""디폴트 프롬프트 상수 파일

이 파일은 Langfuse에서 프롬프트를 가져오지 못할 때 사용되는 fallback 프롬프트들을 관리합니다.
모든 프롬프트는 한국어로 작성되며, JSON 출력 형식을 강조합니다.
"""

from typing import Dict, Any


# 프롬프트 ID 상수
class PromptIds:
    """Langfuse에서 사용할 프롬프트 ID들"""
    QUERY_INTENT_ANALYSIS = "query-intent-analysis"
    QUERY_EXPANSION = "query-expansion"
    VIDEO_ANALYSIS = "video-analysis"
    AUDIO_ANALYSIS = "audio-analysis"
    ANSWER_GENERATION = "answer-generation"
    ANSWER_REFLECTION = "answer-reflection"
    ANSWER_IMAGE_GUIDANCE = "answer-image-guidance"
    ANSWER_IMPROVEMENT_SECTION = "answer-improvement-section"


class DefaultPrompts:
    """디폴트 프롬프트 템플릿 모음"""

    @staticmethod
    def get_query_intent_analysis_prompt(modality_context: str = "", element_list: str = "") -> str:
        """쿼리 의도 분석 프롬프트"""
        return f"""쿼리 내용을 분석하여 검색에 적합한 element_type별 가중치를 계산하세요.
{modality_context}
사용 가능한 타입:
{element_list}

**중요한 우선순위 규칙**:
- 이미지 관련 쿼리 ("이미지", "사진", "그림" 등):
  → origin (원본 이미지): 1.0 (최고 우선순위)
  → caption (이미지 설명): 0.2-0.3 (매우 낮은 우선순위)
- 요약 관련 쿼리 ("요약", "정리" 등):
  → summary: 1.0, paragraph: 0.5-0.7
- 일반 텍스트 쿼리 ("내용", "문서", "텍스트" 등):
  → paragraph: 1.0, summary: 0.5-0.7

가중치 (0.0~1.0):
- 1.0: 핵심 요구사항 (최고 우선순위)
- 0.7: 관련 높음
- 0.5: 보통 관련
- 0.3: 약간 관련
- 0.2: 매우 낮은 관련성
- 0.0: 관련 없음

JSON만 출력:
{{
    "element_type_weights": {{
        "paragraph": 0.3,
        "summary": 0.5,
        "caption": 0.2,
        "origin": 1.0
    }},
    "reasoning": "이미지 검색이므로 origin을 최우선으로, caption은 매우 낮게 설정",
    "confidence": 0.9
}}"""

    @staticmethod
    def get_query_expansion_prompt(context_info: str = "") -> str:
        """쿼리 확장 프롬프트"""
        return f"""검색 쿼리를 분석하여 필요한 경우에만 확장하세요. 원본 쿼리의 의도를 최대한 보존하면서 검색 성능을 개선하는 것이 목표입니다.

{context_info}

적용 가능한 기법:

1. **Query Rewriting (쿼리 재작성)** - 기본적으로 적용:
   - 동의어, 유의어로 재작성
   - 예시: "AI" → "인공지능", "방법" → "how to"

2. **Query Decomposition (쿼리 분해)** - 복합 쿼리일 때만:
   - 2개 이상의 독립적 개념이 명확히 구분되는 경우에만 적용
   - 예시: "파이썬과 자바스크립트 차이점" → "파이썬" + "자바스크립트"

3. **Semantic Expansion (의미적 확장)** - 매우 제한적으로 적용:
   **다음 경우에만 적용**:
   - 쿼리가 너무 추상적이어서 구체적인 검색이 어려운 경우
   - 사용자가 명시적으로 "관련된", "비슷한", "유사한" 등의 확장을 요청한 경우
   - 도메인 전문 용어가 필요한 매우 기술적인 쿼리인 경우

   **적용하지 말아야 할 경우**:
   - 구체적인 제품명, 브랜드명, 고유명사가 포함된 쿼리
   - 이미 충분히 구체적인 쿼리
   - 정확한 매칭이 중요한 쿼리

**원칙**: 의심스러우면 Semantic Expansion을 사용하지 마세요. Query Rewriting만으로도 충분한 경우가 대부분입니다.

간소화된 JSON 형식으로만 응답하세요:
{{
    "original_query": "원본 쿼리",
    "final_queries": [
        {{
            "query": "확장된 쿼리1",
            "priority": 1
        }},
        {{
            "query": "확장된 쿼리2",
            "priority": 2
        }}
    ],
    "has_dependency": false,
    "dependency_reason": "분해된 쿼리들이 독립적으로 실행 가능",
    "applied_techniques": ["rewriting", "decomposition"],
    "expansion_summary": "Query rewriting and decomposition applied (2 variants generated)"
}}

참고:
- 원본 쿼리는 항상 priority 1로 final_queries에 포함
- 확장 쿼리는 최대 2-3개까지만 생성
- priority가 낮을수록 우선순위가 높음
- applied_techniques: ["rewriting", "decomposition", "semantic_expansion"] 중 사용된 것만
- has_dependency가 true면 순차 검색, false면 병렬 검색"""

    @staticmethod
    def get_video_analysis_prompt() -> str:
        """비디오 분석 프롬프트"""
        return """이 비디오를 분석하여 다음 정보를 JSON 형식으로 제공하세요:
{
    "description": "비디오 전체 설명",
    "scenes": [
        {
            "timestamp": "0:00-0:30",
            "description": "장면 설명"
        }
    ],
    "activities": ["활동1", "활동2"],
    "objects": ["객체1", "객체2"],
    "setting": "장소/환경",
    "duration_estimate": "추정 길이(초)"
}"""

    @staticmethod
    def get_audio_analysis_prompt() -> str:
        """오디오 분석 프롬프트"""
        return """이 오디오를 분석하여 다음 정보를 JSON 형식으로 제공하세요:
{
    "transcription": "음성 내용 (있다면)",
    "type": "speech|music|sound_effect|ambient|mixed",
    "detected_sounds": ["소리1", "소리2"],
    "language": "언어 (있다면)",
    "quality": "음질 평가",
    "duration_estimate": "추정 길이(초)"
}"""

    @staticmethod
    def get_answer_generation_base_prompt() -> str:
        """답변 생성 기본 프롬프트"""
        return """당신은 멀티모달 검색 결과를 바탕으로 정확하고 유용한 답변을 생성하는 AI 어시스턴트입니다.

다음 원칙을 따라 답변을 생성하세요:

1. **정확성**: 제공된 검색 결과에 기반하여 정확한 정보만 제공
2. **완성도**: 질문에 대해 포괄적이고 완전한 답변 제공
3. **명확성**: 이해하기 쉽고 구체적인 설명
4. **구조화**: 논리적 순서와 명확한 구조로 답변 구성
5. **출처 표시**: 검색 결과의 어떤 부분을 참고했는지 명시

답변 형식:
- 질문에 직접적으로 답변하는 내용으로 시작
- 필요시 배경 설명이나 맥락 정보 제공
- 구체적인 예시나 세부사항 포함
- 관련된 추가 정보나 주의사항 언급

검색 결과에 없는 정보에 대해서는 추측하지 말고, 검색 결과의 한계를 명시하세요."""

    @staticmethod
    def get_answer_generation_image_guidance() -> str:
        """답변 생성 이미지 가이드"""
        return """

**중요**: 검색 결과에 "=== 첨부 이미지 정보 ===" 섹션이 있다면, 이는 사용자가 첨부한 이미지에 대한 AI 생성 캡션입니다.
사용자가 "이 이미지", "사진", "그림" 등을 언급할 때는 이 캡션을 참고하여 구체적인 이미지 내용을 설명할 수 있습니다."""

    @staticmethod
    def get_answer_generation_improvement_section(improvement_text: str) -> str:
        """답변 생성 개선 섹션"""
        return f"""

**이전 답변에서 개선이 필요했던 부분들:**
{improvement_text}

위 개선사항들을 반드시 고려하여 더 나은 답변을 생성해주세요."""

    @staticmethod
    def get_answer_reflection_prompt() -> str:
        """답변 품질 평가 프롬프트"""
        return """당신은 생성된 답변의 품질을 평가하고 개선점을 제안하는 전문가입니다.

다음 기준으로 답변을 평가하세요:

1. **정확성** (0-10): 검색 결과와 일치하는 정보 제공 여부
2. **완성도** (0-10): 질문에 대한 포괄적인 답변 제공 여부
3. **명확성** (0-10): 이해하기 쉽고 구체적인 설명 여부
4. **구조** (0-10): 논리적 구성과 읽기 쉬운 형태 여부
5. **관련성** (0-10): 질문과의 직접적인 연관성

전체 점수가 35점 이상(평균 7점)이면 is_acceptable: true로 설정하세요.

JSON 형식으로만 응답하세요:
{
    "scores": {
        "accuracy": 8,
        "completeness": 7,
        "clarity": 9,
        "structure": 8,
        "relevance": 9
    },
    "total_score": 41,
    "is_acceptable": true,
    "strengths": ["명확한 설명", "좋은 구조"],
    "improvement_suggestions": ["더 구체적인 예시 필요"],
    "overall_assessment": "전반적으로 우수한 답변이나 예시가 더 필요함"
}"""


class PromptTemplates:
    """프롬프트 템플릿 유틸리티"""

    @staticmethod
    def format_user_prompt(template: str, **kwargs) -> str:
        """사용자 프롬프트 포맷팅"""
        return template.format(**kwargs)

    @staticmethod
    def create_messages(system_prompt: str, user_prompt: str) -> list[Dict[str, Any]]:
        """메시지 리스트 생성"""
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

    @staticmethod
    def create_multimodal_messages(system_prompt: str, content_list: list[Dict[str, Any]]) -> list[Dict[str, Any]]:
        """멀티모달 메시지 생성 (비디오/오디오 분석용)"""
        return [
            {
                "role": "user",
                "content": [{"type": "text", "text": system_prompt}] + content_list
            }
        ]


# 상수 인스턴스
prompt_ids = PromptIds()
default_prompts = DefaultPrompts()
prompt_templates = PromptTemplates()
