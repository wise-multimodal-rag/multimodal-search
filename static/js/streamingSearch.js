/**
 * 실시간 스트리밍 검색 컨트롤러 (v2.0)
 */
class StreamingSearchController {
    constructor() {
        this.eventSource = null;
        this.searchProcessContainer = document.getElementById('searchProcessContainer');
        this.searchSteps = document.getElementById('searchSteps');
        this.progressFill = document.getElementById('progressFill');
        this.progressText = document.getElementById('progressText');
        this.currentStep = 0;
        this.totalSteps = 8;
        this.isStreaming = false;
        this.searchProcessData = []; // 검색 진행 과정 데이터 저장
        this.partialData = ''; // 부분적 스트리밍 데이터 누적용
    }
    
    async startStreamingSearch(formData) {
        if (this.isStreaming) {
            console.log('Search already in progress');
            return;
        }
        
        this.isStreaming = true;
        
        // 검색 과정 데이터 초기화
        this.searchProcessData = [];
        this.partialData = ''; // 부분 데이터도 초기화
        
        // 히스토리 복원 모드 클래스 제거 (실시간 검색 시작)
        this.searchProcessContainer.classList.remove('history-restore');
        
        // 검색 과정 컨테이너 표시
        this.searchProcessContainer.style.display = 'block';
        this.searchSteps.innerHTML = '';
        this.currentStep = 0;
        this.updateProgress();
        
        try {
            // FormData를 URLSearchParams로 변환 (GET 방식이 아니므로 POST로 전송)
            const response = await fetch('/api/v1/search/multimodal/stream', {
                method: 'POST',
                body: formData
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
                                    streamEnded = true;
                                    break;
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
                                    console.error('📄 Data around error position:', data.substring(Math.max(0, 60190-100), 60190+100));
                                    
                                    // JSON 수정 시도 (마지막 incomplete 부분 제거)
                                    const cleanedData = this.cleanIncompleteJson(data);
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
                                
                                // COMPLETED 단계 처리 및 스트림 종료
                                if (stepResult.step === 'completed') {
                                    console.log('🎯 Handling completed step');
                                    this.handleStepResult(stepResult);
                                    streamEnded = true;
                                    break;
                                } else {
                                    this.handleStepResult(stepResult);
                                }
                            }
                        } catch (error) {
                            console.error('❌ General streaming error:', error);
                            console.error('📄 Line content:', line);
                        }
                    }
                }
            }
            
            // 스트림 종료 시 남은 부분 데이터 처리
            if (this.partialData.trim()) {
                console.log('🧹 Processing remaining partial data:', this.partialData.substring(0, 100));
                if (this.partialData.startsWith('data: ')) {
                    try {
                        const data = this.partialData.slice(6).trim();
                        if (data && data !== '[DONE]') {
                            const cleanedData = this.cleanIncompleteJson(data);
                            const stepResult = JSON.parse(cleanedData);
                            this.handleStepResult(stepResult);
                        }
                    } catch (error) {
                        console.error('❌ Failed to process remaining data:', error);
                    }
                }
            }
            
        } catch (error) {
            console.error('Streaming search failed:', error);
            this.showError(`스트리밍 검색 실패: ${error.message}`);
        } finally {
            console.log('🔚 Streaming finally block - setting isStreaming to false');
            this.isStreaming = false;
        }
    }
    
    handleStepResult(stepResult) {
        const { step, message, data, timestamp, error } = stepResult;
        
        console.log('🔍 Step result received:', stepResult);
        console.log('📊 Current step before:', this.currentStep, 'New step:', step);
        console.log('⏰ Timestamp:', timestamp, 'Message:', message);
        
        // 진행 과정 데이터에 저장 (error가 있을 때는 message 대신 error 사용)
        const processStep = {
            step,
            message: error || message,
            data,
            timestamp,
            recordedAt: new Date().toISOString()
        };
        this.searchProcessData.push(processStep);
        console.log('Added process step:', step, '- Total steps:', this.searchProcessData.length);
        
        switch (step) {
            case 'start':
                this.addStep('검색 시작', message, data, 'info', timestamp);
                this.currentStep = 1;
                break;
                
            case 'input_processing':
                this.addStep('입력 처리 중', message, null, 'loading', timestamp);
                break;
                
            case 'input_processed':
                this.updateLastLoadingStep('입력 처리 완료', message, data, 'success', timestamp);
                this.currentStep = 2;
                break;
                
            case 'query_expansion':
                this.addStep('쿼리 확장 중', message, null, 'loading', timestamp);
                break;
                
            case 'query_expanded':
                this.updateLastLoadingStep('쿼리 확장 완료', message, data, 'success', timestamp);
                this.currentStep = 3;
                break;
                
            case 'intent_analysis':
                this.addStep('쿼리 의도 분석 중', message, null, 'loading', timestamp);
                break;
                
            case 'intent_analyzed':
                this.updateLastLoadingStep('쿼리 의도 분석 완료', message, data, 'success', timestamp);
                this.currentStep = 4;
                break;
                
            case 'feature_extraction':
                this.addStep('특징 추출 중', message, null, 'loading', timestamp);
                break;
                
            case 'features_extracted':
                this.updateLastLoadingStep('특징 추출 완료', message, data, 'success', timestamp);
                this.currentStep = 5;
                break;
                
            case 'embedding_generation':
                this.addStep('임베딩 생성 중', message, null, 'loading', timestamp);
                break;
                
            case 'embeddings_generated':
                this.updateLastLoadingStep('임베딩 생성 완료', message, data, 'success', timestamp);
                this.currentStep = 6;
                break;
                
            case 'search_execution':
                this.addStep('검색 실행 중', message, null, 'loading', timestamp);
                break;
                
            case 'search_executed':
                this.updateLastLoadingStep('검색 실행 완료', message, data, 'success', timestamp);
                this.currentStep = 7;
                break;
                
            case 'result_enrichment':
                this.addStep('결과 보강 중', message, null, 'loading', timestamp);
                break;
                
            case 'result_enriched':
                this.updateLastLoadingStep('결과 보강 완료', message, data, 'success', timestamp);
                this.currentStep = 8;
                break;
                
            case 'completed':
                this.addStep('검색 완료', message, data, 'success', timestamp);
                this.renderFinalResults(data);
                break;
                
            case 'error':
                this.addStep('오류 발생', error, null, 'error', timestamp);
                this.showError(error);
                break;
                
            case 'file_read_failed':
                this.addStep('파일 처리 실패', message || '파일을 읽을 수 없어 텍스트만으로 검색을 진행합니다', data, 'warning', timestamp);
                break;
                
            default:
                console.log('Unknown step:', step);
        }
        
        this.updateProgress();
    }
    
    updateLastLoadingStep(title, message, data = null, type = 'success', serverTimestamp = null) {
        // 마지막 loading 상태의 단계를 찾아서 업데이트
        const loadingSteps = this.searchSteps.querySelectorAll('.search-step.loading');
        if (loadingSteps.length > 0) {
            const lastLoadingStep = loadingSteps[loadingSteps.length - 1];
            
            // 클래스 변경
            lastLoadingStep.className = `search-step ${type}`;
            
            // 서버 타임스탬프가 있으면 사용, 없으면 클라이언트 시간 사용
            let displayTime;
            if (serverTimestamp) {
                const date = new Date(serverTimestamp * 1000);
                displayTime = date.toLocaleTimeString('ko-KR', { 
                    hour12: false, 
                    hour: '2-digit', 
                    minute: '2-digit', 
                    second: '2-digit' 
                });
            } else {
                displayTime = new Date().toLocaleTimeString('ko-KR', { 
                    hour12: false, 
                    hour: '2-digit', 
                    minute: '2-digit', 
                    second: '2-digit' 
                });
            }
            
            // 내용 업데이트 (로딩 애니메이션 제거)
            lastLoadingStep.innerHTML = `
                <div class="step-header">
                    <div class="step-title-and-message">
                        <div class="step-title">${title}</div>
                        <div class="step-message">${message}</div>
                    </div>
                    <div class="step-time">${displayTime}</div>
                </div>
                ${data ? `<div class="step-data" id="step-data-${Date.now()}"></div>` : ''}
            `;
            
            // 데이터가 있으면 렌더링
            if (data) {
                const dataContainer = lastLoadingStep.querySelector('.step-data');
                this.renderStepData(dataContainer, data, type);
            }
        } else {
            // 마지막 loading 단계가 없으면 새로 추가
            this.addStep(title, message, data, type, serverTimestamp);
        }
    }
    
    addStep(title, message, data = null, type = 'info', serverTimestamp = null) {
        console.log('addStep called:', title, type, 'with timestamp:', serverTimestamp);
        
        const stepElement = document.createElement('div');
        stepElement.className = `search-step ${type}`;
        
        // 서버 타임스탬프가 있으면 사용, 없으면 클라이언트 시간 사용
        let displayTime;
        if (serverTimestamp) {
            // 서버 타임스탬프를 Date 객체로 변환 (초 단위를 밀리초로 변환)
            const date = new Date(serverTimestamp * 1000);
            displayTime = date.toLocaleTimeString('ko-KR', { 
                hour12: false, 
                hour: '2-digit', 
                minute: '2-digit', 
                second: '2-digit' 
            });
        } else {
            displayTime = new Date().toLocaleTimeString('ko-KR', { 
                hour12: false, 
                hour: '2-digit', 
                minute: '2-digit', 
                second: '2-digit' 
            });
        }
        
        // 로딩 상태일 때만 메시지에 점 애니메이션 추가
        const messageWithAnimation = type === 'loading' 
            ? `${message}<span class="loading-dots"></span>` 
            : message;
        
        stepElement.innerHTML = `
            <div class="step-header">
                <div class="step-title-and-message">
                    <div class="step-title">${title}</div>
                    <div class="step-message">${messageWithAnimation}</div>
                </div>
                <div class="step-time">${displayTime}</div>
            </div>
            ${data ? `<div class="step-data" id="step-data-${Date.now()}"></div>` : ''}
        `;
        
        this.searchSteps.appendChild(stepElement);
        
        // 데이터가 있으면 렌더링
        if (data) {
            const dataContainer = stepElement.querySelector('.step-data');
            this.renderStepData(dataContainer, data, type);
        }
        
        // 검색 과정 컨테이너 내에서만 스크롤 (페이지 전체 스크롤 방지)
        if (this.searchSteps.scrollHeight > this.searchSteps.clientHeight) {
            this.searchSteps.scrollTop = this.searchSteps.scrollHeight;
        }
    }
    
    // 긴 텍스트를 생략하여 표시하는 헬퍼 함수
    truncateText(text, maxLength = 50) {
        if (!text) return '';
        const textStr = typeof text === 'object' ? JSON.stringify(text) : String(text);
        return textStr.length > maxLength 
            ? textStr.substring(0, maxLength) + '...' 
            : textStr;
    }

    // 불완전한 JSON 데이터를 정리하는 함수
    cleanIncompleteJson(jsonStr) {
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

    renderStepData(container, data, stepType) {
        if (!container || !data) return;
        
        let content = '';
        
        // 시작 단계 데이터
        if (data.input_types) {
            content += `<div class="data-item"><strong>입력 타입:</strong> ${data.input_types.join(', ')}</div>`;
        }
        
        // 입력 처리 완료 데이터
        if (data.modalities) {
            content += `<div class="data-item"><strong>처리된 모달리티:</strong> ${data.modalities.join(', ')}</div>`;
            if (data.text_query) {
                const truncatedQuery = this.truncateText(data.text_query, 60);
                content += `<div class="data-item">
                    <strong>텍스트 쿼리:</strong>
                    <div class="text-query-display" title="${data.text_query}">
                        "${truncatedQuery}"
                    </div>
                </div>`;
            }
        }
        
        // 쿼리 확장 데이터
        if (data.expanded_queries) {
            content += `
                <div class="data-section">
                    <h4>확장된 쿼리들 (${data.expanded_queries.length}개)</h4>
                    <div class="expanded-queries">
                        ${data.expanded_queries.map((query, index) => {
                            const queryText = typeof query === 'object' ? query.query || JSON.stringify(query) : query;
                            const truncatedQuery = this.truncateText(queryText, 45);
                            return `<div class="expanded-query">
                                <div class="query-label"><strong>Query ${index + 1}:</strong></div>
                                <div class="query-content" title="${queryText}">${truncatedQuery}</div>
                            </div>`;
                        }).join('')}
                    </div>
                </div>
            `;
        }
        
        if (data.expansion_used !== undefined) {
            const expansionText = data.expansion_used ? 
                `성공 (${data.total_queries || 1}개 쿼리 생성)` : 
                '실패 (원본 쿼리만 사용)';
            content += `<div class="data-item"><strong>쿼리 확장:</strong> ${expansionText}</div>`;
        }
        
        // 확장 분석 상세 정보
        if (data.expansion_analysis) {
            const analysis = data.expansion_analysis;
            
            content += `<div class="data-section">
                <h4>쿼리 확장 분석 상세</h4>`;
            
            // 의존성 정보
            if (analysis.has_dependency !== undefined) {
                content += `<div class="data-item">
                    <strong>쿼리 의존성:</strong> ${analysis.has_dependency ? '있음' : '없음'}
                </div>`;
                
                if (analysis.dependency_reason) {
                    content += `<div class="data-item">
                        <strong>의존성 이유:</strong> ${analysis.dependency_reason}
                    </div>`;
                }
            }
            
            // 적용된 기법들
            if (analysis.applied_techniques && analysis.applied_techniques.length > 0) {
                content += `<div class="data-item">
                    <strong>적용된 기법:</strong> ${analysis.applied_techniques.join(', ')}
                </div>`;
            }
            
            // 분해된 쿼리들
            if (analysis.decomposition && analysis.decomposition.length > 0) {
                content += `<div class="sub-section">
                    <h5>쿼리 분해 (${analysis.decomposition.length}개)</h5>
                    <div class="decomposition-list">
                        ${analysis.decomposition.map((item, index) => {
                            const queryText = typeof item === 'object' ? item.query || JSON.stringify(item) : item;
                            const truncatedQuery = this.truncateText(queryText, 40);
                            return `<div class="decomposition-item">
                                <div class="query-label"><strong>${index + 1}.</strong></div>
                                <div class="query-content" title="${queryText}">${truncatedQuery}</div>
                            </div>`;
                        }).join('')}
                    </div>
                </div>`;
            }
            
            // 재작성된 쿼리들
            if (analysis.rewritten_queries && analysis.rewritten_queries.length > 0) {
                content += `<div class="sub-section">
                    <h5>재작성된 쿼리 (${analysis.rewritten_queries.length}개)</h5>
                    <div class="rewritten-list">
                        ${analysis.rewritten_queries.map((item, index) => {
                            const queryText = typeof item === 'object' ? item.query || JSON.stringify(item) : item;
                            const truncatedQuery = this.truncateText(queryText, 40);
                            return `<div class="rewritten-item">
                                <div class="query-label"><strong>${index + 1}.</strong></div>
                                <div class="query-content" title="${queryText}">${truncatedQuery}</div>
                            </div>`;
                        }).join('')}
                    </div>
                </div>`;
            }
            
            // 의미적 확장들
            if (analysis.semantic_expansions && analysis.semantic_expansions.length > 0) {
                content += `<div class="sub-section">
                    <h5>의미적 확장 (${analysis.semantic_expansions.length}개)</h5>
                    <div class="semantic-list">
                        ${analysis.semantic_expansions.map((item, index) => {
                            const queryText = typeof item === 'object' ? item.query || JSON.stringify(item) : item;
                            const truncatedQuery = this.truncateText(queryText, 40);
                            return `<div class="semantic-item">
                                <div class="query-label"><strong>${index + 1}.</strong></div>
                                <div class="query-content" title="${queryText}">${truncatedQuery}</div>
                            </div>`;
                        }).join('')}
                    </div>
                </div>`;
            }
            
            // 최종 쿼리들 (실제 사용된 것만 표시)
            // expanded_queries와 매칭하여 실제 사용된 쿼리만 표시
            if (analysis.final_queries && analysis.final_queries.length > 0 && data.expanded_queries) {
                // expanded_queries와 매칭되는 final_queries만 찾기
                const usedFinalQueries = analysis.final_queries.filter(item => {
                    const queryText = typeof item === 'object' ? item.query : item;
                    return data.expanded_queries.includes(queryText);
                });
                
                if (usedFinalQueries.length > 0) {
                    content += `<div class="sub-section">
                        <h5>최종 선별된 쿼리 (${usedFinalQueries.length}개 - 실제 검색에 사용)</h5>
                        <div class="final-queries-list">
                            ${usedFinalQueries.map((item, index) => {
                                if (typeof item === 'object' && item.query) {
                                    const truncatedQuery = this.truncateText(item.query, 40);
                                    return `<div class="final-query-item">
                                        <div class="query-text" title="${item.query}"><strong>${index + 1}.</strong> ${truncatedQuery}</div>
                                        ${item.score !== undefined ? `<div class="query-score">점수: ${item.score.toFixed(2)}</div>` : ''}
                                        ${item.reason ? `<div class="query-reason">이유: ${item.reason}</div>` : ''}
                                    </div>`;
                                } else {
                                    const queryText = typeof item === 'object' ? JSON.stringify(item) : item;
                                    const truncatedQuery = this.truncateText(queryText, 40);
                                    return `<div class="final-query-item">
                                        <div class="query-text" title="${queryText}"><strong>${index + 1}.</strong> ${truncatedQuery}</div>
                                    </div>`;
                                }
                            }).join('')}
                        </div>
                    </div>`;
                }
                
                // 사용되지 않은 쿼리들도 참고용으로 표시
                const unusedFinalQueries = analysis.final_queries.filter(item => {
                    const queryText = typeof item === 'object' ? item.query : item;
                    return !data.expanded_queries.includes(queryText);
                });
                
                if (unusedFinalQueries.length > 0) {
                    content += `<div class="sub-section">
                        <h5>후보 쿼리 (${unusedFinalQueries.length}개 - 미사용)</h5>
                        <div class="unused-queries-list">
                            ${unusedFinalQueries.map((item, index) => {
                                if (typeof item === 'object' && item.query) {
                                    const truncatedQuery = this.truncateText(item.query, 40);
                                    return `<div class="unused-query-item">
                                        <div class="query-text" title="${item.query}"><strong>${index + 1}.</strong> ${truncatedQuery}</div>
                                        ${item.score !== undefined ? `<div class="query-score">점수: ${item.score.toFixed(2)}</div>` : ''}
                                        ${item.reason ? `<div class="query-reason">이유: ${item.reason}</div>` : ''}
                                    </div>`;
                                } else {
                                    const queryText = typeof item === 'object' ? JSON.stringify(item) : item;
                                    const truncatedQuery = this.truncateText(queryText, 40);
                                    return `<div class="unused-query-item">
                                        <div class="query-text" title="${queryText}"><strong>${index + 1}.</strong> ${truncatedQuery}</div>
                                    </div>`;
                                }
                            }).join('')}
                        </div>
                    </div>`;
                }
            }
            
            // 검색 제안사항
            if (analysis.search_suggestions && analysis.search_suggestions.length > 0) {
                content += `<div class="sub-section">
                    <h5>검색 제안사항 (${analysis.search_suggestions.length}개)</h5>
                    <div class="suggestions-list">
                        ${analysis.search_suggestions.map((suggestion, index) => {
                            const suggestionText = typeof suggestion === 'object' ? suggestion.text || JSON.stringify(suggestion) : suggestion;
                            const truncatedSuggestion = this.truncateText(suggestionText, 40);
                            return `<div class="suggestion-item">
                                <div class="query-label"><strong>${index + 1}.</strong></div>
                                <div class="query-content" title="${suggestionText}">${truncatedSuggestion}</div>
                            </div>`;
                        }).join('')}
                    </div>
                </div>`;
            }
            
            content += `</div>`;
        }
        
        // 쿼리 의도 분석 데이터
        if (data.selected_element_types) {
            content += `
                <div class="data-section">
                    <h4>선택된 Element Types (${data.selected_element_types.length}개)</h4>
                    <div class="element-types">
                        ${data.selected_element_types.map(type => 
                            `<span class="element-type-tag">${type}</span>`
                        ).join('')}
                    </div>
                </div>
            `;
        }
        
        if (data.confidence !== undefined) {
            content += `<div class="data-item"><strong>신뢰도:</strong> ${(data.confidence * 100).toFixed(1)}%</div>`;
        }
        
        if (data.reasoning) {
            content += `<div class="data-item"><strong>추론:</strong> ${data.reasoning}</div>`;
        }
        
        // 특징 추출 데이터
        if (data.extraction_success) {
            const successCount = Object.values(data.extraction_success).filter(val => val === "success").length;
            content += `<div class="data-item"><strong>특징 추출 성공:</strong> ${successCount}/4 모달리티</div>`;
            
            // 이모지 설명 추가
            content += `
                <div class="extraction-legend" style="margin: 8px 0; padding: 8px; background: #f8f9fa; border-radius: 4px; font-size: 0.85em;">
                    <strong>상태 표시:</strong> 
                    <span title="특징 추출 성공">✅ 성공</span> · 
                    <span title="데이터 없어서 진행하지 않음">➖ 데이터 없음</span> · 
                    <span title="데이터는 있었지만 처리 실패">⚠️ 처리 실패</span>
                </div>
            `;
            
            Object.entries(data.extraction_success).forEach(([modality, status]) => {
                let icon;
                if (status === "success") {
                    icon = '✅'; // 성공
                } else if (status === "failed") {
                    icon = '⚠️'; // 실패 (데이터는 있었지만 처리 실패)
                } else {
                    icon = '➖'; // 데이터 없음/진행 안 함
                }
                content += `<div class="data-item">${icon} ${modality.toUpperCase()}</div>`;
            });
        }
        
        // 각 모달리티별 특징 정보 (실제 특징만 표시)
        ['text_features', 'image_features', 'video_features', 'audio_features'].forEach(featureType => {
            if (data[featureType]) {
                const modalityName = featureType.replace('_features', '').toUpperCase();
                const features = data[featureType];
                
                // 메타데이터와 실제 특징을 분리
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
                
                // 실제 특징이 있는 경우에만 표시
                if (Object.keys(actualFeatures).length > 0) {
                    content += `<div class="feature-section">
                        <h5>${modalityName} 추출 특징</h5>`;
                    
                    Object.entries(actualFeatures).forEach(([key, value], index) => {
                        // 특징 데이터를 생략하여 표시
                        let displayValue;
                        
                        if (Array.isArray(value)) {
                            displayValue = JSON.stringify(value, null, 2);
                        } else if (typeof value === 'object' && value !== null) {
                            displayValue = JSON.stringify(value, null, 2);
                        } else {
                            displayValue = String(value);
                        }
                        
                        const truncatedValue = this.truncateText(displayValue, 60);
                        
                        content += `<div class="data-item">
                            <strong>${key}:</strong>
                            <div class="feature-value-truncated" title="${displayValue}">
                                ${truncatedValue}
                            </div>
                        </div>`;
                    });
                    
                    content += `</div>`;
                }
                
                // 메타데이터는 별도 섹션으로 표시 (선택적)
                if (Object.keys(metaData).length > 0) {
                    content += `<div class="meta-section">
                        <h6>${modalityName} 메타 정보</h6>`;
                    
                    Object.entries(metaData).forEach(([key, value]) => {
                        content += `<div class="meta-item">
                            <strong>${key}:</strong> ${value}
                        </div>`;
                    });
                    
                    content += `</div>`;
                }
            }
        });
        
        // 추출된 특징의 전체 요약
        if (data.text_features || data.image_features || data.video_features || data.audio_features) {
            // 메타데이터 키 목록 (실제 특징이 아닌 메타정보)
            const metaKeys = ['keywords_count', 'entities_count', 'has_summary', 'has_classification', 
                            'has_caption', 'objects_count', 'has_description', 'scenes_count', 
                            'activities_count', 'has_transcription', 'sounds_count', 'audio_type'];
            
            const countActualFeatures = (features) => {
                if (!features) return 0;
                return Object.keys(features).filter(key => !metaKeys.includes(key)).length;
            };
            
            const totalFeatures = [
                countActualFeatures(data.text_features),
                countActualFeatures(data.image_features),
                countActualFeatures(data.video_features),
                countActualFeatures(data.audio_features)
            ].reduce((a, b) => a + b, 0);
            
            content += `
                <div class="feature-summary">
                    <h5>특징 추출 요약</h5>
                    <div class="summary-grid">
                        <div class="summary-item">
                            <strong>총 특징 수:</strong> ${totalFeatures}개
                        </div>
                        <div class="summary-item">
                            <strong>처리 시간:</strong> ${
                                data.processing_time_ms ? Math.round(data.processing_time_ms) + 'ms' :
                                data.processing_time ? Math.round(data.processing_time) + 'ms' :
                                data.took_ms ? Math.round(data.took_ms) + 'ms' :
                                data.duration_ms ? Math.round(data.duration_ms) + 'ms' :
                                '측정되지 않음'
                            }
                        </div>
                    </div>
                </div>
            `;
        }
        
        // 임베딩 데이터 (상세)
        if (data.embedding_types) {
            content += `
                <div class="data-section">
                    <h4>생성된 임베딩 (${data.embedding_types.length}개)</h4>
                    <div class="embedding-grid">
                        ${data.embedding_types.map(type => {
                            const stats = data.embedding_stats?.[type];
                            return `<div class="embedding-card">
                                <div class="embedding-header">
                                    <span class="embedding-type">${type}</span>
                                    ${stats ? `<span class="embedding-badge">${stats.dimension}D</span>` : ''}
                                </div>
                                ${stats ? `
                                    <div class="embedding-details">
                                        <div class="embedding-stat">
                                            <strong>차원:</strong> ${stats.dimension}
                                        </div>
                                        <div class="embedding-stat">
                                            <strong>벡터 크기:</strong> ${stats.vector_norm.toFixed(3)}
                                        </div>
                                        ${stats.max_value ? `
                                            <div class="embedding-stat">
                                                <strong>최대값:</strong> ${stats.max_value.toFixed(3)}
                                            </div>
                                        ` : ''}
                                        ${stats.min_value ? `
                                            <div class="embedding-stat">
                                                <strong>최소값:</strong> ${stats.min_value.toFixed(3)}
                                            </div>
                                        ` : ''}
                                    </div>
                                ` : ''}
                            </div>`;
                        }).join('')}
                    </div>
                </div>
            `;
        }
        
        // 결과 보강 데이터
        if (data.enriched_count !== undefined) {
            content += `
                <div class="data-section">
                    <h4>결과 보강 상세 정보</h4>
                    <div class="search-summary">
                        <div class="search-stat"><strong>보강된 결과:</strong> ${data.enriched_count}개</div>
                        ${data.chunk_meta_added !== undefined ? `<div class="search-stat"><strong>청크 메타 추가:</strong> ${data.chunk_meta_added}개</div>` : ''}
                        ${data.media_meta_added !== undefined ? `<div class="search-stat"><strong>미디어 메타 추가:</strong> ${data.media_meta_added}개</div>` : ''}
                    </div>
                </div>
            `;
            
            // Element types 분포 표시
            if (data.element_types_distribution) {
                content += `
                    <div class="data-section">
                        <h5>Element Type 분포</h5>
                        <div class="element-types">
                            ${Object.entries(data.element_types_distribution).map(([type, count]) => 
                                `<span class="element-type-tag">${type}: ${count}개</span>`
                            ).join('')}
                        </div>
                    </div>
                `;
            }
            
            // 보강 옵션 표시
            if (data.enrichment_options) {
                content += `
                    <div class="data-section">
                        <h5>보강 옵션</h5>
                        <div class="data-item"><strong>청크 메타데이터:</strong> ${data.enrichment_options.chunk_metadata}</div>
                        <div class="data-item"><strong>미디어 메타데이터:</strong> ${data.enrichment_options.media_metadata}</div>
                    </div>
                `;
            }
        }
        
        // 검색 실행 데이터
        if (data.total_hits !== undefined) {
            content += `
                <div class="data-section">
                    <h4>검색 실행 결과</h4>
                    <div class="search-summary">
                        <div class="search-stat"><strong>총 히트:</strong> ${data.total_hits}개</div>
                        <div class="search-stat"><strong>최고 점수:</strong> ${data.max_score?.toFixed(2) || 0}</div>
                        <div class="search-stat"><strong>반환 결과:</strong> ${data.result_count}개</div>
                        <div class="search-stat"><strong>검색 시간:</strong> ${Math.round(data.took_ms)}ms</div>
                        ${data.queries_executed ? `<div class="search-stat"><strong>실행된 쿼리:</strong> ${data.queries_executed}개</div>` : ''}
                    </div>
                </div>
            `;
            
            // 실행된 쿼리 상세 정보
            if (data.executed_queries && data.executed_queries.length > 0) {
                content += `
                    <div class="data-section">
                        <h5>실행된 쿼리 목록</h5>
                        <div class="executed-queries">
                            ${data.executed_queries.map(queryInfo => {
                                const truncatedQuery = this.truncateText(queryInfo.query, 40);
                                return `<div class="executed-query-item">
                                    <div class="executed-query-header">
                                        <strong>쿼리 ${queryInfo.index}</strong>
                                        <span class="query-weight">가중치: ${queryInfo.weight.toFixed(2)}</span>
                                    </div>
                                    <div class="executed-query-text" title="${queryInfo.query}">
                                        "${truncatedQuery}"
                                    </div>
                                </div>`;
                            }).join('')}
                        </div>
                    </div>
                `;
            }
            
            // OpenSearch 쿼리 정보
            if (data.opensearch_query) {
                const osQuery = data.opensearch_query;
                content += `
                    <div class="data-section">
                        <h5>OpenSearch 쿼리 구성</h5>
                        <div class="opensearch-info">
                            <div class="data-item"><strong>인덱스:</strong> ${osQuery.index_used}</div>
                            <div class="data-item"><strong>쿼리 타입:</strong> ${osQuery.query_type}</div>
                            <div class="data-item"><strong>검색 필드:</strong> ${osQuery.search_fields.join(', ')}</div>
                            <div class="data-item"><strong>Element Types:</strong> ${osQuery.element_types_filter.join(', ')}</div>
                            <div class="data-item"><strong>벡터 검색:</strong> ${osQuery.has_vector_search ? '활성화' : '비활성화'}</div>
                            ${osQuery.has_vector_search ? `<div class="data-item"><strong>벡터 모달리티:</strong> ${osQuery.vector_modalities.join(', ')}</div>` : ''}
                            <div class="data-item"><strong>Fuzziness:</strong> ${osQuery.fuzziness}</div>
                        </div>
                    </div>
                `;
            }
        }
        
        // 최종 결과 데이터
        if (data.results && data.search_stats) {
            content += `
                <div class="final-summary">
                    <div class="summary-stat"><strong>최종 결과:</strong> ${data.results.length}개</div>
                    <div class="summary-stat"><strong>총 처리 시간:</strong> ${Math.round(data.total_time_ms / 1000)}초</div>
                    <div class="summary-stat"><strong>처리 단계:</strong> ${data.processing_steps}단계</div>
                </div>
            `;
        }
        
        container.innerHTML = content;
    }
    
    renderFinalResults(data) {
        const searchResultsContent = document.getElementById('searchResultsContent');
        const searchResultsHeader = document.getElementById('searchResultsHeader');
        const searchResultsContainer = document.querySelector('.search-results-container');
        
        if (data && data.results) {
            // 검색 진행 상황 컨테이너를 접을 수 있도록 수정
            this.makeCollapsible();
            
            // 검색 결과 컨테이너 표시
            if (searchResultsContainer) {
                searchResultsContainer.style.display = 'block';
            }
            
            // 검색 결과 헤더 표시
            if (searchResultsHeader) {
                searchResultsHeader.style.display = 'block';
            }
            
            // 기존 검색 결과 영역에도 결과 표시
            const searchResult = {
                results: data.results,
                total_hits: data.search_stats?.total_hits || data.results.length,
                max_score: data.search_stats?.max_score || 0,
                result_count: data.results.length,
                took_ms: Math.round(data.total_time_ms) || 0,  // 총 처리 시간 추가 (정수로 반올림)
                query_analysis: data.query_analysis,
                expanded_queries: data.expanded_queries,
                element_types_used: data.query_analysis?.selected_element_types || []
            };
            
            // 먼저 직접 렌더링 시도
            this.directRenderResults(data.results);
            
            // 그 다음 기존 컨트롤러도 호출
            if (window.searchController) {
                try {
                    window.searchController.displaySearchResults(searchResult);
                } catch (error) {
                    console.error('Error calling searchController.displaySearchResults:', error);
                }
            }
            
            // 검색 히스토리 업데이트 (진행 과정 포함)
            if (window.historyManager) {
                const searchResultWithProcess = {
                    ...searchResult,
                    searchProcess: this.searchProcessData
                };
                window.historyManager.updateSearchHistoryWithResults(searchResultWithProcess);
            }
        }
    }
    
    sanitizeElementForDisplay(element) {
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
    
    directRenderResults(results) {
        // DOM 요소 찾기
        let searchResultsContent = document.getElementById('searchResultsContent');
        let searchResultsHeader = document.getElementById('searchResultsHeader');
        
        // DOM이 아직 준비되지 않았을 경우 재시도
        if (!searchResultsContent || !searchResultsHeader) {
            setTimeout(() => {
                searchResultsContent = document.getElementById('searchResultsContent');
                searchResultsHeader = document.getElementById('searchResultsHeader');
                this._performDirectRender(results, searchResultsContent, searchResultsHeader);
            }, 100);
            return;
        }
        
        this._performDirectRender(results, searchResultsContent, searchResultsHeader);
    }
    
    _performDirectRender(results, searchResultsContent, searchResultsHeader) {
        if (!searchResultsContent) {
            return;
        }
        
        // 헤더 표시
        if (searchResultsHeader) {
            searchResultsHeader.style.display = 'block';
            const searchResultsInfo = document.getElementById('searchResultsInfo');
            if (searchResultsInfo) {
                searchResultsInfo.textContent = `${results.length}개의 검색 결과`;
            }
        }
        
        // 결과 렌더링
        let resultsHtml = '';
        
        if (results && results.length > 0) {
            results.forEach((result, index) => {
                const element = result.element || result;
                const score = result.score || 0;
                const hybridScore = score.toFixed(3);
                const originalScore = result.original_score ? result.original_score.toFixed(3) : null;
                
                // content에서 origins로 시작하는 경로 감지 (이미지 판단)
                let imageUrl = null;
                let imagePath = null;
                
                if (element.content) {
                    // content에서 origins로 시작하는 경로 찾기
                    try {
                        let contentToCheck = element.content;
                        
                        // JSON 문자열인 경우 파싱 시도
                        if (typeof element.content === 'string') {
                            try {
                                const parsed = JSON.parse(element.content);
                                // 파싱된 객체에서 origins로 시작하는 값 찾기
                                for (const value of Object.values(parsed)) {
                                    if (typeof value === 'string' && value.startsWith('origins/')) {
                                        imagePath = value;
                                        break;
                                    }
                                }
                            } catch (e) {
                                // JSON이 아닌 경우 직접 확인
                                if (element.content.startsWith('origins/')) {
                                    imagePath = element.content;
                                }
                            }
                        } else if (typeof element.content === 'object') {
                            // 객체인 경우 origins로 시작하는 값 찾기
                            for (const value of Object.values(element.content)) {
                                if (typeof value === 'string' && value.startsWith('origins/')) {
                                    imagePath = value;
                                    break;
                                }
                            }
                        }
                        
                        // origins로 시작하는 경로가 있으면 프록시 URL 구성
                        if (imagePath) {
                            imageUrl = `http://internal.example.com/image/proxy/${imagePath}`;
                        }
                    } catch (e) {
                        console.warn('Failed to parse content for image path:', e);
                    }
                }
                
                // 기본 메타데이터 정보
                let basicMetaInfo = '';
                let hasDetailedMeta = false;
                
                // 청크 메타데이터 기본 정보
                if (result.chunk_meta) {
                    const chunk = result.chunk_meta;
                    basicMetaInfo += `<div class="search-result-meta-item">
                        <strong>청크:</strong> ${chunk.chunk_type} (순서: ${chunk.chunk_seq}, 요소: ${chunk.element_count}개)
                    </div>`;
                    hasDetailedMeta = true;
                }
                
                // 미디어 메타데이터 기본 정보
                if (result.media_meta) {
                    const media = result.media_meta;
                    let mediaDetails = `${media.media_type}`;
                    if (media.title) mediaDetails += ` - ${media.title}`;
                    if (media.file_size_bytes) {
                        const sizeMB = (media.file_size_bytes / 1024 / 1024).toFixed(1);
                        mediaDetails += ` (${sizeMB}MB)`;
                    }
                    if (media.duration_seconds) {
                        const duration = Math.round(media.duration_seconds);
                        mediaDetails += ` (${duration}초)`;
                    }
                    
                    basicMetaInfo += `<div class="search-result-meta-item">
                        <strong>미디어:</strong> ${mediaDetails}
                    </div>`;
                    hasDetailedMeta = true;
                }
                
                // 상세 메타데이터 토글 버튼 및 내용 (Element는 항상 표시)
                const resultId = `stream-result-${index}`;
                let detailedMetaSection = `
                    <div class="metadata-toggle">
                        <button class="metadata-button" onclick="toggleMetadata('${resultId}', 'element')">
                            <span>🔍</span> Element 상세정보
                        </button>
                        ${result.chunk_meta ? `<button class="metadata-button" onclick="toggleMetadata('${resultId}', 'chunk')">
                            <span>📄</span> 청크 상세정보
                        </button>` : ''}
                        ${result.media_meta ? `<button class="metadata-button" onclick="toggleMetadata('${resultId}', 'media')">
                            <span>🎬</span> 미디어 상세정보
                        </button>` : ''}
                    </div>
                    <div id="${resultId}-element" class="metadata-content">
                        <pre>${JSON.stringify(this.sanitizeElementForDisplay(element), null, 2)}</pre>
                    </div>
                    ${result.chunk_meta ? `<div id="${resultId}-chunk" class="metadata-content">
                        <pre>${JSON.stringify(result.chunk_meta, null, 2)}</pre>
                    </div>` : ''}
                    ${result.media_meta ? `<div id="${resultId}-media" class="metadata-content">
                        <pre>${JSON.stringify(result.media_meta, null, 2)}</pre>
                    </div>` : ''}
                `;
                
                // 점수 표시
                let scoreDisplay = `<span class="score-tag hybrid" data-tooltip="Hybrid 점수: OpenSearch 원본 점수에 쿼리별 가중치(첫 번째 쿼리 1.0, 두 번째 0.9, 세 번째 0.8...)를 적용하여 계산된 최종 점수입니다. 확장된 쿼리의 우선순위에 따라 가중치가 달라집니다.">Hybrid: ${hybridScore}</span>`;
                if (originalScore) {
                    scoreDisplay += `<span class="score-tag opensearch" data-tooltip="OpenSearch 원본 점수: 추가 처리 전 OpenSearch에서 직접 반환한 원본 relevance 점수입니다. Hybrid 점수와 비교하여 점수 변화를 확인할 수 있습니다.">OpenSearch: ${originalScore}</span>`;
                }
                
                resultsHtml += `
                    <div class="search-result-card">
                        <div class="search-result-header">
                            <div class="search-result-type">${element.element_type || 'Unknown'} (${element.modality || 'text'})</div>
                            <div class="search-result-score">${scoreDisplay}</div>
                        </div>
                        <div class="search-result-content">
                            ${imageUrl ? `
                                <div class="image-preview">
                                    <img data-image-url="${imageUrl}" data-image-path="${imagePath}" alt="Image preview" class="result-image" 
                                         style="display: none;"
                                         onerror="this.style.display='none'; this.nextElementSibling.style.display='block';"
                                         onload="this.style.display='block';">
                                    <div class="image-loading" style="padding: 20px; background: #f8f9fa; border: 1px solid #e5e7eb; text-align: center; color: #666; border-radius: 8px;">
                                        이미지 로딩 중...<br>
                                        <small>경로: ${imagePath}</small>
                                    </div>
                                    <div class="image-error" style="display: none; padding: 20px; background: #f8f9fa; border: 1px dashed #ccc; text-align: center; color: #666; border-radius: 8px;">
                                        이미지를 불러올 수 없습니다<br>
                                        <small>경로: ${imagePath}</small>
                                    </div>
                                </div>
                            ` : ''}
                            <div class="content-text">
                                ${element.content ? (typeof element.content === 'string' ? element.content.substring(0, 300) : JSON.stringify(element.content).substring(0, 300)) : 'No content'}${element.content && (typeof element.content === 'string' ? element.content.length > 300 : JSON.stringify(element.content).length > 300) ? '...' : ''}
                            </div>
                        </div>
                        ${basicMetaInfo ? `<div class="search-result-meta">${basicMetaInfo}</div>` : ''}
                        ${detailedMetaSection}
                    </div>
                `;
            });
        } else {
            resultsHtml = `
                <div class="empty-state">
                    <div class="empty-state-icon">📝</div>
                    <div>검색 결과가 없습니다.</div>
                </div>
            `;
        }
        
        searchResultsContent.innerHTML = resultsHtml;
        
        // 이미지 로딩 처리
        this.loadImages();
        
        // 검색 결과 컨테이너 표시
        const searchResultsContainer = document.querySelector('.search-results-container');
        if (searchResultsContainer) {
            searchResultsContainer.style.display = 'block';
        }
        
        // 검색 결과가 최상단에 위치하므로 페이지 상단으로 부드럽게 스크롤
        window.scrollTo({ top: 0, behavior: 'smooth' });
    }
    
    async loadImages() {
        // API 키 가져오기 (앱 설정에서)
        const apiKey = 'your-api-key-here'; // TODO: 실제 API 키로 변경 필요
        
        const imageElements = document.querySelectorAll('.result-image[data-image-url]');
        
        for (const img of imageElements) {
            const imageUrl = img.getAttribute('data-image-url');
            const imagePath = img.getAttribute('data-image-path');
            const loadingDiv = img.nextElementSibling;
            const errorDiv = loadingDiv.nextElementSibling;
            
            try {
                // 이미지 프록시 API 호출 (헤더에 API 키 포함)
                const response = await fetch(imageUrl, {
                    method: 'GET',
                    headers: {
                        'X-API-Key': apiKey
                    }
                });
                
                if (response.ok) {
                    const blob = await response.blob();
                    const objectUrl = URL.createObjectURL(blob);
                    
                    img.src = objectUrl;
                    loadingDiv.style.display = 'none';
                    
                    // 메모리 해제를 위해 이미지 로드 완료 후 URL 해제
                    img.onload = () => {
                        setTimeout(() => URL.revokeObjectURL(objectUrl), 1000);
                    };
                } else {
                    console.warn(`Failed to load image: ${response.status} ${response.statusText}`);
                    loadingDiv.style.display = 'none';
                    errorDiv.style.display = 'block';
                }
            } catch (error) {
                console.error('Image loading error:', error);
                loadingDiv.style.display = 'none';
                errorDiv.style.display = 'block';
            }
        }
    }
    
    makeCollapsible() {
        // 검색 진행 상황을 접을 수 있도록 토글 버튼 추가
        const header = this.searchProcessContainer.querySelector('.search-process-header');
        if (header && !header.querySelector('.toggle-button')) {
            const toggleButton = document.createElement('button');
            toggleButton.className = 'toggle-button';
            toggleButton.innerHTML = '검색 과정 숨기기';
            toggleButton.onclick = () => {
                const steps = this.searchSteps;
                if (steps.style.display === 'none') {
                    steps.style.display = 'block';
                    toggleButton.innerHTML = '검색 과정 숨기기';
                } else {
                    steps.style.display = 'none';
                    toggleButton.innerHTML = '검색 과정 보기';
                }
            };
            
            header.appendChild(toggleButton);
            
            // 검색 완료 후 바로 접어둠 (결과에 집중하도록)
            setTimeout(() => {
                this.searchSteps.style.display = 'none';
                toggleButton.innerHTML = '검색 과정 보기';
            }, 500);
        }
    }
    
    updateProgress() {
        const progress = Math.min((this.currentStep / this.totalSteps) * 100, 100);
        
        // 진행률 바에 펄스 효과 추가
        this.progressFill.classList.add('updating');
        setTimeout(() => {
            this.progressFill.classList.remove('updating');
        }, 600);
        
        this.progressFill.style.width = `${progress}%`;
        
        // 검색 완료 시 진행바에 completed 클래스 추가
        if (this.currentStep >= this.totalSteps) {
            this.progressFill.classList.add('completed');
        }
        
        console.log('Progress update:', this.currentStep, '/', this.totalSteps);
        
        if (this.progressText) {
            const statusText = this.currentStep === this.totalSteps 
                ? `검색 완료 (${this.totalSteps}/${this.totalSteps})`
                : `${this.currentStep}/${this.totalSteps} 단계 완료`;
            this.progressText.textContent = statusText;
        }
    }
    
    showError(message, timestamp = null) {
        console.error('Streaming error:', message);
        this.addStep('오류', message, null, 'error', timestamp);
        this.isStreaming = false;
    }
    
    stopStreaming() {
        if (this.eventSource) {
            this.eventSource.close();
            this.eventSource = null;
        }
        this.isStreaming = false;
    }
    
    reset() {
        this.stopStreaming();
        this.currentStep = 0;
        this.searchProcessData = [];
        
        // 진행바 completed 클래스 제거
        if (this.progressFill) {
            this.progressFill.classList.remove('completed');
        }
        
        this.updateProgress();
        
        if (this.searchSteps) {
            this.searchSteps.innerHTML = '';
        }
        
        if (this.searchProcessContainer) {
            this.searchProcessContainer.style.display = 'none';
        }
    }
    
    clearProcess() {
        // 진행 과정만 초기화 (결과는 유지)
        this.searchProcessData = [];
        this.currentStep = 0;
        
        // 히스토리 복원 모드 클래스 제거
        if (this.searchProcessContainer) {
            this.searchProcessContainer.classList.remove('history-restore');
        }
        
        // 진행바 completed 클래스 제거
        if (this.progressFill) {
            this.progressFill.classList.remove('completed');
        }
        
        this.updateProgress();
        
        if (this.searchSteps) {
            this.searchSteps.innerHTML = '';
        }
    }
}

// 전역 인스턴스 생성
window.streamingSearchController = new StreamingSearchController();
