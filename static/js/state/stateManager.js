/**
 * 중앙집중식 상태 관리자
 * 애플리케이션의 모든 상태를 중앙에서 관리하고 변경사항을 추적
 */
class StateManager {
    constructor() {
        // 초기 상태 정의
        this.state = {
            // 검색 관련 상태
            search: {
                isSearching: false,
                isStreaming: false,
                isRegenerating: false,
                currentQuery: '',
                selectedFiles: {
                    image: null,
                    video: null,
                    audio: null,
                    text_file: null
                },
                results: null,
                searchHistory: []
            },
            
            // UI 관련 상태
            ui: {
                theme: 'auto',
                sidebarCollapsed: false,
                activeTab: 'search',
                isLoading: false,
                notifications: []
            },
            
            // 답변 생성 관련 상태
            answerGeneration: {
                isGenerating: false,
                hasAnswerGeneration: false,
                currentDraftCount: 0,
                completionReason: null,
                bestAttempt: null,
                bestScore: null
            },
            
            // 진행 상황 관련 상태
            progress: {
                currentStep: 0,
                totalSteps: 7,
                progressData: [],
                isVisible: false
            },
            
            // 설정 관련 상태
            settings: {
                maxResults: 10,
                includeChunkMeta: true,
                includeMediaMeta: true,
                temperature: 0.7,
                maxRetries: 1
            },
            
            // 오류 관련 상태
            errors: {
                lastError: null,
                errorHistory: []
            }
        };
        
        // 상태 변경 구독자들
        this.subscribers = new Map();
        
        // 상태 변경 히스토리 (디버깅용)
        this.history = [];
        this.maxHistorySize = 50;
        
        // 로컬 스토리지 키
        this.storageKey = 'multimodal-search-state';
        
        // 상태 복원
        this.restoreState();
        
        console.log('✅ StateManager initialized');
    }
    
    /**
     * 상태 가져오기 (점 표기법 지원)
     * @param {string} path - 상태 경로 (예: 'search.isSearching')
     * @returns {*} 상태값
     */
    get(path) {
        const keys = path.split('.');
        let value = this.state;
        
        for (const key of keys) {
            if (value && typeof value === 'object' && key in value) {
                value = value[key];
            } else {
                return undefined;
            }
        }
        
        return value;
    }
    
    /**
     * 상태 설정 (점 표기법 지원)
     * @param {string} path - 상태 경로
     * @param {*} value - 설정할 값
     * @param {boolean} persist - 로컬 스토리지 저장 여부
     */
    set(path, value, persist = false) {
        const keys = path.split('.');
        const lastKey = keys.pop();
        let current = this.state;
        
        // 중간 경로 생성
        for (const key of keys) {
            if (!current[key] || typeof current[key] !== 'object') {
                current[key] = {};
            }
            current = current[key];
        }
        
        const oldValue = current[lastKey];
        current[lastKey] = value;
        
        // 히스토리 추가
        this.addToHistory(path, oldValue, value);
        
        // 구독자들에게 알림
        this.notifySubscribers(path, value, oldValue);
        
        // 로컬 스토리지 저장
        if (persist) {
            this.persistState();
        }
        
        console.log(`🔄 State updated: ${path} =`, value);
    }
    
    /**
     * 여러 상태 동시 업데이트
     * @param {Object} updates - 업데이트할 상태들 {path: value}
     * @param {boolean} persist - 로컬 스토리지 저장 여부
     */
    setBatch(updates, persist = false) {
        const changes = [];
        
        for (const [path, value] of Object.entries(updates)) {
            const oldValue = this.get(path);
            this.set(path, value, false); // 개별 저장은 하지 않음
            changes.push({ path, oldValue, newValue: value });
        }
        
        if (persist) {
            this.persistState();
        }
        
        console.log('🔄 Batch state update:', changes);
    }
    
    /**
     * 상태 변경 구독
     * @param {string} path - 구독할 상태 경로
     * @param {Function} callback - 콜백 함수 (newValue, oldValue, path) => void
     * @returns {Function} 구독 해제 함수
     */
    subscribe(path, callback) {
        if (!this.subscribers.has(path)) {
            this.subscribers.set(path, new Set());
        }
        
        this.subscribers.get(path).add(callback);
        
        // 구독 해제 함수 반환
        return () => {
            const pathSubscribers = this.subscribers.get(path);
            if (pathSubscribers) {
                pathSubscribers.delete(callback);
                if (pathSubscribers.size === 0) {
                    this.subscribers.delete(path);
                }
            }
        };
    }
    
    /**
     * 구독자들에게 변경사항 알림
     */
    notifySubscribers(path, newValue, oldValue) {
        // 정확한 경로 구독자들
        const exactSubscribers = this.subscribers.get(path);
        if (exactSubscribers) {
            exactSubscribers.forEach(callback => {
                try {
                    callback(newValue, oldValue, path);
                } catch (error) {
                    console.error('Error in state subscriber:', error);
                }
            });
        }
        
        // 상위 경로 구독자들도 알림 (예: 'search' 구독자는 'search.isSearching' 변경도 받음)
        const pathParts = path.split('.');
        for (let i = pathParts.length - 1; i > 0; i--) {
            const parentPath = pathParts.slice(0, i).join('.');
            const parentSubscribers = this.subscribers.get(parentPath);
            if (parentSubscribers) {
                const parentValue = this.get(parentPath);
                parentSubscribers.forEach(callback => {
                    try {
                        callback(parentValue, undefined, parentPath);
                    } catch (error) {
                        console.error('Error in parent state subscriber:', error);
                    }
                });
            }
        }
    }
    
    /**
     * 히스토리에 변경사항 추가
     */
    addToHistory(path, oldValue, newValue) {
        this.history.push({
            timestamp: Date.now(),
            path,
            oldValue,
            newValue
        });
        
        // 히스토리 크기 제한
        if (this.history.length > this.maxHistorySize) {
            this.history.shift();
        }
    }
    
    /**
     * 상태 초기화
     * @param {string} path - 초기화할 경로 (없으면 전체)
     */
    reset(path = null) {
        if (path) {
            // 특정 경로만 초기화
            const defaultValue = this.getDefaultValue(path);
            this.set(path, defaultValue);
        } else {
            // 전체 초기화
            const initialState = this.getInitialState();
            this.state = initialState;
            this.notifySubscribers('', this.state, {});
        }
        
        console.log(`🔄 State reset: ${path || 'all'}`);
    }
    
    /**
     * 로컬 스토리지에 상태 저장
     */
    persistState() {
        try {
            const persistableState = {
                settings: this.state.settings,
                ui: {
                    theme: this.state.ui.theme,
                    sidebarCollapsed: this.state.ui.sidebarCollapsed
                },
                search: {
                    searchHistory: this.state.search.searchHistory.slice(-10) // 최근 10개만
                }
            };
            
            localStorage.setItem(this.storageKey, JSON.stringify(persistableState));
        } catch (error) {
            console.error('Failed to persist state:', error);
        }
    }
    
    /**
     * 로컬 스토리지에서 상태 복원
     */
    restoreState() {
        try {
            const saved = localStorage.getItem(this.storageKey);
            if (saved) {
                const parsedState = JSON.parse(saved);
                
                // 저장된 상태를 현재 상태에 병합
                if (parsedState.settings) {
                    Object.assign(this.state.settings, parsedState.settings);
                }
                if (parsedState.ui) {
                    Object.assign(this.state.ui, parsedState.ui);
                }
                if (parsedState.search && parsedState.search.searchHistory) {
                    this.state.search.searchHistory = parsedState.search.searchHistory;
                }
                
                console.log('✅ State restored from localStorage');
            }
        } catch (error) {
            console.error('Failed to restore state:', error);
        }
    }
    
    /**
     * 전체 상태 반환 (읽기 전용)
     */
    getState() {
        return JSON.parse(JSON.stringify(this.state));
    }
    
    /**
     * 상태 변경 히스토리 반환
     */
    getHistory() {
        return [...this.history];
    }
    
    /**
     * 디버깅용 정보 출력
     */
    debug() {
        console.group('🐛 StateManager Debug Info');
        console.log('Current State:', this.getState());
        console.log('Subscribers:', Array.from(this.subscribers.keys()));
        console.log('History (last 10):', this.history.slice(-10));
        console.groupEnd();
    }
    
    /**
     * 초기 상태 반환
     */
    getInitialState() {
        // 생성자에서 정의한 초기 상태와 동일
        return {
            search: {
                isSearching: false,
                isStreaming: false,
                isRegenerating: false,
                currentQuery: '',
                selectedFiles: {
                    image: null,
                    video: null,
                    audio: null,
                    text_file: null
                },
                results: null,
                searchHistory: []
            },
            ui: {
                theme: 'auto',
                sidebarCollapsed: false,
                activeTab: 'search',
                isLoading: false,
                notifications: []
            },
            answerGeneration: {
                isGenerating: false,
                hasAnswerGeneration: false,
                currentDraftCount: 0,
                completionReason: null,
                bestAttempt: null,
                bestScore: null
            },
            progress: {
                currentStep: 0,
                totalSteps: 7,
                progressData: [],
                isVisible: false
            },
            settings: {
                maxResults: 10,
                includeChunkMeta: true,
                includeMediaMeta: true,
                temperature: 0.7,
                maxRetries: 1
            },
            errors: {
                lastError: null,
                errorHistory: []
            }
        };
    }
    
    /**
     * 특정 경로의 기본값 반환
     */
    getDefaultValue(path) {
        const initialState = this.getInitialState();
        const keys = path.split('.');
        let value = initialState;
        
        for (const key of keys) {
            if (value && typeof value === 'object' && key in value) {
                value = value[key];
            } else {
                return undefined;
            }
        }
        
        return value;
    }
}

// 전역 상태 관리자 인스턴스 생성
window.stateManager = new StateManager();

console.log('✅ Global StateManager initialized');