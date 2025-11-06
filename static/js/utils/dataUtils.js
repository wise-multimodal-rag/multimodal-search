/**
 * 데이터 처리 유틸리티 클래스
 * JSON 파싱, 데이터 정리, 요소 표시 등의 유틸리티 기능을 제공
 */
class DataUtils {
    /**
     * 불완전한 JSON 문자열을 정리
     * @param {string} jsonStr - 정리할 JSON 문자열
     * @returns {string} 정리된 JSON 문자열
     */
    static cleanIncompleteJson(jsonStr) {
        try {
            // 1. 마지막 쉼표 뒤에 불완전한 부분이 있는지 확인
            let cleaned = jsonStr.trim();
            
            // 2. 열린 괄호나 중괄호가 닫히지 않은 경우 처리
            const openBraces = (cleaned.match(/\{/g) || []).length;
            const closeBraces = (cleaned.match(/\}/g) || []).length;
            const openBrackets = (cleaned.match(/\[/g) || []).length;
            const closeBrackets = (cleaned.match(/\]/g) || []).length;
            
            // 3. 마지막에 불완전한 속성이나 값이 있는 경우 제거
            // 마지막 쉼표를 찾고 그 이후가 완전한 속성인지 확인
            const lastCommaIndex = cleaned.lastIndexOf(',');
            if (lastCommaIndex > 0) {
                const afterComma = cleaned.substring(lastCommaIndex + 1).trim();
                
                // 쉼표 뒤에 완전하지 않은 속성이 있는 경우
                if (afterComma && !afterComma.includes(':') && !afterComma.startsWith('"')) {
                    cleaned = cleaned.substring(0, lastCommaIndex);
                } else if (afterComma.includes(':')) {
                    // 속성은 있지만 값이 불완전한 경우
                    const colonIndex = afterComma.indexOf(':');
                    const value = afterComma.substring(colonIndex + 1).trim();
                    if (value && !value.endsWith('"') && !value.endsWith('}') && !value.endsWith(']') && !(/^[\d\.\-]+$/.test(value)) && !(/^(true|false|null)$/.test(value))) {
                        cleaned = cleaned.substring(0, lastCommaIndex);
                    }
                }
            }
            
            // 4. 필요한 경우 닫는 괄호 추가
            for (let i = closeBraces; i < openBraces; i++) {
                cleaned += '}';
            }
            for (let i = closeBrackets; i < openBrackets; i++) {
                cleaned += ']';
            }
            
            return cleaned;
        } catch (error) {
            console.error('Error cleaning JSON:', error);
            return jsonStr;
        }
    }
    
    /**
     * 표시용 요소 데이터 정리 (embedding 필드 요약)
     * @param {Object} element - 정리할 요소 객체
     * @returns {Object} 정리된 요소 객체
     */
    static sanitizeElementForDisplay(element) {
        // element 객체를 복사하여 embedding 관련 필드 제거/요약
        const sanitized = { ...element };
        
        // embedding 필드들을 찾아서 요약 처리
        for (const [key, value] of Object.entries(sanitized)) {
            if (typeof key === 'string' && key.toLowerCase().includes('embedding')) {
                if (Array.isArray(value)) {
                    // 배열인 경우: 길이와 첫 몇 개 값만 표시
                    sanitized[key] = {
                        __type: 'embedding_array',
                        length: value.length,
                        first_3_values: value.slice(0, 3),
                        sample_values: `[${value.slice(0, 3).map(v => typeof v === 'number' ? v.toFixed(6) : v).join(', ')}...]`
                    };
                } else if (typeof value === 'object' && value !== null) {
                    // 객체인 경우: 구조 정보만 표시
                    sanitized[key] = {
                        __type: 'embedding_object',
                        keys: Object.keys(value),
                        summary: 'embedding data (hidden for readability)'
                    };
                }
            }
        }
        
        return sanitized;
    }
    
    /**
     * 객체를 안전하게 JSON 문자열로 변환
     * @param {any} obj - 변환할 객체
     * @param {number} space - 들여쓰기 공백 수
     * @returns {string} JSON 문자열
     */
    static safeStringify(obj, space = 2) {
        try {
            return JSON.stringify(obj, null, space);
        } catch (error) {
            console.error('Error stringifying object:', error);
            return JSON.stringify({ error: 'Failed to stringify object', type: typeof obj }, null, space);
        }
    }
    
    /**
     * 데이터 타입을 안전하게 확인
     * @param {any} value - 확인할 값
     * @returns {string} 데이터 타입 문자열
     */
    static getDataType(value) {
        if (value === null) return 'null';
        if (value === undefined) return 'undefined';
        if (Array.isArray(value)) return 'array';
        return typeof value;
    }
    
    /**
     * 깊은 복사 (순환 참조 처리)
     * @param {any} obj - 복사할 객체
     * @returns {any} 복사된 객체
     */
    static deepClone(obj) {
        if (obj === null || typeof obj !== 'object') return obj;
        if (obj instanceof Date) return new Date(obj.getTime());
        if (obj instanceof Array) return obj.map(item => DataUtils.deepClone(item));
        if (typeof obj === 'object') {
            const cloned = {};
            for (const key in obj) {
                if (obj.hasOwnProperty(key)) {
                    cloned[key] = DataUtils.deepClone(obj[key]);
                }
            }
            return cloned;
        }
        return obj;
    }
}

// 전역 접근을 위한 export
window.DataUtils = DataUtils;