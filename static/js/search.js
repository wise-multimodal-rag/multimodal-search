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
    
    async sendMessage() {
        const message = this.messageInput.value.trim();
        const hasFiles = (window.hasFiles && window.hasFiles()) || (window.fileHandler && window.fileHandler.hasFiles());
        
        if (!message && !hasFiles) return;

        // Check if this looks like a conversational query
        if (message && window.uiController.checkConversationalQuery(message)) {
            window.uiController.clearInput();
            window.uiController.showConversationalGuide();
            return;
        }

        // 검색 히스토리에 추가
        const historyText = this.buildHistoryText(message, hasFiles);
        const originalText = message;
        const isFileOnly = !message && hasFiles;
        
        if (historyText && window.historyManager) {
            window.historyManager.addToSearchHistory(historyText, originalText, isFileOnly, null);
        }
        
        window.uiController.clearInput();
        window.uiController.disableSearchButton();
        
        // 기존 검색 결과 숨기기
        if (this.searchResultsHeader) {
            this.searchResultsHeader.style.display = 'none';
        }
        this.searchResultsContent.innerHTML = '';

        try {
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

            // Start streaming search
            if (window.streamingSearchController) {
                await window.streamingSearchController.startStreamingSearch(formData);
                
                // Update search history with streaming results
                if (window.historyManager) {
                    // Note: This will be updated once streaming completes
                    // The streaming controller will handle the final results
                }
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
            window.uiController.showError(error);
        } finally {
            window.uiController.enableSearchButton();
        }
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
        if (message && hasFiles) {
            const fileNames = this.getFileNames();
            const fileCount = fileNames.length;
            if (fileCount === 1) {
                return `${message} (+${fileNames[0]})`;
            } else {
                return `${message} (+${fileCount}개: ${fileNames.join(', ')})`;
            }
        } else if (message) {
            return message;
        } else if (hasFiles) {
            const fileNames = this.getFileNames();
            return fileNames.join(', ');
        }
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
        window.uiController.updateSearchResultsHeader(searchResult);
        
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
function sendMessage() {
    if (window.searchController) {
        window.searchController.sendMessage();
    }
}

// window 객체에도 명시적으로 할당
window.sendMessage = sendMessage;