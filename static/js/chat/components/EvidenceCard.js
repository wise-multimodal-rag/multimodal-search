/**
 * 근거(Evidence) 카드 컴포넌트
 * 검색 결과를 AI 답변 아래에 카드 형태로 표시
 * element.content 내용을 실제로 확인할 수 있게 표시
 */
class EvidenceCard {
    constructor() {
        this.allEvidence = {}; // messageId → full results
    }

    renderEvidence(messageId, results) {
        const container = document.getElementById(`evidence-${messageId}`);
        if (!container || !results?.length) return;

        // 전체 결과 저장
        this.allEvidence[messageId] = results;

        // 토글 버튼만 표시 (클릭하면 근거자료 펼침)
        container.innerHTML = `
            <button id="evidence-toggle-${messageId}"
                    class="flex items-center gap-1.5 text-xs text-surface-500 dark:text-surface-400 hover:text-primary-600 dark:hover:text-primary-400 transition-colors py-1">
                <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/></svg>
                <span>근거 자료 ${results.length}건 보기</span>
                <svg class="w-3 h-3 transition-transform" id="evidence-arrow-${messageId}" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"/></svg>
            </button>
            <div id="evidence-body-${messageId}" class="hidden mt-2 space-y-2"></div>
        `;

        // 토글 이벤트
        const toggleBtn = document.getElementById(`evidence-toggle-${messageId}`);
        toggleBtn.addEventListener('click', () => {
            const body = document.getElementById(`evidence-body-${messageId}`);
            const arrow = document.getElementById(`evidence-arrow-${messageId}`);
            const isHidden = body.classList.toggle('hidden');
            arrow.classList.toggle('rotate-180', !isHidden);

            // 최초 펼칠 때만 렌더
            if (!isHidden && !body.dataset.rendered) {
                this._renderCards(messageId, results, body);
                body.dataset.rendered = 'true';
            }
        });
    }

    _renderCards(messageId, results, container) {
        const initialCount = 5;
        const topResults = results.slice(0, initialCount);

        let html = '';
        topResults.forEach((result, idx) => {
            html += this._renderCard(result, messageId, idx);
        });

        if (results.length > initialCount) {
            html += `
                <button id="evidence-more-${messageId}"
                        class="w-full text-xs text-primary-600 dark:text-primary-400 hover:text-primary-700 dark:hover:text-primary-300 hover:underline py-1.5 transition-colors"
                        data-message-id="${messageId}" data-showing="${initialCount}">
                    +${results.length - initialCount}개 더 보기
                </button>
            `;
        }

        container.innerHTML = html;

        // "더 보기" 버튼 이벤트
        const moreBtn = document.getElementById(`evidence-more-${messageId}`);
        if (moreBtn) {
            moreBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                this._showMore(messageId);
            });
        }

        // 스코어 바 렌더
        topResults.forEach((result, idx) => {
            if (result.reranker_score || result.score_breakdown) {
                const barContainer = document.getElementById(`scorebar-${messageId}-${idx}`);
                if (barContainer && window.chatApp?.scoreBreakdown) {
                    window.chatApp.scoreBreakdown.render(barContainer, result);
                }
            }
        });
    }

    _showMore(messageId) {
        const results = this.allEvidence[messageId];
        if (!results) return;

        const moreBtn = document.getElementById(`evidence-more-${messageId}`);
        // 카드들의 부모 컨테이너 = evidence-body
        const listContainer = document.getElementById(`evidence-body-${messageId}`);
        if (!listContainer || !moreBtn) return;

        const currentShowing = parseInt(moreBtn.dataset.showing) || 5;
        const nextBatch = results.slice(currentShowing, currentShowing + 5);

        // 새 카드를 버튼 앞에 추가
        nextBatch.forEach((result, idx) => {
            const realIdx = currentShowing + idx;
            const cardHtml = this._renderCard(result, messageId, realIdx);
            moreBtn.insertAdjacentHTML('beforebegin', cardHtml);

            // 스코어 바 렌더
            if (result.reranker_score || result.score_breakdown) {
                setTimeout(() => {
                    const barContainer = document.getElementById(`scorebar-${messageId}-${realIdx}`);
                    if (barContainer && window.chatApp?.scoreBreakdown) {
                        window.chatApp.scoreBreakdown.render(barContainer, result);
                    }
                }, 50);
            }
        });

        const newShowing = currentShowing + nextBatch.length;
        const remaining = results.length - newShowing;

        if (remaining > 0) {
            moreBtn.dataset.showing = newShowing;
            moreBtn.textContent = `+${remaining}개 더 보기`;
        } else {
            moreBtn.remove();
        }
    }

    _renderCard(result, messageId, idx) {
        const modalityIcons = { text: '📄', image: '🖼️', video: '🎬', audio: '🔊' };

        // 결과 데이터 추출 (SearchResult 또는 plain dict)
        const element = result.element || result;
        const modality = element.modality || result.modality || 'text';
        const icon = modalityIcons[modality] || '📄';
        const score = (result.score ?? 0).toFixed(4);
        const rerankerScore = result.reranker_score?.toFixed(4);
        const matchType = result.match_type || (result._cross_modal ? 'cross_modal' : 'same_modal');

        // 제목: media_meta.title > element_type > modality
        const mediaTitle = result.media_meta?.title || result.chunk_meta?.label || '';
        const elementType = element.element_type || result.element_type || '';
        const title = mediaTitle || elementType || modality;

        // 실제 콘텐츠
        const content = this._getContent(element, result);
        // 출처 정보
        const source = this._getSource(result);

        return `
            <div class="evidence-card bg-surface-50 dark:bg-surface-700/50 border border-surface-200 dark:border-surface-600 rounded-lg p-3 cursor-pointer"
                 onclick="const d=this.querySelector('.evidence-expand'); d.classList.toggle('hidden');">
                <!-- 헤더: 모달리티 + 제목 + 타입 + 점수 -->
                <div class="flex items-center gap-2">
                    <span class="text-sm flex-shrink-0">${icon}</span>
                    <span class="text-xs font-medium text-surface-700 dark:text-surface-200 truncate flex-1">${this._escapeHtml(title)}</span>
                    ${source ? `<span class="flex-shrink-0 text-[10px] text-surface-400 truncate max-w-[100px]" title="${this._escapeHtml(source)}">${this._escapeHtml(source)}</span>` : ''}
                    <span class="flex-shrink-0 text-[10px] px-1.5 py-0.5 rounded ${matchType === 'cross_modal' ? 'bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300' : 'bg-surface-200 dark:bg-surface-600 text-surface-600 dark:text-surface-300'}">${matchType === 'cross_modal' ? 'cross' : 'same'}</span>
                    <span class="flex-shrink-0 text-xs font-mono font-bold text-primary-600 dark:text-primary-400">${score}</span>
                </div>

                <!-- 펼침 영역 (클릭 시 토글) -->
                <div class="evidence-expand hidden mt-2.5 pt-2 border-t border-surface-200 dark:border-surface-600">
                    <!-- 이미지인 경우 실제 이미지 표시 -->
                    ${this._isImageUrl(element, modality) ? `
                        <div class="mb-2 rounded overflow-hidden border border-surface-200 dark:border-surface-600">
                            <img src="${this._escapeHtml(element.content || result.content || '')}"
                                 alt="${this._escapeHtml(element.description || 'image')}"
                                 class="w-full max-h-80 object-contain bg-surface-100 dark:bg-surface-900 cursor-pointer"
                                 onclick="event.stopPropagation(); window.open(this.src, '_blank')"
                                 onerror="this.parentElement.innerHTML='<div class=\\'p-3 text-xs text-surface-400 text-center\\'>이미지를 불러올 수 없습니다</div>'"
                                 loading="lazy">
                        </div>
                    ` : `
                        <!-- 텍스트 원문 콘텐츠 -->
                        <div class="text-xs text-surface-600 dark:text-surface-300 leading-relaxed whitespace-pre-wrap bg-white dark:bg-surface-800 rounded p-2.5 border border-surface-100 dark:border-surface-600 max-h-64 overflow-y-auto mb-2">
                            ${content}
                        </div>
                    `}

                    <!-- 스코어바 -->
                    ${rerankerScore ? `<div class="mb-2" id="scorebar-${messageId}-${idx}"></div>` : ''}

                    <!-- 상세 정보 -->
                    <div class="text-[11px] text-surface-500 dark:text-surface-400 space-y-0.5">
                        ${this._renderDetailRows(result, element)}
                    </div>
                </div>
            </div>
        `;
    }

    _isImageUrl(element, modality) {
        if (modality === 'image') return true;
        const content = element.content || '';
        return content.startsWith('http') && /\.(png|jpg|jpeg|gif|webp|svg)/i.test(content);
    }

    _getContent(element, result) {
        // 우선순위: element.content > element.description > result.content > result.description
        let content = element.content || element.description || result.content || result.description || '';

        // URL인 경우 설명으로 대체
        if (typeof content === 'string' && content.startsWith('http')) {
            content = element.description || result.description || `(미디어 URL: ${content})`;
        }

        return content ? this._escapeHtml(content) : '<span class="italic text-surface-400">(콘텐츠 없음)</span>';
    }

    _getSource(result) {
        if (result.media_meta?.source_uri) {
            // 파일명만 추출
            const uri = result.media_meta.source_uri;
            return uri.split('/').pop() || uri;
        }
        if (result.media_meta?.title) return result.media_meta.title;
        return '';
    }

    _renderDetailRows(result, element) {
        // 긴 값: 한 줄 전체 사용
        const fullRows = [];
        // 짧은 값: 2열로 나란히
        const shortRows = [];

        // 긴 값들 (문서명, 경로, Element ID)
        if (result.media_meta?.title) fullRows.push(['문서', result.media_meta.title]);
        if (result.media_meta?.source_uri) fullRows.push(['경로', result.media_meta.source_uri]);
        if (element.element_id) fullRows.push(['Element ID', element.element_id]);

        // 짧은 값들 (2열로 배치)
        if (result.chunk_meta?.chunk_seq !== undefined) {
            shortRows.push(['위치', `${result.chunk_meta.chunk_type || 'chunk'} #${result.chunk_meta.chunk_seq}`]);
        }
        if (element.element_type) shortRows.push(['요소', element.element_type]);
        if (element.language) shortRows.push(['언어', element.language]);
        if (result.chunk_meta?.modality_set?.length) shortRows.push(['모달리티', result.chunk_meta.modality_set.join(', ')]);
        if (result.match_type) shortRows.push(['매칭', result.match_type]);

        const breakdown = result.score_breakdown || {};
        if (breakdown.search_mode) shortRows.push(['검색모드', breakdown.search_mode]);
        if (result.original_score !== undefined) shortRows.push(['원본점수', result.original_score.toFixed(2)]);

        // 미디어 (의미있는 값만)
        if (result.media_meta) {
            const mm = result.media_meta;
            if (mm.file_size_bytes > 0) shortRows.push(['크기', this._formatSize(mm.file_size_bytes)]);
            if (mm.duration_seconds > 0) shortRows.push(['길이', mm.duration_seconds.toFixed(1) + '초']);
            if (mm.width_pixels > 0 && mm.height_pixels > 0) shortRows.push(['해상도', `${mm.width_pixels}×${mm.height_pixels}`]);
        }

        if (fullRows.length === 0 && shortRows.length === 0) {
            return '<div class="italic text-[11px] text-surface-400">상세 정보 없음</div>';
        }

        let html = '<table class="w-full text-[11px] border-collapse"><tbody>';

        // 긴 값: 전체 행 사용
        fullRows.forEach(([key, val]) => {
            html += `
                <tr class="border-b border-surface-100 dark:border-surface-600/30">
                    <td class="py-1 pr-3 text-surface-400 dark:text-surface-500 whitespace-nowrap font-medium">${key}</td>
                    <td colspan="3" class="py-1 text-surface-600 dark:text-surface-300 break-all">${this._escapeHtml(String(val))}</td>
                </tr>`;
        });

        // 짧은 값: 2열로 나란히
        for (let i = 0; i < shortRows.length; i += 2) {
            const left = shortRows[i];
            const right = shortRows[i + 1];
            html += '<tr class="border-b border-surface-100 dark:border-surface-600/30">';
            html += `<td class="py-1 pr-2 text-surface-400 dark:text-surface-500 whitespace-nowrap font-medium">${left[0]}</td>`;
            html += `<td class="py-1 pr-4 text-surface-600 dark:text-surface-300">${this._escapeHtml(String(left[1]))}</td>`;
            if (right) {
                html += `<td class="py-1 pr-2 text-surface-400 dark:text-surface-500 whitespace-nowrap font-medium">${right[0]}</td>`;
                html += `<td class="py-1 text-surface-600 dark:text-surface-300">${this._escapeHtml(String(right[1]))}</td>`;
            } else {
                html += '<td></td><td></td>';
            }
            html += '</tr>';
        }

        html += '</tbody></table>';
        return html;
    }

    _formatSize(bytes) {
        if (bytes < 1024) return bytes + 'B';
        if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + 'KB';
        return (bytes / (1024 * 1024)).toFixed(1) + 'MB';
    }

    _escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}
