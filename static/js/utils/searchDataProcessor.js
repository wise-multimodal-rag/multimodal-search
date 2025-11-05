/**
 * 검색 데이터 처리 유틸리티
 */
class SearchDataProcessor {
    
    // 긴 텍스트를 생략하여 표시하는 헬퍼 함수
    static truncateText(text, maxLength = 50) {
        if (!text) return '';
        const textStr = typeof text === 'object' ? JSON.stringify(text) : String(text);
        return textStr.length > maxLength 
            ? textStr.substring(0, maxLength) + '...' 
            : textStr;
    }

    // 콘텐츠의 불필요한 들여쓰기를 제거하되 줄바꿈은 유지하는 함수
    static cleanContentIndentation(content) {
        if (!content) return '';
        
        // 앞뒤 공백 제거
        const trimmed = content.trim();
        
        // 각 줄의 앞쪽 공백을 제거하되 줄바꿈은 유지
        const lines = trimmed.split('\n');
        const cleanedLines = lines.map(line => line.trim());
        
        return cleanedLines.join('\n');
    }
    
    // Element 데이터를 화면 표시용으로 정리
    static sanitizeElementForDisplay(element) {
        const sanitized = { ...element };
        
        // 너무 긴 content는 자르기
        if (sanitized.content && typeof sanitized.content === 'string' && sanitized.content.length > 500) {
            sanitized.content = sanitized.content.substring(0, 500) + '... (truncated)';
        }
        
        // embedding 벡터는 제거 (너무 길어서)
        if (sanitized.embedding) {
            delete sanitized.embedding;
        }
        
        return sanitized;
    }
    
    // 타임스탬프 포맷팅
    static formatTimestamp(serverTimestamp) {
        if (serverTimestamp) {
            const date = new Date(serverTimestamp * 1000);
            return date.toLocaleTimeString('ko-KR', { 
                hour12: false, 
                hour: '2-digit', 
                minute: '2-digit', 
                second: '2-digit' 
            });
        } else {
            return new Date().toLocaleTimeString('ko-KR', { 
                hour12: false, 
                hour: '2-digit', 
                minute: '2-digit', 
                second: '2-digit' 
            });
        }
    }
    
    // 파일 크기를 사람이 읽기 쉬운 형태로 변환
    static formatFileSize(bytes) {
        if (!bytes) return '';
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        if (bytes === 0) return '0 Bytes';
        const i = parseInt(Math.floor(Math.log(bytes) / Math.log(1024)));
        return Math.round(bytes / Math.pow(1024, i) * 100) / 100 + ' ' + sizes[i];
    }
    
    // 실제 특징과 메타데이터를 분리
    static separateFeatureData(features) {
        const metaKeys = ['keywords_count', 'entities_count', 'has_summary', 'has_classification', 
                        'has_caption', 'objects_count', 'has_description', 'scenes_count', 
                        'activities_count', 'has_transcription', 'sounds_count', 'audio_type'];
        
        const actualFeatures = {};
        const metaData = {};
        
        Object.entries(features).forEach(([key, value]) => {
            if (metaKeys.includes(key)) {
                metaData[key] = value;
            } else {
                actualFeatures[key] = value;
            }
        });
        
        return { actualFeatures, metaData };
    }
    
    // 실제 특징 수 계산
    static countActualFeatures(features) {
        if (!features) return 0;
        const metaKeys = ['keywords_count', 'entities_count', 'has_summary', 'has_classification', 
                        'has_caption', 'objects_count', 'has_description', 'scenes_count', 
                        'activities_count', 'has_transcription', 'sounds_count', 'audio_type'];
        return Object.keys(features).filter(key => !metaKeys.includes(key)).length;
    }
    
    // 이미지 경로 추출
    static extractImagePath(content) {
        if (!content) return null;
        
        try {
            let contentToCheck = content;
            
            // JSON 문자열인 경우 파싱 시도
            if (typeof content === 'string') {
                try {
                    const parsed = JSON.parse(content);
                    // 파싱된 객체에서 origins로 시작하는 값 찾기
                    for (const value of Object.values(parsed)) {
                        if (typeof value === 'string' && value.startsWith('origins/')) {
                            return value;
                        }
                    }
                } catch (e) {
                    // JSON이 아닌 경우 직접 확인
                    if (content.startsWith('origins/')) {
                        return content;
                    }
                }
            } else if (typeof content === 'object') {
                // 객체인 경우 origins로 시작하는 값 찾기
                for (const value of Object.values(content)) {
                    if (typeof value === 'string' && value.startsWith('origins/')) {
                        return value;
                    }
                }
            }
        } catch (e) {
            console.warn('Failed to parse content for image path:', e);
        }
        
        return null;
    }
}

// 전역 사용을 위한 export
window.SearchDataProcessor = SearchDataProcessor;
console.log('✅ SearchDataProcessor loaded');