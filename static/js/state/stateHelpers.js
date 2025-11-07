/**
 * 상태 관리 헬퍼 함수들
 * 자주 사용되는 상태 조작을 편리하게 해주는 유틸리티
 */

/**
 * 검색 상태 헬퍼
 */
window.searchState = {
    // 검색 시작
    startSearch(query, hasAnswerGeneration = false) {
        window.stateManager.setBatch({
            'search.isSearching': true,
            'search.isStreaming': true,
            'search.currentQuery': query,
            'answerGeneration.hasAnswerGeneration': hasAnswerGeneration,
            'progress.isVisible': true,
            'progress.currentStep': 0,
            'progress.totalSteps': hasAnswerGeneration ? 9 : 7
        });
    },
    
    // 검색 완료
    completeSearch(results) {
        window.stateManager.setBatch({
            'search.isSearching': false,
            'search.isStreaming': false,
            'search.results': results,
            'progress.currentStep': window.stateManager.get('progress.totalSteps')
        });
        
        // 검색 히스토리에 추가
        this.addToHistory(window.stateManager.get('search.currentQuery'));
    },
    
    // 검색 오류
    errorSearch(error) {
        window.stateManager.setBatch({
            'search.isSearching': false,
            'search.isStreaming': false,
            'errors.lastError': error
        });
    },
    
    // 파일 선택
    selectFile(type, file) {
        window.stateManager.set(`search.selectedFiles.${type}`, file);
    },
    
    // 파일 제거
    removeFile(type) {
        window.stateManager.set(`search.selectedFiles.${type}`, null);
    },
    
    // 모든 파일 제거
    clearFiles() {
        window.stateManager.setBatch({
            'search.selectedFiles.image': null,
            'search.selectedFiles.video': null,
            'search.selectedFiles.audio': null,
            'search.selectedFiles.text_file': null
        });
    },
    
    // 검색 히스토리에 추가
    addToHistory(query) {
        if (!query || query.trim() === '') return;
        
        const history = window.stateManager.get('search.searchHistory') || [];
        const newHistory = [
            { query: query.trim(), timestamp: Date.now() },
            ...history.filter(item => item.query !== query.trim())
        ].slice(0, 10); // 최근 10개만 유지
        
        window.stateManager.set('search.searchHistory', newHistory, true);
    },
    
    // 파일 존재 여부 확인
    hasFiles() {
        const files = window.stateManager.get('search.selectedFiles');
        return Object.values(files).some(file => file !== null);
    },
    
    // 선택된 파일들 가져오기
    getSelectedFiles() {
        return window.stateManager.get('search.selectedFiles');
    }
};

/**
 * 답변 생성 상태 헬퍼
 */
window.answerState = {
    // 답변 생성 시작
    startGeneration() {
        window.stateManager.setBatch({
            'answerGeneration.isGenerating': true,
            'answerGeneration.currentDraftCount': 0,
            'search.isRegenerating': false
        });
    },
    
    // 초안 생성 완료
    completeDraft(attemptNumber) {
        window.stateManager.setBatch({
            'answerGeneration.currentDraftCount': attemptNumber,
            'search.isRegenerating': attemptNumber > 1
        });
    },
    
    // 답변 생성 완료
    completeGeneration(data) {
        window.stateManager.setBatch({
            'answerGeneration.isGenerating': false,
            'search.isRegenerating': false,
            'search.isStreaming': false,
            'answerGeneration.completionReason': data.completion_reason,
            'answerGeneration.bestAttempt': data.best_attempt,
            'answerGeneration.bestScore': data.best_score
        });
    },
    
    // 재생성 시작
    startRegeneration() {
        window.stateManager.set('search.isRegenerating', true);
    },
    
    // 답변 생성 오류
    errorGeneration(error) {
        window.stateManager.setBatch({
            'answerGeneration.isGenerating': false,
            'search.isRegenerating': false,
            'search.isStreaming': false,
            'errors.lastError': error
        });
    }
};

/**
 * 진행 상황 상태 헬퍼
 */
window.progressState = {
    // 진행 단계 업데이트
    updateStep(step, message = null) {
        window.stateManager.set('progress.currentStep', step);
        
        if (message) {
            const progressData = window.stateManager.get('progress.progressData') || [];
            progressData.push({
                step,
                message,
                timestamp: Date.now()
            });
            window.stateManager.set('progress.progressData', progressData);
        }
    },
    
    // 진행률 표시/숨김
    setVisible(visible) {
        window.stateManager.set('progress.isVisible', visible);
    },
    
    // 진행 데이터 초기화
    reset() {
        window.stateManager.setBatch({
            'progress.currentStep': 0,
            'progress.progressData': [],
            'progress.isVisible': false
        });
    }
};

/**
 * UI 상태 헬퍼
 */
window.uiState = {
    // 로딩 상태 설정
    setLoading(loading) {
        window.stateManager.set('ui.isLoading', loading);
    },
    
    // 테마 변경
    setTheme(theme) {
        window.stateManager.set('ui.theme', theme, true);
        document.documentElement.setAttribute('data-theme', theme);
    },
    
    // 알림 추가
    addNotification(message, type = 'info', duration = 5000) {
        const notifications = window.stateManager.get('ui.notifications') || [];
        const notification = {
            id: Date.now(),
            message,
            type,
            timestamp: Date.now()
        };
        
        notifications.push(notification);
        window.stateManager.set('ui.notifications', notifications);
        
        // 자동 제거
        if (duration > 0) {
            setTimeout(() => {
                this.removeNotification(notification.id);
            }, duration);
        }
        
        return notification.id;
    },
    
    // 알림 제거
    removeNotification(id) {
        const notifications = window.stateManager.get('ui.notifications') || [];
        const filtered = notifications.filter(n => n.id !== id);
        window.stateManager.set('ui.notifications', filtered);
    },
    
    // 모든 알림 제거
    clearNotifications() {
        window.stateManager.set('ui.notifications', []);
    }
};

/**
 * 설정 상태 헬퍼
 */
window.settingsState = {
    // 검색 설정 업데이트
    updateSearchSettings(settings) {
        const currentSettings = window.stateManager.get('settings');
        const newSettings = { ...currentSettings, ...settings };
        window.stateManager.set('settings', newSettings, true);
    },
    
    // 설정 초기화
    reset() {
        const defaultSettings = window.stateManager.getDefaultValue('settings');
        window.stateManager.set('settings', defaultSettings, true);
    }
};

/**
 * 전역 상태 조작 단축 함수들
 */
window.useState = {
    // 상태 가져오기
    get: (path) => window.stateManager.get(path),
    
    // 상태 설정하기
    set: (path, value, persist = false) => window.stateManager.set(path, value, persist),
    
    // 배치 업데이트
    setBatch: (updates, persist = false) => window.stateManager.setBatch(updates, persist),
    
    // 구독하기
    subscribe: (path, callback) => window.stateManager.subscribe(path, callback),
    
    // 초기화
    reset: (path = null) => window.stateManager.reset(path),
    
    // 디버그
    debug: () => window.stateManager.debug()
};

console.log('✅ State helpers initialized');