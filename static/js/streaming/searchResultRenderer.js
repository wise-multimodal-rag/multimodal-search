/**
 * 검색 결과 및 AI 답변 렌더링 관리자
 */
class SearchResultRenderer {
    constructor() {
        // API 키는 더 이상 필요하지 않음 (서버에서 인증 처리)
        // 필요한 경우 appConfig에서 가져오기
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
                            Text
                        </button>
                    </div>
                `;
                
                // 답변 내용 추가 - 기본 뷰는 마크다운, Text 뷰는 원문
                aiAnswerContent.innerHTML = `
                    <div class="answer-text-container">
                        <div class="answer-text markdown-preview" id="${answerId}-plain">${TextFormatter.renderMarkdown(data.final_answer)}</div>
                        <div class="answer-text raw-text" id="${answerId}-preview" style="display: none;">${TextFormatter.formatRawText(data.final_answer)}</div>
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
        console.log('🎭 Starting to render', results.length, 'results');
        
        if (results && results.length > 0) {
            results.forEach((result, index) => {
                console.log('🎯 Processing result', index, 'of', results.length);
                const singleResultHtml = this.renderSingleResult(result, index);
                resultsHtml += singleResultHtml;
                console.log('✅ Result', index, 'HTML added, total length now:', resultsHtml.length);
            });
        } else {
            resultsHtml = `
                <div class="empty-state">
                    <div class="empty-state-icon">📝</div>
                    <div>검색 결과가 없습니다.</div>
                </div>
            `;
        }
        
        console.log('🎪 Setting innerHTML - Final HTML length:', resultsHtml.length);
        console.log('🎪 HTML preview (first 500 chars):', resultsHtml.substring(0, 500));
        
        searchResultsContent.innerHTML = resultsHtml;
        
        console.log('✅ innerHTML set successfully');
        console.log('🔍 Checking DOM for image elements...');
        const imageElements = document.querySelectorAll('.image-container');
        const imgTags = document.querySelectorAll('img');
        console.log('  - Found .image-container elements:', imageElements.length);
        console.log('  - Found img tags:', imgTags.length);
        
        // 미디어 로딩 처리
        console.log('🎬 Starting media loading...');
        this.loadImages();
        this.loadVideos();
        
        // 검색 결과 컨테이너 표시
        const searchResultsContainer = document.querySelector('.search-results-container');
        if (searchResultsContainer) {
            searchResultsContainer.style.display = 'block';
        }
        
        // 검색 결과가 최상단에 위치하므로 페이지 상단으로 부드럽게 스크롤
        window.scrollTo({ top: 0, behavior: 'smooth' });
    }
    
    renderSingleResult(result, index) {
        console.log('🚀 === STARTING renderSingleResult for index', index, '===');
        
        const element = result.element || result;
        const score = result.score || 0;
        const hybridScore = score.toFixed(3);
        const originalScore = result.original_score ? result.original_score.toFixed(3) : null;
        
        // 디버깅: element 구조 확인
        console.log('🔍 Element analysis:', {
            element_type: element.element_type,
            modality: element.modality,
            content_type: element.content_type,
            content_preview: element.content ? element.content.substring(0, 100) : 'NO CONTENT',
            content_length: element.content ? element.content.length : 0,
            is_origin: element.element_type === 'origin',
            has_content: !!element.content,
            fullElement: element
        });
        
        // content_type과 modality 기반 미디어 처리
        let mediaContent = '';
        let shouldShowContent = true;
        
        // STEP 1: 조건 분기 분석
        console.log('📋 Condition check:');
        console.log('  - element.element_type === "origin"?', element.element_type === 'origin');
        console.log('  - element.content_type === "uri"?', element.content_type === 'uri');
        console.log('  - element.modality === "image"?', element.modality === 'image');
        
        // origin 타입이면 무조건 이미지로 처리
        if (element.element_type === 'origin') {
            console.log('✅ CONDITION MATCHED: origin type detected');
            console.log('🖼️ ORIGIN TYPE DETECTED - Processing as image:', element.content);
            
            // URL 인코딩 처리
            let imageUrl = element.content;
            try {
                // 이미 인코딩된 URL인지 확인하고, 아니면 인코딩
                const urlParts = imageUrl.split('/');
                const encodedParts = urlParts.map((part, index) => {
                    // 프로토콜과 도메인 부분은 인코딩하지 않음 (처음 3개 부분)
                    if (index < 3) return part;
                    // 나머지 부분은 인코딩 (한글 파일명 처리)
                    return encodeURIComponent(decodeURIComponent(part));
                });
                imageUrl = encodedParts.join('/');
                console.log('📝 Original URL:', element.content);
                console.log('📝 Encoded URL:', imageUrl);
            } catch (e) {
                console.warn('URL encoding failed, using original:', e);
            }
            
            // STEP 2: HTML 생성
            console.log('🛠️ Generating image HTML with URL:', imageUrl);
            
            mediaContent = `
                <div class="image-container" style="margin: 15px 0; padding: 10px; border: 2px solid #4CAF50; border-radius: 8px; background: #f9f9f9;">
                    <p style="color: #4CAF50; font-weight: bold; margin-bottom: 10px;">🖼️ Origin 이미지:</p>
                    <img src="${imageUrl}" 
                         alt="Origin Image" 
                         style="max-width: 100%; height: auto; display: block; border-radius: 5px; border: 1px solid #ddd;"
                         onload="console.log('✅ Direct image loaded successfully:', this.src)"
                         onerror="console.error('❌ Direct image load failed:', this.src); this.style.display='none'; this.nextElementSibling.style.display='block';">
                    <div style="display: none; padding: 10px; background:#ffebee; border: 1px solid #f44336; border-radius: 5px; color: #d32f2f;">
                        ❌ 이미지를 불러올 수 없습니다<br>
                        <small style="word-break: break-all;">${element.content}</small><br><br>
                        <a href="${imageUrl}" target="_blank" style="color: #1976d2; text-decoration: none;">🔗 새 탭에서 열기</a>
                    </div>
                </div>
            `;
            shouldShowContent = false;
            
            console.log('✅ Image HTML generated successfully, length:', mediaContent.length);
            console.log('📝 Generated HTML preview:', mediaContent.substring(0, 200) + '...');
        }
        // content_type이 uri이고 modality가 image인 경우
        else if (element.content_type === 'uri' && element.modality === 'image') {
            console.log('🖼️ Rendering image URI (uri+image):', element.content);
            mediaContent = this.renderImagePreview(element.content, element.content);
            shouldShowContent = false; // URI는 별도로 표시하지 않음
        }
        // content_type이 uri이고 modality가 video인 경우
        else if (element.content_type === 'uri' && element.modality === 'video') {
            console.log('🎥 Rendering video URI (uri+video):', element.content);
            mediaContent = this.renderVideoPreview(element.content, element.content);
            shouldShowContent = false; // URI는 별도로 표시하지 않음
        }
        // 3. 기존 방식: 이미지 URL 감지
        else if (SearchDataProcessor.isImageElement(element)) {
            const detectedUrl = SearchDataProcessor.detectImageUrl(element.content) || 
                                SearchDataProcessor.detectMediaUrl(element.content);
            if (detectedUrl) {
                mediaContent = this.renderImagePreview(detectedUrl, element.content);
            } else {
                // 기존 이미지 경로 추출 방식으로 폴백
                const imagePath = SearchDataProcessor.extractImagePath(element.content);
                // 서버 설정 IMAGE_PROXY_URL (/api/config/client 응답은 data 로 감싸져 들어온다)
                const proxyBase = (window.appConfig?.get('data.media.imageProxyUrl') || '').replace(/\/+$/, '');
                if (imagePath && proxyBase) {
                    const imageUrl = `${proxyBase}/${imagePath}`;
                    mediaContent = this.renderImagePreview(imageUrl, element.content);
                }
            }
        }
        // 4. 비디오 요소 처리
        else if (SearchDataProcessor.isVideoElement(element)) {
            const detectedUrl = SearchDataProcessor.detectMediaUrl(element.content);
            if (detectedUrl) {
                mediaContent = this.renderVideoPreview(detectedUrl, element.content);
            }
        }
        
        // 기본 메타데이터 정보
        const basicMetaInfo = this.renderBasicMetaInfo(result);
        
        // 상세 메타데이터 토글 버튼 및 내용
        const resultId = `stream-result-${index}`;
        const detailedMetaSection = this.renderDetailedMetaSection(result, resultId, element);
        
        // Cross-modal 배지
        const matchType = result.match_type || null;
        const crossModalBadge = matchType === 'cross_modal'
            ? '<span class="score-tag cross-modal" data-tooltip="Cross-modal: 다른 모달리티에서 발견된 결과">🔀 Cross</span>'
            : '';

        // 점수 표시
        const scoreBreakdown = result.score_breakdown || null;
        // match_type 기준으로 search_mode 오버라이드 (더 직관적)
        if (scoreBreakdown && matchType) {
            scoreBreakdown._display_mode = matchType;
        }
        const { scoreTags, breakdownPanel } = this.renderScoreDisplay(hybridScore, originalScore, scoreBreakdown, index);

        // STEP 3: 최종 HTML 조합
        const contentTypeInfo = element.content_type ? ` [${element.content_type}]` : '';
        console.log('📦 Final HTML assembly:');
        console.log('  - mediaContent length:', mediaContent.length);
        console.log('  - shouldShowContent:', shouldShowContent);
        console.log('  - Has mediaContent:', !!mediaContent);

        const finalHtml = `
            <div class="search-result-card${matchType === 'cross_modal' ? ' cross-modal-result' : ''}">
                <div class="search-result-header">
                    <div class="search-result-type">${element.element_type || 'Unknown'} (${element.modality || 'text'})${contentTypeInfo}</div>
                    <div class="search-result-score">${crossModalBadge}${scoreTags}</div>
                </div>
                ${breakdownPanel}
                <div class="search-result-content">
                    ${mediaContent}
                    ${shouldShowContent ? `<div class="content-text">
                        ${element.content ? (typeof element.content === 'string' ? SearchDataProcessor.cleanContentIndentation(element.content) : JSON.stringify(element.content, null, 2)) : 'No content'}
                    </div>` : ''}
                </div>
                ${basicMetaInfo ? `<div class="search-result-meta">${basicMetaInfo}</div>` : ''}
                ${detailedMetaSection}
            </div>
        `;
        
        console.log('🎯 Final HTML length:', finalHtml.length);
        console.log('🚀 === FINISHED renderSingleResult for index', index, '===');
        
        return finalHtml;
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
    
    renderScoreDisplay(hybridScore, originalScore, scoreBreakdown, resultIndex) {
        const breakdownId = `score-breakdown-${resultIndex}-${Date.now()}`;
        let scoreTags = `<span class="score-tag hybrid clickable" onclick="toggleScoreBreakdown('${breakdownId}')" data-tooltip="클릭하여 점수 상세 확인">Hybrid: ${hybridScore}</span>`;
        if (originalScore) {
            scoreTags += `<span class="score-tag opensearch" data-tooltip="OpenSearch 원본 점수">OpenSearch: ${originalScore}</span>`;
        }

        // Score breakdown panel is separate (rendered outside the flex score container)
        const breakdownPanel = this._renderScoreBreakdownPanel(breakdownId, scoreBreakdown, hybridScore);

        return { scoreTags, breakdownPanel };
    }

    _renderScoreBreakdownPanel(breakdownId, scoreBreakdown, hybridScore) {
        if (!scoreBreakdown || !scoreBreakdown.components) {
            return `<div id="${breakdownId}" class="score-breakdown-panel" style="display:none;">
                <div class="breakdown-header">📊 점수 상세</div>
                <div class="breakdown-item">
                    <span class="breakdown-label">총점</span>
                    <span class="breakdown-value">${hybridScore}</span>
                </div>
                <div class="breakdown-note">상세 분석 데이터 없음</div>
            </div>`;
        }

        // _display_mode (match_type 기준)를 우선 사용, 없으면 search_mode 사용
        const displayMode = scoreBreakdown._display_mode || scoreBreakdown.search_mode || 'unknown';
        const searchModeLabels = {
            'same_modal': '✅ 동일 모달리티 매칭',
            'cross_modal': '🔀 Cross-modal 매칭',
            'image': '🖼️ 이미지 검색 모드',
            'text': '📝 텍스트 검색 모드',
        };
        const searchModeLabel = searchModeLabels[displayMode] || `📝 ${displayMode}`;

        let componentsHtml = '';

        // Cross-modal 정규화 정보 표시
        const normalization = scoreBreakdown.normalization;
        if (normalization) {
            componentsHtml += `
                <div class="breakdown-item">
                    <span class="breakdown-label">🔢 원본 벡터 유사도</span>
                    <span class="breakdown-value">${normalization.raw_vector_score.toFixed(4)}</span>
                </div>
                <div class="breakdown-item">
                    <span class="breakdown-label">📐 정규화 배율</span>
                    <span class="breakdown-value">× ${normalization.scale_factor}</span>
                </div>
                <div class="breakdown-item total">
                    <span class="breakdown-label">📊 정규화 최종 점수</span>
                    <span class="breakdown-value">${normalization.final_score}</span>
                </div>
                <div class="breakdown-separator"></div>
                <div class="breakdown-note">${normalization.method}</div>`;
        } else {
            for (const comp of scoreBreakdown.components) {
                const typeLabel = this._getComponentTypeLabel(comp.type);
                const boostInfo = comp.details && comp.details.boost ? ` (boost: ${comp.details.boost})` :
                                  comp.boost_applied ? ` (boost: ${comp.boost_applied})` : '';

                componentsHtml += `
                    <div class="breakdown-item">
                        <span class="breakdown-label">${typeLabel}${boostInfo}</span>
                        <span class="breakdown-value">${comp.score.toFixed(4)}</span>
                    </div>`;

                // Render sub-components only for non-BM25 composites
                // BM25 composite는 개별 토큰 점수를 펼치지 않음 (합산 점수만 표시)
                if (comp.sub_components && comp.type !== 'bm25_composite') {
                    for (const sub of comp.sub_components) {
                        const subLabel = this._getComponentTypeLabel(sub.type);
                        componentsHtml += `
                            <div class="breakdown-item sub-item">
                                <span class="breakdown-label">  └ ${subLabel}</span>
                                <span class="breakdown-value">${sub.score.toFixed(4)}</span>
                            </div>`;
                    }
                }
            }
        }

        return `<div id="${breakdownId}" class="score-breakdown-panel" style="display:none;">
            <div class="breakdown-header">📊 점수 상세 분석</div>
            <div class="breakdown-mode">${searchModeLabel}</div>
            <div class="breakdown-item total">
                <span class="breakdown-label">총점 (Hybrid)</span>
                <span class="breakdown-value">${scoreBreakdown.total_score ? scoreBreakdown.total_score.toFixed(4) : hybridScore}</span>
            </div>
            <div class="breakdown-separator"></div>
            ${componentsHtml}
        </div>`;
    }

    _getComponentTypeLabel(type) {
        const labels = {
            'bm25': '🔤 BM25 (키워드 매칭)',
            'bm25_composite': '🔤 BM25 (멀티 키워드 합산)',
            'vector_image': '🖼️ Vector (이미지 임베딩)',
            'vector_text': '📝 Vector (텍스트 임베딩)',
            'vector_image_caption': '💬 Vector (이미지 캡션)',
            'vector_unknown': '🔢 Vector (임베딩)',
            'element_type_boost': '🏷️ Element Type 가중치',
            'element_type_composite': '🏷️ Element Type 가중치 합산',
            'search_boost': '⚡ 검색 유형 가중치',
            'composite': '📦 복합 점수',
            'combined': '📦 통합 점수',
            'other': '📌 기타',
        };
        return labels[type] || `📌 ${type}`;
    }
    
    renderImagePreview(imageUrl, originalContent) {
        // 표시용 경로 결정 (기존 imagePath 또는 전체 URL)
        const displayPath = originalContent.startsWith('origins/') ? originalContent : imageUrl;
        
        console.log('🖼️ renderImagePreview called with:', { imageUrl: imageUrl, originalContent: originalContent, displayPath: displayPath });
        
        return `
            <div class="image-preview">
                <img data-image-url="${imageUrl}" data-original-content="${originalContent}" alt="Image preview" class="result-image" 
                     style="visibility: hidden; opacity: 0; max-width: 100%; height: auto; border-radius: 8px; border: 1px solid #e5e7eb;"
                     onerror="console.error('Image load error:', this.src); this.style.visibility='hidden'; this.nextElementSibling.nextElementSibling.style.display='block';"
                     onload="console.log('Image loaded successfully:', this.src); this.style.visibility='visible'; this.style.opacity='1'; this.nextElementSibling.style.display='none'; console.log('Image now visible - visibility:', this.style.visibility, 'opacity:', this.style.opacity);">
                <div class="image-loading" style="padding: 20px; background: #f8f9fa; border: 1px solid #e5e7eb; text-align: center; color: #666; border-radius: 8px;">
                    🖼️ 이미지 로딩 중...<br>
                    <small style="word-break: break-all; font-size: 11px;">URL: ${SearchDataProcessor.truncateText(displayPath, 60)}</small>
                </div>
                <div class="image-error" style="display: none; padding: 20px; background: #f8f9fa; border: 1px dashed #ccc; text-align: center; color: #666; border-radius: 8px;">
                    ❌ 이미지를 불러올 수 없습니다<br>
                    <small style="word-break: break-all; font-size: 11px;">URL: ${SearchDataProcessor.truncateText(displayPath, 60)}</small>
                    <br><br>
                    <a href="${imageUrl}" target="_blank" style="color: #007bff; text-decoration: none;">
                        🔗 새 탭에서 열기
                    </a>
                </div>
            </div>
        `;
    }
    
    renderVideoPreview(videoUrl, originalContent) {
        // 표시용 경로 결정
        const displayPath = originalContent;
        
        return `
            <div class="video-preview">
                <video data-video-url="${videoUrl}" data-original-content="${originalContent}" class="result-video" 
                       controls preload="metadata" style="display: none; max-width: 100%; height: auto; border-radius: 8px;"
                       onerror="this.style.display='none'; this.nextElementSibling.nextElementSibling.style.display='block';"
                       onloadedmetadata="this.style.display='block'; this.nextElementSibling.style.display='none';">
                    <source src="${videoUrl}" type="video/mp4">
                    <source src="${videoUrl}" type="video/webm">
                    <source src="${videoUrl}" type="video/ogg">
                    브라우저가 비디오를 지원하지 않습니다.
                </video>
                <div class="video-loading" style="padding: 20px; background: #f8f9fa; border: 1px solid #e5e7eb; text-align: center; color: #666; border-radius: 8px;">
                    🎥 비디오 로딩 중...<br>
                    <small style="word-break: break-all; font-size: 11px;">URL: ${SearchDataProcessor.truncateText(displayPath, 60)}</small>
                </div>
                <div class="video-error" style="display: none; padding: 20px; background: #f8f9fa; border: 1px dashed #ccc; text-align: center; color: #666; border-radius: 8px;">
                    🎥 비디오를 불러올 수 없습니다<br>
                    <small style="word-break: break-all; font-size: 11px;">URL: ${SearchDataProcessor.truncateText(displayPath, 60)}</small>
                    <br><br>
                    <a href="${videoUrl}" target="_blank" style="color: #007bff; text-decoration: none;">
                        🔗 새 탭에서 열기
                    </a>
                </div>
            </div>
        `;
    }
    
    async loadImages() {
        const imageElements = document.querySelectorAll('.result-image[data-image-url]');
        console.log('🖼️ loadImages: Found', imageElements.length, 'image elements');
        
        for (const img of imageElements) {
            const imageUrl = img.getAttribute('data-image-url');
            const originalContent = img.getAttribute('data-original-content');
            const loadingDiv = img.nextElementSibling;
            const errorDiv = loadingDiv.nextElementSibling;
            
            try {
                // 도메인과 무관하게 <img src> 로 직접 로드한다. URL() 이 경로의 한글 등을 인코딩한다.
                img.src = new URL(imageUrl, window.location.origin).href;
                loadingDiv.style.display = 'none';
            } catch (error) {
                console.error('Image loading error:', error, 'for URL:', imageUrl);
                loadingDiv.style.display = 'none';
                errorDiv.style.display = 'block';
            }
        }
    }
    
    async loadVideos() {
        const videoElements = document.querySelectorAll('.result-video[data-video-url]');
        
        for (const video of videoElements) {
            const videoUrl = video.getAttribute('data-video-url');
            const originalContent = video.getAttribute('data-original-content');
            const loadingDiv = video.nextElementSibling;
            const errorDiv = loadingDiv.nextElementSibling;
            
            try {
                // 비디오 URL을 직접 설정
                video.src = videoUrl;
                
                // 메타데이터 로드 완료 이벤트 리스너
                video.addEventListener('loadedmetadata', () => {
                    video.style.display = 'block';
                    loadingDiv.style.display = 'none';
                });
                
                // 에러 이벤트 리스너
                video.addEventListener('error', () => {
                    console.warn(`Failed to load video: ${videoUrl}`);
                    video.style.display = 'none';
                    loadingDiv.style.display = 'none';
                    errorDiv.style.display = 'block';
                });
                
                // 로딩 시간이 너무 길면 타임아웃
                setTimeout(() => {
                    if (video.readyState === 0) { // HAVE_NOTHING
                        console.warn(`Video loading timeout: ${videoUrl}`);
                        video.style.display = 'none';
                        loadingDiv.style.display = 'none';
                        errorDiv.style.display = 'block';
                    }
                }, 10000); // 10초 타임아웃
                
            } catch (error) {
                console.error('Video loading error:', error, 'for URL:', videoUrl);
                loadingDiv.style.display = 'none';
                errorDiv.style.display = 'block';
            }
        }
    }
}

// 전역 사용을 위한 export
window.SearchResultRenderer = SearchResultRenderer;
console.log('✅ SearchResultRenderer loaded');