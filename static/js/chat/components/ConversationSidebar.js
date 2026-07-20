/**
 * 대화 사이드바 컴포넌트
 * 대화 목록 렌더, 새 대화, 전환, 삭제
 */
class ConversationSidebar {
    constructor(listId, conversationManager, onSwitch) {
        this.container = document.getElementById(listId);
        this.manager = conversationManager;
        this.onSwitch = onSwitch;
    }

    render() {
        const conversations = this.manager.getAll();
        const currentId = this.manager.currentId;

        if (conversations.length === 0) {
            this.container.innerHTML = `
                <div class="text-center text-xs text-surface-400 dark:text-surface-500 py-8">
                    대화가 없습니다<br>새 대화를 시작하세요
                </div>
            `;
            return;
        }

        let html = '';
        conversations.forEach(conv => {
            const isActive = conv.id === currentId;
            const msgCount = conv.messages.length;
            const timeStr = this._formatTime(conv.updatedAt);

            html += `
                <div class="conv-item group flex items-center gap-2 px-3 py-2.5 rounded-lg cursor-pointer ${isActive ? 'active bg-primary-50 dark:bg-primary-900/20' : 'hover:bg-surface-100 dark:hover:bg-surface-700'}"
                     onclick="window.chatApp?.switchConversation('${conv.id}')">
                    <div class="flex-1 min-w-0">
                        <div class="text-xs font-medium text-surface-700 dark:text-surface-200 truncate">${this._escapeHtml(conv.title)}</div>
                        <div class="text-[10px] text-surface-400 dark:text-surface-500 mt-0.5">${timeStr} · ${msgCount}개 메시지</div>
                    </div>
                    <button onclick="event.stopPropagation(); window.chatApp?.deleteConversation('${conv.id}')"
                            class="opacity-0 group-hover:opacity-100 p-1 text-surface-400 hover:text-red-500 rounded transition-all">
                        <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/></svg>
                    </button>
                </div>
            `;
        });

        this.container.innerHTML = html;
    }

    _formatTime(timestamp) {
        const now = Date.now();
        const diff = now - timestamp;
        if (diff < 60000) return '방금';
        if (diff < 3600000) return `${Math.floor(diff / 60000)}분 전`;
        if (diff < 86400000) return `${Math.floor(diff / 3600000)}시간 전`;
        const date = new Date(timestamp);
        return `${date.getMonth() + 1}/${date.getDate()}`;
    }

    _escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}
