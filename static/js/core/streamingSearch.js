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
        const totalSteps = this.hasAnswerGeneration ? 10 : 7;
        this.progressManager.totalSteps = totalSteps;
        
        console.log(`🎯 Streaming mode: ${this.hasAnswerGeneration ? '검색 + 답변 생성 (10단계)' : '검색만 (7단계)'}`);
        
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
        
        console.log('🔍 Step result received:', stepResult);
        console.log('📊 Current step before:', this.progressManager.currentStep, 'New step:', step);
        
        // LLM 답변 생성 모드에서 특별히 로깅
        if (this.hasAnswerGeneration && step) {
            console.log(`🤖 [Answer Generation Mode] Processing step: ${step}, Current progress: ${this.progressManager.currentStep}/${this.progressManager.totalSteps}`);
        }
        
        // 진행 과정 데이터에 저장
        const processStep = {
            step,
            message: error || message,
            data,
            timestamp,
            recordedAt: new Date().toISOString()
        };
        this.searchProcessData.push(processStep);
        console.log('Added process step:', step, '- Total steps:', this.searchProcessData.length);
        
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
                console.log(`🎯 Search completed. Answer generation mode: ${this.hasAnswerGeneration}`);
                if (this.hasAnswerGeneration) {
                    // 답변 생성 모드인 경우: 검색 완료만 표시하고 계속 진행
                    this.stepRenderer.addStep('검색 완료', message, data, 'success', timestamp);
                    console.log('🔄 Search completed, waiting for answer generation steps...');
                } else {
                    // 검색만 모드인 경우: 최종 단계로 설정하고 완료 처리
                    this.stepRenderer.addStep('검색 완료', message, data, 'success', timestamp);
                    this.progressManager.currentStep = 7; // 검색 완료 = 7단계
                    this.progressManager.updateProgress();
                }
                this.resultRenderer.renderFinalResults(data, this.searchProcessData, this.progressManager);
                break;
                
            // 답변 생성 단계들 (8-10단계)
            case 'answer_generation_start':
                console.log('🤖 Answer generation started - moving to step 8');
                this.stepRenderer.addStep('답변 생성 시작', message, null, 'info', timestamp);
                this.progressManager.currentStep = 8;
                this.progressManager.updateProgress();
                break;
                
            case 'draft_generation':
                this.stepRenderer.addStep('답변 초안 생성 중', message, null, 'loading', timestamp);
                break;
                
            case 'draft_generated':
                console.log('🎯 draft_generated event received with data:', data);
                
                // 메타데이터를 포함한 데이터 객체 생성
                const draftMetadata = data ? {
                    ...data,
                    _metadata: MetadataCreator.createAnswerMetadata(data, '초안 생성')
                } : null;
                this.stepRenderer.updateLastLoadingStep('답변 초안 생성 완료', message, draftMetadata, 'success', timestamp);
                this.progressManager.currentStep = 9;
                this.progressManager.updateProgress();
                break;
                
            case 'reflection':
                this.stepRenderer.addStep('답변 품질 검토 중', message, null, 'loading', timestamp);
                break;
                
            case 'reflection_completed':
                // 메타데이터를 포함한 데이터 객체 생성
                const reflectionMetadata = data ? {
                    ...data,
                    _metadata: MetadataCreator.createReflectionMetadata(data)
                } : null;
                
                // 품질 점수 확인 및 재시도 로직
                if (data && data.total_score !== undefined) {
                    const qualityScore = data.total_score;
                    console.log(`🎯 Quality score check: ${qualityScore}/50`);
                    
                    if (qualityScore < 35) {
                        console.log(`⚠️ Quality score ${qualityScore} is below threshold (35). Triggering retry...`);
                        this.stepRenderer.updateLastLoadingStep('답변 품질 검토 완료 (재시도 필요)', `품질 점수 ${qualityScore}/50 - 35점 이하로 재생성을 시작합니다`, reflectionMetadata, 'warning', timestamp);
                        
                        // 재시도 요청을 서버에 전송
                        this.retryManager.triggerAnswerRetry(this.retryCount, this.streamingHandler.abortController, this.stepRenderer.addStep.bind(this.stepRenderer));
                        return; // 여기서 중단하고 재시도 프로세스 시작
                    } else {
                        console.log(`✅ Quality score ${qualityScore} meets threshold (>=35). Proceeding...`);
                        this.stepRenderer.updateLastLoadingStep('답변 품질 검토 완료', message, reflectionMetadata, 'success', timestamp);
                    }
                } else {
                    // 점수 정보가 없으면 기본 처리
                    this.stepRenderer.updateLastLoadingStep('답변 품질 검토 완료', message, reflectionMetadata, 'success', timestamp);
                }
                break;
                
            case 'regenerating':
                this.stepRenderer.addStep('답변 재생성 중', message, null, 'loading', timestamp);
                break;
                
            case 'answer_completed':
                console.log('✅ Answer generation completed - step 10', data);
                // 메타데이터를 포함한 데이터 객체 생성
                const finalMetadata = data ? {
                    ...data,
                    _metadata: MetadataCreator.createFinalAnswerMetadata(data)
                } : null;
                this.stepRenderer.updateLastLoadingStep('답변 생성 완료', message, finalMetadata, 'success', timestamp);
                this.progressManager.currentStep = 10;
                this.progressManager.updateProgress();
                this.resultRenderer.renderAnswerResult(data, this.searchProcessData);
                break;
                
            case 'answer_generation_error':
                console.log('❌ Answer generation error', message);
                this.stepRenderer.updateLastLoadingStep('답변 생성 실패', message, null, 'error', timestamp);
                this.showError(message);
                break;
                
            case 'error':
                this.stepRenderer.addStep('오류 발생', error, null, 'error', timestamp);
                this.showError(error);
                break;
                
            case 'file_read_failed':
                this.stepRenderer.addStep('파일 처리 실패', message || '파일을 읽을 수 없어 텍스트만으로 검색을 진행합니다', data, 'warning', timestamp);
                break;
                
            case 'user_stopped':
                this.stepRenderer.addStep('검색 중지됨', message, null, 'warning', timestamp);
                break;
                
            default:
                console.log('Unknown step:', step);
        }
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
        toggleBtn.innerHTML = '📖 Preview';
        toggleBtn.classList.remove('active');
    } else {
        // 일반 텍스트 모드에서 Preview 모드로
        plainText.style.display = 'none';
        previewText.style.display = 'block';
        toggleBtn.innerHTML = '📝 Text';
        toggleBtn.classList.add('active');
    }
}

// window 객체에도 할당
window.toggleAnswerPreview = toggleAnswerPreview;