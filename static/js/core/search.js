/**
 * 메인 검색 로직 및 API 통신
 */
class SearchController {
    constructor() {
        this.searchResultsContent = document.getElementById('searchResultsContent');
        this.searchResultsHeader = document.getElementById('searchResultsHeader');
        this.searchResultsInfo = document.getElementById('searchResultsInfo');
        this.messageInput = document.getElementById('messageInput');
    }
    
    async performSearchOnly() {
        console.log('🚀 SearchController.performSearchOnly called');
        
        // 중복 호출 방지
        if (this._isProcessing) {
            console.warn('⚠️ performSearchOnly already in progress, ignoring');
            return;
        }
        this._isProcessing = true;
        
        const formData = this.prepareFormData('search_only');
        if (!formData) {
            this._isProcessing = false;
            return;
        }

        this.startSearchProcess();
        
        // 검색만 수행 시 AI 답변 레이어 숨김
        const aiAnswerContainer = document.getElementById('aiAnswerContainer');
        if (aiAnswerContainer) {
            aiAnswerContainer.style.display = 'none';
        }

        try {
            // 기존 스트리밍 검색 수행
            if (window.streamingSearchController) {
                await window.streamingSearchController.startStreamingSearch(formData);
            } else {
                // Fallback to regular search if streaming is not available
                await this.fallbackToRegularSearch(formData);
            }

            // Clear files after successful search
            if (window.fileHandler) {
                window.fileHandler.clearFiles();
            }

        } catch (error) {
            console.error('Search failed:', error);
            if (window.uiController && typeof window.uiController.showError === 'function') {
                window.uiController.showError(error);
            }
        } finally {
            this._isProcessing = false;
            if (window.uiController && typeof window.uiController.enableSearchButton === 'function') {
                window.uiController.enableSearchButton();
            }
            // 검색 완료 시 버튼 상태 복원
            this.restoreButtonState();
        }
    }

    async performSearchAndGenerate() {
        console.log('🚀 SearchController.performSearchAndGenerate called');
        console.log('🔍 Input value before prepareFormData:', this.messageInput ? this.messageInput.value : 'NO_INPUT_ELEMENT');
        
        // 중복 호출 방지
        if (this._isProcessing) {
            console.warn('⚠️ performSearchAndGenerate already in progress, ignoring');
            return;
        }
        this._isProcessing = true;
        
        const formData = this.prepareFormData('search_with_answer');
        console.log('formData prepared:', !!formData);
        if (!formData) {
            console.log('No formData, returning early');
            return;
        }

        this.startSearchProcess();

        try {
            // 통합 스트리밍 API 사용 - 답변 생성 파라미터 추가
            formData.append('generate_answer', 'true');
            formData.append('temperature', '0.7');
            formData.append('max_retries', '2');
            
            // 기존 스트리밍 검색 로직 재사용
            if (window.streamingSearchController) {
                await window.streamingSearchController.startStreamingSearch(formData);
            } else {
                throw new Error('Streaming controller not available');
            }

            // Clear files after successful search
            if (window.fileHandler) {
                window.fileHandler.clearFiles();
            }

        } catch (error) {
            console.error('Answer generation failed:', error);
            if (window.uiController && typeof window.uiController.showError === 'function') {
                window.uiController.showError(`답변 생성 실패: ${error.message}`);
            }
        } finally {
            this._isProcessing = false;
            if (window.uiController && typeof window.uiController.enableSearchButton === 'function') {
                window.uiController.enableSearchButton();
            }
            // 검색 완료 시 버튼 상태 복원
            this.restoreButtonState();
        }
    }

    prepareFormData(searchType = 'search_only') {
        // 입력값을 미리 저장 (다른 스크립트에서 클리어될 가능성 대비)
        const messageInputValue = this.messageInput ? this.messageInput.value : '';
        const message = messageInputValue.trim();
        const hasFiles = (window.hasFiles && window.hasFiles()) || (window.fileHandler && window.fileHandler.hasFiles());
        
        console.log('🔍 prepareFormData debug:', {
            messageInputValue: messageInputValue,
            messageTrimmed: message,
            hasFiles: hasFiles,
            messageInputElement: this.messageInput,
            messageInputExists: !!this.messageInput
        });
        
        if (!message && !hasFiles) return null;

        // Check if this looks like a conversational query
        try {
            if (message && window.uiController && typeof window.uiController.checkConversationalQuery === 'function') {
                if (window.uiController.checkConversationalQuery(message)) {
                    if (typeof window.uiController.clearInput === 'function') {
                        window.uiController.clearInput();
                    }
                    if (typeof window.uiController.showConversationalGuide === 'function') {
                        window.uiController.showConversationalGuide();
                    }
                    return null;
                }
            }
        } catch (error) {
            console.warn('uiController method call failed:', error);
            // Continue with normal flow
        }

        // 검색 히스토리에 추가
        const historyText = this.buildHistoryText(message, hasFiles);
        const originalText = message;
        const isFileOnly = !message && hasFiles;
        
        console.log('🔍 Debug search history values:', {
            message: message,
            hasFiles: hasFiles,
            historyText: historyText,
            originalText: originalText,
            isFileOnly: isFileOnly,
            searchType: searchType
        });
        
        if (historyText && window.historyManager) {
            window.historyManager.addToSearchHistory(historyText, originalText, isFileOnly, null, searchType);
        }

        // Prepare form data for streaming
        const formData = new FormData();
        if (message) {
            formData.append('text_query', message);
        }
        
        // Add files if selected
        const selectedFiles = window.tempSelectedFiles || (window.fileHandler && window.fileHandler.getSelectedFiles()) || (window.getSelectedFiles && window.getSelectedFiles());
        
        if (selectedFiles) {
            if (selectedFiles.image) {
                formData.append('image', selectedFiles.image);
            }
            if (selectedFiles.video) {
                formData.append('video', selectedFiles.video);
            }
            if (selectedFiles.audio) {
                formData.append('audio', selectedFiles.audio);
            }
            if (selectedFiles.text_file) {
                formData.append('text_file', selectedFiles.text_file);
            }
        }
        
        formData.append('max_results', document.getElementById('maxResults').value);
        formData.append('include_chunk_meta', document.getElementById('includeChunkMeta').checked);
        formData.append('include_media_meta', document.getElementById('includeMediaMeta').checked);

        return formData;
    }

    startSearchProcess() {
        // 버튼 상태 변경: 검색/생성 버튼 숨김, 중지 버튼 표시
        document.getElementById('searchButton').style.display = 'none';
        document.getElementById('generateButton').style.display = 'none';
        document.getElementById('stopButton').style.display = 'inline-block';
        
        if (window.uiController) {
            if (typeof window.uiController.clearInput === 'function') {
                window.uiController.clearInput();
            }
            if (typeof window.uiController.disableSearchButton === 'function') {
                window.uiController.disableSearchButton();
            }
        }
        
        // 기존 검색 결과 숨기기
        if (this.searchResultsHeader) {
            this.searchResultsHeader.style.display = 'none';
        }
        this.searchResultsContent.innerHTML = '';
    }
    
    async fallbackToRegularSearch(formData) {
        // Original search logic as fallback
        const response = await fetch('/api/v1/search/multimodal', {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const searchResult = await response.json();
        
        // Update search history with results
        if (window.historyManager) {
            window.historyManager.updateSearchHistoryWithResults(searchResult);
        }
        
        // Display search results
        this.displaySearchResults(searchResult);
    }
    
    buildHistoryText(message, hasFiles) {
        console.log('🔍 buildHistoryText called with:', { message, hasFiles });
        
        if (message && hasFiles) {
            const fileNames = this.getFileNames();
            const fileCount = fileNames.length;
            console.log('🔍 Case: message + hasFiles, fileNames:', fileNames);
            if (fileCount === 1) {
                return `${message} (+${fileNames[0]})`;
            } else {
                return `${message} (+${fileCount}개: ${fileNames.join(', ')})`;
            }
        } else if (message) {
            console.log('🔍 Case: message only');
            return message;
        } else if (hasFiles) {
            const fileNames = this.getFileNames();
            console.log('🔍 Case: hasFiles only, fileNames:', fileNames);
            return fileNames.join(', ');
        }
        console.log('🔍 Case: empty result');
        return '';
    }
    
    getFileNames() {
        const selectedFiles = window.tempSelectedFiles || (window.fileHandler && window.fileHandler.getSelectedFiles()) || (window.getSelectedFiles && window.getSelectedFiles()) || {};
        
        return Object.entries(selectedFiles)
            .filter(([type, file]) => file !== null)
            .map(([type, file]) => {
                const fileName = file.name;
                if (fileName.length > 25) {
                    const ext = fileName.split('.').pop();
                    const name = fileName.substring(0, 20);
                    return `${name}...${ext}`;
                }
                return fileName;
            });
    }

    // 콘텐츠의 불필요한 들여쓰기를 제거하되 줄바꿈은 유지하는 함수
    cleanContentIndentation(content) {
        if (!content) return '';
        
        // 앞뒤 공백 제거
        const trimmed = content.trim();
        
        // 각 줄의 앞쪽 공백을 제거하되 줄바꿈은 유지
        const lines = trimmed.split('\n');
        const cleanedLines = lines.map(line => line.trim());
        
        return cleanedLines.join('\n');
    }
    
    restoreButtonState() {
        // 검색 완료 시 버튼 상태 복원
        document.getElementById('searchButton').style.display = 'inline-block';
        document.getElementById('generateButton').style.display = 'inline-block';
        document.getElementById('stopButton').style.display = 'none';
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
    
    displaySearchResults(searchResult) {
        // 검색 결과 헤더 업데이트
        if (window.uiController && searchResult) {
            window.uiController.updateSearchResultsHeader(searchResult);
        }
        
        // 검색 결과 내용 생성
        let resultsHtml = '';

        if (searchResult.results && searchResult.results.length > 0) {
            searchResult.results.forEach((result, index) => {
                const element = result.element;
                const hybridScore = result.score.toFixed(3);
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
                
                // 상세 메타데이터 토글 버튼 및 내용 (Element는 항상 표시)
                const resultId = `result-${index}`;
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
                
                let scoreDisplay = `<span class="score-tag hybrid" data-tooltip="Hybrid 점수: OpenSearch 원본 점수에 쿼리별 가중치(첫 번째 쿼리 1.0, 두 번째 0.9, 세 번째 0.8...)를 적용하여 계산된 최종 점수입니다. 확장된 쿼리의 우선순위에 따라 가중치가 달라집니다.">Hybrid: ${hybridScore}</span>`;
                if (originalScore) {
                    scoreDisplay += `<span class="score-tag opensearch" data-tooltip="OpenSearch 원본 점수: 추가 처리 전 OpenSearch에서 직접 반환한 원본 relevance 점수입니다. Hybrid 점수와 비교하여 점수 변화를 확인할 수 있습니다.">OpenSearch: ${originalScore}</span>`;
                }
                
                resultsHtml += `
                    <div class="search-result-card">
                        <div class="search-result-header">
                            <div class="search-result-type">${element.element_type} (${element.modality})</div>
                            <div class="search-result-score">${scoreDisplay}</div>
                        </div>
                        <div class="search-result-content">
                            <div class="content-text">
                                ${element.content ? this.cleanContentIndentation(element.content) : 'No content'}
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
        
        this.searchResultsContent.innerHTML = resultsHtml;
    }
    
}

// 전역 인스턴스 생성
window.searchController = new SearchController();

// HTML에서 호출할 수 있도록 전역 함수 정의
function performSearch() {
    if (window.searchController) {
        window.searchController.performSearchOnly();
    }
}

function performSearchAndGenerate() {
    console.log('performSearchAndGenerate called');
    if (window.searchController) {
        console.log('searchController exists, calling performSearchAndGenerate');
        window.searchController.performSearchAndGenerate();
    } else {
        console.error('searchController not found');
    }
}

// 중지 버튼 클릭 시 호출될 함수
function stopSearch() {
    if (window.streamingSearchController) {
        window.streamingSearchController.stopSearch();
        
        // 검색 중지 시 버튼 상태 복원
        document.getElementById('searchButton').style.display = 'inline-block';
        document.getElementById('generateButton').style.display = 'inline-block';
        document.getElementById('stopButton').style.display = 'none';
    }
}

// window 객체에도 명시적으로 할당
window.performSearch = performSearch;
window.performSearchAndGenerate = performSearchAndGenerate;
window.stopSearch = stopSearch;