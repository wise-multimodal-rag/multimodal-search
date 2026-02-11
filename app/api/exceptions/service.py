"""Service-specific exceptions for multimodal search domains."""

from typing import Any, Dict, Optional

from .base import BaseAppException, BusinessLogicException, ErrorCategory, ErrorCode


# =============================================================================
# Search Domain Exceptions
# =============================================================================

class SearchException(BusinessLogicException):
    """검색 관련 예외"""

    def __init__(self, message: str, search_type: Optional[str] = None, **kwargs):
        details = kwargs.pop("details", {})
        if search_type:
            details["search_type"] = search_type

        super().__init__(
            message=message,
            operation="search",
            error_code=ErrorCode.SEARCH_FAILED,
            details=details,
            **kwargs
        )


class QueryAnalysisException(SearchException):
    """쿼리 분석 실패 예외"""

    def __init__(self, query: str, reason: str, **kwargs):
        super().__init__(
            message=f"Query analysis failed: {reason}",
            search_type="analysis",
            details={"query": query, "reason": reason},
            **kwargs
        )


class OpenSearchException(SearchException):
    """OpenSearch 관련 예외"""

    def __init__(self, message: str, index: Optional[str] = None, **kwargs):
        details = kwargs.pop("details", {})
        if index:
            details["index"] = index

        super().__init__(
            message=f"OpenSearch error: {message}",
            search_type="opensearch",
            details=details,
            **kwargs
        )


# =============================================================================
# Generation Domain Exceptions
# =============================================================================

class GenerationException(BusinessLogicException):
    """답변 생성 관련 예외"""

    def __init__(self, message: str, generation_type: Optional[str] = None, **kwargs):
        details = kwargs.pop("details", {})
        if generation_type:
            details["generation_type"] = generation_type

        super().__init__(
            message=message,
            operation="generation",
            error_code=ErrorCode.GENERATION_FAILED,
            details=details,
            **kwargs
        )


class LLMGenerationException(GenerationException):
    """LLM 답변 생성 실패 예외"""

    def __init__(self, model: str, reason: str, **kwargs):
        super().__init__(
            message=f"LLM generation failed with {model}: {reason}",
            generation_type="llm",
            details={"model": model, "reason": reason},
            **kwargs
        )


class StreamingException(GenerationException):
    """스트리밍 처리 예외"""

    def __init__(self, message: str, step: Optional[str] = None, **kwargs):
        details = kwargs.pop("details", {})
        if step:
            details["step"] = step

        super().__init__(
            message=f"Streaming error: {message}",
            generation_type="streaming",
            details=details,
            **kwargs
        )


# =============================================================================
# Processing Domain Exceptions
# =============================================================================

class ProcessingException(BusinessLogicException):
    """파일 및 데이터 처리 관련 예외"""

    def __init__(self, message: str, processing_type: Optional[str] = None, **kwargs):
        details = kwargs.pop("details", {})
        if processing_type:
            details["processing_type"] = processing_type

        super().__init__(
            message=message,
            operation="processing",
            details=details,
            **kwargs
        )


class FileProcessingException(ProcessingException):
    """파일 처리 예외"""

    def __init__(self, filename: str, file_type: str, reason: str, **kwargs):
        super().__init__(
            message=f"File processing failed for {filename} ({file_type}): {reason}",
            processing_type="file",
            details={"filename": filename, "file_type": file_type, "reason": reason},
            **kwargs
        )


class FeatureExtractionException(ProcessingException):
    """특성 추출 예외"""

    def __init__(self, modality: str, reason: str, **kwargs):
        super().__init__(
            message=f"Feature extraction failed for {modality}: {reason}",
            processing_type="feature_extraction",
            details={"modality": modality, "reason": reason},
            **kwargs
        )


# =============================================================================
# Embedding Domain Exceptions
# =============================================================================

class EmbeddingException(BusinessLogicException):
    """임베딩 관련 예외"""

    def __init__(self, message: str, modality: Optional[str] = None, **kwargs):
        details = kwargs.pop("details", {})
        if modality:
            details["modality"] = modality

        super().__init__(
            message=message,
            operation="embedding",
            error_code=ErrorCode.EMBEDDING_FAILED,
            details=details,
            **kwargs
        )


class VectorGenerationException(EmbeddingException):
    """벡터 생성 실패 예외"""

    def __init__(self, modality: str, model: str, reason: str, **kwargs):
        super().__init__(
            message=f"Vector generation failed for {modality} with {model}: {reason}",
            modality=modality,
            details={"model": model, "reason": reason},
            **kwargs
        )


# =============================================================================
# Analysis Domain Exceptions
# =============================================================================

class AnalysisException(BusinessLogicException):
    """분석 관련 예외"""

    def __init__(self, message: str, analysis_type: Optional[str] = None, **kwargs):
        details = kwargs.pop("details", {})
        if analysis_type:
            details["analysis_type"] = analysis_type

        super().__init__(
            message=message,
            operation="analysis",
            error_code=ErrorCode.ANALYSIS_FAILED,
            details=details,
            **kwargs
        )


class MultimodalAnalysisException(AnalysisException):
    """멀티모달 분석 예외"""

    def __init__(self, modalities: list, reason: str, **kwargs):
        super().__init__(
            message=f"Multimodal analysis failed for {', '.join(modalities)}: {reason}",
            analysis_type="multimodal",
            details={"modalities": modalities, "reason": reason},
            **kwargs
        )


# =============================================================================
# Client Domain Exceptions
# =============================================================================

class ClientException(BaseAppException):
    """외부 클라이언트 관련 예외"""

    def __init__(self, client_name: str, message: str, **kwargs):
        details = kwargs.pop("details", {})
        details["client"] = client_name

        super().__init__(
            message=f"{client_name} client error: {message}",
            error_code=ErrorCode.EXTERNAL_API_ERROR,
            category=ErrorCategory.EXTERNAL_API,
            status_code=503,
            details=details,
            **kwargs
        )


class EmbeddingClientException(ClientException):
    """임베딩 클라이언트 예외"""

    def __init__(self, message: str, **kwargs):
        super().__init__(client_name="Embedding", message=message, **kwargs)


class LLMClientException(ClientException):
    """LLM 클라이언트 예외"""

    def __init__(self, message: str, **kwargs):
        super().__init__(client_name="LLM", message=message, **kwargs)


class FeatureExtractionClientException(ClientException):
    """특성 추출 클라이언트 예외"""

    def __init__(self, message: str, **kwargs):
        super().__init__(client_name="FeatureExtraction", message=message, **kwargs)