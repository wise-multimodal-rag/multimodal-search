/**
 * 채팅 버블 렌더러
 * 사용자 메시지(오른쪽) / AI 메시지(왼쪽) 버블 생성
 */
class ChatBubble {
    constructor() {
        this.markedReady = typeof marked !== 'undefined';
        if (this.markedReady) {
            marked.setOptions({ breaks: true, gfm: true });
        }
    }

    createUserBubble(content, files = {}) {
        const bubble = document.createElement('div');
        bubble.className = 'chat-bubble flex justify-end';

        let filesHtml = '';
        const icons = { image: '🖼️', video: '🎬', audio: '🔊' };
        for (const [type, file] of Object.entries(files)) {
            if (!file) continue;
            filesHtml += `<div class="flex items-center gap-1 text-xs text-primary-200 mt-1"><span>${icons[type]}</span>${file.name}</div>`;
        }

        bubble.innerHTML = `
            <div class="max-w-[70%] bg-primary-600 text-white rounded-2xl rounded-br-md px-4 py-2.5 shadow-sm">
                <p class="text-sm whitespace-pre-wrap">${this._escapeHtml(content)}</p>
                ${filesHtml}
            </div>
        `;
        return bubble;
    }

    createAssistantBubble(messageId) {
        const bubble = document.createElement('div');
        bubble.className = 'chat-bubble flex justify-start';
        bubble.id = `bubble-${messageId}`;

        bubble.innerHTML = `
            <div class="max-w-[80%] flex gap-3">
                <div class="flex-shrink-0 w-8 h-8 bg-surface-100 dark:bg-surface-700 rounded-full flex items-center justify-center text-sm">
                    🤖
                </div>
                <div class="flex-1 min-w-0">
                    <div class="bg-white dark:bg-surface-700 rounded-2xl rounded-tl-md px-4 py-3 shadow-sm border border-surface-100 dark:border-surface-600">
                        <div id="content-${messageId}" class="ai-content text-sm text-surface-800 dark:text-surface-100">
                            <div class="typing-indicator"><span></span><span></span><span></span></div>
                        </div>
                    </div>
                    <!-- 근거 카드 슬롯 -->
                    <div id="evidence-${messageId}" class="mt-2 space-y-2"></div>
                    <!-- 액션 버튼 -->
                    <div id="actions-${messageId}" class="hidden mt-2 flex items-center gap-2">
                        <button onclick="window.chatApp?.copyAnswer('${messageId}')" class="text-xs text-surface-400 hover:text-surface-600 dark:hover:text-surface-300 flex items-center gap-1 transition-colors">
                            <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"/></svg>
                            복사
                        </button>
                        <button onclick="window.chatApp?.regenerate('${messageId}')" class="text-xs text-surface-400 hover:text-surface-600 dark:hover:text-surface-300 flex items-center gap-1 transition-colors">
                            <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/></svg>
                            다시 생성
                        </button>
                    </div>
                </div>
            </div>
        `;
        return bubble;
    }

    updateAssistantContent(messageId, content, isStreaming = false) {
        const el = document.getElementById(`content-${messageId}`);
        if (!el) return;

        // 스트리밍 중에는 업데이트 안 함 (타이핑 인디케이터 유지)
        // 완료 시에만 마크다운 렌더
        if (isStreaming) return;

        if (this.markedReady && content) {
            el.innerHTML = marked.parse(content);
        } else {
            el.textContent = content || '';
        }

        // 액션 버튼 표시
        const actions = document.getElementById(`actions-${messageId}`);
        if (actions) actions.classList.remove('hidden');
    }

    showTyping(messageId) {
        const el = document.getElementById(`content-${messageId}`);
        if (el) {
            el.innerHTML = '<div class="typing-indicator"><span></span><span></span><span></span></div>';
        }
    }

    _escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}
