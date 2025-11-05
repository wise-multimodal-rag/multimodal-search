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
    
    addToSearchHistory(query, originalText = '', isFileOnly = false, searchResult = null, searchType = null) {
        console.log('🔍 Adding to search history:', { query, originalText, isFileOnly, hasSearchResult: !!searchResult, searchType });
        
        // 모달리티 타입 결정
        const modality = this.getSearchModality(query, isFileOnly);
        
        // 검색 타입 자동 결정 (전달되지 않은 경우)
        if (!searchType) {
            searchType = this.determineSearchType(searchResult);
        }
        
        // 새로운 히스토리 항목 생성
        const historyEntry = {
            id: Date.now().toString(),
            query: query,
            originalText: originalText,
            isFileOnly: isFileOnly,
            modality: modality,
            searchType: searchType, // 검색 타입 추가 ('search_only' | 'search_with_answer')
            timestamp: Date.now(),
            searchResult: searchResult ? {
                total_hits: searchResult.total_hits || 0,
                took_ms: Math.round(searchResult.took_ms) || 0, // 소수점 제거
                element_types_used: searchResult.element_types_used || [],
                results: searchResult.results?.slice(0, 20) || [], // 최대 20개 결과만 저장
                searchProcess: searchResult.searchProcess || null, // 진행 과정 데이터 저장
                aiAnswer: searchResult.aiAnswer || null // AI 답변 데이터 저장
            } : null
        };

        // 기존 히스토리 데이터 가져오기
        let historyData = this.getSearchHistoryData();
        
        // 중복 제거: 같은 쿼리이거나 비슷한 검색 제거
        historyData = historyData.filter(item => {
            // 정확히 같은 쿼리
            if (item.query === query) {
                console.log('🗑️ Removing duplicate query:', item.query);
                return false;
            }
            
            // originalText가 같은 경우 (텍스트+파일 vs 텍스트만)
            if (item.originalText && originalText && item.originalText === originalText) {
                console.log('🗑️ Removing duplicate originalText:', item.originalText);
                return false;
            }
            
            // 비슷한 최근 검색 제거 (같은 파일 + 비슷한 시간)
            const timeDiff = Math.abs(Date.now() - item.timestamp);
            if (timeDiff < 30000) { // 30초 이내
                // 파일만 검색한 것과 텍스트+파일 검색한 것이 같은 파일을 사용하는 경우
                if (isFileOnly && !item.isFileOnly && item.query.includes(query)) {
                    console.log('🗑️ Removing file-only search replaced by text+file:', item.query);
                    return false;
                }
                if (!isFileOnly && item.isFileOnly && query.includes(item.query)) {
                    console.log('🗑️ Removing previous file-only search:', item.query);
                    return false;
                }
            }
            
            return true;
        });
        
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
    
    determineSearchType(searchResult) {
        // AI 답변이 있거나 10단계 진행 과정이 있으면 답변 생성으로 판단
        if (searchResult) {
            // AI 답변 데이터가 있는 경우
            if (searchResult.aiAnswer && searchResult.aiAnswer.final_answer) {
                return 'search_with_answer';
            }
            
            // 진행 과정에서 답변 생성 단계가 있는 경우
            if (searchResult.searchProcess && searchResult.searchProcess.length > 0) {
                const hasAnswerSteps = searchResult.searchProcess.some(step => 
                    step.step === 'answer_generation_start' || 
                    step.step === 'answer_completed' || 
                    step.step === 'draft_generated'
                );
                if (hasAnswerSteps) {
                    return 'search_with_answer';
                }
            }
        }
        
        // 기본값은 검색만 수행
        return 'search_only';
    }
    
    getSearchTypeDisplay(searchType) {
        switch (searchType) {
            case 'search_with_answer':
                return '검색+답변';
            case 'search_only':
                return '검색만';
            default:
                return '검색만';
        }
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
            
            // AI 답변 포함 여부 확인
            const hasAiAnswer = entry.searchResult && entry.searchResult.aiAnswer && entry.searchResult.aiAnswer.final_answer;
            const aiAnswerIcon = hasAiAnswer ? '<span class="ai-answer-icon" title="AI 답변 포함">🤖</span>' : '';
            
            // 검색 타입 표시 (기존 modality 대신 또는 추가로)
            const searchTypeText = this.getSearchTypeDisplay(entry.searchType || 'search_only');
            
            historyItem.innerHTML = `
                <div class="search-history-query">${entry.query} ${processIcon} ${aiAnswerIcon}</div>
                <div class="search-history-meta">
                    <div class="search-history-type">${searchTypeText}</div>
                    <div class="search-history-modality">${entry.modality}</div>
                    <div class="search-history-time">${timeText}</div>
                </div>
            `;
            
            // 클릭 동작 설정
            historyItem.onclick = () => {
                console.log('🖱️ History item clicked:', {
                    query: entry.query,
                    originalText: entry.originalText,
                    isFileOnly: entry.isFileOnly,
                    hasSearchResult: !!entry.searchResult,
                    searchResultKeys: entry.searchResult ? Object.keys(entry.searchResult) : [],
                    hasResults: !!(entry.searchResult?.results?.length),
                    hasAiAnswer: !!(entry.searchResult?.aiAnswer),
                    hasSearchProcess: !!(entry.searchResult?.searchProcess?.length)
                });
                
                if (entry.searchResult && (entry.searchResult.results?.length > 0 || entry.searchResult.aiAnswer || entry.searchResult.searchProcess?.length > 0)) {
                    console.log('✅ Restoring search results from history');
                    this.restoreSearchResult(entry.searchResult);
                } else {
                    console.log('⚠️ No search result data to restore, only setting search example');
                }
                
                // 검색창에 텍스트 복원
                if (entry.originalText) {
                    window.uiController?.setSearchExample(entry.originalText);
                } else if (!entry.isFileOnly) {
                    window.uiController?.setSearchExample(entry.query);
                }
            };
            
            this.searchHistory.appendChild(historyItem);
        });
    }
    
    restoreSearchResult(searchResult) {
        console.log('🔄 restoreSearchResult called with:', {
            hasResults: !!(searchResult?.results?.length),
            resultsCount: searchResult?.results?.length || 0, 
            hasAiAnswer: !!searchResult.aiAnswer,
            hasSearchProcess: !!searchResult.searchProcess,
            processSteps: searchResult.searchProcess?.length || 0,
            totalHits: searchResult.total_hits,
            tookMs: searchResult.took_ms
        });
        
        // 검색 결과가 있는 경우 복원
        if (searchResult.results && searchResult.results.length > 0) {
            console.log('✅ Restoring search results...');
            if (window.searchController) {
                window.searchController.displaySearchResults(searchResult);
            } else {
                console.error('❌ searchController not available');
            }
        } else {
            console.log('⚠️ No search results to restore');
        }
        
        // AI 답변도 복원 (있는 경우)
        if (searchResult.aiAnswer && searchResult.aiAnswer.final_answer) {
            console.log('🤖 Restoring AI answer from history...');
            if (window.streamingSearchController && window.streamingSearchController.renderAnswerResult) {
                window.streamingSearchController.renderAnswerResult(searchResult.aiAnswer);
            } else {
                console.error('❌ streamingSearchController.renderAnswerResult not available');
            }
        } else if (searchResult.aiAnswer) {
            console.log('⚠️ AI answer exists but no final_answer:', searchResult.aiAnswer);
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
        streamingController.progressManager.currentStep = 0;
        streamingController.searchProcessData = [...searchProcessData]; // 데이터 복사
        
        // 답변 생성 포함 여부 미리 확인
        const hasAnswerGeneration = searchProcessData.some(s => 
            s.step === 'answer_generation_start' || 
            s.step === 'answer_completed' || 
            s.step === 'draft_generated'
        );
        
        if (hasAnswerGeneration) {
            streamingController.progressManager.totalSteps = 10;
            streamingController.hasAnswerGeneration = true;
            console.log('🤖 History restore: Setting 10-step mode for answer generation');
        } else {
            streamingController.progressManager.totalSteps = 7;
            streamingController.hasAnswerGeneration = false;
            console.log('🔍 History restore: Setting 7-step mode for search only');
        }
        
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
                        streamingController.stepRenderer.addStep('검색 시작', message, data, 'info', timestamp);
                        streamingController.progressManager.currentStep = 1;
                        break;
                    case 'input_processing':
                        streamingController.stepRenderer.addStep('입력 처리 중', message, null, 'loading', timestamp);
                        break;
                    case 'input_processed':
                        streamingController.stepRenderer.addStep('입력 처리 완료', message, data, 'success', timestamp);
                        streamingController.progressManager.currentStep = 2;
                        break;
                    case 'query_analysis':
                        streamingController.stepRenderer.addStep('쿼리 분석 중', message, null, 'loading', timestamp);
                        break;
                    case 'query_analyzed':
                        streamingController.stepRenderer.addStep('쿼리 분석 완료', message, data, 'success', timestamp);
                        streamingController.progressManager.currentStep = 3;
                        break;
                    case 'feature_extraction':
                        streamingController.stepRenderer.addStep('특징 추출 중', message, null, 'loading', timestamp);
                        break;
                    case 'features_extracted':
                        streamingController.stepRenderer.addStep('특징 추출 완료', message, data, 'success', timestamp);
                        streamingController.progressManager.currentStep = 4;
                        break;
                    case 'embedding_generation':
                        streamingController.stepRenderer.addStep('임베딩 생성 중', message, null, 'loading', timestamp);
                        break;
                    case 'embeddings_generated':
                        streamingController.stepRenderer.addStep('임베딩 생성 완료', message, data, 'success', timestamp);
                        streamingController.progressManager.currentStep = 5;
                        break;
                    case 'search_execution':
                        streamingController.stepRenderer.addStep('검색 실행 중', message, null, 'loading', timestamp);
                        break;
                    case 'search_executed':
                        streamingController.stepRenderer.addStep('검색 실행 완료', message, data, 'success', timestamp);
                        streamingController.progressManager.currentStep = 6;
                        break;
                    case 'result_enrichment':
                        streamingController.stepRenderer.addStep('결과 보강 중', message, null, 'loading', timestamp);
                        break;
                    case 'result_enriched':
                        streamingController.stepRenderer.addStep('결과 보강 완료', message, data, 'success', timestamp);
                        streamingController.progressManager.currentStep = 7;
                        break;
                    case 'completed':
                        streamingController.stepRenderer.addStep('검색 완료', message, data, 'success', timestamp);
                        break;
                        
                    // 답변 생성 단계들 추가
                    case 'answer_generation_start':
                        streamingController.stepRenderer.addStep('답변 생성 시작', message, data, 'info', timestamp);
                        streamingController.progressManager.currentStep = 8;
                        break;
                    case 'draft_generation':
                        streamingController.stepRenderer.addStep('답변 초안 생성 중', message, null, 'loading', timestamp);
                        break;
                    case 'draft_generated':
                        // 메타데이터를 포함한 데이터 객체 생성
                        const draftMetadata = data && MetadataCreator.createAnswerMetadata ? {
                            ...data,
                            _metadata: MetadataCreator.createAnswerMetadata(data, '초안 생성')
                        } : data;
                        streamingController.stepRenderer.addStep('답변 초안 생성 완료', message, draftMetadata, 'success', timestamp);
                        streamingController.progressManager.currentStep = 9;
                        break;
                    case 'reflection':
                        streamingController.stepRenderer.addStep('답변 품질 검토 중', message, null, 'loading', timestamp);
                        break;
                    case 'reflection_completed':
                        // 메타데이터를 포함한 데이터 객체 생성
                        const reflectionMetadata = data && MetadataCreator.createReflectionMetadata ? {
                            ...data,
                            _metadata: MetadataCreator.createReflectionMetadata(data)
                        } : data;
                        streamingController.stepRenderer.addStep('답변 품질 검토 완료', message, reflectionMetadata, 'success', timestamp);
                        break;
                    case 'regenerating':
                        streamingController.stepRenderer.addStep('답변 재생성 중', message, null, 'loading', timestamp);
                        break;
                    case 'answer_completed':
                        // 메타데이터를 포함한 데이터 객체 생성
                        const finalMetadata = data && MetadataCreator.createFinalAnswerMetadata ? {
                            ...data,
                            _metadata: MetadataCreator.createFinalAnswerMetadata(data)
                        } : data;
                        streamingController.stepRenderer.addStep('답변 생성 완료', message, finalMetadata, 'success', timestamp);
                        streamingController.progressManager.currentStep = 10;
                        // 답변 결과 렌더링
                        if (data && streamingController.resultRenderer.renderAnswerResult) {
                            streamingController.resultRenderer.renderAnswerResult(data, streamingController.searchProcessData);
                        }
                        break;
                    case 'answer_generation_error':
                        streamingController.stepRenderer.addStep('답변 생성 실패', message, data, 'error', timestamp);
                        break;
                        
                    case 'error':
                        streamingController.stepRenderer.addStep('오류 발생', message, data, 'error', timestamp);
                        break;
                    case 'file_read_failed':
                        streamingController.stepRenderer.addStep('파일 처리 실패', message, data, 'warning', timestamp);
                        break;
                    default:
                        console.log('Unknown step in restore:', step);
                        streamingController.stepRenderer.addStep(step, message, data, 'info', timestamp);
                        break;
                }
                
                streamingController.progressManager.updateProgress();
                
                // 마지막 단계 완료 후 접기
                if (index === searchProcessData.length - 1) {
                    setTimeout(() => {
                        // 최고 단계 찾기 (이미 totalSteps는 설정됨)
                        const maxStep = Math.max(...searchProcessData.map(s => {
                            switch(s.step) {
                                case 'start': return 1;
                                case 'input_processed': return 2;
                                case 'query_analyzed': return 3;
                                case 'features_extracted': return 4;
                                case 'embeddings_generated': return 5;
                                case 'search_executed': return 6;
                                case 'result_enriched': return 7;
                                case 'answer_generation_start': return 8;
                                case 'draft_generated': return 9;
                                case 'answer_completed': return 10;
                                default: return 0;
                            }
                        }));
                        streamingController.progressManager.currentStep = Math.max(maxStep, streamingController.progressManager.currentStep);
                        
                        console.log(`🏁 History restore completed: ${streamingController.progressManager.currentStep}/${streamingController.progressManager.totalSteps}`);
                        streamingController.progressManager.updateProgress();
                        streamingController.progressManager.makeCollapsible();
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
            // 기존 searchResult가 없으면 새로 생성, 있으면 업데이트
            if (!historyData[0].searchResult) {
                historyData[0].searchResult = {};
            }
            
            // 가장 최근 항목에 검색 결과 업데이트 (기존 데이터 유지)
            const currentResult = historyData[0].searchResult;
            
            // 새로운 데이터로 업데이트 (있는 경우만)
            if (searchResult.total_hits !== undefined) currentResult.total_hits = searchResult.total_hits || 0;
            if (searchResult.took_ms !== undefined) currentResult.took_ms = Math.round(searchResult.took_ms) || 0;
            if (searchResult.element_types_used !== undefined) currentResult.element_types_used = searchResult.element_types_used || [];
            if (searchResult.results !== undefined) currentResult.results = searchResult.results?.slice(0, 20) || [];
            if (searchResult.searchProcess !== undefined) currentResult.searchProcess = searchResult.searchProcess;
            if (searchResult.aiAnswer !== undefined) currentResult.aiAnswer = searchResult.aiAnswer;
            
            console.log('✅ Updated latest history entry with results:', {
                totalHits: currentResult.total_hits,
                resultsCount: currentResult.results?.length || 0,
                hasSearchProcess: !!(currentResult.searchProcess?.length),
                processSteps: currentResult.searchProcess?.length || 0,
                hasAiAnswer: !!currentResult.aiAnswer,
                query: historyData[0].query
            });
            
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
    
    // AI 답변 데이터를 검색 히스토리에 추가하는 함수
    updateSearchHistoryWithAnswer(answerData) {
        console.log('🤖 Updating search history with AI answer:', {
            hasAnswer: !!answerData?.final_answer,
            answerLength: answerData?.final_answer?.length || 0,
            attempts: answerData?.total_attempts || 0
        });
        
        // localStorage에서 히스토리 데이터 가져오기
        let historyData = this.getSearchHistoryData();
        
        if (historyData.length > 0 && answerData) {
            // 가장 최근 항목에 AI 답변 데이터 추가
            if (!historyData[0].searchResult) {
                historyData[0].searchResult = {};
            }
            
            historyData[0].searchResult.aiAnswer = {
                final_answer: answerData.final_answer,
                processing_time_ms: answerData.processing_time_ms,
                total_attempts: answerData.total_attempts,
                success: answerData.success,
                generation_attempts: answerData.generation_attempts?.slice(0, 5) || [], // 최대 5개 시도만 저장
                search_context: answerData.search_context
            };
            
            // LLM 답변 생성의 경우 전체 처리 시간을 took_ms에 업데이트
            if (answerData.processing_time_ms && answerData.processing_time_ms > 0) {
                // 기존 검색 시간과 AI 답변 생성 시간을 합산
                const existingSearchTime = historyData[0].searchResult.took_ms || 0;
                historyData[0].searchResult.took_ms = Math.round(existingSearchTime + answerData.processing_time_ms);
                console.log(`📊 Updated total processing time: ${historyData[0].searchResult.took_ms}ms (search: ${existingSearchTime}ms + answer: ${Math.round(answerData.processing_time_ms)}ms)`);
            }
            
            // AI 답변이 추가되면 searchType을 'search_with_answer'로 업데이트
            historyData[0].searchType = 'search_with_answer';
            console.log('📝 Updated searchType to search_with_answer');
            
            console.log('✅ Updated latest history entry with AI answer');
            
            // 저장
            this.saveSearchHistoryData(historyData);
            console.log('✅ Search history with AI answer saved');
            
            // UI 업데이트
            this.updateSearchHistoryUI();
            console.log('✅ Search history UI updated with AI answer');
        } else {
            console.log('❌ No history data found to update with AI answer');
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