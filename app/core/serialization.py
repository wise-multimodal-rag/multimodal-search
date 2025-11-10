"""공통 직렬화 유틸리티 클래스

여러 서비스에서 사용되는 직렬화 로직을 중앙화
"""
import json
from typing import Any, Dict, List, Optional, Union

from loguru import logger


class SerializationUtils:
    """안전한 직렬화를 위한 유틸리티 클래스"""
    
    @staticmethod
    def safely_serialize_feature(feature_value: Any) -> Any:
        """특징 값을 안전하게 직렬화 가능한 형태로 변환
        
        Args:
            feature_value: 직렬화할 특징 값
            
        Returns:
            직렬화 가능한 형태로 변환된 값
        """
        if feature_value is None:
            return None

        # Pydantic 모델인 경우
        if hasattr(feature_value, "model_dump"):
            return feature_value.model_dump()

        # 기본 JSON 직렬화 가능한 타입들
        if isinstance(feature_value, (list, dict, str, int, float, bool)):
            # 리스트인 경우 각 요소도 재귀적으로 처리
            if isinstance(feature_value, list):
                return [SerializationUtils.safely_serialize_feature(item) for item in feature_value]
            # 딕셔너리인 경우 각 값을 재귀적으로 처리
            elif isinstance(feature_value, dict):
                return {key: SerializationUtils.safely_serialize_feature(value) for key, value in feature_value.items()}
            else:
                return feature_value

        # 그 외의 경우 문자열로 변환
        return str(feature_value)
    
    @staticmethod
    def safely_serialize_model(model: Any) -> Dict[str, Any]:
        """Pydantic 모델을 안전하게 직렬화
        
        Args:
            model: 직렬화할 Pydantic 모델
            
        Returns:
            직렬화된 딕셔너리
        """
        try:
            if hasattr(model, "model_dump"):
                return model.model_dump()
            elif hasattr(model, "dict"):
                return model.dict()
            elif isinstance(model, dict):
                return model
            else:
                return {"serialized_value": str(model), "original_type": type(model).__name__}
        except Exception as e:
            logger.error(f"Failed to serialize model: {e}")
            return {"error": f"Serialization failed: {str(e)}", "original_type": type(model).__name__}
    
    @staticmethod
    def safely_serialize_results(results: List[Any], max_size_mb: float = 5.0) -> List[Dict[str, Any]]:
        """결과 리스트를 안전하게 직렬화하고 크기 제한 적용
        
        Args:
            results: 직렬화할 결과 리스트
            max_size_mb: 최대 크기 (MB)
            
        Returns:
            직렬화된 결과 리스트와 통계 정보
        """
        results_data = []
        total_bytes = 0
        failed_count = 0
        max_bytes = int(max_size_mb * 1024 * 1024)
        
        for i, result in enumerate(results):
            try:
                serialized = SerializationUtils.safely_serialize_model(result)
                
                # 크기 확인
                size_check = len(json.dumps(serialized, default=str))
                
                # 크기 제한 체크
                if total_bytes + size_check > max_bytes:
                    logger.warning(f"Size limit exceeded at result {i}, truncating remaining results")
                    results_data.append({
                        "truncated": True,
                        "message": f"Results truncated due to size limit ({max_size_mb}MB)",
                        "remaining_count": len(results) - i
                    })
                    break
                
                total_bytes += size_check
                results_data.append(serialized)

            except Exception as e:
                failed_count += 1
                logger.error(f"Failed to serialize result {i}: {type(e).__name__}: {e}")
                results_data.append({
                    "error": f"Serialization failed: {str(e)}", 
                    "result_index": i,
                    "original_type": type(result).__name__
                })

        # 통계 로깅
        success_count = len(results_data) - failed_count
        if failed_count > 0:
            logger.warning(
                f"Serialization completed: {success_count}/{len(results)} successful, "
                f"{failed_count} failed, {total_bytes:,} bytes total"
            )
        else:
            logger.info(f"Serialization completed: {len(results_data)} results, {total_bytes:,} bytes total")
        
        return results_data
    
    @staticmethod
    def sanitize_element_for_display(element: Dict[str, Any]) -> Dict[str, Any]:
        """표시용 요소 데이터 정리 (embedding 필드 요약)
        
        Args:
            element: 정리할 요소 딕셔너리
            
        Returns:
            정리된 요소 딕셔너리
        """
        sanitized = element.copy() if isinstance(element, dict) else {}
        
        # embedding 필드들을 찾아서 요약 처리
        for key, value in list(sanitized.items()):
            if isinstance(key, str) and 'embedding' in key.lower():
                if isinstance(value, list) and len(value) > 0:
                    # 배열인 경우: 길이와 첫 몇 개 값만 표시
                    sanitized[key] = {
                        "__type": "embedding_array",
                        "length": len(value),
                        "first_3_values": value[:3],
                        "sample_values": f"[{', '.join(str(v)[:8] if isinstance(v, float) else str(v) for v in value[:3])}...]"
                    }
                elif isinstance(value, dict):
                    # 객체인 경우: 구조 정보만 표시
                    sanitized[key] = {
                        "__type": "embedding_object",
                        "keys": list(value.keys()) if isinstance(value, dict) else [],
                        "summary": "embedding data (hidden for readability)"
                    }
        
        return sanitized
    
    @staticmethod
    def safe_json_dumps(obj: Any, indent: int = 2, default_handler=None) -> str:
        """안전한 JSON 문자열 변환
        
        Args:
            obj: 변환할 객체
            indent: 들여쓰기
            default_handler: 기본 변환 핸들러
            
        Returns:
            JSON 문자열
        """
        try:
            if default_handler is None:
                default_handler = str
            return json.dumps(obj, indent=indent, default=default_handler, ensure_ascii=False)
        except Exception as e:
            logger.error(f"JSON serialization failed: {e}")
            return json.dumps({
                "error": "Failed to serialize object",
                "error_message": str(e),
                "object_type": type(obj).__name__
            }, indent=indent, ensure_ascii=False)
    
    @staticmethod
    def clean_incomplete_json(json_str: str) -> str:
        """불완전한 JSON 문자열을 정리
        
        Args:
            json_str: 정리할 JSON 문자열
            
        Returns:
            정리된 JSON 문자열
        """
        try:
            cleaned = json_str.strip()
            
            # 열린 괄호나 중괄호가 닫히지 않은 경우 처리
            open_braces = cleaned.count('{')
            close_braces = cleaned.count('}')
            open_brackets = cleaned.count('[')
            close_brackets = cleaned.count(']')
            
            # 마지막에 불완전한 속성이나 값이 있는 경우 제거
            last_comma_index = cleaned.rfind(',')
            if last_comma_index > 0:
                after_comma = cleaned[last_comma_index + 1:].strip()
                
                # 쉼표 뒤에 완전하지 않은 속성이 있는 경우
                if after_comma and ':' not in after_comma:
                    cleaned = cleaned[:last_comma_index]
                elif ':' in after_comma:
                    # 속성은 있지만 값이 불완전한 경우
                    colon_index = after_comma.find(':')
                    value = after_comma[colon_index + 1:].strip()
                    if value and not any(value.endswith(end) for end in ['"', '}', ']']) and not value.replace('.', '').replace('-', '').isdigit():
                        cleaned = cleaned[:last_comma_index]
            
            # 필요한 경우 닫는 괄호 추가
            for _ in range(open_braces - close_braces):
                cleaned += '}'
            for _ in range(open_brackets - close_brackets):
                cleaned += ']'
            
            return cleaned
        except Exception as e:
            logger.error(f"Error cleaning JSON: {e}")
            return json_str