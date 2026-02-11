from typing import Dict

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.config.config import ENV_FILE_PATH


class WeightingConfig(BaseSettings):
    """검색 가중치 설정을 중앙화하는 설정 클래스

    멀티모달 검색 시스템의 모든 가중치 설정을 관리합니다.
    가중치는 검색 결과의 관련성과 우선순위를 결정하는 핵심 요소입니다.

    모든 가중치는 환경변수로 설정 가능하며, 기본값이 제공됩니다.
    자세한 설명과 예시는 README.md의 '가중치 시스템' 섹션을 참조하세요.

    주요 개념:
    - 쿼리별 가중치: 확장된 쿼리들의 중요도 조절 (1.0 → 0.9 → 0.8...)
    - Element Type 가중치: 콘텐츠 타입별 중요도 (origin=1.0, paragraph=0.8...)
    - 동적 계산: 쿼리 내용에 따라 가중치 자동 조정
    """
    model_config = SettingsConfigDict(env_file=str(ENV_FILE_PATH), env_file_encoding="utf-8", env_prefix="WEIGHT_",
                                      extra="ignore")

    # === 쿼리별 가중치 설정 ===
    query_weight_decay: float = Field(default=0.1, alias="WEIGHT_QUERY_DECAY")  # 각 쿼리마다 감소할 가중치 (1.0 → 0.9 → 0.8...)

    # === Element Type별 기본 가중치 ===
    paragraph_default: float = Field(default=0.8, alias="WEIGHT_PARAGRAPH_DEFAULT")  # 일반 문단 기본 가중치
    summary_default: float = Field(default=0.6, alias="WEIGHT_SUMMARY_DEFAULT")  # AI 요약문 기본 가중치
    caption_default: float = Field(default=0.3, alias="WEIGHT_CAPTION_DEFAULT")  # 이미지 캡션 기본 가중치
    origin_default: float = Field(default=1.0, alias="WEIGHT_ORIGIN_DEFAULT")  # 원본 이미지 기본 가중치

    @property
    def QUERY_WEIGHT_DECAY(self) -> float:
        return self.query_weight_decay

    # === 핵심 가중치 설정 (사용자 설정 가능) ===
    # 텍스트 검색 강도 (0.0~1.0): 높을수록 텍스트 기반 검색 우선
    text_search_strength: float = Field(default=0.7, alias="WEIGHT_TEXT_STRENGTH")

    # 이미지 검색 강도 (0.0~1.0): 높을수록 이미지 기반 검색 우선
    image_search_strength: float = Field(default=0.8, alias="WEIGHT_IMAGE_STRENGTH")

    # 벡터 검색 boost 강도 (0.5~3.0): 벡터 검색의 전반적인 가중치
    vector_boost_strength: float = Field(default=1.5, alias="WEIGHT_VECTOR_BOOST_STRENGTH")

    # === 계산된 가중치들 (핵심 설정을 기반으로 자동 계산) ===
    @property
    def TEXT_SUMMARY_BASE_WEIGHT(self) -> float:
        # 텍스트 강도 기반으로 계산 (0.5~0.9 범위)
        return 0.5 + (self.text_search_strength * 0.4)

    @property
    def TEXT_SUMMARY_BOOST(self) -> float:
        # 텍스트 강도 기반으로 boost 계산
        return self.text_search_strength * 0.15

    @property
    def TEXT_PARAGRAPH_BASE_WEIGHT(self) -> float:
        # summary보다 약간 낮게
        return self.TEXT_SUMMARY_BASE_WEIGHT - 0.1

    @property
    def TEXT_PARAGRAPH_PENALTY(self) -> float:
        return 0.1  # 고정값

    @property
    def TEXT_MIN_WEIGHT(self) -> float:
        return 0.3 + (self.text_search_strength * 0.2)  # 0.3~0.5 범위

    @property
    def TEXT_PARAGRAPH_DEFAULT(self) -> float:
        return self.text_search_strength * 0.8  # 텍스트 강도에 비례

    @property
    def TEXT_SUMMARY_DEFAULT(self) -> float:
        return self.text_search_strength * 0.6  # paragraph보다 낮게

    @property
    def IMAGE_ORIGIN_WEIGHT(self) -> float:
        return self.image_search_strength  # 이미지 강도와 동일

    @property
    def IMAGE_CAPTION_BASE_WEIGHT(self) -> float:
        # 이미지 강도 기반으로 caption 가중치 계산 (0.2~0.5 범위)
        return 0.2 + (self.image_search_strength * 0.3)

    @property
    def IMAGE_CAPTION_BOOST(self) -> float:
        return self.image_search_strength * 0.06

    @property
    def IMAGE_CAPTION_MAX_WEIGHT(self) -> float:
        return self.IMAGE_CAPTION_BASE_WEIGHT + 0.2

    @property
    def IMAGE_CAPTION_MIN_WEIGHT(self) -> float:
        return self.IMAGE_CAPTION_BASE_WEIGHT - 0.1

    @property
    def UNIVERSAL_DEFAULT_WEIGHT(self) -> float:
        # 텍스트와 이미지 강도의 평균
        return (self.text_search_strength + self.image_search_strength) / 2

    @property
    def OPENSEARCH_DEFAULT_WEIGHT(self) -> float:
        return 1.0  # 고정값

    @property
    def HIGH_PRIORITY_THRESHOLD(self) -> float:
        return 0.8  # 고정값

    @property
    def MEDIUM_PRIORITY_THRESHOLD(self) -> float:
        return 0.5  # 고정값

    @property
    def LOW_PRIORITY_THRESHOLD(self) -> float:
        return 0.0  # 고정값

    @property
    def MODALITY_BOOST_MIN_MULTIPLIER(self) -> float:
        # vector_boost_strength 기반으로 계산 (0.3~0.7 범위)
        return 0.3 + (self.vector_boost_strength / 3.0 * 0.4)

    @property
    def MODALITY_BOOST_MAX_MULTIPLIER(self) -> float:
        # vector_boost_strength와 비례 (1.0~3.0 범위)
        return self.vector_boost_strength * 2.0

    @property
    def MODALITY_BOOST_RANGE(self) -> float:
        # max - min
        return self.MODALITY_BOOST_MAX_MULTIPLIER - self.MODALITY_BOOST_MIN_MULTIPLIER

    @property
    def MODALITY_FALLBACK_WEIGHTS(self) -> Dict[str, Dict[str, float]]:
        return {
            "text": {
                "paragraph": self.TEXT_PARAGRAPH_DEFAULT,
                "summary": 0.5,  # 기본값 사용
            },
            "image": {
                "origin": self.IMAGE_ORIGIN_WEIGHT,
                "caption": self.IMAGE_CAPTION_BASE_WEIGHT,
            }
        }


weighting_config = WeightingConfig()
