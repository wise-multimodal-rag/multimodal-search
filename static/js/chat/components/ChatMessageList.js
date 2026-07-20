/**
 * 메시지 목록 관리
 * 자동 스크롤, 웰컴 메시지 토글
 */
class ChatMessageList {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
        this.welcomeEl = document.getElementById('welcomeMessage');
        this.autoScroll = true;

        // 스크롤 감지 — 사용자가 위로 스크롤하면 자동 스크롤 비활성
        this.container.addEventListener('scroll', () => {
            const { scrollTop, scrollHeight, clientHeight } = this.container;
            this.autoScroll = (scrollHeight - scrollTop - clientHeight) < 100;
        });
    }

    appendBubble(bubbleEl) {
        this._hideWelcome();
        this.container.appendChild(bubbleEl);
        this._scrollToBottom();
    }

    scrollToBottom() {
        this._scrollToBottom();
    }

    clear() {
        // 웰컴 메시지 외 모두 제거
        const children = [...this.container.children];
        children.forEach(child => {
            if (child.id !== 'welcomeMessage') {
                child.remove();
            }
        });
        this._showWelcome();
    }

    loadMessages(messages, chatBubble, evidenceCard) {
        this.clear();
        if (!messages || messages.length === 0) return;

        for (const msg of messages) {
            if (msg.role === 'user') {
                const bubble = chatBubble.createUserBubble(msg.content, msg.meta?.files);
                this.container.appendChild(bubble);
            } else if (msg.role === 'assistant') {
                const bubble = chatBubble.createAssistantBubble(msg.id);
                this.container.appendChild(bubble);
                chatBubble.updateAssistantContent(msg.id, msg.content, false);

                // 근거 카드 복원
                if (msg.meta?.evidence && evidenceCard) {
                    evidenceCard.renderEvidence(msg.id, msg.meta.evidence);
                }
            }
        }
        this._scrollToBottom();
    }

    _scrollToBottom() {
        if (this.autoScroll) {
            requestAnimationFrame(() => {
                this.container.scrollTop = this.container.scrollHeight;
            });
        }
    }

    _hideWelcome() {
        if (this.welcomeEl) {
            this.welcomeEl.style.display = 'none';
        }
    }

    _showWelcome() {
        if (this.welcomeEl) {
            this.welcomeEl.style.display = '';
        }
    }
}
