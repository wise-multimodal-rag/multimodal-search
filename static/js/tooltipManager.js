/**
 * 동적 툴팁 시스템 관리
 */
class TooltipManager {
    constructor() {
        this.currentTooltip = null;
        this.initializeEventListeners();
    }
    
    createTooltip(content) {
        const tooltip = document.createElement('div');
        tooltip.className = 'custom-tooltip';
        tooltip.textContent = content;
        document.body.appendChild(tooltip);
        return tooltip;
    }
    
    showTooltip(element, content) {
        this.hideTooltip();
        
        this.currentTooltip = this.createTooltip(content);
        const rect = element.getBoundingClientRect();
        
        // Position tooltip above the element
        const tooltipRect = this.currentTooltip.getBoundingClientRect();
        let left = rect.left + rect.width / 2 - tooltipRect.width / 2;
        let top = rect.top - tooltipRect.height - 10;
        
        // Adjust if tooltip goes off screen
        if (left < 10) left = 10;
        if (left + tooltipRect.width > window.innerWidth - 10) {
            left = window.innerWidth - tooltipRect.width - 10;
        }
        if (top < 10) {
            top = rect.bottom + 10;
            this.currentTooltip.style.transform = 'translateY(-100%)';
        }
        
        this.currentTooltip.style.left = left + 'px';
        this.currentTooltip.style.top = top + 'px';
        
        setTimeout(() => {
            if (this.currentTooltip) {
                this.currentTooltip.classList.add('show');
            }
        }, 10);
    }
    
    hideTooltip() {
        if (this.currentTooltip) {
            this.currentTooltip.classList.remove('show');
            setTimeout(() => {
                if (this.currentTooltip && this.currentTooltip.parentNode) {
                    this.currentTooltip.parentNode.removeChild(this.currentTooltip);
                }
                this.currentTooltip = null;
            }, 200);
        }
    }
    
    initializeEventListeners() {
        // Event listeners for tooltips
        document.addEventListener('mouseover', (e) => {
            const scoreTag = e.target.closest('.score-tag[data-tooltip]');
            if (scoreTag) {
                const content = scoreTag.getAttribute('data-tooltip');
                this.showTooltip(scoreTag, content);
            }
        });

        document.addEventListener('mouseout', (e) => {
            const scoreTag = e.target.closest('.score-tag[data-tooltip]');
            if (scoreTag) {
                this.hideTooltip();
            }
        });
    }
}

// 전역 인스턴스 생성
window.tooltipManager = new TooltipManager();