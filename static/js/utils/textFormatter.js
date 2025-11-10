/**
 * 텍스트 포맷팅 유틸리티 클래스
 * 답변 텍스트의 포맷팅과 마크다운 렌더링을 담당
 */
class TextFormatter {
    /**
     * 기본적인 텍스트 포맷팅 (일반 텍스트 뷰용)
     * @param {string} text - 포맷팅할 텍스트
     * @returns {string} HTML 포맷팅된 텍스트
     */
    static formatAnswerText(text) {
        if (!text) return '';
        
        // 기본적인 텍스트 포맷팅 (일반 텍스트 뷰용)
        // 단순히 줄바꿈을 <br>로 변환하고 기본적인 마크다운 스타일만 적용
        return text
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            .replace(/\n/g, '<br>');
    }
    
    /**
     * 원문 텍스트 표시 (HTML 이스케이프 및 줄바꿈만 처리)
     * @param {string} text - 원문 텍스트
     * @returns {string} HTML 안전한 원문 텍스트
     */
    static formatRawText(text) {
        if (!text) return '';
        
        // HTML 특수문자 이스케이프 후 줄바꿈만 <br>로 변환
        return text
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#x27;')
            .replace(/\n/g, '<br>');
    }
    
    /**
     * 마크다운 렌더링 (Preview 모드용)
     * @param {string} text - 마크다운 텍스트
     * @returns {string} HTML로 렌더링된 마크다운
     */
    static renderMarkdown(text) {
        if (!text) return '';
        
        // marked.js 라이브러리가 로드되었는지 확인
        if (typeof marked !== 'undefined') {
            try {
                // marked.js를 사용한 마크다운 렌더링
                const html = marked.parse(text);
                console.log('✅ Markdown rendered with marked.js');
                return html;
            } catch (error) {
                console.warn('⚠️ marked.js failed, falling back to custom renderer:', error);
            }
        } else {
            console.warn('⚠️ marked.js not loaded, using custom renderer');
        }
        
        // Fallback: 기존 커스텀 렌더러 사용
        return this.renderMarkdownCustom(text);
    }
    
    /**
     * 커스텀 마크다운 렌더러 (fallback용)
     * @param {string} text - 마크다운 텍스트
     * @returns {string} HTML로 렌더링된 마크다운
     */
    static renderMarkdownCustom(text) {
        if (!text) return '';
        
        // 텍스트를 단락별로 분리
        const paragraphs = text.split(/\n\s*\n/);
        let htmlParts = [];
        
        for (let paragraph of paragraphs) {
            paragraph = paragraph.trim();
            if (!paragraph) continue;
            
            let html = paragraph;
            
            // 헤더 처리
            if (html.match(/^###\s/)) {
                html = html.replace(/^###\s(.*)$/gm, '<h3>$1</h3>');
            } else if (html.match(/^##\s/)) {
                html = html.replace(/^##\s(.*)$/gm, '<h2>$1</h2>');
            } else if (html.match(/^#\s/)) {
                html = html.replace(/^#\s(.*)$/gm, '<h1>$1</h1>');
            } else if (html.match(/^[\*\-]\s/) || html.match(/^\d+\.\s/) || html.includes('\n- ') || html.includes('\n* ') || /\n\d+\.\s/.test(html)) {
                // 리스트 처리
                const lines = html.split('\n');
                const listItems = [];
                let isOrderedList = false;
                let currentContent = '';
                
                for (let i = 0; i < lines.length; i++) {
                    const line = lines[i].trim();
                    
                    if (line.match(/^[\*\-]\s/)) {
                        // 이전 아이템이 있다면 먼저 처리
                        if (currentContent) {
                            let content = currentContent
                                .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
                                .replace(/\*(.*?)\*/g, '<em>$1</em>');
                            listItems.push('<li>' + content + '</li>');
                        }
                        // 새로운 아이템 시작
                        currentContent = line.replace(/^[\*\-]\s/, '');
                    } else if (line.match(/^\d+\.\s/)) {
                        // 이전 아이템이 있다면 먼저 처리
                        if (currentContent) {
                            let content = currentContent
                                .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
                                .replace(/\*(.*?)\*/g, '<em>$1</em>');
                            listItems.push('<li>' + content + '</li>');
                        }
                        isOrderedList = true;
                        // 새로운 아이템 시작
                        currentContent = line.replace(/^\d+\.\s/, '');
                    } else if (line && (line.startsWith('  ') || (!line.match(/^[\*\-]\s/) && !line.match(/^\d+\.\s/)))) {
                        // 연속된 내용이나 들여쓰기된 내용을 현재 아이템에 추가
                        if (currentContent) {
                            currentContent += ' ' + line.replace(/^\s+/, '');
                        }
                    } else if (line && currentContent) {
                        // 일반 텍스트가 있고 현재 아이템이 있으면 추가
                        currentContent += ' ' + line;
                    }
                }
                
                // 마지막 아이템 처리
                if (currentContent) {
                    let content = currentContent
                        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
                        .replace(/\*(.*?)\*/g, '<em>$1</em>');
                    listItems.push('<li>' + content + '</li>');
                }
                
                const listTag = isOrderedList ? 'ol' : 'ul';
                html = `<${listTag}>` + listItems.join('') + `</${listTag}>`;
            } else {
                // 일반 단락 처리
                html = html
                    // 코드 블록 처리 (먼저 처리)
                    .replace(/```([\s\S]*?)```/g, '<pre><code>$1</code></pre>')
                    .replace(/`([^`]+)`/g, '<code>$1</code>')
                    // 볼드체와 이탤릭체
                    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
                    .replace(/\*(.*?)\*/g, '<em>$1</em>')
                    // 단일 줄바꿈을 <br>로 변환
                    .replace(/\n/g, '<br>');
                
                // 헤더나 코드 블록이 아닌 경우에만 <p> 태그로 감싸기
                if (!html.startsWith('<h') && !html.startsWith('<pre') && !html.startsWith('<ul')) {
                    html = '<p>' + html + '</p>';
                }
            }
            
            htmlParts.push(html);
        }
        
        return htmlParts.join('');
    }
}

// 전역 접근을 위한 export
window.TextFormatter = TextFormatter;

// 가중치 상세보기 토글 함수
window.toggleWeightDetails = function(button) {
    const table = button.nextElementSibling;
    const isVisible = table.style.display !== 'none';
    
    if (isVisible) {
        table.style.display = 'none';
        button.innerHTML = '📊 전체 가중치 상세보기 ▼';
    } else {
        table.style.display = 'block';
        button.innerHTML = '📊 전체 가중치 상세보기 ▲';
    }
};

// 디버그 정보 토글 함수
window.toggleDebugInfo = function(button) {
    const content = button.nextElementSibling;
    const isVisible = content.style.display !== 'none';
    
    if (isVisible) {
        content.style.display = 'none';
        button.innerHTML = '🔧 디버그 정보 ▼';
    } else {
        content.style.display = 'block';
        button.innerHTML = '🔧 디버그 정보 ▲';
    }
};

console.log('✅ TextFormatter and toggle functions loaded');