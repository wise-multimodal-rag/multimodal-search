/**
 * 파일 미리보기 컴포넌트
 * 첨부된 파일을 입력창 위에 뱃지로 표시
 */
class FilePreview {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
        this.files = { image: null, video: null, audio: null };
    }

    setFile(type, file) {
        this.files[type] = file;
        this._render();
    }

    removeFile(type) {
        this.files[type] = null;
        this._render();
    }

    getFiles() {
        return { ...this.files };
    }

    hasFiles() {
        return Object.values(this.files).some(f => f !== null);
    }

    clear() {
        this.files = { image: null, video: null, audio: null };
        this._render();
    }

    _render() {
        const hasAny = this.hasFiles();
        this.container.classList.toggle('hidden', !hasAny);
        if (!hasAny) {
            this.container.innerHTML = '';
            return;
        }

        const icons = { image: '🖼️', video: '🎬', audio: '🔊' };
        let html = '';

        for (const [type, file] of Object.entries(this.files)) {
            if (!file) continue;
            const name = file.name.length > 20 ? file.name.slice(0, 17) + '...' : file.name;
            const size = this._formatSize(file.size);
            html += `
                <div class="file-badge inline-flex items-center gap-1.5 px-2.5 py-1.5 bg-surface-100 dark:bg-surface-700 rounded-lg text-xs">
                    <span>${icons[type]}</span>
                    <span class="text-surface-700 dark:text-surface-300 font-medium">${name}</span>
                    <span class="text-surface-400">(${size})</span>
                    <button onclick="window.chatApp?.filePreview.removeFile('${type}')" class="ml-1 text-surface-400 hover:text-red-500 transition-colors">
                        <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg>
                    </button>
                </div>
            `;
        }

        this.container.innerHTML = html;
    }

    _formatSize(bytes) {
        if (bytes < 1024) return bytes + 'B';
        if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + 'KB';
        return (bytes / (1024 * 1024)).toFixed(1) + 'MB';
    }
}
