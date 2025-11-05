/**
 * 스트리밍 연결 및 데이터 처리 핸들러
 */
class StreamingHandler {
    constructor() {
        this.partialData = '';
        this.abortController = null;
    }
    
    async startStreaming(url, formData, hasAnswerGeneration, onStepResult, onError) {
        this.abortController = new AbortController();
        this.partialData = '';
        this.hasAnswerGeneration = hasAnswerGeneration;
        
        try {
            const response = await fetch(url, {
                method: 'POST',
                body: formData,
                signal: this.abortController.signal
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let streamEnded = false;
            
            while (true && !streamEnded) {
                const { done, value } = await reader.read();
                
                if (done) {
                    break;
                }
                
                const chunk = decoder.decode(value);
                streamEnded = await this.processChunk(chunk, onStepResult);
            }
            
            // 스트림 종료 시 남은 부분 데이터 처리
            if (this.partialData.trim()) {
                console.log('🧹 Processing remaining partial data:', this.partialData.substring(0, 100));
                if (this.partialData.startsWith('data: ')) {
                    try {
                        const data = this.partialData.slice(6).trim();
                        if (data && data !== '[DONE]') {
                            const cleanedData = DataUtils.cleanIncompleteJson(data);
                            const stepResult = JSON.parse(cleanedData);
                            onStepResult(stepResult);
                        }
                    } catch (error) {
                        console.error('❌ Failed to process remaining data:', error);
                    }
                }
            }
            
        } catch (error) {
            if (error.name === 'AbortError') {
                console.log('🛑 Search was stopped by user');
                onStepResult({
                    step: 'user_stopped',
                    message: '사용자가 검색을 중지했습니다',
                    timestamp: Date.now() / 1000
                });
            } else {
                console.error('Streaming failed:', error);
                onError(`스트리밍 검색 실패: ${error.message}`);
            }
        }
    }
    
    async processChunk(chunk, onStepResult) {
        // 부분 데이터와 새 청크를 결합
        this.partialData += chunk;
        const lines = this.partialData.split('\n');
        
        // 마지막 라인은 불완전할 수 있으므로 따로 보관
        this.partialData = lines.pop() || '';
        
        for (const line of lines) {
            if (line.startsWith('data: ')) {
                try {
                    const data = line.slice(6); // 'data: ' 제거
                    if (data.trim()) {
                        // 스트림 종료 신호 확인
                        if (data.trim() === '[DONE]') {
                            console.log('🏁 Stream end signal received');
                            return true; // 스트림 종료
                        }
                        
                        // JSON 파싱 전 데이터 로깅 (첫 200자만)
                        console.log('📥 Raw streaming data (first 200 chars):', data.substring(0, 200));
                        
                        // JSON 파싱 시도
                        let stepResult;
                        try {
                            stepResult = JSON.parse(data);
                        } catch (parseError) {
                            console.error('❌ JSON Parse Error:', parseError);
                            console.error('📄 Problematic data length:', data.length);
                            
                            // JSON 수정 시도 (마지막 incomplete 부분 제거)
                            const cleanedData = DataUtils.cleanIncompleteJson(data);
                            if (cleanedData !== data) {
                                console.log('🔧 Attempting to parse cleaned JSON...');
                                try {
                                    stepResult = JSON.parse(cleanedData);
                                    console.log('✅ Successfully parsed cleaned JSON');
                                } catch (cleanedError) {
                                    console.error('❌ Cleaned JSON also failed:', cleanedError);
                                    continue; // 이 라인 건너뛰기
                                }
                            } else {
                                continue; // 이 라인 건너뛰기
                            }
                        }
                        
                        // 단계 결과 처리
                        onStepResult(stepResult);
                        
                        // COMPLETED 단계에서 답변 생성이 없으면 스트림 종료
                        if (stepResult.step === 'completed' && !this.hasAnswerGeneration) {
                            console.log('🏁 Search completed without answer generation - ending stream');
                            return true; // 스트림 종료
                        } else if (stepResult.step === 'completed' && this.hasAnswerGeneration) {
                            console.log('🔄 Search completed with answer generation - continuing stream for answer steps');
                        }
                        
                        // 답변 생성 완료 시 스트림 종료
                        if (stepResult.step === 'answer_completed') {
                            console.log('🏁 Answer generation completed - ending stream');
                            return true; // 스트림 종료
                        }
                    }
                } catch (error) {
                    console.error('❌ General streaming error:', error);
                    console.error('📄 Line content:', line);
                }
            }
        }
        
        return false; // 스트림 계속
    }
    
    stop() {
        if (this.abortController) {
            console.log('🛑 Stopping streaming...');
            this.abortController.abort();
        }
    }
    
    reset() {
        this.partialData = '';
        this.abortController = null;
        this.hasAnswerGeneration = false;
    }
}

// 전역 사용을 위한 export
window.StreamingHandler = StreamingHandler;
console.log('✅ StreamingHandler loaded');