/**
 * 실시간 스트리밍 검색 컨트롤러 (v2.0 - Refactored)
 */
class StreamingSearchController {
    constructor() {
        // DOM 요소들
        this.searchProcessContainer = document.getElementById('searchProcessContainer');
        this.searchSteps = document.getElementById('searchSteps');
        this.progressFill = document.getElementById('progressFill');
        this.progressText = document.getElementById('progressText');
        
        // 상태 관리
        this.isStreaming = false;
        this.hasAnswerGeneration = false;
        this.searchProcessData = [];
        this.retryCount = 0;
        this.draftCount = 0; // 초안 생성 횟수 추적
        this.isRegenerating = false; // 재생성 중 상태 추적
        
        // 모듈 인스턴스 생성
        this.progressManager = new ProgressManager(
            this.progressFill, 
            this.progressText, 
            this.searchProcessContainer, 
            this.searchSteps
        );
        this.streamingHandler = new StreamingHandler();
        this.stepRenderer = new SearchStepRenderer(this.searchSteps);
        this.resultRenderer = new SearchResultRenderer();
        this.retryManager = new RetryManager(this);
    }
    
    async startStreamingSearch(formData) {
        if (this.isStreaming) {
            console.log('Search already in progress');
            return;
        }
        
        this.isStreaming = true;
        
        // 답변 생성 모드 확인 및 총 단계 수 설정
        this.hasAnswerGeneration = formData.get('generate_answer') === 'true';
        const totalSteps = this.hasAnswerGeneration ? 9 : 7; // 최대 2회 시도로 단계 수 조정
        this.progressManager.totalSteps = totalSteps;
        
        console.log(`🎯 Streaming mode: ${this.hasAnswerGeneration ? '검색 + 답변 생성 (최대 9단계)' : '검색만 (7단계)'}`);
        
        // 초기화
        this.searchProcessData = [];
        this.retryCount = 0;
        
        // UI 초기화
        this.initializeUI();
        
        try {
            await this.streamingHandler.startStreaming(
                '/api/v1/search/multimodal/stream',
                formData,
                this.hasAnswerGeneration,
                (stepResult) => this.handleStepResult(stepResult),
                (error) => this.showError(error)
            );
        } catch (error) {
            console.error('Streaming search failed:', error);
            this.showError(`스트리밍 검색 실패: ${error.message}`);
        } finally {
            console.log('🔚 Streaming finally block - setting isStreaming to false');
            this.isStreaming = false;
            
            // 검색 완료 시 버튼 상태 복원
            if (window.searchController && window.searchController.restoreButtonState) {
                window.searchController.restoreButtonState();
            }
        }
    }
    
    initializeUI() {
        // 히스토리 복원 모드 클래스 제거 (실시간 검색 시작)
        this.searchProcessContainer.classList.remove('history-restore');
        
        // 검색 과정 컨테이너 표시
        this.searchProcessContainer.style.display = 'block';
        this.searchSteps.innerHTML = '';
        this.progressManager.currentStep = 0;
        this.progressManager.updateProgress();
        
        // AI 답변 레이어 숨김 (새 검색 시작)
        const aiAnswerContainer = document.getElementById('aiAnswerContainer');
        if (aiAnswerContainer) {
            aiAnswerContainer.style.display = 'none';
        }
    }
    
    stopSearch() {
        if (this.streamingHandler && this.isStreaming) {
            console.log('🛑 Stopping search...');
            
            // 진행 중인 loading 상태의 단계들을 정리
            this.stepRenderer.cleanupLoadingSteps();
            
            this.streamingHandler.stop();
        }
    }
    
    handleStepResult(stepResult) {
        const { step, message, data, timestamp, error } = stepResult;
        
        console.log(`🔍 Step: ${step} (${this.progressManager.currentStep}/${this.progressManager.totalSteps})`);
        
        // 진행 과정 데이터에 저장
        const processStep = {
            step,
            message: error || message,
            data,
            timestamp,
            recordedAt: new Date().toISOString()
        };
        this.searchProcessData.push(processStep);
        
        // 단계별 처리
        this.processStep(step, message, data, timestamp, error);
        
        this.progressManager.updateProgress();
    }
    
    processStep(step, message, data, timestamp, error) {
        switch (step) {
            // 검색 단계들 (1-7단계)
            case 'start':
                this.stepRenderer.addStep('검색 시작', message, data, 'info', timestamp);
                this.progressManager.currentStep = 1;
                this.progressManager.updateProgress();
                break;
                
            case 'input_processing':
                this.stepRenderer.addStep('입력 처리 중', message, null, 'loading', timestamp);
                break;
                
            case 'input_processed':
                this.stepRenderer.updateLastLoadingStep('입력 처리 완료', message, data, 'success', timestamp);
                this.progressManager.currentStep = 2;
                this.progressManager.updateProgress();
                break;
                
            case 'query_analysis':
                this.stepRenderer.addStep('쿼리 분석 중', message, null, 'loading', timestamp);
                break;
                
            case 'query_analyzed':
                this.stepRenderer.updateLastLoadingStep('쿼리 분석 완료', message, data, 'success', timestamp);
                this.progressManager.currentStep = 3;
                this.progressManager.updateProgress();
                break;
                
            case 'feature_extraction':
                this.stepRenderer.addStep('특징 추출 중', message, null, 'loading', timestamp);
                break;
                
            case 'features_extracted':
                this.stepRenderer.updateLastLoadingStep('특징 추출 완료', message, data, 'success', timestamp);
                this.progressManager.currentStep = 4;
                this.progressManager.updateProgress();
                break;
                
            case 'embedding_generation':
                this.stepRenderer.addStep('임베딩 생성 중', message, null, 'loading', timestamp);
                break;
                
            case 'embeddings_generated':
                this.stepRenderer.updateLastLoadingStep('임베딩 생성 완료', message, data, 'success', timestamp);
                this.progressManager.currentStep = 5;
                this.progressManager.updateProgress();
                break;
                
            case 'search_execution':
                this.stepRenderer.addStep('검색 실행 중', message, null, 'loading', timestamp);
                break;
                
            case 'search_executed':
                this.stepRenderer.updateLastLoadingStep('검색 실행 완료', message, data, 'success', timestamp);
                this.progressManager.currentStep = 6;
                this.progressManager.updateProgress();
                break;
                
            case 'result_enrichment':
                this.stepRenderer.addStep('결과 보강 중', message, null, 'loading', timestamp);
                break;
                
            case 'result_enriched':
                this.stepRenderer.updateLastLoadingStep('결과 보강 완료', message, data, 'success', timestamp);
                this.progressManager.currentStep = 7;
                this.progressManager.updateProgress();
                break;
                
            case 'completed':
                console.log(`🎯 Search completed (answer mode: ${this.hasAnswerGeneration})`);
                if (this.hasAnswerGeneration) {
                    // 답변 생성 모드인 경우: 검색 완료만 표시하고 계속 진행
                    this.stepRenderer.addStep('검색 완료', message, data, 'success', timestamp);
                } else {
                    // 검색만 모드인 경우: 최종 단계로 설정하고 완료 처리
                    this.stepRenderer.addStep('검색 완룼', message, data, 'success', timestamp);
                    this.progressManager.currentStep = 7; // 검색 완료 = 7단계
                    this.progressManager.updateProgress();
                }
                this.resultRenderer.renderFinalResults(data, this.searchProcessData, this.progressManager);
                break;
                
            // 답변 생성 단계들 (8-10단계)
            case 'answer_generation_start':
                console.log('🤖 Answer generation started');
                this.stepRenderer.addStep('답변 생성 시작', message, null, 'info', timestamp);
                this.progressManager.currentStep = 8;
                this.progressManager.updateProgress();
                break;
                
            case 'draft_generation':
                this.stepRenderer.addStep('답변 초안 생성 중', message, null, 'loading', timestamp);
                break;
                
            case 'draft_generated':
                console.log('🎯 Draft generated:', data?.answer_length || 0, 'chars');
                
                this.draftCount++;
                const isRegenerated = this.draftCount > 1;
                const draftTitle = isRegenerated ? 
                    `답변 초안 재생성 완료 (${this.draftCount}회차)` : 
                    '답변 초안 생성 완료';
                
                // 메타데이터를 포함한 데이터 객체 생성
                const draftMetadata = data ? {
                    ...data,
                    _metadata: MetadataCreator.createAnswerMetadata(data, isRegenerated ? `초안 재생성 (${this.draftCount}회차)` : '초안 생성')
                } : null;
                
                if (isRegenerated) {
                    // 재생성된 초안은 새로운 단계로 추가
                    this.stepRenderer.addStep(draftTitle, message, draftMetadata, 'success', timestamp);
                } else {
                    // 첫 번째 초안은 기존 로딩 단계 업데이트
                    this.stepRenderer.updateLastLoadingStep(draftTitle, message, draftMetadata, 'success', timestamp);
                    this.progressManager.currentStep = 9;
                    this.progressManager.updateProgress();
                }
                break;
                
            case 'reflection':
                this.stepRenderer.addStep('답변 품질 검토 중', message, null, 'loading', timestamp);
                break;
                
            case 'reflection_completed':
                // 메타데이터를 포함한 데이터 객체 생성
                const reflectionMetadata = data ? {
                    ...data,
                    _metadata: MetadataCreator.createReflectionMetadata(data, this.draftCount)
                } : null;
                
                // 품질 점수 정보 표시 (재시도 로직은 백엔드에서 자동 처리)
                if (data && data.total_score !== undefined) {
                    const qualityScore = data.total_score;
                    const isAcceptable = qualityScore >= 35;
                    console.log(`🎯 Quality: ${qualityScore}/50 ${isAcceptable ? 'ACCEPTABLE' : 'NEEDS_IMPROVEMENT'}`);
                    
                    const reflectionTitle = this.draftCount > 1 ? 
                        `답변 품질 검토 완료 (${this.draftCount}회차)` : 
                        '답변 품질 검토 완료';
                    
                    let reflectionMessage;
                    let reflectionStatus;
                    
                    if (isAcceptable) {
                        reflectionMessage = `품질 점수 ${qualityScore}/50 - 기준 충족으로 답변 완료`;
                        reflectionStatus = 'success';
                    } else {
                        if (this.draftCount === 1) {
                            reflectionMessage = `품질 점수 ${qualityScore}/50 - 35점 미만으로 재생성 진행`;
                            reflectionStatus = 'warning';
                        } else {
                            reflectionMessage = `품질 점수 ${qualityScore}/50 - 최대 시도 완료, 최고 점수 답변 선택`;
                            reflectionStatus = 'info';
                        }
                    }
                    
                    if (this.draftCount > 1) {
                        // 재생성된 검토는 새로운 단계로 추가
                        this.stepRenderer.addStep(reflectionTitle, reflectionMessage, reflectionMetadata, reflectionStatus, timestamp);
                    } else {
                        // 첫 번째 검토는 기존 로딩 단계 업데이트
                        this.stepRenderer.updateLastLoadingStep(reflectionTitle, reflectionMessage, reflectionMetadata, reflectionStatus, timestamp);
                    }
                } else {
                    // 점수 정보가 없으면 기본 처리
                    const reflectionTitle = this.draftCount > 1 ? 
                        `답변 품질 검토 완료 (${this.draftCount}회차)` : 
                        '답변 품질 검토 완료';
                    
                    if (this.draftCount > 1) {
                        this.stepRenderer.addStep(reflectionTitle, message, reflectionMetadata, 'success', timestamp);
                    } else {
                        this.stepRenderer.updateLastLoadingStep(reflectionTitle, message, reflectionMetadata, 'success', timestamp);
                    }
                }
                break;
                
            case 'regenerating':
                console.log('🔄 Regenerating attempt - final attempt (2/2)');
                this.isRegenerating = true;
                const regenerationTitle = `답변 재생성 중 (2차 시도 - 최종)`;
                this.stepRenderer.addStep(regenerationTitle, message || '품질 개선을 위해 마지막 재생성을 진행합니다', null, 'loading', timestamp);
                // 재생성 중임을 진행률에 반영
                this.progressManager.updateProgress(null, null, true);
                break;
                
            case 'answer_completed':
                console.log('✅ Answer completed');
                
                // 🔧 스트리밍 상태 해제 (중복 요청 방지)
                console.log('🔚 Answer completed - setting isStreaming to false');
                this.isStreaming = false;
                
                // 최종 답변 선택 정보 로깅
                if (data) {
                    const bestAttempt = data.best_attempt || 'unknown';
                    const bestScore = data.best_score || 'unknown';
                    const completionReason = data.completion_reason || 'unknown';
                    console.log(`🏆 Final answer selected: attempt ${bestAttempt}, score ${bestScore}/50, reason: ${completionReason}`);
                }
                
                // 메타데이터를 포함한 데이터 객체 생성
                const finalMetadata = data ? {
                    ...data,
                    _metadata: MetadataCreator.createFinalAnswerMetadata(data)
                } : null;
                
                // 완료 메시지 생성
                let completionTitle;
                let completionMessage = message;
                
                if (data && data.best_attempt && data.best_score !== undefined) {
                    if (data.completion_reason === 'quality_accepted') {
                        completionTitle = `답변 생성 완료 (${data.best_attempt}차 시도 성공)`;
                        completionMessage = `품질 기준 충족으로 답변이 완료되었습니다 (점수: ${data.best_score}/50)`;
                    } else if (data.completion_reason === 'best_score_selected') {
                        completionTitle = `답변 생성 완료 (최고 점수 답변 선택)`;
                        completionMessage = `${data.total_attempts}번의 시도 중 ${data.best_attempt}차 답변을 선택했습니다 (점수: ${data.best_score}/50)`;
                    } else {
                        completionTitle = '답변 생성 완료';
                    }
                } else {
                    // 재생성 중이었다면 regenerating 단계를 완료로 업데이트
                    const hasRegeneratingStep = Array.from(this.searchSteps.querySelectorAll('.search-step.loading .step-title'))
                        .some(title => title.textContent.includes('재생성 중'));
                    
                    completionTitle = hasRegeneratingStep ? '답변 재생성 완료' : '답변 생성 완료';
                }
                
                this.stepRenderer.updateLastLoadingStep(completionTitle, completionMessage, finalMetadata, 'success', timestamp);
                
                this.progressManager.currentStep = this.progressManager.totalSteps; // 동적으로 설정
                
                // 재생성 상태 해제
                this.isRegenerating = false;
                this.progressManager.updateProgress(null, null, false);
                
                // 최종 완료 시 남아있는 중간 로딩 단계들 숨김
                this.stepRenderer.hideCompletedLoadingSteps();
                
                // 재생성이 진행 중이 아닐 때만 최종 답변 렌더링
                const shouldRenderFinalAnswer = this.shouldRenderFinalAnswer(data);
                console.log('🤖 Should render:', shouldRenderFinalAnswer);
                
                if (shouldRenderFinalAnswer) {
                    this.resultRenderer.renderAnswerResult(data, this.searchProcessData);
                }
                
                // 검색 완료 시 버튼 상태 복원
                if (window.searchController && window.searchController.restoreButtonState) {
                    window.searchController.restoreButtonState();
                }
                break;
                
            case 'answer_generation_error':
                console.error('❌ Answer generation failed:', message);
                
                // 🔧 스트리밍 상태 해제 (중복 요청 방지)
                console.log('🔚 Answer generation error - setting isStreaming to false');
                this.isStreaming = false;
                
                this.stepRenderer.updateLastLoadingStep('답변 생성 실패', message, null, 'error', timestamp);
                
                // 검색 완료 시 버튼 상태 복원
                if (window.searchController && window.searchController.restoreButtonState) {
                    window.searchController.restoreButtonState();
                }
                this.showError(message);
                break;
                
            case 'error':
                // 🔧 스트리밍 상태 해제 (중복 요청 방지)
                console.log('🔚 General error - setting isStreaming to false');
                this.isStreaming = false;
                
                this.stepRenderer.addStep('오류 발생', error, null, 'error', timestamp);
                this.showError(error);
                
                // 검색 완료 시 버튼 상태 복원
                if (window.searchController && window.searchController.restoreButtonState) {
                    window.searchController.restoreButtonState();
                }
                break;
                
            case 'file_read_failed':
                this.stepRenderer.addStep('파일 처리 실패', message || '파일을 읽을 수 없어 텍스트만으로 검색을 진행합니다', data, 'warning', timestamp);
                break;
                
            case 'user_stopped':
                this.stepRenderer.addStep('검색 중지됨', message, null, 'warning', timestamp);
                break;
                
            default:
                console.warn('Unknown step:', step);
        }
    }
    
    shouldRenderFinalAnswer(data) {
        // 재생성이 진행 중이면 렌더링하지 않음
        if (this.isRegenerating) {
            console.log('🚫 Not rendering - regeneration in progress');
            return false;
        }
        
        // 백엔드에서 is_final 플래그를 보내는 경우 이를 우선 사용
        if (data && typeof data.is_final === 'boolean') {
            if (data.is_final) {
                const reason = data.completion_reason || 'unknown';
                const bestScore = data.best_score || 'unknown';
                const bestAttempt = data.best_attempt || 'unknown';
                console.log(`🎯 Final answer ready - reason: ${reason}, best attempt: ${bestAttempt}, score: ${bestScore}/50`);
            }
            return data.is_final;
        }
        
        // 기본적으로는 렌더링하지 않음 (is_final 플래그 없으면 계속 진행 중)
        console.log('⏳ Not rendering - waiting for completion signal');
        return false;
    }
    
    addMetadataToLastStep(metadata) {
        this.stepRenderer.addMetadataToLastStep(metadata);
    }
    
    showError(message, timestamp = null) {
        console.error('Streaming error:', message);
        this.stepRenderer.addStep('오류', message, null, 'error', timestamp);
        this.isStreaming = false;
    }
    
    reset() {
        this.streamingHandler.reset();
        this.progressManager.reset();
        this.isStreaming = false;
        this.hasAnswerGeneration = false;
        this.searchProcessData = [];
        this.draftCount = 0;
        this.isRegenerating = false;
        
        if (this.searchSteps) {
            this.searchSteps.innerHTML = '';
        }
        
        if (this.searchProcessContainer) {
            this.searchProcessContainer.style.display = 'none';
        }
    }
    
    clearProcess() {
        // 진행 과정만 초기화 (결과는 유지)
        this.searchProcessData = [];
        this.progressManager.clearProcess();
        this.hasAnswerGeneration = false;
        this.draftCount = 0;
        this.isRegenerating = false;
    }
}

// 전역 인스턴스 생성
try {
    window.streamingSearchController = new StreamingSearchController();
    console.log('✅ StreamingSearchController initialized successfully');
} catch (error) {
    console.error('❌ Failed to initialize StreamingSearchController:', error);
}

// Preview 토글 전역 함수
function toggleAnswerPreview(answerId) {
    const plainText = document.getElementById(`${answerId}-plain`);
    const previewText = document.getElementById(`${answerId}-preview`);
    const toggleBtn = document.querySelector(`[onclick="toggleAnswerPreview('${answerId}')"]`);
    
    if (!plainText || !previewText || !toggleBtn) {
        console.error('Preview toggle elements not found:', {
            answerId,
            plainText: !!plainText,
            previewText: !!previewText,
            toggleBtn: !!toggleBtn,
            plainTextId: `${answerId}-plain`,
            previewTextId: `${answerId}-preview`
        });
        return;
    }
    
    if (plainText.style.display === 'none') {
        // Preview 모드에서 일반 텍스트 모드로
        plainText.style.display = 'block';
        previewText.style.display = 'none';
        toggleBtn.innerHTML = 'Preview';
        toggleBtn.classList.remove('active');
    } else {
        // 일반 텍스트 모드에서 Preview 모드로
        plainText.style.display = 'none';
        previewText.style.display = 'block';
        toggleBtn.innerHTML = 'Text';
        toggleBtn.classList.add('active');
    }
}

// window 객체에도 할당
window.toggleAnswerPreview = toggleAnswerPreview;