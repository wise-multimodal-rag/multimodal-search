/**
 * 애플리케이션 설정 관리
 * 환경변수와 기본값을 중앙집중식으로 관리
 */
class AppConfig {
    constructor() {
        // 기본 설정값
        this.defaults = {
            api: {
                baseUrl: '',  // 현재 도메인 사용
                timeout: 30000,  // 30초
                retryAttempts: 3
            },
            search: {
                maxResults: 5,
                defaultTimeout: 2000
            },
            ui: {
                animationDuration: 300,
                debounceDelay: 500,
                progressUpdateInterval: 100
            },
            streaming: {
                maxSteps: 50,
                reconnectAttempts: 3,
                heartbeatInterval: 30000
            },
            // 개발 모드 감지
            development: window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
        };

        // 런타임 설정 (서버에서 주입되거나 환경에 따라 동적 설정)
        this.runtime = {};
        
        // 설정 병합
        this.config = this._mergeConfigs();
    }

    /**
     * 설정값들을 병합
     */
    _mergeConfigs() {
        return {
            ...this.defaults,
            ...this.runtime,
            // 환경별 오버라이드
            ...(this.defaults.development ? this._getDevelopmentOverrides() : {})
        };
    }

    /**
     * 개발 환경 전용 설정
     */
    _getDevelopmentOverrides() {
        return {
            api: {
                ...this.defaults.api,
                timeout: 60000  // 개발 시 더 긴 타임아웃
            },
            ui: {
                ...this.defaults.ui,
                animationDuration: 100  // 개발 시 빠른 애니메이션
            }
        };
    }

    /**
     * 설정값 가져오기 (점 표기법 지원)
     * @param {string} path - 설정 경로 (예: 'api.timeout')
     * @param {*} defaultValue - 기본값
     * @returns {*} 설정값
     */
    get(path, defaultValue = null) {
        const keys = path.split('.');
        let value = this.config;
        
        for (const key of keys) {
            if (value && typeof value === 'object' && key in value) {
                value = value[key];
            } else {
                return defaultValue;
            }
        }
        
        return value;
    }

    /**
     * 런타임 설정값 설정
     * @param {string} path - 설정 경로
     * @param {*} value - 설정값
     */
    set(path, value) {
        const keys = path.split('.');
        let current = this.runtime;
        
        for (let i = 0; i < keys.length - 1; i++) {
            const key = keys[i];
            if (!current[key] || typeof current[key] !== 'object') {
                current[key] = {};
            }
            current = current[key];
        }
        
        current[keys[keys.length - 1]] = value;
        
        // 설정 재병합
        this.config = this._mergeConfigs();
    }

    /**
     * 서버에서 설정 주입
     * @param {Object} serverConfig - 서버 설정
     */
    injectServerConfig(serverConfig) {
        this.runtime = { ...this.runtime, ...serverConfig };
        this.config = this._mergeConfigs();
        console.log('✅ Server configuration injected:', serverConfig);
    }

    /**
     * 전체 설정 반환
     */
    getAll() {
        return { ...this.config };
    }

    /**
     * 개발 모드 여부
     */
    isDevelopment() {
        return this.get('development', false);
    }

    /**
     * API 설정 편의 메서드
     */
    getApiConfig() {
        return this.get('api', {});
    }

    /**
     * UI 설정 편의 메서드
     */
    getUIConfig() {
        return this.get('ui', {});
    }

    /**
     * 검색 설정 편의 메서드
     */
    getSearchConfig() {
        return this.get('search', {});
    }

    /**
     * 스트리밍 설정 편의 메서드
     */
    getStreamingConfig() {
        return this.get('streaming', {});
    }
}

// 전역 설정 인스턴스 생성
window.appConfig = new AppConfig();

console.log('✅ AppConfig initialized:', window.appConfig.isDevelopment() ? 'DEVELOPMENT' : 'PRODUCTION');