/**
 * 메타데이터 생성 유틸리티 클래스
 * 답변 생성 과정의 각 단계별 메타데이터를 생성
 */
class MetadataCreator {
    /**
     * 답변 메타데이터 생성
     * @param {Object} data - 답변 데이터
     * @param {string} stage - 단계 ('초안 생성' 등)
     * @returns {string} HTML 메타데이터 문자열
     */
    static createAnswerMetadata(data, stage) {
        console.log('createAnswerMetadata:', stage);
        let content = '<div class="step-details">';
        
        // 초안 생성 단계의 메타데이터 (재생성 포함)
        if (stage === '초안 생성' || stage.includes('초안 재생성')) {
            if (data.attempt_number) {
                content += `<div class="data-item"><strong>시도 번호:</strong> ${data.attempt_number}회차</div>`;
            }
            
            if (data.answer_length) {
                content += `<div class="data-item"><strong>답변 길이:</strong> ${data.answer_length}자</div>`;
            }
            
            if (data.processing_time_ms) {
                content += `<div class="data-item"><strong>생성 시간:</strong> ${data.processing_time_ms}ms</div>`;
            }
            
            if (data.temperature) {
                content += `<div class="data-item"><strong>Temperature:</strong> ${data.temperature}</div>`;
            }
            
            if (data.search_context_size) {
                content += `<div class="data-item"><strong>참고 문서:</strong> ${data.search_context_size}개</div>`;
            }
            
            // 생성된 초안 내용 추가 - 다양한 가능한 키 확인
            const possibleDraftKeys = [
                'answer_draft', 'draft', 'draft_answer', 'generated_answer', 
                'answer', 'content', 'final_answer', 'text', 'response', 'draft_preview',
                'result', 'output', 'generated_text', 'draft_text'
            ];
            
            let draftFound = false;
            
            // 1단계: 최상위 키에서 직접 검색
            for (const key of possibleDraftKeys) {
                const value = data[key];
                
                if (value && typeof value === 'string' && value.trim().length > 0) {
                    console.log(`✅ Found draft in '${key}': ${value.length} chars`);
                    content += `<div class="data-section">
                        <h4>생성된 답변 초안</h4>
                        <div class="draft-content">${TextFormatter.formatAnswerText(value)}</div>
                    </div>`;
                    draftFound = true;
                    break;
                }
            }
            
            // 2단계: 중첩된 객체에서 재귀적으로 검색
            if (!draftFound && data && typeof data === 'object') {
                const foundDraftContent = this.findNestedDraftContent(data, possibleDraftKeys, 3);
                if (foundDraftContent) {
                    console.log(`✅ Found draft in nested object: ${foundDraftContent.length} chars`);
                    content += `<div class="data-section">
                        <h4>생성된 답변 초안</h4>
                        <div class="draft-content">${TextFormatter.formatAnswerText(foundDraftContent)}</div>
                    </div>`;
                    draftFound = true;
                }
            }
            
            if (!draftFound) {
                console.log('❌ No draft content found. Available keys:', Object.keys(data || {}));
                
                // 초안이 없음을 사용자에게 알림
                content += `<div class="data-section">
                    <h4>생성된 답변 초안</h4>
                    <div class="draft-content" style="color: #6b7280; font-style: italic;">
                        초안 내용이 백엔드에서 전송되지 않았습니다.<br>
                        백엔드 API에서 초안 데이터를 포함하도록 설정이 필요합니다.<br>
                        <small>디버그: 사용 가능한 키: ${Object.keys(data || {}).join(', ')}</small>
                    </div>
                </div>`;
            }
        }
        
        content += '</div>';
        return content;
    }
    
    /**
     * 중첩된 객체에서 초안 콘텐츠를 재귀적으로 검색
     * @param {Object} obj - 검색할 객체
     * @param {Array} draftKeys - 찾을 키 목록
     * @param {number} maxDepth - 최대 검색 깊이
     * @param {number} currentDepth - 현재 검색 깊이
     * @returns {string|null} 찾은 초안 내용 또는 null
     */
    static findNestedDraftContent(obj, draftKeys, maxDepth = 3, currentDepth = 0) {
        if (!obj || typeof obj !== 'object' || currentDepth >= maxDepth) {
            return null;
        }
        
        // 현재 레벨에서 직접 키 검색
        for (const key of draftKeys) {
            if (obj[key] && typeof obj[key] === 'string' && obj[key].trim().length > 0) {
                return obj[key];
            }
        }
        
        // 하위 객체들을 재귀적으로 검색
        for (const [objKey, objValue] of Object.entries(obj)) {
            if (objValue && typeof objValue === 'object' && !Array.isArray(objValue)) {
                const foundContent = this.findNestedDraftContent(objValue, draftKeys, maxDepth, currentDepth + 1);
                if (foundContent) {
                    return foundContent;
                }
            }
        }
        
        return null;
    }
    
    /**
     * 객체의 모든 중첩된 키를 수집하는 헬퍼 메서드
     * @param {Object} obj - 검색할 객체
     * @param {number} maxDepth - 최대 검색 깊이
     * @param {number} currentDepth - 현재 검색 깊이
     * @returns {Array} 모든 키의 배열
     */
    static getAllNestedKeys(obj, maxDepth = 3, currentDepth = 0) {
        if (!obj || typeof obj !== 'object' || currentDepth >= maxDepth) {
            return [];
        }
        
        let keys = Object.keys(obj);
        
        // 하위 객체들의 키도 수집
        for (const [key, value] of Object.entries(obj)) {
            if (value && typeof value === 'object' && !Array.isArray(value)) {
                const nestedKeys = this.getAllNestedKeys(value, maxDepth, currentDepth + 1);
                keys = keys.concat(nestedKeys.map(nestedKey => `${key}.${nestedKey}`));
            }
        }
        
        return keys;
    }
    
    /**
     * 품질 검토 메타데이터 생성
     * @param {Object} data - 검토 데이터
     * @param {number} attemptNumber - 시도 횟수 (선택적)
     * @returns {string} HTML 메타데이터 문자열
     */
    static createReflectionMetadata(data, attemptNumber = null) {
        let content = '<div class="step-details">';
        
        // 시도 횟수 정보 추가
        if (attemptNumber !== null) {
            content += `<div class="data-item"><strong>검토 대상:</strong> ${attemptNumber}회차 답변</div>`;
        }
        
        if (data.total_score !== undefined) {
            content += `<div class="data-item"><strong>종합 점수:</strong> ${data.total_score}/50</div>`;
        }
        
        if (data.scores && Object.keys(data.scores).length > 0) {
            const scores = data.scores;
            const scoreItems = [];
            if (scores.relevance !== undefined) scoreItems.push(`관련성 ${scores.relevance}/10`);
            if (scores.accuracy !== undefined) scoreItems.push(`정확성 ${scores.accuracy}/10`);
            if (scores.completeness !== undefined) scoreItems.push(`완성도 ${scores.completeness}/10`);
            if (scores.clarity !== undefined) scoreItems.push(`명확성 ${scores.clarity}/10`);
            if (scores.structure !== undefined) scoreItems.push(`구조 ${scores.structure}/10`);
            
            if (scoreItems.length > 0) {
                content += `<div class="data-item"><strong>세부 점수:</strong> ${scoreItems.join(', ')}</div>`;
            }
        }
        
        if (data.answer_quality) {
            content += `<div class="data-item"><strong>품질 평가:</strong> ${data.answer_quality}</div>`;
        }
        
        if (data.is_acceptable !== undefined) {
            const acceptText = data.is_acceptable ? '승인됨' : '재생성 필요';
            content += `<div class="data-item"><strong>승인 여부:</strong> ${acceptText}</div>`;
        }
        
        if (data.improvement_suggestions && data.improvement_suggestions.length > 0) {
            const suggestions = data.improvement_suggestions.slice(0, 3).join(', ');
            content += `<div class="data-item"><strong>개선 제안:</strong> ${suggestions}</div>`;
        }
        
        content += '</div>';
        return content;
    }
    
    /**
     * 최종 답변 메타데이터 생성
     * @param {Object} data - 최종 답변 데이터
     * @returns {string} HTML 메타데이터 문자열
     */
    static createFinalAnswerMetadata(data) {
        let content = '<div class="step-details">';
        
        if (data.total_attempts) {
            content += `<div class="data-item"><strong>총 시도 횟수:</strong> ${data.total_attempts}회</div>`;
        }
        
        if (data.processing_time_ms) {
            const timeInSeconds = (data.processing_time_ms / 1000).toFixed(1);
            content += `<div class="data-item"><strong>총 처리 시간:</strong> ${timeInSeconds}초</div>`;
        }
        
        if (data.success !== undefined) {
            const successText = data.success ? '성공' : '실패';
            content += `<div class="data-item"><strong>생성 결과:</strong> ${successText}</div>`;
        }
        
        if (data.final_answer) {
            content += `<div class="data-item"><strong>최종 답변 길이:</strong> ${data.final_answer.length}자</div>`;
        }
        
        if (data.search_context) {
            const context = data.search_context;
            if (context.total_results) {
                content += `<div class="data-item"><strong>참고 검색 결과:</strong> ${context.total_results}개</div>`;
            }
        }
        
        // 품질 지표 추가
        if (data.generation_attempts && data.generation_attempts.length > 0) {
            const lastAttempt = data.generation_attempts[data.generation_attempts.length - 1];
            if (lastAttempt.reflection && lastAttempt.reflection.total_score) {
                const score = lastAttempt.reflection.total_score;
                const scoreColor = score >= 40 ? '🟢' : score >= 30 ? '🟡' : '🔴';
                content += `<div class="data-item"><strong>최종 품질 점수:</strong> ${scoreColor} ${score}/50</div>`;
            }
        }
        
        content += '</div>';
        return content;
    }
}

// 전역 접근을 위한 export
window.MetadataCreator = MetadataCreator;