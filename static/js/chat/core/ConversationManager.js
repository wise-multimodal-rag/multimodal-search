/**
 * 대화 관리 (localStorage CRUD)
 * 추후 서버 세션으로 교체 가능한 인터페이스
 */
class ConversationManager {
    constructor() {
        this.STORAGE_KEY = 'rag_chat_conversations';
        this.conversations = this._load();
        this.currentId = null;
    }

    _load() {
        try {
            const data = localStorage.getItem(this.STORAGE_KEY);
            return data ? JSON.parse(data) : [];
        } catch {
            return [];
        }
    }

    _save() {
        try {
            localStorage.setItem(this.STORAGE_KEY, JSON.stringify(this.conversations));
        } catch (e) {
            console.warn('Failed to save conversations:', e);
        }
    }

    getAll() {
        return this.conversations.sort((a, b) => b.updatedAt - a.updatedAt);
    }

    get(id) {
        return this.conversations.find(c => c.id === id) || null;
    }

    getCurrent() {
        return this.currentId ? this.get(this.currentId) : null;
    }

    create(title = '새 대화') {
        const conv = {
            id: 'conv_' + Date.now() + '_' + Math.random().toString(36).slice(2, 8),
            title,
            messages: [],
            createdAt: Date.now(),
            updatedAt: Date.now(),
        };
        this.conversations.unshift(conv);
        this.currentId = conv.id;
        this._save();
        return conv;
    }

    switchTo(id) {
        const conv = this.get(id);
        if (conv) {
            this.currentId = id;
            return conv;
        }
        return null;
    }

    addMessage(role, content, meta = {}) {
        const conv = this.getCurrent();
        if (!conv) return null;

        const message = {
            id: 'msg_' + Date.now() + '_' + Math.random().toString(36).slice(2, 8),
            role, // 'user' | 'assistant'
            content,
            meta, // { files, pipeline, evidence, scores, ... }
            timestamp: Date.now(),
        };
        conv.messages.push(message);
        conv.updatedAt = Date.now();

        // 첫 사용자 메시지로 제목 자동 설정
        if (role === 'user' && conv.messages.filter(m => m.role === 'user').length === 1) {
            conv.title = content.slice(0, 30) + (content.length > 30 ? '...' : '');
        }

        this._save();
        return message;
    }

    updateLastAssistantMessage(content, meta = {}) {
        const conv = this.getCurrent();
        if (!conv) return;

        const lastMsg = [...conv.messages].reverse().find(m => m.role === 'assistant');
        if (lastMsg) {
            lastMsg.content = content;
            lastMsg.meta = { ...lastMsg.meta, ...meta };
            conv.updatedAt = Date.now();
            this._save();
        }
    }

    delete(id) {
        this.conversations = this.conversations.filter(c => c.id !== id);
        if (this.currentId === id) {
            this.currentId = this.conversations[0]?.id || null;
        }
        this._save();
    }

    rename(id, title) {
        const conv = this.get(id);
        if (conv) {
            conv.title = title;
            this._save();
        }
    }

    getConversationContext(maxTurns = 5) {
        const conv = this.getCurrent();
        if (!conv || conv.messages.length === 0) return [];

        const turns = [];
        const messages = conv.messages.slice(-(maxTurns * 2));
        for (const msg of messages) {
            turns.push({ role: msg.role, content: msg.content });
        }
        return turns;
    }

    clear() {
        this.conversations = [];
        this.currentId = null;
        this._save();
    }
}
