/**
 * 채팅 입력 컴포넌트
 * textarea 자동 확장, 키보드 단축키, 파일 첨부 연동
 */
class ChatInput {
    constructor(onSend) {
        this.textarea = document.getElementById('chatInput');
        this.sendBtn = document.getElementById('sendBtn');
        this.stopBtn = document.getElementById('stopBtn');
        this.onSend = onSend;

        this._setupAutoResize();
        this._setupKeyboard();
        this._setupFileInputs();
        this._setupSendButton();
    }

    getValue() {
        return this.textarea.value.trim();
    }

    clear() {
        this.textarea.value = '';
        this.textarea.style.height = 'auto';
    }

    focus() {
        this.textarea.focus();
    }

    setDisabled(disabled) {
        this.textarea.disabled = disabled;
        this.sendBtn.disabled = disabled;
        this.sendBtn.classList.toggle('hidden', disabled);
        this.stopBtn.classList.toggle('hidden', !disabled);
    }

    _setupAutoResize() {
        this.textarea.addEventListener('input', () => {
            this.textarea.style.height = 'auto';
            this.textarea.style.height = Math.min(this.textarea.scrollHeight, 128) + 'px';
        });
    }

    _setupKeyboard() {
        this.textarea.addEventListener('keydown', (e) => {
            // Enter = 전송, Shift+Enter = 줄바꿈
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this._handleSend();
            }
        });

        // 전역 단축키
        document.addEventListener('keydown', (e) => {
            // Ctrl+N = 새 대화
            if ((e.ctrlKey || e.metaKey) && e.key === 'n') {
                e.preventDefault();
                window.chatApp?.newConversation();
            }
        });
    }

    _setupFileInputs() {
        const fileTypes = ['Image', 'Video', 'Audio'];
        fileTypes.forEach(type => {
            const input = document.getElementById(`chat${type}Input`);
            if (input) {
                input.addEventListener('change', (e) => {
                    const file = e.target.files[0];
                    if (file) {
                        window.chatApp?.filePreview.setFile(type.toLowerCase(), file);
                    }
                    input.value = ''; // 같은 파일 재선택 허용
                });
            }
        });
    }

    _setupSendButton() {
        this.sendBtn.addEventListener('click', () => this._handleSend());
        this.stopBtn.addEventListener('click', () => {
            window.chatApp?.stopStreaming();
        });
    }

    _handleSend() {
        const text = this.getValue();
        const hasFiles = window.chatApp?.filePreview.hasFiles();

        if (!text && !hasFiles) return;
        if (this.onSend) this.onSend(text);
    }
}
