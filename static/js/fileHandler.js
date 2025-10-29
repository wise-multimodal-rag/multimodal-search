/**
 * 파일 업로드 및 처리 관련 기능
 */
class FileHandler {
    constructor() {
        this.selectedFiles = {
            image: null,
            video: null,
            audio: null,
            text_file: null
        };
        
        this.selectedFilesDiv = document.getElementById('selectedFiles');
        this.imageInput = document.getElementById('imageInput');
        this.videoInput = document.getElementById('videoInput');
        this.audioInput = document.getElementById('audioInput');
        this.textFileInput = document.getElementById('textFileInput');
        
        // 요소들이 제대로 로드되었는지 확인
        console.log('FileHandler elements:', {
            selectedFilesDiv: !!this.selectedFilesDiv,
            imageInput: !!this.imageInput,
            videoInput: !!this.videoInput,
            audioInput: !!this.audioInput,
            textFileInput: !!this.textFileInput
        });
        
        // textFileInput 특별 디버깅
        if (this.textFileInput) {
            console.log('textFileInput 속성들:', {
                id: this.textFileInput.id,
                type: this.textFileInput.type,
                accept: this.textFileInput.accept,
                style: this.textFileInput.style.display
            });
        } else {
            console.error('textFileInput을 찾을 수 없습니다!');
            // 다른 방법으로 찾아보기
            const allInputs = document.querySelectorAll('input[type="file"]');
            console.log('페이지의 모든 파일 입력들:', Array.from(allInputs).map(input => input.id));
        }
        
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

        if (this.textFileInput) {
            this.textFileInput.addEventListener('change', (e) => {
                console.log('텍스트 파일 선택 이벤트 발생:', e.target.files);
                if (e.target.files && e.target.files[0]) {
                    console.log('선택된 텍스트 파일:', e.target.files[0].name, e.target.files[0].type);
                    this.handleFileSelection('text_file', e.target.files[0], '📄');
                } else {
                    console.log('텍스트 파일이 선택되지 않음');
                }
            });
        } else {
            console.error('textFileInput element not found!');
        }
    }
    
    handleFileSelection(type, file, emoji) {
        console.log('handleFileSelection 호출됨:', { type, fileName: file?.name, fileType: file?.type });
        if (file) {
            this.selectedFiles[type] = file;
            console.log('파일 저장됨:', type, file.name);
            console.log('현재 선택된 파일들:', Object.keys(this.selectedFiles).filter(key => this.selectedFiles[key] !== null));
            this.updateFilePreview();
            this.updateFileButtonState();
        } else {
            console.log('파일이 null입니다:', type);
        }
    }
    
    updateFilePreview() {
        this.selectedFilesDiv.innerHTML = '';
        
        Object.entries(this.selectedFiles).forEach(([type, file]) => {
            if (file) {
                const preview = document.createElement('div');
                preview.className = 'file-preview';
                
                const emoji = type === 'image' ? '📷' : type === 'video' ? '🎥' : type === 'audio' ? '🎵' : '📄';
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
            if (button) {
                if (file) {
                    button.classList.add('selected');
                } else {
                    button.classList.remove('selected');
                }
            }
        });
    }
    
    removeFile(type) {
        this.selectedFiles[type] = null;
        const inputId = type === 'text_file' ? 'textFileInput' : type + 'Input';
        const input = document.getElementById(inputId);
        if (input) {
            input.value = '';
        }
        this.updateFilePreview();
        this.updateFileButtonState();
    }
    
    hasFiles() {
        return Object.values(this.selectedFiles).some(file => file !== null);
    }
    
    clearFiles() {
        this.selectedFiles = { image: null, video: null, audio: null, text_file: null };
        if (this.imageInput) this.imageInput.value = '';
        if (this.videoInput) this.videoInput.value = '';
        if (this.audioInput) this.audioInput.value = '';
        if (this.textFileInput) this.textFileInput.value = '';
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
            'audio': { label: '오디오', icon: '🎵' },
            'text_file': { label: '텍스트', icon: '📄' }
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

// 스크립트 로드 시 즉시 클래스 정의하고 나중에 초기화
console.log('FileHandler 클래스 정의됨');

// FileHandler 전역 인스턴스는 HTML에서 직접 초기화