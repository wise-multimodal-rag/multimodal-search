/**
 * 검색 히스토리 관리 기능
 */
class HistoryManager {
    constructor() {
        this.searchHistory = document.getElementById('searchHistory');
        this.maxHistoryItems = 10;
    }
    
    getSearchHistoryData() {
        try {
            const data = localStorage.getItem('searchHistory');
            return data ? JSON.parse(data) : [];
        } catch (e) {
            console.error('Failed to load search history:', e);
            return [];
        }
    }
    
    saveSearchHistoryData(historyData) {
        try {
            // 최대 10개까지만 저장
            const limitedData = historyData.slice(0, this.maxHistoryItems);
            localStorage.setItem('searchHistory', JSON.stringify(limitedData));
        } catch (e) {
            console.error('Failed to save search history:', e);
        }
    }
    
    addToSearchHistory(query, originalText = '', isFileOnly = false, searchResult = null) {
        // 모달리티 타입 결정
        const modality = this.getSearchModality(query, isFileOnly);
        
        // 새로운 히스토리 항목 생성
        const historyEntry = {
            id: Date.now().toString(),
            query: query,
            originalText: originalText,
            isFileOnly: isFileOnly,
            modality: modality,
            timestamp: Date.now(),
            searchResult: searchResult ? {
                total_hits: searchResult.total_hits,
                took_ms: searchResult.took_ms,
                element_types_used: searchResult.element_types_used,
                results: searchResult.results?.slice(0, 20) || [] // 최대 20개 결과만 저장
            } : null
        };

        // 기존 히스토리 데이터 가져오기
        let historyData = this.getSearchHistoryData();
        
        // 같은 쿼리 제거
        historyData = historyData.filter(item => item.query !== query);
        
        // 새 항목을 맨 앞에 추가
        historyData.unshift(historyEntry);
        
        // 저장
        this.saveSearchHistoryData(historyData);
        
        // UI 업데이트
        this.updateSearchHistoryUI();
    }
    
    getSearchModality(query, isFileOnly) {
        const messageInput = document.getElementById('messageInput');
        const message = messageInput.value.trim();
        const hasFiles = window.fileHandler && window.fileHandler.hasFiles();
        
        if (!message && !hasFiles) {
            return '';
        }
        
        const fileTypes = [];
        if (window.fileHandler) {
            const selectedFiles = window.fileHandler.getSelectedFiles();
            if (selectedFiles.image) fileTypes.push('이미지');
            if (selectedFiles.video) fileTypes.push('비디오');
            if (selectedFiles.audio) fileTypes.push('오디오');
        }
        
        if (message && hasFiles) {
            return `텍스트+${fileTypes.join('+')}`;
        } else if (message) {
            return '텍스트';
        } else if (hasFiles) {
            return fileTypes.join('+');
        }
        
        return '';
    }
    
    updateSearchHistoryUI() {
        const historyData = this.getSearchHistoryData();
        
        // 기존 히스토리 아이템 제거 (placeholder 제외)
        const existingItems = this.searchHistory.querySelectorAll('.search-history-item');
        existingItems.forEach(item => item.remove());
        
        if (historyData.length === 0) {
            // 히스토리가 없으면 placeholder 표시
            if (!this.searchHistory.querySelector('.search-history-placeholder')) {
                const placeholder = document.createElement('div');
                placeholder.className = 'search-history-placeholder';
                placeholder.style.cssText = 'padding: 20px; text-align: center; color: #9ca3af; font-size: 13px;';
                placeholder.textContent = '검색 히스토리가 여기에 표시됩니다';
                this.searchHistory.appendChild(placeholder);
            }
            return;
        }
        
        // placeholder 제거
        const placeholder = this.searchHistory.querySelector('.search-history-placeholder');
        if (placeholder) {
            placeholder.remove();
        }
        
        // 히스토리 아이템 생성
        historyData.forEach(entry => {
            const historyItem = document.createElement('div');
            historyItem.className = 'search-history-item';
            historyItem.dataset.historyId = entry.id;
            
            const timeText = entry.searchResult ? `${entry.searchResult.took_ms}ms` : '-';
            
            historyItem.innerHTML = `
                <div class="search-history-query">${entry.query}</div>
                <div class="search-history-meta">
                    <div class="search-history-modality">${entry.modality}</div>
                    <div class="search-history-time">${timeText}</div>
                </div>
            `;
            
            // 클릭 동작 설정
            if (entry.isFileOnly) {
                // 파일만 검색한 경우 결과 복원만 가능
                historyItem.onclick = () => {
                    if (entry.searchResult) {
                        this.restoreSearchResult(entry.searchResult);
                    }
                };
            } else if (entry.originalText) {
                // 텍스트 + 파일 조합인 경우
                historyItem.onclick = () => {
                    if (entry.searchResult) {
                        this.restoreSearchResult(entry.searchResult);
                        window.uiController.setSearchExample(entry.originalText);
                    } else {
                        window.uiController.setSearchExample(entry.originalText);
                    }
                };
            } else {
                // 텍스트만 검색한 경우
                historyItem.onclick = () => {
                    if (entry.searchResult) {
                        this.restoreSearchResult(entry.searchResult);
                        window.uiController.setSearchExample(entry.query);
                    } else {
                        window.uiController.setSearchExample(entry.query);
                    }
                };
            }
            
            this.searchHistory.appendChild(historyItem);
        });
    }
    
    restoreSearchResult(searchResult) {
        // 검색 결과 복원
        if (window.searchController) {
            window.searchController.displaySearchResults(searchResult);
        }
        
        // 검색 결과 영역으로 스크롤
        const searchResultsContent = document.getElementById('searchResultsContent');
        searchResultsContent.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
    
    updateSearchHistoryWithResults(searchResult) {
        // localStorage에서 히스토리 데이터 가져오기
        let historyData = this.getSearchHistoryData();
        
        if (historyData.length > 0) {
            // 가장 최근 항목에 검색 결과 추가
            historyData[0].searchResult = {
                total_hits: searchResult.total_hits,
                took_ms: searchResult.took_ms,
                element_types_used: searchResult.element_types_used,
                results: searchResult.results?.slice(0, 20) || [] // 최대 20개 결과만 저장
            };
            
            // 저장
            this.saveSearchHistoryData(historyData);
            
            // UI 업데이트
            this.updateSearchHistoryUI();
        }
    }
    
    initialize() {
        // 페이지 로드 시 히스토리 복원
        this.updateSearchHistoryUI();
    }
}

// 전역 인스턴스 생성
window.historyManager = new HistoryManager();