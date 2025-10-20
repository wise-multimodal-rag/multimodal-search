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
        this.totalSteps = 7;
        this.isStreaming = false;
        this.searchProcessData = []; // 검색 진행 과정 데이터 저장
    }
    
    async startStreamingSearch(formData) {
        if (this.isStreaming) {
            console.log('Search already in progress');
            return;
        }
        
        this.isStreaming = true;
        
        // 검색 과정 데이터 초기화
        this.searchProcessData = [];
        
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
            
            while (true) {
                const { done, value } = await reader.read();
                
                if (done) {
                    console.log('Streaming completed');
                    break;
                }
                
                const chunk = decoder.decode(value);
                const lines = chunk.split('\n');
                
                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        try {
                            const data = line.slice(6); // 'data: ' 제거
                            if (data.trim()) {
                                const stepResult = JSON.parse(data);
                                this.handleStepResult(stepResult);
                            }
                        } catch (error) {
                            console.error('Failed to parse streaming data:', error, line);
                        }
                    }
                }
            }
            
        } catch (error) {
            console.error('Streaming search failed:', error);
            this.showError(`스트리밍 검색 실패: ${error.message}`);
        } finally {
            this.isStreaming = false;
        }
    }
    
    handleStepResult(stepResult) {
        const { step, message, data, timestamp, error } = stepResult;
        
        console.log('Step result:', stepResult);
        console.log('Current step before:', this.currentStep, 'New step:', step);
        
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
                
            case 'query_analysis':
                this.addStep('쿼리 분석 중', message, null, 'loading', timestamp);
                break;
                
            case 'query_analyzed':
                this.updateLastLoadingStep('쿼리 분석 완료', message, data, 'success', timestamp);
                this.currentStep = 3;
                break;
                
            case 'feature_extraction':
                this.addStep('특징 추출 중', message, null, 'loading', timestamp);
                break;
                
            case 'features_extracted':
                this.updateLastLoadingStep('특징 추출 완료', message, data, 'success', timestamp);
                this.currentStep = 4;
                break;
                
            case 'embedding_generation':
                this.addStep('임베딩 생성 중', message, null, 'loading', timestamp);
                break;
                
            case 'embeddings_generated':
                this.updateLastLoadingStep('임베딩 생성 완료', message, data, 'success', timestamp);
                this.currentStep = 5;
                break;
                
            case 'search_execution':
                this.addStep('검색 실행 중', message, null, 'loading', timestamp);
                break;
                
            case 'search_executed':
                this.updateLastLoadingStep('검색 실행 완료', message, data, 'success', timestamp);
                this.currentStep = 6;
                break;
                
            case 'result_enrichment':
                this.addStep('결과 보강 중', message, null, 'loading', timestamp);
                break;
                
            case 'result_enriched':
                this.updateLastLoadingStep('결과 보강 완료', message, data, 'success', timestamp);
                this.currentStep = 7;
                break;
                
            case 'completed':
                this.addStep('검색 완료', message, data, 'success', timestamp);
                // currentStep은 이미 result_enriched에서 7로 설정됨
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
                content += `<div class="data-item"><strong>텍스트 쿼리:</strong> "${data.text_query}"</div>`;
            }
        }
        
        // 쿼리 분석 데이터
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
        
        if (data.expanded_queries) {
            content += `
                <div class="data-section">
                    <h4>확장된 쿼리들 (${data.expanded_queries.length}개)</h4>
                    <div class="expanded-queries">
                        ${data.expanded_queries.map((query, index) => 
                            `<div class="expanded-query">
                                <strong>Query ${index + 1}:</strong> ${typeof query === 'object' ? query.query || JSON.stringify(query) : query}
                            </div>`
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
            const successCount = Object.values(data.extraction_success).filter(Boolean).length;
            content += `<div class="data-item"><strong>특징 추출 성공:</strong> ${successCount}/4 모달리티</div>`;
            
            Object.entries(data.extraction_success).forEach(([modality, success]) => {
                const icon = success ? '✅' : '❌';
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
                        // 디버깅: entities 데이터 확인
                        if (key === 'entities') {
                            console.log('Entities data:', value);
                            console.log('Entities JSON length:', JSON.stringify(value).length);
                        }
                        
                        let previewValue = value;
                        let fullValue = value;
                        let needsToggle = false;
                        
                        // 값의 타입에 따라 표시 방식 조정
                        if (Array.isArray(value)) {
                            fullValue = JSON.stringify(value, null, 2);
                            const allItems = value.map(item => {
                                if (typeof item === 'object' && item !== null) {
                                    return typeof item === 'string' ? item : JSON.stringify(item);
                                }
                                return String(item);
                            });
                            previewValue = `[${allItems.join(', ')}]`;
                            
                            // 디버깅: 배열 처리 정보
                            if (key === 'entities') {
                                console.log('Entities preview:', previewValue);
                                console.log('Entities full:', fullValue);
                            }
                            
                            // 전체 JSON 문자열이 매우 긴 경우에만 토글 적용 (300자로 낮춤)
                            if (JSON.stringify(value).length > 300) {
                                needsToggle = true;
                                if (key === 'entities') {
                                    console.log('Entities will use toggle (length:', JSON.stringify(value).length, ')');
                                }
                            }
                        } else if (typeof value === 'object' && value !== null) {
                            fullValue = JSON.stringify(value, null, 2);
                            
                            // 객체가 단순하고 작으면 바로 표시
                            const jsonString = JSON.stringify(value);
                            if (jsonString.length <= 200 && Object.keys(value).length <= 5) {
                                previewValue = jsonString;
                            } else {
                                previewValue = `{${Object.keys(value).length}개 속성}`;
                                needsToggle = true;
                            }
                        } else if (typeof value === 'string' && value.length > 300) {
                            // 긴 텍스트만 토글 처리 (300자 이상)
                            fullValue = value;
                            previewValue = `${value.substring(0, 150)}... (총 ${value.length}자)`;
                            needsToggle = true;
                        } else {
                            previewValue = String(value);
                        }
                        
                        const featureId = `feature-${modalityName.toLowerCase()}-${index}`;
                        
                        content += `<div class="data-item">
                            <strong>${key}:</strong> 
                            <span class="feature-value">${previewValue}</span>
                            ${needsToggle ? `
                                <button class="feature-toggle-btn" onclick="toggleFeatureValue('${featureId}')">
                                    <span class="toggle-icon">▼</span> 전체보기
                                </button>
                                <div id="${featureId}" class="feature-full-value" style="display: none;">
                                    <pre>${fullValue}</pre>
                                </div>
                            ` : ''}
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
            const totalFeatures = [
                data.text_features ? Object.keys(data.text_features).length : 0,
                data.image_features ? Object.keys(data.image_features).length : 0,
                data.video_features ? Object.keys(data.video_features).length : 0,
                data.audio_features ? Object.keys(data.audio_features).length : 0
            ].reduce((a, b) => a + b, 0);
            
            content += `
                <div class="feature-summary">
                    <h5>특징 추출 요약</h5>
                    <div class="summary-grid">
                        <div class="summary-item">
                            <strong>총 특징 수:</strong> ${totalFeatures}개
                        </div>
                        <div class="summary-item">
                            <strong>처리 시간:</strong> ${data.processing_time_ms ? Math.round(data.processing_time_ms) + 'ms' : '-'}
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
        
        // 검색 실행 데이터
        if (data.total_hits !== undefined) {
            content += `
                <div class="search-summary">
                    <div class="search-stat"><strong>총 히트:</strong> ${data.total_hits}개</div>
                    <div class="search-stat"><strong>최고 점수:</strong> ${data.max_score?.toFixed(2) || 0}</div>
                    <div class="search-stat"><strong>반환 결과:</strong> ${data.result_count}개</div>
                    <div class="search-stat"><strong>검색 시간:</strong> ${Math.round(data.took_ms)}ms</div>
                    ${data.queries_executed ? `<div class="search-stat"><strong>실행된 쿼리:</strong> ${data.queries_executed}개</div>` : ''}
                </div>
            `;
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
        console.log('renderFinalResults called with data:', data);
        
        if (data.results) {
            console.log('Results found:', data.results.length, 'items');
            
            // 검색 진행 상황 컨테이너를 접을 수 있도록 수정
            this.makeCollapsible();
            
            // 검색 결과 컨테이너 표시
            const searchResultsContainer = document.querySelector('.search-results-container');
            if (searchResultsContainer) {
                searchResultsContainer.style.display = 'block';
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
            
            console.log('Calling displaySearchResults with:', searchResult);
            
            // 먼저 직접 렌더링 시도
            this.directRenderResults(data.results);
            
            // 그 다음 기존 컨트롤러도 호출 (중복 방지를 위해)
            if (window.searchController) {
                try {
                    window.searchController.displaySearchResults(searchResult);
                } catch (error) {
                    console.error('Error calling searchController.displaySearchResults:', error);
                }
            }
            
            // 검색 히스토리 업데이트 (진행 과정 포함)
            if (window.historyManager) {
                console.log('Updating history with process data:', this.searchProcessData.length, 'steps');
                const searchResultWithProcess = {
                    ...searchResult,
                    searchProcess: this.searchProcessData // 진행 과정 데이터 추가
                };
                console.log('searchResultWithProcess:', searchResultWithProcess);
                window.historyManager.updateSearchHistoryWithResults(searchResultWithProcess);
            }
        } else {
            console.log('No results found in data:', data);
        }
    }
    
    directRenderResults(results) {
        console.log('Direct rendering results:', results);
        
        // 검색 결과 컨테이너 찾기
        const searchResultsContent = document.getElementById('searchResultsContent');
        const searchResultsHeader = document.getElementById('searchResultsHeader');
        
        if (!searchResultsContent) {
            console.error('searchResultsContent not found');
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
                
                // 상세 메타데이터 토글 버튼 및 내용
                let detailedMetaSection = '';
                if (hasDetailedMeta) {
                    const resultId = `stream-result-${index}`;
                    detailedMetaSection = `
                        <div class="metadata-toggle">
                            ${result.chunk_meta ? `<button class="metadata-button" onclick="toggleMetadata('${resultId}', 'chunk')">
                                <span>📄</span> 청크 상세정보
                            </button>` : ''}
                            ${result.media_meta ? `<button class="metadata-button" onclick="toggleMetadata('${resultId}', 'media')">
                                <span>🎬</span> 미디어 상세정보
                            </button>` : ''}
                        </div>
                        ${result.chunk_meta ? `<div id="${resultId}-chunk" class="metadata-content">
                            <pre>${JSON.stringify(result.chunk_meta, null, 2)}</pre>
                        </div>` : ''}
                        ${result.media_meta ? `<div id="${resultId}-media" class="metadata-content">
                            <pre>${JSON.stringify(result.media_meta, null, 2)}</pre>
                        </div>` : ''}
                    `;
                }
                
                // 점수 표시
                let scoreDisplay = `<span class="score-tag hybrid" data-tooltip="Hybrid 점수: OpenSearch의 BM25 텍스트 검색과 벡터 유사도 검색을 결합한 하이브리드 점수입니다. 높을수록 쿼리와 더 관련이 높습니다.">Hybrid: ${hybridScore}</span>`;
                if (originalScore) {
                    scoreDisplay += `<span class="score-tag opensearch" data-tooltip="OpenSearch 원본 점수: BM25 텍스트 유사도와 벡터 코사인 유사도를 결합한 하이브리드 검색 점수입니다. 높을수록 쿼리와 더 관련이 높습니다.">OpenSearch: ${originalScore}</span>`;
                }
                
                resultsHtml += `
                    <div class="search-result-card">
                        <div class="search-result-header">
                            <div class="search-result-type">${element.element_type || 'Unknown'} (${element.modality || 'text'})</div>
                            <div class="search-result-score">${scoreDisplay}</div>
                        </div>
                        <div class="search-result-content">
                            ${element.content ? element.content.substring(0, 300) : 'No content'}${element.content && element.content.length > 300 ? '...' : ''}
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
        
        // 검색 결과가 최상단에 위치하므로 페이지 상단으로 부드럽게 스크롤
        window.scrollTo({ top: 0, behavior: 'smooth' });
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
        this.updateProgress();
        
        if (this.searchSteps) {
            this.searchSteps.innerHTML = '';
        }
    }
}

// 전역 인스턴스 생성
window.streamingSearchController = new StreamingSearchController();

// 특징 값 토글 함수
window.toggleFeatureValue = function(featureId) {
    const fullValueDiv = document.getElementById(featureId);
    const toggleBtn = document.querySelector(`button[onclick="toggleFeatureValue('${featureId}')"]`);
    const toggleIcon = toggleBtn.querySelector('.toggle-icon');
    
    if (fullValueDiv.style.display === 'none') {
        fullValueDiv.style.display = 'block';
        toggleIcon.textContent = '▲';
        toggleBtn.childNodes[1].textContent = ' 숨기기';
    } else {
        fullValueDiv.style.display = 'none';
        toggleIcon.textContent = '▼';
        toggleBtn.childNodes[1].textContent = ' 전체보기';
    }
};