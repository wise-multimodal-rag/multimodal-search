/**
 * 검색 히스토리 관리 기능
 */
class HistoryManager {
    constructor() {
        this.searchHistory = document.getElementById('searchHistory');
        this.maxHistoryItems = 10;
    }
    
    getSearchHistoryData() {
        try {
            const data = localStorage.getItem('searchHistory');
            return data ? JSON.parse(data) : [];
        } catch (e) {
            console.error('Failed to load search history:', e);
            return [];
        }
    }
    
    saveSearchHistoryData(historyData) {
        try {
            // 최대 10개까지만 저장
            const limitedData = historyData.slice(0, this.maxHistoryItems);
            localStorage.setItem('searchHistory', JSON.stringify(limitedData));
        } catch (e) {
            console.error('Failed to save search history:', e);
        }
    }
    
    addToSearchHistory(query, originalText = '', isFileOnly = false, searchResult = null) {
        console.log('🔍 Adding to search history:', { query, originalText, isFileOnly, hasSearchResult: !!searchResult });
        
        // 모달리티 타입 결정
        const modality = this.getSearchModality(query, isFileOnly);
        
        // 새로운 히스토리 항목 생성
        const historyEntry = {
            id: Date.now().toString(),
            query: query,
            originalText: originalText,
            isFileOnly: isFileOnly,
            modality: modality,
            timestamp: Date.now(),
            searchResult: searchResult ? {
                total_hits: searchResult.total_hits,
                took_ms: Math.round(searchResult.took_ms) || 0, // 소수점 제거
                element_types_used: searchResult.element_types_used,
                results: searchResult.results?.slice(0, 20) || [], // 최대 20개 결과만 저장
                searchProcess: searchResult.searchProcess || null // 진행 과정 데이터 저장
            } : null
        };

        // 기존 히스토리 데이터 가져오기
        let historyData = this.getSearchHistoryData();
        
        // 같은 쿼리 제거
        historyData = historyData.filter(item => item.query !== query);
        
        // 새 항목을 맨 앞에 추가
        historyData.unshift(historyEntry);
        
        // 저장
        this.saveSearchHistoryData(historyData);
        console.log('✅ Search history saved, total items:', historyData.length);
        
        // UI 업데이트
        this.updateSearchHistoryUI();
        console.log('✅ Search history UI updated');
    }
    
    getSearchModality(query, isFileOnly) {
        const messageInput = document.getElementById('messageInput');
        const message = messageInput.value.trim();
        const hasFiles = window.fileHandler && window.fileHandler.hasFiles();
        
        if (!message && !hasFiles) {
            return '';
        }
        
        const fileTypes = [];
        if (window.fileHandler) {
            const selectedFiles = window.fileHandler.getSelectedFiles();
            if (selectedFiles.image) fileTypes.push('이미지');
            if (selectedFiles.video) fileTypes.push('비디오');
            if (selectedFiles.audio) fileTypes.push('오디오');
        }
        
        if (message && hasFiles) {
            return `텍스트+${fileTypes.join('+')}`;
        } else if (message) {
            return '텍스트';
        } else if (hasFiles) {
            return fileTypes.join('+');
        }
        
        return '';
    }
    
    updateSearchHistoryUI() {
        const historyData = this.getSearchHistoryData();
        
        // 기존 히스토리 아이템 제거 (placeholder 제외)
        const existingItems = this.searchHistory.querySelectorAll('.search-history-item');
        existingItems.forEach(item => item.remove());
        
        if (historyData.length === 0) {
            // 히스토리가 없으면 placeholder 표시
            if (!this.searchHistory.querySelector('.search-history-placeholder')) {
                const placeholder = document.createElement('div');
                placeholder.className = 'search-history-placeholder';
                placeholder.style.cssText = 'padding: 20px; text-align: center; color: #9ca3af; font-size: 13px;';
                placeholder.textContent = '검색 히스토리가 여기에 표시됩니다';
                this.searchHistory.appendChild(placeholder);
            }
            return;
        }
        
        // placeholder 제거
        const placeholder = this.searchHistory.querySelector('.search-history-placeholder');
        if (placeholder) {
            placeholder.remove();
        }
        
        // 히스토리 아이템 생성
        historyData.forEach(entry => {
            const historyItem = document.createElement('div');
            historyItem.className = 'search-history-item';
            historyItem.dataset.historyId = entry.id;
            
            const timeText = entry.searchResult && entry.searchResult.took_ms !== undefined 
                ? `${Math.round(entry.searchResult.took_ms)}ms` 
                : '-';
            
            // 진행 과정 데이터가 있는지 확인
            const hasProcessData = entry.searchResult && entry.searchResult.searchProcess && entry.searchResult.searchProcess.length > 0;
            const processIcon = hasProcessData ? '<span class="process-icon" title="검색 진행 과정 포함">⚙️</span>' : '';
            
            historyItem.innerHTML = `
                <div class="search-history-query">${entry.query} ${processIcon}</div>
                <div class="search-history-meta">
                    <div class="search-history-modality">${entry.modality}</div>
                    <div class="search-history-time">${timeText}</div>
                </div>
            `;
            
            // 클릭 동작 설정
            if (entry.isFileOnly) {
                // 파일만 검색한 경우 결과 복원만 가능
                historyItem.onclick = () => {
                    if (entry.searchResult) {
                        this.restoreSearchResult(entry.searchResult);
                    }
                };
            } else if (entry.originalText) {
                // 텍스트 + 파일 조합인 경우
                historyItem.onclick = () => {
                    if (entry.searchResult) {
                        this.restoreSearchResult(entry.searchResult);
                        window.uiController.setSearchExample(entry.originalText);
                    } else {
                        window.uiController.setSearchExample(entry.originalText);
                    }
                };
            } else {
                // 텍스트만 검색한 경우
                historyItem.onclick = () => {
                    if (entry.searchResult) {
                        this.restoreSearchResult(entry.searchResult);
                        window.uiController.setSearchExample(entry.query);
                    } else {
                        window.uiController.setSearchExample(entry.query);
                    }
                };
            }
            
            this.searchHistory.appendChild(historyItem);
        });
    }
    
    restoreSearchResult(searchResult) {
        console.log('restoreSearchResult called with:', searchResult);
        
        // 검색 결과 복원
        if (window.searchController) {
            window.searchController.displaySearchResults(searchResult);
        }
        
        // 검색 진행 과정도 복원 (있는 경우)
        console.log('Checking searchProcess:', searchResult.searchProcess);
        console.log('streamingSearchController available:', !!window.streamingSearchController);
        
        if (searchResult.searchProcess && searchResult.searchProcess.length > 0) {
            if (window.streamingSearchController) {
                console.log('Restoring search process with', searchResult.searchProcess.length, 'steps');
                this.restoreSearchProcess(searchResult.searchProcess);
            } else {
                console.log('StreamingSearchController not ready, waiting...');
                // 컨트롤러가 준비될 때까지 대기 (최대 3초)
                this.waitForStreamingController(searchResult.searchProcess, 0);
            }
        } else {
            console.log('No search process to restore:', {
                hasProcess: !!searchResult.searchProcess,
                processLength: searchResult.searchProcess?.length || 0,
                hasController: !!window.streamingSearchController
            });
        }
        
        // 페이지 상단으로 스크롤 (검색 결과가 최상단에 위치)
        window.scrollTo({ top: 0, behavior: 'smooth' });
    }
    
    waitForStreamingController(searchProcessData, attempts) {
        const maxAttempts = 30; // 3초 (100ms * 30)
        
        if (attempts >= maxAttempts) {
            console.error('StreamingSearchController not available after waiting');
            return;
        }
        
        if (window.streamingSearchController) {
            console.log('StreamingSearchController ready after', attempts * 100, 'ms');
            this.restoreSearchProcess(searchProcessData);
        } else {
            setTimeout(() => {
                this.waitForStreamingController(searchProcessData, attempts + 1);
            }, 100);
        }
    }
    
    restoreSearchProcess(searchProcessData) {
        console.log('restoreSearchProcess called with', searchProcessData.length, 'steps');
        const streamingController = window.streamingSearchController;
        
        if (!streamingController) {
            console.error('StreamingSearchController not found');
            return;
        }
        
        // 검색 진행 상황 컨테이너 초기화 (숨기지 않고)
        console.log('Initializing search process container for history restore');
        streamingController.searchSteps.innerHTML = '';
        streamingController.currentStep = 0;
        streamingController.searchProcessData = [...searchProcessData]; // 데이터 복사
        
        // 히스토리 복원 모드 클래스 추가
        streamingController.searchProcessContainer.classList.add('history-restore');
        
        // 컨테이너 표시
        streamingController.searchProcessContainer.style.display = 'block';
        
        // 저장된 각 단계를 순차적으로 복원
        let stepCount = 0;
        searchProcessData.forEach((stepData, index) => {
            setTimeout(() => {
                const { step, message, data, timestamp } = stepData;
                
                // 단계별 처리 (handleStepResult의 로직을 재사용) - CSS로 loading 단계가 숨겨짐
                switch (step) {
                    case 'start':
                        streamingController.addStep('검색 시작', message, data, 'info', timestamp);
                        streamingController.currentStep = 1;
                        break;
                    case 'input_processing':
                        streamingController.addStep('입력 처리 중', message, null, 'loading', timestamp);
                        break;
                    case 'input_processed':
                        streamingController.addStep('입력 처리 완료', message, data, 'success', timestamp);
                        streamingController.currentStep = 2;
                        break;
                    case 'query_analysis':
                        streamingController.addStep('쿼리 분석 중', message, null, 'loading', timestamp);
                        break;
                    case 'query_analyzed':
                        streamingController.addStep('쿼리 분석 완료', message, data, 'success', timestamp);
                        streamingController.currentStep = 3;
                        break;
                    case 'feature_extraction':
                        streamingController.addStep('특징 추출 중', message, null, 'loading', timestamp);
                        break;
                    case 'features_extracted':
                        streamingController.addStep('특징 추출 완료', message, data, 'success', timestamp);
                        streamingController.currentStep = 4;
                        break;
                    case 'embedding_generation':
                        streamingController.addStep('임베딩 생성 중', message, null, 'loading', timestamp);
                        break;
                    case 'embeddings_generated':
                        streamingController.addStep('임베딩 생성 완료', message, data, 'success', timestamp);
                        streamingController.currentStep = 5;
                        break;
                    case 'search_execution':
                        streamingController.addStep('검색 실행 중', message, null, 'loading', timestamp);
                        break;
                    case 'search_executed':
                        streamingController.addStep('검색 실행 완료', message, data, 'success', timestamp);
                        streamingController.currentStep = 6;
                        break;
                    case 'result_enrichment':
                        streamingController.addStep('결과 보강 중', message, null, 'loading', timestamp);
                        break;
                    case 'result_enriched':
                        streamingController.addStep('결과 보강 완료', message, data, 'success', timestamp);
                        streamingController.currentStep = 7;
                        break;
                    case 'completed':
                        streamingController.addStep('검색 완료', message, data, 'success', timestamp);
                        break;
                    case 'error':
                        streamingController.addStep('오류 발생', message, data, 'error', timestamp);
                        break;
                    case 'file_read_failed':
                        streamingController.addStep('파일 처리 실패', message, data, 'warning', timestamp);
                        break;
                    default:
                        console.log('Unknown step in restore:', step);
                        streamingController.addStep(step, message, data, 'info', timestamp);
                        break;
                }
                
                streamingController.updateProgress();
                
                // 마지막 단계 완료 후 접기
                if (index === searchProcessData.length - 1) {
                    setTimeout(() => {
                        // 완료된 검색이므로 currentStep을 totalSteps로 설정하여 8/8 표시
                        streamingController.currentStep = streamingController.totalSteps;
                        streamingController.updateProgress();
                        streamingController.makeCollapsible();
                    }, 500);
                }
            }, index * 100); // 각 단계를 100ms 간격으로 표시
        });
    }
    
    updateSearchHistoryWithResults(searchResult) {
        console.log('📊 Updating search history with results:', { 
            total_hits: searchResult?.total_hits, 
            took_ms: searchResult?.took_ms,
            results_count: searchResult?.results?.length 
        });
        
        // localStorage에서 히스토리 데이터 가져오기
        let historyData = this.getSearchHistoryData();
        console.log('📋 Current history data length:', historyData.length);
        
        if (historyData.length > 0) {
            // 가장 최근 항목에 검색 결과 추가
            historyData[0].searchResult = {
                total_hits: searchResult.total_hits,
                took_ms: Math.round(searchResult.took_ms) || 0, // 소수점 제거
                element_types_used: searchResult.element_types_used,
                results: searchResult.results?.slice(0, 20) || [], // 최대 20개 결과만 저장
                searchProcess: searchResult.searchProcess || null // 진행 과정 데이터 저장
            };
            
            console.log('✅ Updated latest history entry with results');
            
            // 저장
            this.saveSearchHistoryData(historyData);
            console.log('✅ Search history with results saved');
            
            // UI 업데이트
            this.updateSearchHistoryUI();
            console.log('✅ Search history UI updated with results');
        } else {
            console.log('❌ No history data found to update with results');
        }
    }
    
    initialize() {
        // 페이지 로드 시 히스토리 복원
        this.updateSearchHistoryUI();
        
        // 디버깅용: 히스토리 데이터 확인
        window.debugHistory = () => {
            const historyData = this.getSearchHistoryData();
            console.log('Current history data:', historyData);
            historyData.forEach((entry, index) => {
                console.log(`Entry ${index}:`, entry.query);
                console.log('- Has searchResult:', !!entry.searchResult);
                console.log('- Has searchProcess:', !!(entry.searchResult?.searchProcess));
                console.log('- Process steps:', entry.searchResult?.searchProcess?.length || 0);
            });
        };
    }
}

// 전역 인스턴스 생성
window.historyManager = new HistoryManager();