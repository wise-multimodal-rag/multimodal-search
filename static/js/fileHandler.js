/**
 * 파일 업로드 및 처리 관련 기능
 */
class FileHandler {
    constructor() {
        this.selectedFiles = {
            image: null,
            video: null,
            audio: null
        };
        
        this.selectedFilesDiv = document.getElementById('selectedFiles');
        this.imageInput = document.getElementById('imageInput');
        this.videoInput = document.getElementById('videoInput');
        this.audioInput = document.getElementById('audioInput');
        
        this.initializeEventListeners();
    }
    
    initializeEventListeners() {
        // File input handlers
        this.imageInput.addEventListener('change', (e) => {
            this.handleFileSelection('image', e.target.files[0], '📷');
        });

        this.videoInput.addEventListener('change', (e) => {
            this.handleFileSelection('video', e.target.files[0], '🎥');
        });

        this.audioInput.addEventListener('change', (e) => {
            this.handleFileSelection('audio', e.target.files[0], '🎵');
        });
    }
    
    handleFileSelection(type, file, emoji) {
        if (file) {
            this.selectedFiles[type] = file;
            this.updateFilePreview();
            this.updateFileButtonState();
        }
    }
    
    updateFilePreview() {
        this.selectedFilesDiv.innerHTML = '';
        
        Object.entries(this.selectedFiles).forEach(([type, file]) => {
            if (file) {
                const preview = document.createElement('div');
                preview.className = 'file-preview';
                
                const emoji = type === 'image' ? '📷' : type === 'video' ? '🎥' : '🎵';
                const size = (file.size / 1024 / 1024).toFixed(1);
                
                preview.innerHTML = `
                    ${emoji} ${file.name} (${size}MB)
                    <span class="remove-file" onclick="fileHandler.removeFile('${type}')">×</span>
                `;
                
                this.selectedFilesDiv.appendChild(preview);
            }
        });
    }
    
    updateFileButtonState() {
        Object.entries(this.selectedFiles).forEach(([type, file]) => {
            const button = document.querySelector(`[onclick*="${type}Input"]`);
            if (file) {
                button.classList.add('selected');
            } else {
                button.classList.remove('selected');
            }
        });
    }
    
    removeFile(type) {
        this.selectedFiles[type] = null;
        const input = document.getElementById(type + 'Input');
        input.value = '';
        this.updateFilePreview();
        this.updateFileButtonState();
    }
    
    hasFiles() {
        return Object.values(this.selectedFiles).some(file => file !== null);
    }
    
    clearFiles() {
        this.selectedFiles = { image: null, video: null, audio: null };
        this.imageInput.value = '';
        this.videoInput.value = '';
        this.audioInput.value = '';
        this.updateFilePreview();
        this.updateFileButtonState();
    }
    
    getSelectedFiles() {
        return this.selectedFiles;
    }
    
    createFilePreview(type, file) {
        const typeLabels = {
            'image': { label: '이미지', icon: '🖼️' },
            'video': { label: '비디오', icon: '🎬' },
            'audio': { label: '오디오', icon: '🎵' }
        };
        
        const { label, icon } = typeLabels[type];
        const fileUrl = URL.createObjectURL(file);
        
        let preview = '';
        if (type === 'image') {
            preview = `<img src="${fileUrl}" class="user-file-preview" alt="${file.name}">`;
        } else {
            preview = `<div class="user-file-preview">${icon}</div>`;
        }
        
        return `
            <div class="user-file-item">
                ${preview}
                <div class="user-file-info">
                    <div class="user-file-name">${file.name}</div>
                    <div class="user-file-type">${label} • ${(file.size / 1024 / 1024).toFixed(1)}MB</div>
                </div>
            </div>
        `;
    }
    
    getFileNames() {
        return Object.entries(this.selectedFiles)
            .filter(([type, file]) => file !== null)
            .map(([type, file]) => {
                // 파일명이 너무 길면 줄임
                const fileName = file.name;
                if (fileName.length > 25) {
                    const ext = fileName.split('.').pop();
                    const name = fileName.substring(0, 20);
                    return `${name}...${ext}`;
                }
                return fileName;
            });
    }
}

// 전역 인스턴스 생성
window.fileHandler = new FileHandler();