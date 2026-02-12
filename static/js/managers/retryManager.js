/**
 * 답변 재시도 관리 클래스
 * 품질 점수가 낮을 때 답변 재생성을 처리
 */
class RetryManager {
    constructor(streamingController) {
        this.streamingController = streamingController;
        this.maxRetries = 2;
    }
    
    /**
     * 답변 재시도 실행
     * @param {number} retryCount - 현재 재시도 횟수
     * @param {Object} abortController - 요청 중단 컨트롤러
     * @param {Function} addStep - 단계 추가 함수
     * @returns {Promise<void>}
     */
    async triggerAnswerRetry(retryCount, abortController, addStep) {
        console.log('🔄 Triggering answer retry due to low quality score...');
        
        try {
            // 재시도 횟수 확인
            if (retryCount >= this.maxRetries) {
                console.log(`❌ Maximum retry attempts reached (${this.maxRetries}), proceeding with current answer`);
                addStep('재시도 한계 도달', `최대 재시도 횟수(${this.maxRetries}회)에 도달했습니다. 현재 답변으로 진행합니다.`, null, 'warning', Date.now() / 1000);
                return;
            }
            
            const currentRetry = retryCount + 1;
            console.log(`🔄 Retry attempt ${currentRetry}/${this.maxRetries}`);
            
            // FormData 구성
            const retryFormData = this.buildRetryFormData(currentRetry);
            
            console.log('📤 Sending retry request to server...');
            
            // 재시도 요청 전송
            const response = await fetch('/api/search/multimodal/stream', {
                method: 'POST',
                body: retryFormData,
                signal: abortController ? abortController.signal : null
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            console.log('✅ Retry request sent successfully - server will send regenerating step');
            
        } catch (error) {
            console.error('❌ Failed to trigger answer retry:', error);
            
            // 재시도 실패 시 사용자에게 알림
            addStep('답변 재생성 실패', `재시도 중 오류가 발생했습니다: ${error.message}`, null, 'error', Date.now() / 1000);
            
            // 재시도 실패해도 기존 답변으로 진행 (가능한 경우)
            addStep('기존 답변으로 진행', '재시도에 실패했으나 기존 답변을 사용합니다', null, 'warning', Date.now() / 1000);
        }
    }
    
    /**
     * 재시도용 FormData 구성
     * @param {number} retryCount - 재시도 횟수
     * @returns {FormData} 구성된 FormData
     */
    buildRetryFormData(retryCount) {
        const retryFormData = new FormData();
        
        // 최근 검색 히스토리에서 쿼리 정보 가져오기
        if (window.historyManager) {
            const historyData = window.historyManager.getSearchHistoryData();
            if (historyData.length > 0) {
                const lastSearch = historyData[0];
                if (lastSearch.originalText || lastSearch.query) {
                    retryFormData.append('text_query', lastSearch.originalText || lastSearch.query);
                }
            }
        }
        
        // 답변 재생성 플래그 설정
        retryFormData.append('generate_answer', 'true');
        retryFormData.append('regenerate_answer', 'true'); // 재생성 플래그
        retryFormData.append('temperature', Math.min(0.7 + (retryCount * 0.1), 0.9)); // 재시도할 때마다 온도 증가
        retryFormData.append('max_retries', this.maxRetries.toString());
        retryFormData.append('retry_attempt', retryCount.toString());
        
        // 검색 옵션 추가
        this.addSearchOptions(retryFormData);
        
        return retryFormData;
    }
    
    /**
     * 검색 옵션을 FormData에 추가
     * @param {FormData} formData - FormData 객체
     */
    addSearchOptions(formData) {
        const maxResults = document.getElementById('maxResults');
        const includeChunkMeta = document.getElementById('includeChunkMeta');
        const includeMediaMeta = document.getElementById('includeMediaMeta');
        
        if (maxResults) formData.append('max_results', maxResults.value);
        if (includeChunkMeta) formData.append('include_chunk_meta', includeChunkMeta.checked);
        if (includeMediaMeta) formData.append('include_media_meta', includeMediaMeta.checked);
    }
    
    /**
     * 품질 점수가 재시도 임계값보다 낮은지 확인
     * @param {number} qualityScore - 품질 점수
     * @param {number} threshold - 임계값 (기본값: 35)
     * @returns {boolean} 재시도가 필요한지 여부
     */
    static shouldRetry(qualityScore, threshold = 35) {
        return qualityScore < threshold;
    }
    
    /**
     * 재시도 가능 여부 확인
     * @param {number} currentRetryCount - 현재 재시도 횟수
     * @param {number} maxRetries - 최대 재시도 횟수
     * @returns {boolean} 재시도 가능 여부
     */
    static canRetry(currentRetryCount, maxRetries = 2) {
        return currentRetryCount < maxRetries;
    }
    
    /**
     * 점수에 따른 품질 레벨 반환
     * @param {number} score - 품질 점수
     * @returns {Object} 품질 레벨 정보 (level, color, emoji)
     */
    static getQualityLevel(score) {
        if (score >= 40) return { level: 'excellent', color: '🟢', emoji: '✨' };
        if (score >= 35) return { level: 'good', color: '🟡', emoji: '👍' };
        if (score >= 25) return { level: 'poor', color: '🟠', emoji: '⚠️' };
        return { level: 'very_poor', color: '🔴', emoji: '❌' };
    }
}

// 전역 접근을 위한 export
window.RetryManager = RetryManager;