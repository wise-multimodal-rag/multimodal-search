/**
 * Chat App 진입점
 * 모든 모듈을 초기화하고 연결
 */
class ChatApp {
    constructor() {
        // Core
        this.convManager = new ConversationManager();
        this.streamHandler = new ChatStreamHandler();

        // Components
        this.chatBubble = new ChatBubble();
        this.messageList = new ChatMessageList('messageList');
        this.filePreview = new FilePreview('filePreview');
        this.pipelinePanel = new PipelinePanel('pipelineContent');
        this.evidenceCard = new EvidenceCard();
        this.scoreBreakdown = new ScoreBreakdown();

        this.sidebar = new ConversationSidebar('conversationList', this.convManager, (id) => {
            this.switchConversation(id);
        });

        this.chatInput = new ChatInput((text) => {
            this.controller.sendMessage(text);
        });

        // Controller (오케스트레이터)
        this.controller = new ChatController({
            conversationManager: this.convManager,
            streamHandler: this.streamHandler,
            messageList: this.messageList,
            chatBubble: this.chatBubble,
            chatInput: this.chatInput,
            pipelinePanel: this.pipelinePanel,
            evidenceCard: this.evidenceCard,
            scoreBreakdown: this.scoreBreakdown,
            sidebar: this.sidebar,
        });

        this._setupUI();
        this._loadInitialState();
    }

    // === Public API (HTML onclick에서 호출) ===

    newConversation() {
        this.convManager.create();
        this.messageList.clear();
        this.pipelinePanel.reset();
        this.sidebar.render();
        this.chatInput.focus();
    }

    switchConversation(id) {
        const conv = this.convManager.switchTo(id);
        if (conv) {
            this.messageList.loadMessages(conv.messages, this.chatBubble, this.evidenceCard);
            this.pipelinePanel.reset();
            this.sidebar.render();
        }
    }

    deleteConversation(id) {
        if (!confirm('이 대화를 삭제할까요?')) return;
        this.convManager.delete(id);
        const current = this.convManager.getCurrent();
        if (current) {
            this.messageList.loadMessages(current.messages, this.chatBubble, this.evidenceCard);
        } else {
            this.messageList.clear();
        }
        this.sidebar.render();
    }

    stopStreaming() {
        this.controller.stopStreaming();
    }

    copyAnswer(messageId) {
        const el = document.getElementById(`content-${messageId}`);
        if (el) {
            const text = el.innerText || el.textContent;
            navigator.clipboard.writeText(text).then(() => {
                this._showToast('답변이 복사되었습니다');
            });
        }
    }

    regenerate(messageId) {
        // 해당 메시지 이전의 마지막 사용자 메시지를 다시 전송
        const conv = this.convManager.getCurrent();
        if (!conv) return;

        const msgIdx = conv.messages.findIndex(m => m.id === messageId);
        if (msgIdx <= 0) return;

        const userMsg = conv.messages[msgIdx - 1];
        if (userMsg?.role !== 'user') return;

        // 기존 AI 메시지 제거
        conv.messages.splice(msgIdx, 1);
        const bubble = document.getElementById(`bubble-${messageId}`);
        if (bubble) bubble.remove();

        // 다시 전송
        this.controller.sendMessage(userMsg.content);
    }

    showAllEvidence(messageId) {
        // TODO: 전체 근거 모달/패널 표시
        console.log('Show all evidence for', messageId);
    }

    // === Private ===

    _setupUI() {
        // 새 대화 버튼
        document.getElementById('newChatBtn')?.addEventListener('click', () => this.newConversation());

        // 사이드바 토글 (모바일)
        document.getElementById('sidebarToggle')?.addEventListener('click', () => {
            document.getElementById('sidebar')?.classList.toggle('open');
        });

        // 파이프라인 패널 토글
        document.getElementById('pipelineToggle')?.addEventListener('click', () => {
            document.getElementById('pipelinePanel')?.classList.toggle('open');
            document.getElementById('pipelinePanel')?.classList.toggle('hidden');
        });
        document.getElementById('pipelineClose')?.addEventListener('click', () => {
            document.getElementById('pipelinePanel')?.classList.remove('open');
            // 데스크탑에서는 hidden 토글
            if (window.innerWidth >= 1024) {
                document.getElementById('pipelinePanel')?.classList.toggle('hidden');
            }
        });

        // 다크모드 토글
        document.getElementById('themeToggle')?.addEventListener('click', () => this._toggleTheme());

        // 빠른 질의 버튼
        document.querySelectorAll('.quick-query').forEach(btn => {
            btn.addEventListener('click', () => {
                const text = btn.textContent.replace(/^"|"$/g, '');
                document.getElementById('chatInput').value = text;
                this.controller.sendMessage(text);
            });
        });

        // 드래그 앤 드롭
        this._setupDragDrop();

        // 초기 다크모드 상태 확인
        this._initTheme();
    }

    _loadInitialState() {
        this.sidebar.render();

        // 마지막 대화 복원
        const conversations = this.convManager.getAll();
        if (conversations.length > 0) {
            const last = conversations[0];
            this.convManager.switchTo(last.id);
            if (last.messages.length > 0) {
                this.messageList.loadMessages(last.messages, this.chatBubble, this.evidenceCard);
            }
        }
    }

    _setupDragDrop() {
        const main = document.querySelector('main');
        if (!main) return;

        ['dragenter', 'dragover'].forEach(evt => {
            main.addEventListener(evt, (e) => {
                e.preventDefault();
                main.classList.add('ring-2', 'ring-primary-400', 'ring-inset');
            });
        });

        ['dragleave', 'drop'].forEach(evt => {
            main.addEventListener(evt, (e) => {
                e.preventDefault();
                main.classList.remove('ring-2', 'ring-primary-400', 'ring-inset');
            });
        });

        main.addEventListener('drop', (e) => {
            const file = e.dataTransfer?.files[0];
            if (!file) return;

            if (file.type.startsWith('image/')) this.filePreview.setFile('image', file);
            else if (file.type.startsWith('video/')) this.filePreview.setFile('video', file);
            else if (file.type.startsWith('audio/')) this.filePreview.setFile('audio', file);
        });
    }

    _initTheme() {
        const saved = localStorage.getItem('rag_chat_theme');
        if (saved === 'dark' || (!saved && window.matchMedia('(prefers-color-scheme: dark)').matches)) {
            document.documentElement.classList.add('dark');
            this._updateThemeUI(true);
        }
    }

    _toggleTheme() {
        const isDark = document.documentElement.classList.toggle('dark');
        localStorage.setItem('rag_chat_theme', isDark ? 'dark' : 'light');
        this._updateThemeUI(isDark);
    }

    _updateThemeUI(isDark) {
        const label = document.getElementById('themeLabel');
        const icon = document.getElementById('themeIcon');
        if (label) label.textContent = isDark ? '라이트 모드' : '다크 모드';
        if (icon) {
            icon.innerHTML = isDark
                ? '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z"/>'
                : '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z"/>';
        }
    }

    _showToast(message) {
        const toast = document.createElement('div');
        toast.className = 'fixed bottom-20 left-1/2 -translate-x-1/2 px-4 py-2 bg-surface-800 dark:bg-surface-200 text-white dark:text-surface-800 text-sm rounded-lg shadow-lg z-50 transition-opacity';
        toast.textContent = message;
        document.body.appendChild(toast);
        setTimeout(() => {
            toast.style.opacity = '0';
            setTimeout(() => toast.remove(), 300);
        }, 2000);
    }
}

// 앱 초기화
window.addEventListener('DOMContentLoaded', () => {
    window.chatApp = new ChatApp();
});
