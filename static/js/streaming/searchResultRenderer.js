/**
 * 검색 결과 및 AI 답변 렌더링 관리자
 */
class SearchResultRenderer {
    constructor() {
        this.apiKey = 'your-api-key-here'; // TODO: 실제 API 키로 변경 필요
    }
    
    renderFinalResults(data, searchProcessData, progressManager) {
        const searchResultsContent = document.getElementById('searchResultsContent');
        const searchResultsHeader = document.getElementById('searchResultsHeader');
        const searchResultsContainer = document.querySelector('.search-results-container');
        
        if (data && data.results) {
            // 검색 진행 상황 컨테이너를 접을 수 있도록 수정
            progressManager.makeCollapsible();
            
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
                results: data.results || [],
                total_hits: data.search_stats?.total_hits || 0,
                max_score: data.search_stats?.max_score || 0,
                result_count: (data.results || []).length,
                took_ms: Math.round(data.total_time_ms || data.search_stats?.took_ms || 0) || 0,
                query_analysis: data.query_analysis,
                expanded_queries: data.expanded_queries,
                element_types_used: data.query_analysis?.selected_element_types || [],
                message: data.message
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
                    searchProcess: searchProcessData
                };
                window.historyManager.updateSearchHistoryWithResults(searchResultWithProcess);
            }
        }
    }
    
    renderAnswerResult(data, searchProcessData) {
        console.log('🎯 renderAnswerResult called with data:', data);
        
        if (data && data.final_answer) {
            console.log('✅ Final answer found, rendering AI section');
        } else {
            console.log('❌ No final answer in data:', data);
        }
        
        if (data && data.final_answer) {
            // AI 답변을 전용 레이어에 표시
            const aiAnswerContainer = document.getElementById('aiAnswerContainer');
            const aiAnswerContent = document.getElementById('aiAnswerContent');
            const aiAnswerHeader = document.getElementById('aiAnswerHeader');
            
            if (aiAnswerContainer && aiAnswerContent && aiAnswerHeader) {
                const answerId = `answer-${Date.now()}`;
                
                // 기존 헤더 구조를 Preview 버튼이 있는 구조로 업데이트
                aiAnswerHeader.innerHTML = `
                    <div class="answer-header-left">
                        <div class="ai-answer-title">생성된 답변</div>
                        <div class="ai-answer-info">검색 결과를 기반으로 생성된 AI 답변입니다</div>
                    </div>
                    <div class="answer-header-right">
                        <button class="preview-toggle-btn" onclick="toggleAnswerPreview('${answerId}')">
                            📖 Preview
                        </button>
                    </div>
                `;
                
                // 답변 내용 추가
                aiAnswerContent.innerHTML = `
                    <div class="answer-text-container">
                        <div class="answer-text plain-text" id="${answerId}-plain">${TextFormatter.formatAnswerText(data.final_answer)}</div>
                        <div class="answer-text markdown-preview" id="${answerId}-preview" style="display: none;">${TextFormatter.renderMarkdown(data.final_answer)}</div>
                    </div>
                `;
                // AI 답변 레이어 표시
                aiAnswerContainer.style.display = 'flex';
            }
            
            // AI 답변 데이터를 검색 히스토리에 저장
            if (window.historyManager && window.historyManager.updateSearchHistoryWithAnswer) {
                window.historyManager.updateSearchHistoryWithAnswer(data);
            }
            
            // 전체 프로세스 데이터(8-10단계 포함)로 히스토리 업데이트
            if (window.historyManager && searchProcessData && searchProcessData.length > 0) {
                // 기존 검색 결과에 전체 프로세스 데이터 업데이트
                const updatedSearchResult = {
                    searchProcess: searchProcessData  // 1-10단계 전체 포함
                };
                window.historyManager.updateSearchHistoryWithResults(updatedSearchResult);
            }
        }
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
                resultsHtml += this.renderSingleResult(result, index);
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
    
    renderSingleResult(result, index) {
        const element = result.element || result;
        const score = result.score || 0;
        const hybridScore = score.toFixed(3);
        const originalScore = result.original_score ? result.original_score.toFixed(3) : null;
        
        // 이미지 경로 추출
        const imagePath = SearchDataProcessor.extractImagePath(element.content);
        const imageUrl = imagePath ? `http://internal.example.com/image/proxy/${imagePath}` : null;
        
        // 기본 메타데이터 정보
        const basicMetaInfo = this.renderBasicMetaInfo(result);
        
        // 상세 메타데이터 토글 버튼 및 내용
        const resultId = `stream-result-${index}`;
        const detailedMetaSection = this.renderDetailedMetaSection(result, resultId, element);
        
        // 점수 표시
        const scoreDisplay = this.renderScoreDisplay(hybridScore, originalScore);
        
        return `
            <div class="search-result-card">
                <div class="search-result-header">
                    <div class="search-result-type">${element.element_type || 'Unknown'} (${element.modality || 'text'})</div>
                    <div class="search-result-score">${scoreDisplay}</div>
                </div>
                <div class="search-result-content">
                    ${imageUrl ? this.renderImagePreview(imageUrl, imagePath) : ''}
                    <div class="content-text">
                        ${element.content ? (typeof element.content === 'string' ? SearchDataProcessor.cleanContentIndentation(element.content) : JSON.stringify(element.content, null, 2)) : 'No content'}
                    </div>
                </div>
                ${basicMetaInfo ? `<div class="search-result-meta">${basicMetaInfo}</div>` : ''}
                ${detailedMetaSection}
            </div>
        `;
    }
    
    renderBasicMetaInfo(result) {
        let basicMetaInfo = '';
        
        // 청크 메타데이터 기본 정보
        if (result.chunk_meta) {
            const chunk = result.chunk_meta;
            basicMetaInfo += `<div class="search-result-meta-item">
                <strong>청크:</strong> ${chunk.chunk_type} (순서: ${chunk.chunk_seq}, 요소: ${chunk.element_count}개)
            </div>`;
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
        }
        
        return basicMetaInfo;
    }
    
    renderDetailedMetaSection(result, resultId, element) {
        return `
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
                <pre>${JSON.stringify(SearchDataProcessor.sanitizeElementForDisplay(element), null, 2)}</pre>
            </div>
            ${result.chunk_meta ? `<div id="${resultId}-chunk" class="metadata-content">
                <pre>${JSON.stringify(result.chunk_meta, null, 2)}</pre>
            </div>` : ''}
            ${result.media_meta ? `<div id="${resultId}-media" class="metadata-content">
                <pre>${JSON.stringify(result.media_meta, null, 2)}</pre>
            </div>` : ''}
        `;
    }
    
    renderScoreDisplay(hybridScore, originalScore) {
        let scoreDisplay = `<span class="score-tag hybrid" data-tooltip="Hybrid 점수: OpenSearch 원본 점수에 쿼리별 가중치(첫 번째 쿼리 1.0, 두 번째 0.9, 세 번째 0.8...)를 적용하여 계산된 최종 점수입니다. 확장된 쿼리의 우선순위에 따라 가중치가 달라집니다.">Hybrid: ${hybridScore}</span>`;
        if (originalScore) {
            scoreDisplay += `<span class="score-tag opensearch" data-tooltip="OpenSearch 원본 점수: 추가 처리 전 OpenSearch에서 직접 반환한 원본 relevance 점수입니다. Hybrid 점수와 비교하여 점수 변화를 확인할 수 있습니다.">OpenSearch: ${originalScore}</span>`;
        }
        return scoreDisplay;
    }
    
    renderImagePreview(imageUrl, imagePath) {
        return `
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
        `;
    }
    
    async loadImages() {
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
                        'X-API-Key': this.apiKey
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
}

// 전역 사용을 위한 export
window.SearchResultRenderer = SearchResultRenderer;
console.log('✅ SearchResultRenderer loaded');