/**
 * UI 상호작용 및 이벤트 처리 기능
 */
class UIController {
    constructor() {
        this.messageInput = document.getElementById('messageInput');
        this.searchButton = document.getElementById('searchButton');
        this.generateButton = document.getElementById('generateButton');
        this.searchResultsContent = document.getElementById('searchResultsContent');
        this.searchResultsHeader = document.getElementById('searchResultsHeader');
        this.searchResultsInfo = document.getElementById('searchResultsInfo');
        
        this.initializeEventListeners();
    }
    
    initializeEventListeners() {
        // 엔터키 이벤트 통합 처리 - 중복 리스너 방지
        this.messageInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                if (e.shiftKey) {
                    // Shift+Enter로 검색+생성 실행
                    this.handleSearchAndGenerate();
                } else {
                    // 일반 Enter로 기본 검색 실행
                    this.handleSearch();
                }
            }
        });
        
        // 검색 버튼 클릭 - 중복 클릭 방지
        if (this.searchButton) {
            this.searchButton.addEventListener('click', (e) => {
                // 이미 비활성화된 버튼은 클릭 무시
                if (this.searchButton.disabled) {
                    console.log('🚫 Search button is disabled, ignoring click');
                    return;
                }
                this.handleSearch();
            });
        }
        
        // 생성 버튼 클릭 - 중복 클릭 방지
        if (this.generateButton) {
            this.generateButton.addEventListener('click', (e) => {
                // 이미 비활성화된 버튼은 클릭 무시
                if (this.generateButton.disabled) {
                    console.log('🚫 Generate button is disabled, ignoring click');
                    return;
                }
                this.handleSearchAndGenerate();
            });
        }
    }
    
    handleSearch() {
        if (window.searchController) {
            window.searchController.performSearchOnly();
        }
    }
    
    handleSearchAndGenerate() {
        if (window.searchController) {
            window.searchController.performSearchAndGenerate();
        }
    }
    
    setSearchExample(example) {
        this.messageInput.value = example;
        this.messageInput.focus();
        
        // Optional: Auto-scroll to input
        this.messageInput.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
    
    showLoading() {
        this.searchResultsContent.innerHTML = `
            <div class="empty-state">
                <div class="loading">
                    검색 중
                    <div class="loading-dots">
                        <div class="loading-dot"></div>
                        <div class="loading-dot"></div>
                        <div class="loading-dot"></div>
                    </div>
                </div>
            </div>
        `;
    }
    
    showError(error) {
        this.searchResultsContent.innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon">⚠️</div>
                <div>검색 중 오류가 발생했습니다: ${error.message}</div>
            </div>
        `;
    }
    
    showEmptyState() {
        this.searchResultsHeader.style.display = 'none';
        this.searchResultsContent.innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon">🔍</div>
                <div>검색어를 입력하거나 미디어 파일을 업로드하여 검색을 시작하세요</div>
            </div>
        `;
    }
    
    updateSearchResultsHeader(searchResult) {
        if (!searchResult) {
            console.warn('searchResult is undefined in updateSearchResultsHeader');
            return;
        }
        
        const resultCount = searchResult.total_hits || 0;
        const took = searchResult.took_ms || 0;
        
        // element_types_used를 더 안전하게 처리
        let elementTypes = '';
        if (searchResult.element_types_used) {
            if (Array.isArray(searchResult.element_types_used)) {
                elementTypes = searchResult.element_types_used.join(', ');
            } else {
                console.warn('element_types_used is not an array:', searchResult.element_types_used);
            }
        }
        
        // 검색 결과 헤더 업데이트
        let infoText = `${resultCount}개 결과 • ${took}ms`;
        if (elementTypes) {
            infoText += ` • ${elementTypes}`;
        }
        
        this.searchResultsInfo.innerHTML = infoText;
        this.searchResultsHeader.style.display = 'block';
    }
    
    clearInput() {
        this.messageInput.value = '';
    }
    
    disableSearchButton() {
        if (this.searchButton) this.searchButton.disabled = true;
        if (this.generateButton) this.generateButton.disabled = true;
    }
    
    enableSearchButton() {
        if (this.searchButton) this.searchButton.disabled = false;
        if (this.generateButton) this.generateButton.disabled = false;
    }
    
    focusMessageInput() {
        this.messageInput.focus();
    }
    
    toggleMetadata(resultId, metaType) {
        const button = event.target.closest('.metadata-button');
        const content = document.getElementById(`${resultId}-${metaType}`);
        
        if (content.classList.contains('show')) {
            content.classList.remove('show');
            button.classList.remove('active');
        } else {
            content.classList.add('show');
            button.classList.add('active');
        }
    }
    
    checkConversationalQuery(query) {
        const conversationalPatterns = [
            /^(그|그거|그것|저것|이것|이거)\s*(어떻게|뭔지|뭔가|이야|은|는)/,  // 더 정확한 지시대명사 패턴
            /더 알려.*줘|더 자세히.*해줘|추가로.*알려/,  // 명확한 요청 패턴
            /^(네|예|아니|아니요|맞아|틀렸어|응|어)/,  // 대답 패턴
            /이전.*말|앞서.*말|위에서.*말|방금.*말/,  // 이전 대화 참조 패턴
            /그래서|그럼|그러면.*어떻게/  // 연결어 패턴
        ];
        
        return conversationalPatterns.some(pattern => pattern.test(query.toLowerCase()));
    }
    
    showConversationalGuide() {
        const guideMessage = `
            <div class="message-content">
                <strong>알림:</strong> 이 시스템은 대화형이 아닌 <strong>독립적인 검색</strong>을 수행합니다.<br><br>
                
                이전 검색과 연관된 질문을 하신 것 같습니다. 더 정확한 결과를 위해 <strong>구체적인 검색어</strong>를 입력해주세요.<br><br>
                
                <strong>예시:</strong><br>
                • "AI 기술 동향"<br>
                • "머신러닝 알고리즘"<br>
                • "데이터 분석 방법"<br>
                • 또는 관련 파일을 업로드해주세요
            </div>
        `;
        
        // 가이드 메시지 표시 로직이 필요하다면 여기에 구현
        console.log('Conversational query detected, showing guide');
    }
    
    clearSearchResults() {
        this.showEmptyState();
        this.clearInput();
        
        if (window.fileHandler) {
            window.fileHandler.clearFiles();
        }
        
        this.focusMessageInput();
    }
    
    initialize() {
        // 페이지 로드 시 입력창에 포커스
        this.focusMessageInput();
    }
}

// 전역 함수들 (HTML에서 호출되는 함수들)
function setSearchExample(example) {
    if (window.uiController) {
        window.uiController.setSearchExample(example);
    }
}

function toggleMetadata(resultId, metaType) {
    if (window.uiController) {
        window.uiController.toggleMetadata(resultId, metaType);
    }
}

// 전역 인스턴스 생성
window.uiController = new UIController();