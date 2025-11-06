/**
 * 검색 단계별 렌더링 관리자
 */
class SearchStepRenderer {
    constructor(searchSteps) {
        this.searchSteps = searchSteps;
    }
    
    addStep(title, message, data = null, type = 'info', serverTimestamp = null) {
        console.log('addStep called:', title, type, 'with timestamp:', serverTimestamp);
        
        const stepElement = document.createElement('div');
        stepElement.className = `search-step ${type}`;
        
        const displayTime = SearchDataProcessor.formatTimestamp(serverTimestamp);
        
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
    
    updateLastLoadingStep(title, message, data = null, type = 'success', serverTimestamp = null) {
        // 마지막 loading 상태의 단계를 찾아서 업데이트
        const loadingSteps = this.searchSteps.querySelectorAll('.search-step.loading');
        if (loadingSteps.length > 0) {
            const lastLoadingStep = loadingSteps[loadingSteps.length - 1];
            
            // 클래스 변경
            lastLoadingStep.className = `search-step ${type}`;
            
            const displayTime = SearchDataProcessor.formatTimestamp(serverTimestamp);
            
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
    
    addMetadataToLastStep(metadata) {
        if (!metadata || (typeof metadata === 'string' && metadata.length === 0)) return;
        
        const lastStep = this.searchSteps.lastElementChild;
        if (!lastStep) return;
        
        // 기존 step-data 컨테이너가 있는지 확인
        let stepDataContainer = lastStep.querySelector('.step-data');
        
        if (!stepDataContainer) {
            // step-data 컨테이너가 없으면 생성
            const stepHeader = lastStep.querySelector('.step-header');
            if (stepHeader) {
                stepDataContainer = document.createElement('div');
                stepDataContainer.className = 'step-data';
                stepDataContainer.id = `step-data-${Date.now()}`;
                stepHeader.insertAdjacentElement('afterend', stepDataContainer);
            }
        }
        
        if (stepDataContainer && typeof metadata === 'string') {
            // step-data 컨테이너 안에 메타데이터 삽입 (1-7단계와 동일한 방식)
            stepDataContainer.innerHTML = metadata;
        }
    }
    
    cleanupLoadingSteps() {
        // 현재 loading 상태인 단계들을 찾아서 중지됨 상태로 변경
        const loadingSteps = this.searchSteps.querySelectorAll('.search-step.loading');
        
        loadingSteps.forEach(step => {
            // loading 클래스 제거하고 warning 클래스 추가
            step.classList.remove('loading');
            step.classList.add('warning');
            
            // 제목 업데이트
            const titleElement = step.querySelector('.step-title');
            if (titleElement) {
                let currentTitle = titleElement.textContent;
                // "~~ 중" 또는 "~~ 하는 중" 패턴을 "~~ 중지됨"으로 변경
                if (currentTitle.includes('중')) {
                    titleElement.textContent = currentTitle.replace(/\s*(하는\s*)?중.*$/, ' 중지됨');
                } else {
                    titleElement.textContent = currentTitle + ' 중지됨';
                }
            }
            
            // 메시지 업데이트
            const messageElement = step.querySelector('.step-message');
            if (messageElement) {
                messageElement.textContent = '사용자가 검색을 중지했습니다';
            }
            
            // 타임스탬프 업데이트
            const timestampElement = step.querySelector('.step-timestamp');
            if (timestampElement) {
                timestampElement.textContent = new Date().toLocaleTimeString();
            }
        });
        
        console.log(`🧹 Cleaned up ${loadingSteps.length} loading steps`);
    }
    
    hideCompletedLoadingSteps() {
        // 최종 완료 시 남아있는 로딩 단계들을 숨김
        const loadingSteps = this.searchSteps.querySelectorAll('.search-step.loading');
        console.log(`🧹 hideCompletedLoadingSteps: Found ${loadingSteps.length} loading steps to check`);
        
        loadingSteps.forEach(step => {
            const titleElement = step.querySelector('.step-title');
            if (titleElement) {
                const title = titleElement.textContent;
                console.log(`🔍 Checking loading step title: "${title}"`);
                
                // 답변 생성 관련 모든 중간 로딩 단계들 숨김
                const shouldHide = title.includes('검토 중') || 
                                 title.includes('재생성 중') ||
                                 title.includes('초안 생성 중') ||
                                 title.includes('답변 품질 검토 중');
                
                if (shouldHide) {
                    console.log(`🧹 Hiding intermediate loading step: ${title}`);
                    step.style.display = 'none';
                } else {
                    console.log(`✅ Keeping step visible: ${title}`);
                }
            }
        });
    }
    
    renderStepData(container, data, stepType) {
        if (!container || !data) return;
        
        // 답변 생성 단계의 메타데이터가 있으면 직접 사용
        if (data._metadata) {
            container.innerHTML = data._metadata;
            return;
        }
        
        let content = '';
        
        // 시작 단계 데이터
        if (data.input_types) {
            content += `<div class="data-item"><strong>입력 타입:</strong> ${data.input_types.join(', ')}</div>`;
        }
        
        // 입력 처리 완료 데이터
        content += this.renderInputProcessedData(data);
        
        // 쿼리 확장 데이터
        content += this.renderQueryExpansionData(data);
        
        // 쿼리 의도 분석 데이터
        content += this.renderQueryAnalysisData(data);
        
        // 특징 추출 데이터
        content += this.renderFeatureExtractionData(data);
        
        // 임베딩 데이터
        content += this.renderEmbeddingData(data);
        
        // 검색 실행 데이터
        content += this.renderSearchExecutionData(data);
        
        // 결과 보강 데이터
        content += this.renderResultEnrichmentData(data);
        
        // 답변 생성 관련 데이터
        content += this.renderAnswerGenerationData(data);
        
        // 최종 결과 데이터
        content += this.renderFinalResultData(data);
        
        container.innerHTML = content;
    }
    
    renderInputProcessedData(data) {
        let content = '';
        
        if (data.modalities) {
            content += `<div class="data-item"><strong>처리된 모달리티:</strong> ${data.modalities.join(', ')}</div>`;
            if (data.text_query) {
                const truncatedQuery = SearchDataProcessor.truncateText(data.text_query, 60);
                content += `<div class="data-item">
                    <strong>텍스트 쿼리:</strong>
                    <div class="text-query-display" title="${data.text_query}">
                        "${truncatedQuery}"
                    </div>
                </div>`;
            }
            
            // 파일 정보 표시
            if (data.file_info && Object.keys(data.file_info).length > 0) {
                let hasValidFiles = false;
                let fileList = '';
                
                Object.entries(data.file_info).forEach(([fileType, fileData]) => {
                    if (fileData && fileData.filename) {
                        hasValidFiles = true;
                        const truncatedFilename = SearchDataProcessor.truncateText(fileData.filename, 40);
                        fileList += `<div class="data-item file-info">
                            <span title="${fileData.filename}">${truncatedFilename}</span>
                        </div>`;
                    }
                });
                
                if (hasValidFiles) {
                    content += `<div class="data-item"><strong>첨부 파일:</strong></div>`;
                    content += fileList;
                } else {
                    content += `<div class="data-item"><strong>첨부 파일:</strong> 없음</div>`;
                }
            } else {
                content += `<div class="data-item"><strong>첨부 파일:</strong> 없음</div>`;
            }
        }
        
        return content;
    }
    
    renderQueryExpansionData(data) {
        let content = '';
        
        // === 1. 쿼리 확장 섹션 ===
        if (data.expanded_queries || data.expansion_used !== undefined) {
            content += `<div class="data-section">
                <h4>🔍 쿼리 확장</h4>`;
            
            if (data.expansion_used !== undefined) {
                const expansionText = data.expansion_used ? 
                    `성공 (${data.total_queries || 1}개 쿼리 생성)` : 
                    '실패 (원본 쿼리만 사용)';
                content += `<div class="data-item"><strong>확장 결과:</strong> ${expansionText}</div>`;
            }
            
            if (data.expanded_queries && data.expanded_queries.length > 0) {
                content += `<div class="data-item"><strong>확장된 쿼리 목록:</strong></div>
                    <div class="expanded-queries">
                        ${data.expanded_queries.map((query, index) => {
                            const queryText = typeof query === 'object' ? query.query || JSON.stringify(query) : query;
                            const truncatedQuery = SearchDataProcessor.truncateText(queryText, 50);
                            return `<div class="expanded-query">
                                <div class="query-label"><strong>${index + 1}.</strong></div>
                                <div class="query-content" title="${queryText}">${truncatedQuery}</div>
                            </div>`;
                        }).join('')}
                    </div>`;
            }
            
            content += `</div>`;
        }
        
        // === 2. 쿼리 확장 상세 분석 섹션 ===
        if (data.expansion_analysis) {
            content += this.renderExpansionAnalysis(data.expansion_analysis, data.expanded_queries);
        }
        
        return content;
    }
    
    renderExpansionAnalysis(analysis, expandedQueries) {
        let content = `<div class="data-section">
            <h4>쿼리 확장 상세 분석</h4>`;
        
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
        content += this.renderQueryList('분해', analysis.decomposition, 'decomposition');
        
        // 재작성된 쿼리들
        content += this.renderQueryList('재작성된 쿼리', analysis.rewritten_queries, 'rewritten');
        
        // 의미적 확장들
        content += this.renderQueryList('의미적 확장', analysis.semantic_expansions, 'semantic');
        
        // 최종 쿼리들 (실제 사용된 것만 표시)
        if (analysis.final_queries && analysis.final_queries.length > 0 && expandedQueries) {
            content += this.renderFinalQueries(analysis.final_queries, expandedQueries);
        }
        
        // 검색 제안사항
        content += this.renderQueryList('검색 제안사항', analysis.search_suggestions, 'suggestions');
        
        content += `</div>`;
        return content;
    }
    
    renderQueryList(title, queries, className) {
        if (!queries || queries.length === 0) return '';
        
        return `<div class="sub-section">
            <h5>${title} (${queries.length}개)</h5>
            <div class="${className}-list">
                ${queries.map((item, index) => {
                    const queryText = typeof item === 'object' ? item.query || JSON.stringify(item) : item;
                    const truncatedQuery = SearchDataProcessor.truncateText(queryText, 40);
                    return `<div class="${className}-item">
                        <div class="query-label"><strong>${index + 1}.</strong></div>
                        <div class="query-content" title="${queryText}">${truncatedQuery}</div>
                    </div>`;
                }).join('')}
            </div>
        </div>`;
    }
    
    renderFinalQueries(finalQueries, expandedQueries) {
        // expanded_queries와 매칭되는 final_queries만 찾기
        const usedFinalQueries = finalQueries.filter(item => {
            const queryText = typeof item === 'object' ? item.query : item;
            return expandedQueries.includes(queryText);
        });
        
        const unusedFinalQueries = finalQueries.filter(item => {
            const queryText = typeof item === 'object' ? item.query : item;
            return !expandedQueries.includes(queryText);
        });
        
        let content = '';
        
        if (usedFinalQueries.length > 0) {
            content += `<div class="sub-section">
                <h5>최종 선별된 쿼리 (${usedFinalQueries.length}개 - 실제 검색에 사용)</h5>
                <div class="final-queries-list">
                    ${usedFinalQueries.map((item, index) => {
                        return this.renderFinalQueryItem(item, index);
                    }).join('')}
                </div>
            </div>`;
        }
        
        // 사용되지 않은 쿼리들도 참고용으로 표시
        if (unusedFinalQueries.length > 0) {
            content += `<div class="sub-section">
                <h5>후보 쿼리 (${unusedFinalQueries.length}개 - 미사용)</h5>
                <div class="unused-queries-list">
                    ${unusedFinalQueries.map((item, index) => {
                        return this.renderUnusedQueryItem(item, index);
                    }).join('')}
                </div>
            </div>`;
        }
        
        return content;
    }
    
    renderFinalQueryItem(item, index) {
        if (typeof item === 'object' && item.query) {
            const truncatedQuery = SearchDataProcessor.truncateText(item.query, 40);
            return `<div class="final-query-item">
                <div class="query-text" title="${item.query}"><strong>${index + 1}.</strong> ${truncatedQuery}</div>
                ${item.score !== undefined ? `<div class="query-score">점수: ${item.score.toFixed(2)}</div>` : ''}
                ${item.reason ? `<div class="query-reason">이유: ${item.reason}</div>` : ''}
            </div>`;
        } else {
            const queryText = typeof item === 'object' ? JSON.stringify(item) : item;
            const truncatedQuery = SearchDataProcessor.truncateText(queryText, 40);
            return `<div class="final-query-item">
                <div class="query-text" title="${queryText}"><strong>${index + 1}.</strong> ${truncatedQuery}</div>
            </div>`;
        }
    }
    
    renderUnusedQueryItem(item, index) {
        if (typeof item === 'object' && item.query) {
            const truncatedQuery = SearchDataProcessor.truncateText(item.query, 40);
            return `<div class="unused-query-item">
                <div class="query-text" title="${item.query}"><strong>${index + 1}.</strong> ${truncatedQuery}</div>
                ${item.score !== undefined ? `<div class="query-score">점수: ${item.score.toFixed(2)}</div>` : ''}
                ${item.reason ? `<div class="query-reason">이유: ${item.reason}</div>` : ''}
            </div>`;
        } else {
            const queryText = typeof item === 'object' ? JSON.stringify(item) : item;
            const truncatedQuery = SearchDataProcessor.truncateText(queryText, 40);
            return `<div class="unused-query-item">
                <div class="query-text" title="${queryText}"><strong>${index + 1}.</strong> ${truncatedQuery}</div>
            </div>`;
        }
    }
    
    renderQueryAnalysisData(data) {
        let content = '';
        
        // === 3. 쿼리 의도 분석 섹션 ===
        if (data.selected_element_types || data.confidence !== undefined || data.reasoning) {
            content += `<div class="data-section">
                <h4>🎯 쿼리 의도 분석</h4>`;
            
            if (data.selected_element_types && data.selected_element_types.length > 0) {
                content += `<div class="data-item">
                    <strong>선택된 Element Types (${data.selected_element_types.length}개):</strong>
                    <div class="element-types">
                        ${data.selected_element_types.map(type => 
                            `<span class="element-type-tag">${type}</span>`
                        ).join('')}
                    </div>
                </div>`;
            }
            
            if (data.confidence !== undefined) {
                content += `<div class="data-item"><strong>신뢰도:</strong> ${(data.confidence * 100).toFixed(1)}%</div>`;
            }
            
            if (data.reasoning) {
                content += `<div class="data-item"><strong>분석 근거:</strong> ${data.reasoning}</div>`;
            }
            
            content += `</div>`;
        }
        
        return content;
    }
    
    renderFeatureExtractionData(data) {
        let content = '';
        
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
                
                const { actualFeatures, metaData } = SearchDataProcessor.separateFeatureData(features);
                
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
                        
                        const truncatedValue = SearchDataProcessor.truncateText(displayValue, 60);
                        
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
            const totalFeatures = [
                SearchDataProcessor.countActualFeatures(data.text_features),
                SearchDataProcessor.countActualFeatures(data.image_features),
                SearchDataProcessor.countActualFeatures(data.video_features),
                SearchDataProcessor.countActualFeatures(data.audio_features)
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
        
        return content;
    }
    
    renderEmbeddingData(data) {
        let content = '';
        
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
        
        return content;
    }
    
    renderSearchExecutionData(data) {
        let content = '';
        
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
                                const truncatedQuery = SearchDataProcessor.truncateText(queryInfo.query, 40);
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
        
        return content;
    }
    
    renderResultEnrichmentData(data) {
        let content = '';
        
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
        
        return content;
    }
    
    renderFinalResultData(data) {
        let content = '';
        
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
        
        return content;
    }
    
    renderAnswerGenerationData(data) {
        let content = '';
        
        // 답변 생성 시작 데이터
        if (data.step === 'answer_generation_start') {
            content += `
                <div class="data-section">
                    <h4>🤖 AI 답변 생성 시작</h4>
                    <div class="data-item">
                        <strong>검색 결과 기반 답변 생성을 시작합니다</strong>
                    </div>
                </div>
            `;
        }
        
        // 초안 생성 중 데이터
        if (data.step === 'draft_generation') {
            content += `
                <div class="data-section">
                    <h4>📝 답변 초안 생성 중</h4>
                    ${data.attempt_number ? `<div class="data-item"><strong>시도 번호:</strong> ${data.attempt_number}회차</div>` : ''}
                    <div class="data-item">
                        <strong>상태:</strong> 검색 결과를 분석하여 답변 초안을 생성하고 있습니다
                    </div>
                </div>
            `;
        }
        
        // 초안 생성 완료 데이터
        if (data.step === 'draft_generated' && data.data) {
            const draftData = data.data;
            content += `
                <div class="data-section">
                    <h4>✅ 답변 초안 생성 완료</h4>
                    <div class="generation-summary">
                        <div class="data-item"><strong>시도 번호:</strong> ${draftData.attempt_number}회차</div>
                        <div class="data-item"><strong>답변 길이:</strong> ${draftData.answer_length}자</div>
                        <div class="data-item"><strong>Temperature:</strong> ${draftData.temperature}</div>
                        <div class="data-item"><strong>참고 문서:</strong> ${draftData.search_context_size}개</div>
                    </div>
                    ${draftData.draft_preview ? `
                        <div class="draft-preview">
                            <strong>생성된 답변 초안:</strong>
                            <div class="draft-preview-text">${draftData.draft_preview}</div>
                        </div>
                    ` : ''}
                </div>
            `;
        }
        
        // 품질 검토 중 데이터
        if (data.step === 'reflection') {
            content += `
                <div class="data-section">
                    <h4>🔍 답변 품질 검토 중</h4>
                    ${data.attempt_number ? `<div class="data-item"><strong>검토 대상:</strong> ${data.attempt_number}회차 답변</div>` : ''}
                    <div class="data-item">
                        <strong>상태:</strong> 생성된 답변의 정확성, 완성도, 명확성을 검토하고 있습니다
                    </div>
                </div>
            `;
        }
        
        // 품질 검토 완료 데이터
        if (data.step === 'reflection_completed' && data.data) {
            const reflectionData = data.data;
            content += `
                <div class="data-section">
                    <h4>📊 품질 검토 완료</h4>
                    <div class="reflection-summary">
                        <div class="data-item"><strong>검토 대상:</strong> ${reflectionData.attempt_number}회차 답변</div>
                        <div class="data-item"><strong>총 점수:</strong> ${reflectionData.total_score}/50점</div>
                        <div class="data-item"><strong>답변 품질:</strong> ${reflectionData.answer_quality}</div>
                        <div class="data-item"><strong>허용 여부:</strong> ${reflectionData.is_acceptable ? '✅ 승인' : '❌ 재생성 필요'}</div>
                    </div>
                    
                    ${reflectionData.scores ? `
                        <div class="scores-breakdown">
                            <strong>세부 점수:</strong>
                            <div class="scores-grid">
                                ${Object.entries(reflectionData.scores).map(([criterion, score]) => {
                                    const criterionName = {
                                        'accuracy': '정확성',
                                        'completeness': '완성도', 
                                        'clarity': '명확성',
                                        'structure': '구조',
                                        'relevance': '관련성'
                                    }[criterion] || criterion;
                                    return `<div class="score-item">${criterionName}: ${score}/10</div>`;
                                }).join('')}
                            </div>
                        </div>
                    ` : ''}
                    
                    ${reflectionData.improvement_suggestions && reflectionData.improvement_suggestions.length > 0 ? `
                        <div class="improvement-suggestions">
                            <strong>개선 제안:</strong>
                            <ul>
                                ${reflectionData.improvement_suggestions.map(suggestion => 
                                    `<li>${suggestion}</li>`
                                ).join('')}
                            </ul>
                        </div>
                    ` : ''}
                </div>
            `;
        }
        
        // 재생성 중 데이터
        if (data.step === 'regenerating') {
            content += `
                <div class="data-section">
                    <h4>🔄 답변 재생성 중</h4>
                    <div class="data-item">
                        <strong>이유:</strong> 품질 개선을 위해 답변을 재생성하고 있습니다
                    </div>
                    <div class="data-item">
                        <strong>상태:</strong> 이전 피드백을 반영하여 더 나은 답변을 생성합니다
                    </div>
                </div>
            `;
        }
        
        // 답변 생성 완료 데이터
        if (data.step === 'answer_completed' && data.data) {
            const completionData = data.data;
            content += `
                <div class="data-section">
                    <h4>🎯 AI 답변 생성 완료</h4>
                    <div class="completion-summary">
                        <div class="data-item"><strong>성공 여부:</strong> ${completionData.success ? '✅ 성공' : '❌ 실패'}</div>
                        <div class="data-item"><strong>총 시도 횟수:</strong> ${completionData.total_attempts}회</div>
                        ${completionData.best_attempt ? `<div class="data-item"><strong>선택된 답변:</strong> ${completionData.best_attempt}회차</div>` : ''}
                        ${completionData.best_score ? `<div class="data-item"><strong>최종 점수:</strong> ${completionData.best_score}/50점</div>` : ''}
                        <div class="data-item"><strong>완료 사유:</strong> ${completionData.completion_reason === 'quality_accepted' ? '품질 승인' : '최고 점수 선택'}</div>
                    </div>
                    
                    ${completionData.search_context ? `
                        <div class="context-info">
                            <strong>검색 컨텍스트:</strong>
                            <div class="data-item">참고 결과: ${completionData.search_context.total_results}개</div>
                            ${completionData.search_context.element_types ? `
                                <div class="data-item">
                                    요소 타입: ${completionData.search_context.element_types.join(', ')}
                                </div>
                            ` : ''}
                        </div>
                    ` : ''}
                </div>
            `;
        }
        
        // 취소 또는 타임아웃 데이터
        if (data.step === 'answer_generation_cancelled') {
            content += `
                <div class="data-section">
                    <h4>⚠️ 답변 생성 취소</h4>
                    <div class="data-item">
                        <strong>상태:</strong> 사용자 요청에 의해 답변 생성이 취소되었습니다
                    </div>
                </div>
            `;
        }
        
        if (data.step === 'answer_generation_timeout') {
            content += `
                <div class="data-section">
                    <h4>⏰ 답변 생성 시간 초과</h4>
                    <div class="data-item">
                        <strong>상태:</strong> 설정된 시간 내에 답변 생성을 완료하지 못했습니다
                    </div>
                </div>
            `;
        }
        
        return content;
    }
}

// 전역 사용을 위한 export
window.SearchStepRenderer = SearchStepRenderer;
console.log('✅ SearchStepRenderer loaded');