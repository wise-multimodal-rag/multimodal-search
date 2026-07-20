/**
 * ChatController — 메인 오케스트레이터
 * 메시지 전송 → SSE 스트림 시작 → 이벤트를 각 컴포넌트에 분배
 */
class ChatController {
    constructor({ conversationManager, streamHandler, messageList, chatBubble, chatInput, pipelinePanel, evidenceCard, scoreBreakdown, sidebar }) {
        this.convManager = conversationManager;
        this.streamHandler = streamHandler;
        this.messageList = messageList;
        this.chatBubble = chatBubble;
        this.chatInput = chatInput;
        this.pipelinePanel = pipelinePanel;
        this.evidenceCard = evidenceCard;
        this.scoreBreakdown = scoreBreakdown;
        this.sidebar = sidebar;

        this.currentMessageId = null;
        this.answerBuffer = '';
        this.searchResults = null;
    }

    async sendMessage(text) {
        // 대화가 없으면 생성
        if (!this.convManager.getCurrent()) {
            this.convManager.create();
            this.sidebar.render();
        }

        const files = window.chatApp.filePreview.getFiles();

        // 사용자 메시지 추가
        this.convManager.addMessage('user', text, { files });
        const userBubble = this.chatBubble.createUserBubble(text, files);
        this.messageList.appendBubble(userBubble);

        // AI 메시지 슬롯 생성
        const assistantMsg = this.convManager.addMessage('assistant', '', {});
        this.currentMessageId = assistantMsg.id;
        const aiBubble = this.chatBubble.createAssistantBubble(assistantMsg.id);
        this.messageList.appendBubble(aiBubble);

        // 입력 초기화
        this.chatInput.clear();
        window.chatApp.filePreview.clear();
        this.chatInput.setDisabled(true);

        // 파이프라인 리셋
        this.pipelinePanel.reset();
        this.answerBuffer = '';
        this.searchResults = null;

        // FormData 구성
        const formData = this._buildFormData(text, files);

        // SSE 스트리밍 시작
        await this.streamHandler.startStreaming('/api/search/multimodal/stream', formData, {
            onStep: (data) => this._handleStep(data),
            onAnswerToken: (data) => this._handleAnswerToken(data),
            onComplete: () => this._handleComplete(),
            onError: (error) => this._handleError(error),
        });
    }

    stopStreaming() {
        this.streamHandler.stop();
        this.chatInput.setDisabled(false);
        this.chatInput.focus();
    }

    _buildFormData(text, files) {
        const formData = new FormData();
        formData.append('text_query', text);
        formData.append('max_results', '10');
        formData.append('include_chunk_meta', 'true');
        formData.append('include_media_meta', 'true');
        formData.append('generate_answer', 'true');

        // 대화 맥락 (이전 턴들)
        const context = this.convManager.getConversationContext(5);
        if (context.length > 2) { // 현재 턴 제외 이전 메시지가 있을 때만
            formData.append('conversation_context', JSON.stringify(context.slice(0, -2)));
        }

        // 파일 첨부
        if (files.image) formData.append('image', files.image);
        if (files.video) formData.append('video', files.video);
        if (files.audio) formData.append('audio', files.audio);

        return formData;
    }

    _handleStep(data) {
        const step = data.step || data.type || '';

        // 파이프라인 패널 업데이트
        this.pipelinePanel.addStep(data);

        // 검색 완료 시 결과 저장
        if (step === 'completed' && data.data?.results) {
            this.searchResults = data.data.results;
        }

        // 답변 생성 관련 이벤트
        if (step === 'draft_generation' && data.data?.answer) {
            this.answerBuffer = data.data.answer;
            this.chatBubble.updateAssistantContent(this.currentMessageId, this.answerBuffer, true);
            this.messageList.scrollToBottom();
        }

        if (step === 'answer_completed' && data.data?.final_answer) {
            this.answerBuffer = data.data.final_answer;
            this.chatBubble.updateAssistantContent(this.currentMessageId, this.answerBuffer, false);

            // 근거 카드 렌더
            if (this.searchResults) {
                this.evidenceCard.renderEvidence(this.currentMessageId, this.searchResults);
            }
            this.messageList.scrollToBottom();
        }
    }

    _handleAnswerToken(data) {
        const token = data.token || data.content || '';
        if (token) {
            this.answerBuffer += token;
            this.chatBubble.updateAssistantContent(this.currentMessageId, this.answerBuffer, true);
            this.messageList.scrollToBottom();
        }
    }

    _handleComplete() {
        // 답변이 아직 스트리밍 중이었으면 최종 렌더
        if (this.answerBuffer) {
            this.chatBubble.updateAssistantContent(this.currentMessageId, this.answerBuffer, false);
        }

        // 근거 카드가 아직 안 그려졌으면 렌더
        if (this.searchResults) {
            this.evidenceCard.renderEvidence(this.currentMessageId, this.searchResults);
        }

        // 대화 저장
        this.convManager.updateLastAssistantMessage(this.answerBuffer, {
            evidence: this.searchResults,
        });

        this.sidebar.render();
        this.chatInput.setDisabled(false);
        this.chatInput.focus();
        this.messageList.scrollToBottom();
    }

    _handleError(error) {
        const errorMsg = `⚠️ 오류가 발생했습니다: ${error.message || '알 수 없는 오류'}`;
        this.chatBubble.updateAssistantContent(this.currentMessageId, errorMsg, false);
        this.convManager.updateLastAssistantMessage(errorMsg, {});
        this.chatInput.setDisabled(false);
        this.chatInput.focus();
    }
}
