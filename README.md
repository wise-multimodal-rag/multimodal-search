# Multimodal Search & RAG System

## 프로젝트 개요

OpenSearch를 사용한 멀티모달 검색 및 RAG 시스템입니다. 텍스트, 이미지, 비디오, 오디오를 통합하여 검색하고, 하이브리드 검색(BM25 + 벡터 검색)과 LLM 기반 질의 분석을 지원합니다.

## 검색 파이프라인 플로우

```mermaid
flowchart TD
    %% 입력 단계
    A[사용자 요청] --> B{입력 유형 확인}
    B --> C[텍스트 쿼리]
    B --> D[이미지 파일]
    B --> E[비디오 파일]  
    B --> F[오디오 파일]
    
    %% Step 1: 입력 처리
    C --> G[Step 1: 멀티모달 입력 처리<br/>InputProcessor]
    D --> G
    E --> G
    F --> G
    G --> G1[텍스트 데이터 구조화]
    G --> G2[이미지 Base64 변환]
    G --> G3[비디오 Base64 변환]
    G --> G4[오디오 Base64 변환]
    
    %% Step 2: 쿼리 확장 및 의도 분석
    G1 --> H[Step 2: 쿼리 확장 및 의도 분석<br/>QueryAnalyzer]
    H --> H1[Step 2-1: 🤖 지능형 쿼리 확장<br/>필요한 기법만 선택적 적용]
    H1 --> H1A{🤖 LLM 확장 성공?}
    H1A -->|성공| H2[적응형 확장 쿼리 생성<br/>쿼리 특성에 따라 1-3개]
    H1A -->|실패| H3[원본 쿼리 사용<br/>확장 없이 진행]
    
    H2 --> H4[Step 2-2: 🤖 의도 분석<br/>확장된 주요 쿼리 기반]
    H3 --> H4
    H4 --> H4A{🤖 LLM 분석 성공?}
    H4A -->|성공| H5[🤖 LLM 기반 element_type 선택]
    H4A -->|실패| H6[휴리스틱 기반 폴백 분석]
    H5 --> I[선택된 element_types + 확장된 쿼리들<br/>paragraph, title, image, etc.]
    H6 --> I
    
    %% Step 3: 특징 추출 (선택된 element_types에 따라 제어됨)
    G1 --> J[Step 3: 멀티모달 특징 추출<br/>MultimodalFeatureExtractor]
    G2 --> J
    G3 --> J
    G4 --> J
    I --> J
    J --> J1{선택된 element_types<br/>확인}
    J1 -->|텍스트 관련 타입| J2[텍스트 특징 추출<br/>키워드, 엔티티, 요약]
    J1 -->|이미지 관련 타입| J3[이미지 특징 추출<br/>캡션, 객체 탐지]
    J1 -->|비디오 관련 타입| J4[🤖 비디오 특징 추출<br/>장면, 활동, 객체]
    J1 -->|오디오 관련 타입| J5[🤖 오디오 특징 추출<br/>STT, 소리 분류]
    
    %% Step 4: 임베딩 생성
    G1 --> K[Step 4: 임베딩 생성<br/>EmbeddingService]
    G2 --> K
    G3 --> K
    G4 --> K
    J2 --> K
    J3 --> K
    J4 --> K
    J5 --> K
    
    %% Step 5: OpenSearch 검색 (확장된 쿼리 사용)
    I --> L[Step 5: OpenSearch 검색<br/>OpenSearchService]
    K1 --> L
    K2 --> L
    L --> L1[확장된 쿼리별 개별 검색<br/>Query 1, 2, 3 순차 실행]
    L1 --> L2[각 쿼리마다<br/>하이브리드 쿼리 구성 BM25+벡터]
    L2 --> L3[OpenSearch 인덱스 검색<br/>multimodal_rag_element]
    L3 --> L4[쿼리별 가중치 적용<br/>1st-1.0 2nd-0.9 3rd-0.8]
    L4 --> L5[결과 통합 및 중복 제거<br/>점수 기준 재정렬]
    L5 --> L6[RRF 리랭킹<br/>최종 순위 조정]
    
    %% Step 6: 결과 강화
    L6 --> M[Step 6: 결과 enrichment<br/>ResultEnricher]
    M --> M1{chunk_meta 포함?}
    M --> M2{media_meta 포함?}
    M1 -->|Yes| M3[청크 메타데이터 조회]
    M2 -->|Yes| M4[미디어 메타데이터 조회]
    M3 --> N[강화된 검색 결과]
    M4 --> N
    M1 -->|No| N
    M2 -->|No| N
    
    %% Step 7: 응답 생성
    N --> O[Step 7: 응답 생성<br/>SearchResponse]
    O --> O1[검색 통계 계산]
    O --> O2[실행 시간 측정]
    O --> P[최종 응답 반환<br/>총 검색 수, 최대 점수, 결과 목록]
    
    %% 외부 API 의존성
    J2 -.->|API 호출| API1[Feature Extraction API<br/>키워드, 엔티티, 요약]
    J3 -.->|API 호출| API2[Feature Extraction API<br/>이미지 캡션, 객체 탐지]
    J4 -.->|🤖 LLM 호출| API3[🤖 LiteLLM<br/>비디오 분석]
    J5 -.->|🤖 LLM 호출| API3
    K -.->|API 호출| API4[Embedding API<br/>텍스트/이미지/비디오/오디오 임베딩]
    API4 --> K1[원본 모달리티 임베딩<br/>text, image, video, audio]
    API4 --> K2[특징 기반 임베딩<br/>summary, caption, keywords, etc.]
    H -.->|🤖 LLM 호출| API3
    
    %% 인덱스 구조
    L3 -.-> IDX1[(multimodal_rag_element<br/>검색 가능한 요소)]
    M3 -.-> IDX2[(multimodal_rag_chunk<br/>청크 메타데이터)]
    M4 -.-> IDX3[(multimodal_rag_media<br/>미디어 메타데이터)]
    
    %% 스타일링
    classDef stepClass fill:#e1f5fe,stroke:#01579b,stroke-width:2px
    classDef apiClass fill:#fff3e0,stroke:#f57c00,stroke-width:2px
    classDef dbClass fill:#e8f5e8,stroke:#2e7d32,stroke-width:2px
    classDef llmClass fill:#f3e5f5,stroke:#7b1fa2,stroke-width:3px
    
    class G,H,J,J1,K,L,M,O stepClass
    class API1,API2,API4 apiClass
    class API3 llmClass
    class H1,H1A,H2,H4,H4A,H5,J4,J5 llmClass
    class IDX1,IDX2,IDX3 dbClass
```

## 주요 특징

- **멀티모달 입력**: 텍스트, 이미지, 비디오, 오디오 동시 지원
- **적응형 쿼리 확장**: 쿼리 특성에 따른 선택적 기법 적용 (Decomposition, Rewriting, Expansion)
- **하이브리드 검색**: BM25 텍스트 검색 + 벡터 유사도 검색 + 확장 쿼리 통합
- **LLM 기반 질의 분석**: 검색 의도 파악 및 최적 element type 선택
- **가중치 기반 결과 융합**: 확장된 쿼리별 가중치 적용 및 중복 제거
- **3계층 인덱스 구조**: media_meta, chunk_meta, elements로 체계적 관리
- **외부 API 통합**: Feature Extraction 및 Embedding API 활용

## 기술 스택

- **Backend**: FastAPI (Python 3.11+)
- **Package Manager**: uv + pyproject.toml
- **Search Engine**: OpenSearch (벡터 검색 지원)
- **LLM**: LiteLLM (다중 모델 지원)
- **External APIs**: Embedding & Feature Extraction Services
- **Deployment**: Docker + GitLab CI/CD

## 빠른 시작

### 1. 개발 환경 설정
```bash
# 의존성 설치
uv pip install -e .

# 개발 서버 실행
python run.py
```

### 2. Docker 실행
```bash
# 전체 서비스 실행
docker-compose up --build

# OpenSearch만 실행
docker-compose up opensearch opensearch-dashboards
```

### 3. API 테스트
- Demo 페이지: http://localhost:8000/demo
- API 문서: http://localhost:8000/docs

## 아키텍처

### 디렉토리 구조
```
app/
├── main.py              # FastAPI 애플리케이션
├── core/                # 설정 및 로깅
├── models/              # Pydantic 모델
├── services/            # 비즈니스 로직
│   ├── search/          # 검색 서비스
│   ├── embeddings/      # 임베딩 서비스  
│   ├── analysis/        # 분석 서비스
│   └── processing/      # 전처리 서비스
├── clients/             # 외부 API 클라이언트
└── api/routes/          # API 엔드포인트
```

### OpenSearch 인덱스 구조
1. **multimodal_rag_media**: 미디어 파일 메타데이터
2. **multimodal_rag_chunk**: 청크 구조 정보
3. **multimodal_rag_element**: 검색 가능한 요소 (임베딩 포함)

## 환경 변수 설정

`.env` 파일에 다음 설정이 필요합니다:

```bash
# OpenSearch
OPENSEARCH_HOST=localhost
OPENSEARCH_PORT=9200

# External APIs
EMBEDDING_API_URL=http://localhost:8080
FEATURE_EXTRACTION_API_URL=http://localhost:8081

# LLM
LITELLM_URL=http://localhost:4000
LITELLM_MODEL=gpt-4o-mini

# Logging
LOG_LEVEL=info
```

### 멀티모달 입력 지원

시스템은 다음과 같은 입력 조합을 지원합니다:
- 텍스트 + 이미지 + 비디오
- 텍스트 + 비디오  
- 텍스트 + 이미지
- 단일 모달리티 입력도 가능

### 적응형 쿼리 확장 예시

**단순 쿼리 ("파이썬 튜토리얼")**:
```
적용 기법: Rewriting, Semantic Expansion
분해 여부: ⏭️ 건너뜀 (단일 개념)
확장 결과:
  1. "Python 가이드" (재작성)
  2. "파이썬 프로그래밍 학습" (의미 확장)
```

**복합 쿼리 ("파이썬 머신러닝과 데이터 시각화")**:
```
적용 기법: Decomposition, Rewriting, Semantic Expansion  
분해 결과: "파이썬 머신러닝" + "데이터 시각화"
확장 결과:
  1. "Python scikit-learn pandas" (기법별 통합)
  2. "머신러닝 모델 시각화" (의미 확장)
  3. "데이터 분석 차트 그래프" (관련 개념)
```

**구체적 쿼리 ("Matplotlib pyplot.show() 함수")**:
```
적용 기법: Rewriting만
분해 여부: ⏭️ 건너뜀 (구체적 검색)
의미 확장: ⏭️ 건너뜀 (정확한 매칭 중요)
확장 결과:
  1. "Matplotlib show 메서드" (표현 변경)
```

### OpenSearch 인덱스 설계

#### 1. Media Meta 인덱스 (multimodal_rag_media)
미디어 파일의 기본 정보와 메타데이터를 저장하여 필터링 및 집계 기능을 제공합니다.

**주요 필드:**
- `media_id`: 기본키
- `media_type`: 비즈니스 도메인 분류 (video|audio|image|document)
- `file_size_bytes`, `duration_seconds`: 기본 메타데이터
- `width_pixels`, `height_pixels`: 해상도 정보
- `language_primary`: 언어 필터링
- `metadata_flat`: 확장 가능한 기술적 메타데이터 (flattened 타입)

#### 2. Chunk Meta 인덱스 (multimodal_rag_chunk)
미디어 내의 의미 단위 청크에 대한 구조적 정보를 제공합니다.

**주요 필드:**
- `chunk_id`: 기본키
- `media_id`: 부모 미디어 참조
- `chunk_seq`: 미디어 내 순서
- `chunk_type`: 청크 유형 (overview|section|scene|figure|table)
- `modality_set`: 포함된 모달리티 목록
- `element_count`: 포함된 요소 개수

#### 3. Element 인덱스 (multimodal_rag_element)
실제 검색이 수행되는 핵심 인덱스로, 벡터 검색과 텍스트 검색을 모두 지원합니다.

**주요 필드:**
- `element_id`: 기본키
- `chunk_id`, `media_id`: 계층 구조 참조
- `modality`: 모달리티 구분 (text|image|video|audio)
- `element_type`: 세부 유형 (summary|stt|caption|ocr|paragraph)
- `content`: 검색 대상 내용 (BM25 검색용)
- `embeddings`: 벡터 검색용 임베딩 (모달리티별)
- `quality_scores`: 품질 점수 (리랭킹용)

## 시스템 특징

### 계층적 결과 반환
- Element 검색 결과를 기준으로 상위 Chunk Meta와 Media Meta 정보 포함
- Element 점수 기준 정렬 유지
- Chunk/Media Meta 포함 여부는 요청 옵션으로 제어 가능

### 적응형 쿼리 처리
- **선택적 기법 적용**: 쿼리 복잡도와 특성에 따라 필요한 확장 기법만 적용
  - **Query Decomposition**: 복잡한 복합 쿼리에만 적용 (2개 이상 독립 개념)
  - **Query Rewriting**: 대부분 쿼리에 유용 (동의어, 표현 변경)
  - **Semantic Expansion**: 검색 범위 확대가 필요할 때만 적용
- **효율적 확장**: 불필요한 기법 생략으로 처리 시간 단축 및 정확도 향상
- **의도 분석**: 확장된 주요 쿼리 기반으로 적절한 element_type 선택
- **적응형 검색**: 확장된 각 쿼리로 개별 검색 후 가중치 적용하여 통합
- **폴백 메커니즘**: LLM 실패 시 원본 쿼리로 진행

### 고급 검색 기능
- **확장 쿼리 융합**: 우선순위별 가중치 적용 (1.0 → 0.9 → 0.8)
- **중복 제거**: element_id 기반 중복 제거 및 최고 점수 유지
- **RRF 리랭킹**: Reciprocal Rank Fusion 기반 최종 순위 조정
- **하이브리드 검색**: BM25 + 벡터 검색으로 정확도 향상

### 로깅 시스템
- LLM 요청/응답 전체 로깅
- 디버그/운영 레벨 분리 (기본: info)
- 상세 성능 메트릭 제공

### 웹 인터페이스
- `/demo` 엔드포인트에서 검색 테스트 가능
- 실시간 멀티모달 검색 체험
- 결과 시각화 및 메타데이터 표시

## 개발 및 배포

### 코드 품질
```bash
# 코드 포맷팅
python -m isort app/
python -m pyright app/
```

### CI/CD
- GitLab CI를 통한 자동 빌드
- Docker 이미지 GitLab Container Registry 푸시
- 다단계 배포 파이프라인 지원

---

## 라이선스 및 기여

이 프로젝트는 멀티모달 검색 기술의 연구 및 개발 목적으로 작성되었습니다.
