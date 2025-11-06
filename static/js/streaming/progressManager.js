/**
 * 검색 진행률 및 상태 관리자
 */
class ProgressManager {
    constructor(progressFill, progressText, searchProcessContainer, searchSteps) {
        this.progressFill = progressFill;
        this.progressText = progressText;
        this.searchProcessContainer = searchProcessContainer;
        this.searchSteps = searchSteps;
        this.currentStep = 0;
        this.totalSteps = 7;
    }
    
    updateProgress(currentStep = null, totalSteps = null, isRegenerating = false) {
        if (currentStep !== null) this.currentStep = currentStep;
        if (totalSteps !== null) this.totalSteps = totalSteps;
        
        // 재생성 중일 때는 진행률을 100%로 고정하되 특별한 표시
        const progress = isRegenerating ? 100 : Math.min((this.currentStep / this.totalSteps) * 100, 100);
        
        // 진행률 바에 펄스 효과 추가
        this.progressFill.classList.add('updating');
        setTimeout(() => {
            this.progressFill.classList.remove('updating');
        }, 600);
        
        this.progressFill.style.width = `${progress}%`;
        
        // 재생성 중이거나 검색 완료 시 진행바에 completed 클래스 추가
        if (this.currentStep >= this.totalSteps || isRegenerating) {
            this.progressFill.classList.add('completed');
        }
        
        console.log('Progress update:', this.currentStep, '/', this.totalSteps, isRegenerating ? '(regenerating)' : '');
        
        if (this.progressText) {
            let statusText;
            if (isRegenerating) {
                statusText = `답변 재생성 중 (${this.totalSteps}/${this.totalSteps})`;
            } else if (this.currentStep === this.totalSteps) {
                // 답변 생성 모드일 때는 "답변 생성 완료", 검색만 모드일 때는 "검색 완료"
                statusText = this.totalSteps === 10 ? 
                    `답변 생성 완료 (${this.totalSteps}/${this.totalSteps})` : 
                    `검색 완료 (${this.totalSteps}/${this.totalSteps})`;
            } else {
                statusText = `${this.currentStep}/${this.totalSteps} 단계 완료`;
            }
            this.progressText.textContent = statusText;
        }
    }
    
    makeCollapsible() {
        // 검색 진행 상황을 접을 수 있도록 토글 버튼 추가
        const header = this.searchProcessContainer.querySelector('.search-process-header');
        if (header && !header.querySelector('.toggle-button')) {
            const toggleButton = document.createElement('button');
            toggleButton.className = 'toggle-button';
            toggleButton.innerHTML = '진행 과정 숨기기';
            toggleButton.onclick = () => {
                const steps = this.searchSteps;
                if (steps.style.display === 'none') {
                    steps.style.display = 'block';
                    toggleButton.innerHTML = '진행 과정 숨기기';
                } else {
                    steps.style.display = 'none';
                    toggleButton.innerHTML = '진행 과정 보기';
                }
            };
            
            header.appendChild(toggleButton);
        }
    }
    
    reset() {
        this.currentStep = 0;
        this.totalSteps = 7;
        
        // 진행바 completed 클래스 제거
        if (this.progressFill) {
            this.progressFill.classList.remove('completed');
        }
        
        this.updateProgress();
    }
    
    clearProcess() {
        // 진행 과정만 초기화 (결과는 유지)
        this.currentStep = 0;
        this.totalSteps = 7;
        
        // 히스토리 복원 모드 클래스 제거
        if (this.searchProcessContainer) {
            this.searchProcessContainer.classList.remove('history-restore');
        }
        
        // 진행바 completed 클래스 제거
        if (this.progressFill) {
            this.progressFill.classList.remove('completed');
        }
        
        this.updateProgress();
        
        if (this.searchSteps) {
            this.searchSteps.innerHTML = '';
        }
    }
    
    showError(message, stepRenderer = null) {
        console.error('Progress error:', message);
        if (stepRenderer) {
            stepRenderer.addStep('오류', message, null, 'error', null);
        }
    }
}

// 전역 사용을 위한 export
window.ProgressManager = ProgressManager;
console.log('✅ ProgressManager loaded');