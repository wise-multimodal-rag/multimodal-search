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
        console.log('createAnswerMetadata called with:', { stage, data });
        let content = '<div class="step-details">';
        
        // 초안 생성 단계의 메타데이터
        if (stage === '초안 생성') {
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
            console.log('🔍 Looking for draft content in data:', data);
            const possibleDraftKeys = [
                'answer_draft', 'draft', 'draft_answer', 'generated_answer', 
                'answer', 'content', 'final_answer', 'text', 'response', 'draft_preview'
            ];
            
            let draftFound = false;
            for (const key of possibleDraftKeys) {
                const value = data[key];
                if (value && typeof value === 'string' && value.trim().length > 0) {
                    console.log(`✅ Found draft content in key '${key}':`, value.substring(0, 100) + '...');
                    content += `<div class="data-section">
                        <h4>📝 생성된 답변 초안</h4>
                        <div class="draft-content">${TextFormatter.formatAnswerText(value)}</div>
                    </div>`;
                    draftFound = true;
                    break;
                }
            }
            
            if (!draftFound) {
                console.log('❌ No draft content found. Available data:', {
                    keys: Object.keys(data || {}),
                    dataType: typeof data,
                    dataPreview: data ? JSON.stringify(data).substring(0, 200) + '...' : 'null'
                });
                
                // 초안이 없음을 사용자에게 알림
                content += `<div class="data-section">
                    <h4>📝 생성된 답변 초안</h4>
                    <div class="draft-content" style="color: #6b7280; font-style: italic;">
                        초안 내용이 백엔드에서 전송되지 않았습니다.<br>
                        백엔드 API에서 초안 데이터를 포함하도록 설정이 필요합니다.
                    </div>
                </div>`;
            }
        }
        
        content += '</div>';
        return content;
    }
    
    /**
     * 품질 검토 메타데이터 생성
     * @param {Object} data - 검토 데이터
     * @returns {string} HTML 메타데이터 문자열
     */
    static createReflectionMetadata(data) {
        let content = '<div class="step-details">';
        
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