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
        const hasFiles = window.fileHandler && window.fileHandler.hasFiles();
        
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
        window.uiController.showLoading();

        try {
            // Prepare form data
            const formData = new FormData();
            if (message) {
                formData.append('text_query', message);
            }
            
            // Add files if selected
            if (window.fileHandler) {
                const selectedFiles = window.fileHandler.getSelectedFiles();
                if (selectedFiles.image) {
                    formData.append('image', selectedFiles.image);
                }
                if (selectedFiles.video) {
                    formData.append('video', selectedFiles.video);
                }
                if (selectedFiles.audio) {
                    formData.append('audio', selectedFiles.audio);
                }
            }
            
            formData.append('max_results', document.getElementById('maxResults').value);
            formData.append('include_chunk_meta', document.getElementById('includeChunkMeta').checked);
            formData.append('include_media_meta', document.getElementById('includeMediaMeta').checked);

            // Send search request
            const response = await fetch('/api/v1/search/multimodal', {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const searchResult = await response.json();
            
            // Debug: Log the response to see original_score
            console.log('Search result:', searchResult);
            if (searchResult.results && searchResult.results.length > 0) {
                console.log('First result:', searchResult.results[0]);
                console.log('Original score:', searchResult.results[0].original_score);
            }
            
            // Update search history with results
            if (window.historyManager) {
                window.historyManager.updateSearchHistoryWithResults(searchResult);
            }
            
            // Display search results
            this.displaySearchResults(searchResult);

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
    
    buildHistoryText(message, hasFiles) {
        if (message && hasFiles) {
            const fileNames = window.fileHandler.getFileNames();
            const fileCount = fileNames.length;
            if (fileCount === 1) {
                return `${message} (+${fileNames[0]})`;
            } else {
                return `${message} (+${fileCount}개: ${fileNames.join(', ')})`;
            }
        } else if (message) {
            return message;
        } else if (hasFiles) {
            const fileNames = window.fileHandler.getFileNames();
            return fileNames.join(', ');
        }
        return '';
    }
    
    displaySearchResults(searchResult) {
        // 검색 결과 헤더 업데이트
        window.uiController.updateSearchResultsHeader(searchResult);
        
        // 검색 결과 내용 생성
        let resultsHtml = '';

        if (searchResult.results && searchResult.results.length > 0) {
            searchResult.results.forEach((result, index) => {
                const element = result.element;
                const rrfScore = result.score.toFixed(6);
                const originalScore = result.original_score ? result.original_score.toFixed(6) : null;
                
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
                    const resultId = `result-${index}`;
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
                
                let scoreDisplay = `<span class="score-tag rrf" data-tooltip="RRF (Reciprocal Rank Fusion): 여러 검색 알고리즘의 결과를 결합한 점수입니다. 텍스트 검색과 벡터 검색 결과를 융합하여 더 정확한 순위를 제공합니다.">RRF: ${rrfScore}</span>`;
                if (originalScore) {
                    scoreDisplay += `<span class="score-tag opensearch" data-tooltip="OpenSearch 원본 점수: BM25 텍스트 유사도와 벡터 코사인 유사도를 결합한 하이브리드 검색 점수입니다. 높을수록 쿼리와 더 관련이 높습니다.">OpenSearch: ${originalScore}</span>`;
                }
                
                resultsHtml += `
                    <div class="search-result-card">
                        <div class="search-result-header">
                            <div class="search-result-type">${element.element_type} (${element.modality})</div>
                            <div class="search-result-score">${scoreDisplay}</div>
                        </div>
                        <div class="search-result-content">
                            ${element.content.substring(0, 300)}${element.content.length > 300 ? '...' : ''}
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