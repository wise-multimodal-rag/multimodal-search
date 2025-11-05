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
        return text
            .replace(/\n\n/g, '</p><p>')
            .replace(/\n/g, '<br>')
            .replace(/^/, '<p>')
            .replace(/$/, '</p>')
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>');
    }
    
    /**
     * 마크다운 렌더링 (Preview 모드용)
     * @param {string} text - 마크다운 텍스트
     * @returns {string} HTML로 렌더링된 마크다운
     */
    static renderMarkdown(text) {
        if (!text) return '';
        
        // 마크다운 렌더링 (Preview 모드용)
        let html = text
            // 헤더 처리
            .replace(/^### (.*$)/gm, '<h3>$1</h3>')
            .replace(/^## (.*$)/gm, '<h2>$1</h2>')
            .replace(/^# (.*$)/gm, '<h1>$1</h1>')
            // 코드 블록 처리 (먼저 처리)
            .replace(/```([\s\S]*?)```/g, '<pre><code>$1</code></pre>')
            .replace(/`([^`]+)`/g, '<code>$1</code>')
            // 리스트 처리
            .replace(/^\* (.*$)/gm, '<li>$1</li>')
            .replace(/^- (.*$)/gm, '<li>$1</li>')
            .replace(/^(\d+)\. (.*$)/gm, '<li>$2</li>')
            // 볼드체와 이탤릭체
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            // 줄바꿈 처리
            .replace(/\n\n/g, '</p><p>')
            .replace(/\n/g, '<br>');
            
        // 연속된 리스트 항목들을 ul로 감싸기
        html = html.replace(/(<li>.*?<\/li>)(?:\s*<li>.*?<\/li>)*/g, function(match) {
            return '<ul>' + match + '</ul>';
        });
        
        // 단락으로 감싸기
        if (!html.startsWith('<h') && !html.startsWith('<ul') && !html.startsWith('<pre')) {
            html = '<p>' + html + '</p>';
        }
        
        return html;
    }
}

// 전역 접근을 위한 export
window.TextFormatter = TextFormatter;