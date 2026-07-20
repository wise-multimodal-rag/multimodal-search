/**
 * 파이프라인 시각화 패널
 * /search의 진행상황 스타일을 참조하여 깔끔하게 표시
 * - 사소한 단계는 통합
 * - 한 줄 요약 + 접힌 상세
 * - 프로그레스 바
 */
class PipelinePanel {
    constructor(contentId) {
        this.container = document.getElementById(contentId);
        this.startTime = null;
        this.lastStepTime = null;
        this.stepCount = 0;
        this.totalSteps = 7; // 예상 총 단계 수
    }

    reset() {
        this.startTime = Date.now();
        this.lastStepTime = this.startTime;
        this.stepCount = 0;
        this.container.innerHTML = `
            <div class="mb-4">
                <div class="flex items-center justify-between mb-1.5">
                    <span class="text-xs font-medium text-surface-600 dark:text-surface-300">검색 진행 중</span>
                    <span id="pipeline-progress-text" class="text-xs text-surface-400">0%</span>
                </div>
                <div class="h-1.5 bg-surface-200 dark:bg-surface-600 rounded-full overflow-hidden">
                    <div id="pipeline-progress-bar" class="h-full bg-gradient-to-r from-primary-500 to-green-500 rounded-full transition-all duration-500 ease-out" style="width: 0%"></div>
                </div>
            </div>
            <div id="pipeline-steps" class="space-y-1.5"></div>
        `;
    }

    addStep(stepData) {
        const stepName = stepData.step || stepData.type || 'unknown';
        const now = Date.now();
        const elapsed = now - (this.lastStepTime || now);
        this.lastStepTime = now;

        // 통합 로직: 사소한 단계는 건너뛰거나 이전 단계에 병합
        if (this._shouldSkip(stepName)) return;

        const mapped = this._mapStep(stepName, stepData.data || stepData, elapsed);
        if (!mapped) return;

        this.stepCount++;
        this._updateProgress();
        this._renderStep(mapped);
        this._scrollToBottom();
    }

    complete(totalTimeMs) {
        this.stepCount = this.totalSteps;
        this._updateProgress(true);

        // 프로그레스 텍스트 업데이트
        const textEl = document.getElementById('pipeline-progress-text');
        if (textEl) {
            const totalTime = totalTimeMs || (Date.now() - this.startTime);
            textEl.textContent = `완료 · ${(totalTime / 1000).toFixed(1)}s`;
        }
    }

    // === Private ===

    _shouldSkip(stepName) {
        // 이 단계들은 별도로 표시하지 않고 다른 단계에 통합
        return ['start'].includes(stepName);
    }

    _mapStep(stepName, data, elapsed) {
        switch (stepName) {
            case 'input_processed':
                return {
                    icon: '📥',
                    title: '입력 처리',
                    message: this._inputMessage(data),
                    elapsed,
                    detail: null, // 간단해서 상세 불필요
                };

            case 'query_analyzed':
                return {
                    icon: '🧠',
                    title: '쿼리 분석',
                    message: this._queryAnalysisMessage(data),
                    elapsed,
                    detail: this._queryAnalysisDetail(data),
                };

            case 'features_extracted':
                return {
                    icon: '🔬',
                    title: '특징 추출',
                    message: this._featureMessage(data),
                    elapsed,
                    detail: this._featureDetail(data),
                };

            case 'embeddings_generated':
                return {
                    icon: '🧮',
                    title: '임베딩 생성',
                    message: this._embeddingMessage(data),
                    elapsed,
                    detail: null,
                };

            case 'search_executed':
                return {
                    icon: '🔍',
                    title: '검색 실행',
                    message: this._searchMessage(data),
                    elapsed,
                    detail: this._searchDetail(data),
                };

            case 'result_enriched':
                return {
                    icon: '✨',
                    title: '결과 보강',
                    message: this._enrichMessage(data),
                    elapsed,
                    detail: null,
                };

            case 'completed':
                this.complete(data.total_time_ms || data.took_ms);
                return {
                    icon: '✅',
                    title: '검색 완료',
                    message: this._completedMessage(data),
                    elapsed,
                    detail: null,
                };

            case 'answer_generation_start':
                this.totalSteps = 9; // 답변 생성 포함 시 단계 증가
                return {
                    icon: '💬',
                    title: '답변 생성 시작',
                    message: '검색 결과를 기반으로 답변 생성 중',
                    elapsed,
                    detail: null,
                };

            case 'draft_generation':
            case 'draft_generated':
                return {
                    icon: '📝',
                    title: '답변 작성',
                    message: data.answer_length ? `${data.answer_length}자 생성` : '초안 작성 중...',
                    elapsed,
                    detail: null,
                };

            case 'answer_completed':
                return {
                    icon: '✅',
                    title: '답변 완료',
                    message: data.total_attempts ? `${data.total_attempts}회 시도, 점수 ${data.best_score || '-'}/50` : '답변 생성 완료',
                    elapsed,
                    detail: null,
                };

            case 'error':
                return {
                    icon: '❌',
                    title: '오류',
                    message: data.message || data.error || '알 수 없는 오류',
                    elapsed,
                    detail: null,
                };

            default:
                return null; // 알 수 없는 단계는 무시
        }
    }

    _renderStep(step) {
        const stepsContainer = document.getElementById('pipeline-steps');
        if (!stepsContainer) return;

        const el = document.createElement('div');
        el.className = 'pipeline-step group rounded-lg px-3 py-2 hover:bg-surface-50 dark:hover:bg-surface-700/50 transition-colors';

        const timeStr = step.elapsed > 0 ? `${(step.elapsed / 1000).toFixed(1)}s` : '<0.1s';
        const hasDetail = step.detail && step.detail.length > 0;

        el.innerHTML = `
            <div class="flex items-center gap-2.5 ${hasDetail ? 'cursor-pointer' : ''}">
                <span class="text-sm flex-shrink-0">${step.icon}</span>
                <div class="flex-1 min-w-0">
                    <span class="text-xs font-medium text-surface-700 dark:text-surface-200">${step.title}</span>
                    <span class="text-xs text-surface-400 dark:text-surface-500 ml-2">${step.message}</span>
                </div>
                <span class="text-[10px] text-surface-400 flex-shrink-0">${timeStr}</span>
                ${hasDetail ? '<svg class="w-3 h-3 text-surface-300 dark:text-surface-600 flex-shrink-0 transition-transform detail-arrow" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"/></svg>' : ''}
            </div>
            ${hasDetail ? `<div class="pipeline-detail ml-7 mt-1.5 text-[11px] text-surface-500 dark:text-surface-400 leading-relaxed">${step.detail}</div>` : ''}
        `;

        if (hasDetail) {
            el.addEventListener('click', () => {
                const detail = el.querySelector('.pipeline-detail');
                const arrow = el.querySelector('.detail-arrow');
                if (detail) detail.classList.toggle('expanded');
                if (arrow) arrow.classList.toggle('rotate-180');
            });
        }

        stepsContainer.appendChild(el);
    }

    _updateProgress(complete = false) {
        const bar = document.getElementById('pipeline-progress-bar');
        const text = document.getElementById('pipeline-progress-text');
        if (!bar || !text) return;

        const pct = complete ? 100 : Math.min(95, Math.round((this.stepCount / this.totalSteps) * 100));
        bar.style.width = pct + '%';
        text.textContent = pct + '%';

        if (complete) {
            bar.classList.remove('from-primary-500', 'to-green-500');
            bar.classList.add('bg-green-500');
        }
    }

    _scrollToBottom() {
        requestAnimationFrame(() => {
            this.container.scrollTop = this.container.scrollHeight;
        });
    }

    // === Message formatters (한 줄 요약) ===

    _inputMessage(data) {
        const modalities = data.modalities || data.input_types || [];
        if (modalities.length === 0) return '텍스트 입력';
        return modalities.join(' + ');
    }

    _queryAnalysisMessage(data) {
        const parts = [];
        if (data.expanded_queries?.length) parts.push(`쿼리 ${data.expanded_queries.length}개`);
        if (data.confidence !== undefined) parts.push(`신뢰도 ${(data.confidence * 100).toFixed(0)}%`);
        if (data.expansion_used === false) parts.push('확장 없음');
        return parts.join(', ') || '분석 완료';
    }

    _featureMessage(data) {
        const success = data.extraction_success;
        const parts = [];
        if (success) {
            const successList = Object.entries(success)
                .filter(([, v]) => v === 'success')
                .map(([k]) => k);
            parts.push(successList.join('+') || '없음');
        }
        // 핵심 정보 추가
        if (data.text_features?.keywords_count) parts.push(`키워드 ${data.text_features.keywords_count}개`);
        else if (data.text_features?.source) parts.push('원본 쿼리 사용');
        if (data.image_features?.caption) parts.push('캡션 생성');
        if (data.image_features?.objects_count) parts.push(`객체 ${data.image_features.objects_count}개`);
        if (data.video_features?.description) parts.push('비디오 분석');
        if (data.audio_features?.transcription) parts.push('음성 전사');
        return parts.join(', ') || '특징 추출 완료';
    }

    _embeddingMessage(data) {
        if (data.embedding_types?.length) {
            return `${data.embedding_types.join(', ')} (${data.dimensions || '?'}D)`;
        }
        return '벡터 생성 완료';
    }

    _searchMessage(data) {
        const parts = [];
        if (data.total_hits !== undefined) parts.push(`${data.total_hits}건 발견`);
        if (data.took_ms !== undefined) parts.push(`${data.took_ms}ms`);
        if (data.reranker_applied) parts.push('Reranker ✓');
        return parts.join(', ') || '검색 완료';
    }

    _enrichMessage(data) {
        if (data.enriched_count) return `${data.enriched_count}건 메타데이터 보강`;
        return '결과 보강 완료';
    }

    _completedMessage(data) {
        const parts = [];
        if (data.results?.length) parts.push(`${data.results.length}건 반환`);
        if (data.total_time_ms) parts.push(`총 ${(data.total_time_ms / 1000).toFixed(1)}s`);
        else if (data.took_ms) parts.push(`총 ${(data.took_ms / 1000).toFixed(1)}s`);
        return parts.join(', ') || '완료';
    }

    // === Detail formatters (접힌 상세, 클릭 시 펼침) ===

    _queryAnalysisDetail(data) {
        let html = '';

        // 의도 가중치
        if (data.element_type_weights) {
            const weights = Object.entries(data.element_type_weights)
                .filter(([, w]) => w > 0)
                .sort((a, b) => b[1] - a[1]);
            if (weights.length) {
                html += '<div class="mb-1.5"><span class="font-medium">의도 가중치:</span></div>';
                html += '<div class="flex flex-wrap gap-1 mb-2">';
                weights.forEach(([type, w]) => {
                    const opacity = w >= 0.8 ? 'bg-primary-100 dark:bg-primary-900/40 text-primary-700 dark:text-primary-300' :
                                    w >= 0.5 ? 'bg-surface-100 dark:bg-surface-600 text-surface-600 dark:text-surface-300' :
                                    'bg-surface-50 dark:bg-surface-700 text-surface-400';
                    html += `<span class="inline-block px-1.5 py-0.5 rounded text-[10px] ${opacity}">${type} ${w.toFixed(1)}</span>`;
                });
                html += '</div>';
            }
        }

        // 확장 쿼리
        if (data.expanded_queries?.length) {
            html += '<div class="mb-1"><span class="font-medium">확장 쿼리:</span></div>';
            data.expanded_queries.slice(0, 4).forEach((q, i) => {
                const text = typeof q === 'object' ? q.query || JSON.stringify(q) : q;
                html += `<div class="ml-2 truncate" title="${text}">${i + 1}. ${text.slice(0, 60)}${text.length > 60 ? '...' : ''}</div>`;
            });
        }

        // 추론 근거
        if (data.reasoning) {
            html += `<div class="mt-1.5 italic opacity-70">"${data.reasoning.slice(0, 120)}${data.reasoning.length > 120 ? '...' : ''}"</div>`;
        }

        return html || null;
    }

    _featureDetail(data) {
        let html = '';

        // 텍스트 특징
        if (data.text_features) {
            const tf = data.text_features;
            html += '<div class="mb-2"><span class="font-medium">📄 텍스트</span></div>';

            // 원본 쿼리 직접 사용 케이스
            if (tf.source) {
                html += `<div class="ml-2 mb-1 opacity-70">${tf.note || '원본 텍스트가 임베딩 생성에 직접 사용됨'}</div>`;
                if (tf.query) {
                    html += `<div class="ml-2 mb-1">쿼리: <span class="opacity-80">"${String(tf.query).slice(0, 60)}${String(tf.query).length > 60 ? '...' : ''}"</span></div>`;
                }
            } else {
                // Feature Extraction API를 통해 추출된 경우
                if (tf.keywords?.length) {
                    const kws = Array.isArray(tf.keywords) ? tf.keywords : [];
                    html += `<div class="ml-2 mb-1">키워드: <span class="opacity-80">${kws.slice(0, 6).join(', ')}${kws.length > 6 ? ' ...' : ''}</span></div>`;
                } else if (tf.keywords_count) {
                    html += `<div class="ml-2 mb-1">키워드: <span class="opacity-80">${tf.keywords_count}개 추출</span></div>`;
                }
                if (tf.entities?.length) {
                    const ents = Array.isArray(tf.entities) ? tf.entities : [];
                    html += `<div class="ml-2 mb-1">엔티티: <span class="opacity-80">${ents.slice(0, 5).join(', ')}${ents.length > 5 ? ' ...' : ''}</span></div>`;
                } else if (tf.entities_count) {
                    html += `<div class="ml-2 mb-1">엔티티: <span class="opacity-80">${tf.entities_count}개 추출</span></div>`;
                }
                if (tf.summary) {
                    const sum = typeof tf.summary === 'string' ? tf.summary : '';
                    html += `<div class="ml-2 mb-1">요약: <span class="opacity-80">${sum.slice(0, 80)}${sum.length > 80 ? '...' : ''}</span></div>`;
                }
                if (tf.classification) {
                    html += `<div class="ml-2 mb-1">분류: <span class="opacity-80">${tf.classification}</span></div>`;
                }
                if (tf.sentiment) {
                    html += `<div class="ml-2 mb-1">감성: <span class="opacity-80">${tf.sentiment}</span></div>`;
                }
                if (tf.topics?.length) {
                    const topics = Array.isArray(tf.topics) ? tf.topics : [];
                    html += `<div class="ml-2 mb-1">토픽: <span class="opacity-80">${topics.slice(0, 4).join(', ')}</span></div>`;
                }
            }
        }

        // 이미지 특징
        if (data.image_features) {
            const imf = data.image_features;
            html += '<div class="mb-2 mt-2"><span class="font-medium">🖼️ 이미지</span></div>';

            if (imf.caption) {
                html += `<div class="ml-2 mb-1">캡션: <span class="opacity-80">${String(imf.caption).slice(0, 80)}${String(imf.caption).length > 80 ? '...' : ''}</span></div>`;
            }
            if (imf.objects?.length) {
                const objs = Array.isArray(imf.objects) ? imf.objects : [];
                html += `<div class="ml-2 mb-1">객체: <span class="opacity-80">${objs.slice(0, 6).join(', ')}${objs.length > 6 ? ' ...' : ''}</span></div>`;
            }
            if (imf.tags?.length) {
                const tags = Array.isArray(imf.tags) ? imf.tags : [];
                html += `<div class="ml-2 mb-1">태그: <span class="opacity-80">${tags.slice(0, 5).join(', ')}</span></div>`;
            }
            if (imf.scene_analysis) {
                html += `<div class="ml-2 mb-1">장면: <span class="opacity-80">${String(imf.scene_analysis).slice(0, 60)}</span></div>`;
            }
        }

        // 비디오 특징
        if (data.video_features) {
            const vf = data.video_features;
            html += '<div class="mb-2 mt-2"><span class="font-medium">🎬 비디오</span></div>';

            if (vf.description) {
                html += `<div class="ml-2 mb-1">설명: <span class="opacity-80">${String(vf.description).slice(0, 80)}${String(vf.description).length > 80 ? '...' : ''}</span></div>`;
            }
            if (vf.scenes_count) {
                html += `<div class="ml-2 mb-1">장면: <span class="opacity-80">${vf.scenes_count}개 감지</span></div>`;
            }
            if (vf.activities_count) {
                html += `<div class="ml-2 mb-1">활동: <span class="opacity-80">${vf.activities_count}개 감지</span></div>`;
            }
        }

        // 오디오 특징
        if (data.audio_features) {
            const af = data.audio_features;
            html += '<div class="mb-2 mt-2"><span class="font-medium">🔊 오디오</span></div>';

            if (af.transcription) {
                html += `<div class="ml-2 mb-1">전사: <span class="opacity-80">${String(af.transcription).slice(0, 80)}${String(af.transcription).length > 80 ? '...' : ''}</span></div>`;
            }
            if (af.sounds?.length) {
                const sounds = Array.isArray(af.sounds) ? af.sounds : [];
                html += `<div class="ml-2 mb-1">사운드: <span class="opacity-80">${sounds.slice(0, 4).join(', ')}</span></div>`;
            }
        }

        return html || null;
    }

    _searchDetail(data) {
        let html = '';

        if (data.executed_queries?.length) {
            html += '<div class="mb-1"><span class="font-medium">실행된 쿼리:</span></div>';
            data.executed_queries.slice(0, 3).forEach(q => {
                const text = q.query || q;
                html += `<div class="ml-2 truncate">"${typeof text === 'string' ? text.slice(0, 50) : text}" (가중치 ${q.weight?.toFixed(2) || '1.0'})</div>`;
            });
        }

        if (data.opensearch_query) {
            const oq = data.opensearch_query;
            if (oq.query_type) html += `<div>쿼리 타입: ${oq.query_type}</div>`;
            if (oq.has_vector_search) html += `<div>벡터 검색: ${oq.vector_modalities?.join(', ') || '활성'}</div>`;
        }

        if (data.max_score) html += `<div>최고 점수: ${data.max_score.toFixed(4)}</div>`;

        return html || null;
    }
}
