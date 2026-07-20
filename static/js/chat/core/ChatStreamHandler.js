/**
 * SSE 스트림 핸들러 (기존 StreamingHandler 패턴 참조)
 * fetch + ReadableStream으로 SSE 이벤트를 파싱하여 콜백으로 분배
 */
class ChatStreamHandler {
    constructor() {
        this.abortController = null;
        this.isStreaming = false;
        this.partialData = '';
    }

    async startStreaming(url, formData, callbacks = {}) {
        if (this.isStreaming) {
            console.warn('ChatStreamHandler: Already streaming');
            return;
        }

        this.isStreaming = true;
        this.abortController = new AbortController();
        this.partialData = '';

        const { onStep, onAnswerToken, onComplete, onError } = callbacks;

        try {
            const response = await fetch(url, {
                method: 'POST',
                body: formData,
                signal: this.abortController.signal,
            });

            if (!response.ok) {
                const errText = await response.text();
                throw new Error(`HTTP ${response.status}: ${errText}`);
            }

            const reader = response.body.getReader();
            const decoder = new TextDecoder();

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                const chunk = decoder.decode(value, { stream: true });
                const shouldStop = this._processChunk(chunk, onStep, onAnswerToken);
                if (shouldStop) break;
            }

            // 남은 partial 데이터 처리
            if (this.partialData.trim()) {
                this._tryParseLine(this.partialData, onStep, onAnswerToken);
            }

            if (onComplete) onComplete();
        } catch (error) {
            if (error.name === 'AbortError') {
                console.log('Stream aborted by user');
            } else {
                console.error('Stream error:', error);
                if (onError) onError(error);
            }
        } finally {
            this.isStreaming = false;
            this.abortController = null;
        }
    }

    stop() {
        if (this.abortController) {
            this.abortController.abort();
        }
        this.isStreaming = false;
    }

    _processChunk(chunk, onStep, onAnswerToken) {
        this.partialData += chunk;
        const lines = this.partialData.split('\n');
        // 마지막 줄은 아직 완전하지 않을 수 있으므로 보존
        this.partialData = lines.pop() || '';

        for (const line of lines) {
            const trimmed = line.trim();
            if (!trimmed) continue;

            if (trimmed === 'data: [DONE]') {
                return true; // 스트림 종료
            }

            if (this._tryParseLine(trimmed, onStep, onAnswerToken)) {
                return true;
            }
        }
        return false;
    }

    _tryParseLine(line, onStep, onAnswerToken) {
        if (!line.startsWith('data: ')) return false;

        try {
            const jsonStr = line.slice(6).trim();
            if (!jsonStr || jsonStr === '[DONE]') return true;

            const data = JSON.parse(jsonStr);

            // 답변 토큰 이벤트
            if (data.step === 'answer_token' || data.type === 'answer_token') {
                if (onAnswerToken) onAnswerToken(data.data || data);
                return false;
            }

            // 일반 파이프라인 스텝 이벤트
            if (onStep) onStep(data);
            return false;
        } catch (e) {
            // JSON 파싱 실패 — 무시
            console.debug('SSE parse skip:', line.slice(0, 80));
            return false;
        }
    }
}
