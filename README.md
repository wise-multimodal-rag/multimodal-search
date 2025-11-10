# Multimodal Search & RAG System

## 프로젝트 개요

OpenSearch를 사용한 멀티모달 검색 및 RAG 시스템입니다. 텍스트, 이미지, 비디오, 오디오를 통합하여 검색하고, 하이브리드 검색(BM25 + 벡터 검색)과 LLM 기반 질의 분석을 지원합니다.

## 시스템 아키텍처

### 1. 멀티모달 검색 파이프라인

```mermaid
flowchart TD
    %% 입력 단계
    A[사용자 요청] --> B[입력 파일 분석]
    B --> C1[텍스트 쿼리]
    B --> C2[이미지 파일]
    B --> C3[비디오 파일]
    B --> C4[오디오 파일]
    B --> C5[텍스트 파일]
    
    %% Step 1: 입력 처리
    C1 --> G[Step 1: 멀티모달 입력 처리<br/>InputProcessor]
    C2 --> G
    C3 --> G
    C4 --> G
    C5 --> G
    G --> G1[텍스트 데이터 구조화]
    G --> G2[이미지 Base64 변환]
    G --> G3[비디오 Base64 변환]
    G --> G4[오디오 Base64 변환]
    
    %% Step 2: 쿼리 확장 및 의도 분석
    G1 --> H[Step 2: 쿼리 확장 및 의도 분석<br/>QueryAnalyzer]
    H --> H1[🤖 지능형 쿼리 확장<br/>필요한 기법만 선택적 적용]
    H1 --> H1A{🤖 LLM 확장 성공?}
    H1A -->|성공| H2[적응형 확장 쿼리 생성<br/>쿼리 특성에 따라 1-3개]
    H1A -->|실패| H3[원본 쿼리 사용<br/>확장 없이 진행]
    
    H2 --> H2A{🤖 의존성 판단<br/>has_dependency?}
    H2A -->|true| H2B[순차적 의존성 표시<br/>Query 2가 Query 1 결과 필요]
    H2A -->|false| H2C[병렬 독립 실행 표시<br/>모든 쿼리 독립적]
    
    H2B --> H4[🤖 의도 분석<br/>확장된 주요 쿼리 기반]
    H2C --> H4
    H3 --> H4
    H4 --> H4A{🤖 LLM 분석 성공?}
    H4A -->|성공| H5[🤖 LLM 기반 element_type 선택 + 가중치 계산]
    H4A -->|실패| H6[휴리스틱 기반 폴백 분석]
    H5 --> I[선택된 element_types + 확장된 쿼리들 + element_type_weights<br/>paragraph:0.8, summary:0.6, caption:0.3, origin:1.0]
    H6 --> I
    
    %% Step 3: 특징 추출
    G2 --> J[Step 3: 멀티모달 특징 추출<br/>MultimodalFeatureExtractor]
    I --> J
    J --> J1{입력 모달리티 확인}
    J1 -->|텍스트만| J2[텍스트 특징 건너뛰기<br/>원본 텍스트 쿼리 직접 사용]
    J1 -->|이미지 첨부| J3[이미지 특징 추출<br/>캡션 + tags 무조건 생성]
    J1 -->|비디오 첨부| J4[🤖 비디오 특징 추출<br/>현재 비활성화됨]
    J1 -->|오디오 첨부| J5[🤖 오디오 특징 추출<br/>현재 비활성화됨]
    
    %% Step 4: 임베딩 생성
    G1 --> K[Step 4: 임베딩 생성<br/>EmbeddingService]
    G2 --> K
    G3 --> K
    G4 --> K
    J2 --> K
    J3 --> K
    J4 --> K
    J5 --> K
    K --> K1[원본 모달리티 임베딩<br/>text, image, video, audio]
    K --> K2[특징 기반 임베딩<br/>image_caption만 활성화]
    
    %% Step 5: 확장 쿼리 검색 실행 + 이미지 태그 보강
    I --> L[Step 5: 확장 쿼리 검색 실행<br/>SearchExecutor]
    K1 --> L
    K2 --> L
    J3 --> L5A[이미지 캡션 tags 추출]
    L5A --> L
    L --> L0{의존성 확인<br/>has_dependency?}
    L0 -->|true| L1A[순차적 검색 실행<br/>Query 1 → 컨텍스트 추출 → Query 2]
    L0 -->|false| L1B[병렬 검색 실행<br/>Query 1, 2, 3 동시 실행]
    
    L1A --> L1A1[Query 1 실행<br/>element_types 필터 + 하이브리드 검색]
    L1A1 --> L1A2[결과에서 컨텍스트 추출<br/>키워드, 엔티티, 개념]
    L1A2 --> L1A3[Query 2 컨텍스트 보강<br/>이전 결과 정보 활용]
    L1A3 --> L1A4[Query 2 실행<br/>보강된 쿼리로 검색]
    
    L1B --> L2[각 쿼리마다<br/>element_types 필터 + 하이브리드 검색]
    L1A4 --> L3[OpenSearch 통합 쿼리<br/>OpenSearchService → multimodal_rag_element]
    L2 --> L3
    L3 --> L3A[텍스트 검색: multi_match + image_caption_tags<br/>벡터 검색: modality 매핑 + 동적 boost]
    L3A --> L4[쿼리별 가중치 적용<br/>1st-1.0 2nd-0.9 3rd-0.8]
    L4 --> L5[결과 통합 및 중복 제거<br/>점수 기준 최종 정렬]
    
    %% Step 6: 결과 강화
    L5 --> M[Step 6: 결과 enrichment<br/>ResultEnricher]
    M --> M1{chunk_meta 포함?}
    M --> M2{media_meta 포함?}
    M1 -->|Yes| M3[청크 메타데이터 조회]
    M2 -->|Yes| M4[미디어 메타데이터 조회]
    M3 --> N[강화된 검색 결과]
    M4 --> N
    M1 -->|No| N
    M2 -->|No| N
    
    %% Step 7: 검색 응답 생성
    N --> O[Step 7: 검색 응답 생성<br/>SearchResponse + 첨부 이미지 캡션]
    O --> O1[검색 통계 계산]
    O --> O2[실행 시간 측정]
    O --> SR[검색 결과 완료]
    
    %% 외부 API 의존성
    J3 -.->|API 호출| API2[Embedding API<br/>이미지 캡션 + tags 생성]
    J4 -.->|🤖 LLM 호출| API3[🤖 LiteLLM<br/>비디오 분석 - 비활성화]
    J5 -.->|🤖 LLM 호출| API3[🤖 LiteLLM<br/>오디오 분석 - 비활성화]
    K -.->|API 호출| API4[Embedding API<br/>text + image_caption 임베딩]
    H -.->|🤖 LLM 호출| API3[🤖 LiteLLM<br/>쿼리 분석 + element_type 가중치]
    
    %% 인덱스 구조
    L3A -.-> IDX1[(multimodal_rag_element<br/>검색 가능한 요소<br/>embeddings.text + embeddings.image)]
    M3 -.-> IDX2[(multimodal_rag_chunk<br/>청크 메타데이터)]
    M4 -.-> IDX3[(multimodal_rag_media<br/>미디어 메타데이터)]
    
    %% 스타일링
    classDef stepClass fill:#e1f5fe,stroke:#01579b,stroke-width:2px
    classDef apiClass fill:#fff3e0,stroke:#f57c00,stroke-width:2px
    classDef dbClass fill:#e8f5e8,stroke:#2e7d32,stroke-width:2px
    classDef llmClass fill:#f3e5f5,stroke:#7b1fa2,stroke-width:3px
    classDef enhancedClass fill:#e8f5e8,stroke:#4caf50,stroke-width:3px
    
    class G,H,J,J1,K,L,M,O stepClass
    class API2,API4 apiClass
    class API3 llmClass
    class H1,H1A,H2,H2A,H2B,H2C,H4,H4A,H5,J4,J5 llmClass
    class IDX1,IDX2,IDX3 dbClass
    class L3A,L5A enhancedClass
```

### 2. LLM 답변 생성 파이프라인

```mermaid
flowchart TD
    %% 시작점
    START[검색 결과 입력<br/>SearchResponse] --> AG[AnswerGenerationService]
    
    %% 컨텍스트 준비
    AG --> AG1[검색 결과를 컨텍스트로 변환<br/>상위 10개 결과 사용]
    AG1 --> AG1A{첨부 이미지 캡션<br/>존재?}
    AG1A -->|Yes| AG1B[첨부 이미지 캡션<br/>컨텍스트에 추가]
    AG1A -->|No| AG1C[origin element의 caption 자동 조회<br/>중복 제거 후 컨텍스트 보강]
    AG1B --> AG1C
    AG1C --> AG2[답변 생성 루프 시작<br/>최대 2회 시도 고정]
    
    %% 답변 생성 루프 (간소화됨)
    AG2 --> ATTEMPT1[1차 시도: 초안 생성]
    ATTEMPT1 --> GEN1[🤖 LLM 답변 생성<br/>temperature: 0.7<br/>이전 개선 제안 없음]
    GEN1 --> REF1[🤖 LLM Reflection 평가<br/>5차원 평가: 정확성, 완성도, 명확성, 구조, 관련성]
    REF1 --> EVAL1[평가 점수 계산<br/>총점 / 50점]
    EVAL1 --> CHECK1{1차 품질 평가<br/>35점 이상?}
    
    %% 1차 시도 결과 처리
    CHECK1 -->|Yes, 수락| ACCEPT1[1차 답변 수락<br/>생성 완료]
    CHECK1 -->|No, 재시도| ATTEMPT2[2차 시도: 개선 답변]
    
    %% 2차 시도 (개선 제안 활용)
    ATTEMPT2 --> IMPROVE[이전 reflection에서<br/>improvement_suggestions 추출]
    IMPROVE --> GEN2[🤖 LLM 답변 재생성<br/>temperature: 0.8<br/>개선 제안 반영]
    GEN2 --> REF2[🤖 LLM Reflection 평가<br/>2차 답변 품질 평가]
    REF2 --> EVAL2[평가 점수 계산<br/>총점 / 50점]
    EVAL2 --> CHECK2{2차 품질 평가<br/>35점 이상?}
    
    %% 2차 시도 결과 처리
    CHECK2 -->|Yes, 수락| ACCEPT2[2차 답변 수락<br/>개선된 답변 채택]
    CHECK2 -->|No, 최고점 선택| SELECT_BEST[1차 vs 2차 점수 비교<br/>최고 점수 답변 선택]
    
    %% 최종 결과 생성
    ACCEPT1 --> SUCCESS_GR[GenerationResponse 생성<br/>success: true, 1차 시도]
    ACCEPT2 --> SUCCESS_GR2[GenerationResponse 생성<br/>success: true, 2차 시도]
    SELECT_BEST --> FINAL_CHECK{최종 선택 답변<br/>35점 이상?}
    FINAL_CHECK -->|Yes| SUCCESS_GR3[GenerationResponse 생성<br/>success: true, best attempt]
    FINAL_CHECK -->|No| PARTIAL_GR[GenerationResponse 생성<br/>success: false, 부분적 성공]
    
    %% 최종 응답
    SUCCESS_GR --> RESPONSE[최종 응답 반환<br/>final_answer, generation_attempts, best_score]
    SUCCESS_GR2 --> RESPONSE
    SUCCESS_GR3 --> RESPONSE
    PARTIAL_GR --> RESPONSE
    
    %% 외부 API 호출
    GEN1 -.->|🤖 LLM 호출| LLM_API[🤖 LiteLLM<br/>답변 생성]
    GEN2 -.->|🤖 LLM 호출| LLM_API
    REF1 -.->|🤖 LLM 호출| LLM_API2[🤖 LiteLLM<br/>JSON 강제 품질 평가]
    REF2 -.->|🤖 LLM 호출| LLM_API2
    AG1C -.->|OpenSearch 조회| OS_API[OpenSearch<br/>origin element caption 조회]
    
    %% 스타일링
    classDef startClass fill:#e8f5e8,stroke:#4caf50,stroke-width:2px
    classDef processClass fill:#e1f5fe,stroke:#01579b,stroke-width:2px
    classDef llmClass fill:#f3e5f5,stroke:#7b1fa2,stroke-width:3px
    classDef decisionClass fill:#fff3e0,stroke:#f57c00,stroke-width:2px
    classDef endClass fill:#fce4ec,stroke:#c2185b,stroke-width:2px
    classDef apiClass fill:#fff8e1,stroke:#ff8f00,stroke-width:2px
    classDef improveClass fill:#e8f5e8,stroke:#4caf50,stroke-width:3px
    
    class START,AG1,AG1B,AG1C,AG2,SUCCESS_GR,SUCCESS_GR2,SUCCESS_GR3,PARTIAL_GR startClass
    class ATTEMPT1,ATTEMPT2,EVAL1,EVAL2,SELECT_BEST processClass
    class GEN1,GEN2,REF1,REF2 llmClass
    class AG1A,CHECK1,CHECK2,FINAL_CHECK decisionClass
    class ACCEPT1,ACCEPT2,RESPONSE endClass
    class LLM_API,LLM_API2,OS_API apiClass
    class IMPROVE improveClass
```

## 주요 특징

### 멀티모달 검색 엔진
- **멀티모달 입력**: 텍스트, 이미지, 비디오, 오디오, 텍스트 파일 동시 지원
- **적응형 쿼리 확장**: 쿼리 특성에 따른 선택적 기법 적용 (Decomposition, Rewriting, Expansion)
- **지능형 의존성 처리**: LLM이 판단하는 순차/병렬 실행 방식 자동 선택
- **하이브리드 검색**: BM25 텍스트 검색 + 벡터 유사도 검색 + 이미지 캡션 태그 보강
- **LLM 기반 질의 분석**: 검색 의도 파악 및 최적 element type 선택 + 가중치 계산
- **이미지 캡션 태그 통합**: 이미지 캡션의 tags를 텍스트 검색 쿼리에 자동 추가 (1000자 제한)
- **동적 modality boost**: element_type_weights 기반 벡터 검색 가중치 동적 계산
- **간소화된 가중치 시스템**: 3개 핵심 설정으로 모든 세부 가중치 자동 계산

### AI 답변 생성 시스템
- **간소화된 2회 시도 시스템**: 초안 생성 → Reflection 평가 → 개선 제안 기반 재생성 (고정 2회)
- **5차원 품질 평가**: 정확성, 완성도, 명확성, 구조, 관련성 종합 평가 (총 50점)
- **첨부 이미지 지원**: 검색 결과와 첨부 이미지 캡션을 통합한 컨텍스트 생성
- **자동 캡션 보강**: origin element의 관련 caption 자동 조회 및 중복 제거
- **스트리밍 답변 생성**: 실시간 생성 과정 모니터링, 취소 가능, 시간 제한 (5분)
- **개선 제안 활용**: 이전 시도의 improvement_suggestions를 다음 시도에 반영

### 시스템 아키텍처
- **3계층 인덱스 구조**: media_meta, chunk_meta, elements로 체계적 관리
- **외부 API 통합**: Feature Extraction 및 Embedding API 활용
- **고급 예외 처리**: Circuit Breaker 패턴과 Retry Handler로 시스템 안정성 보장
- **보안 강화**: 민감 정보 마스킹 및 API 키 관리 시스템
- **병렬 처리 최적화**: 검색 및 임베딩 생성의 비동기 병렬 처리
- **외부 API 모니터링**: 실시간 외부 서비스 상태 체크 및 헬스 모니터링
- **스마트 로깅**: Base64 데이터 마스킹 및 노이즈 필터링으로 효율적인 디버깅
- **강화된 입력 검증**: 유연한 파일 시그니처 검증 및 XSS 방지

## 기술 스택

- **Backend**: FastAPI (Python 3.11+)
- **Package Manager**: uv + pyproject.toml
- **Search Engine**: OpenSearch (벡터 검색 지원)
- **LLM**: LiteLLM (다중 모델 지원)
- **External APIs**: Embedding & Feature Extraction Services
- **Deployment**: Docker + GitLab CI/CD

## ⚖️ 가중치 시스템

검색 정확도를 제어하는 핵심 시스템입니다. 사용자는 3개의 핵심 설정만 하면 됩니다.

### 핵심 사용자 설정 (3개)
- **WEIGHT_TEXT_STRENGTH** (0.0~1.0): 텍스트 검색 강도
- **WEIGHT_IMAGE_STRENGTH** (0.0~1.0): 이미지 검색 강도  
- **WEIGHT_VECTOR_BOOST_STRENGTH** (0.5~3.0): 벡터 검색 가중치

### 자동 계산되는 세부 가중치
- **Element Type별 가중치**: origin(1.0), paragraph(0.8), summary(0.6), caption(0.3)
- **쿼리별 가중치**: 1st(1.0), 2nd(0.9), 3rd(0.8) - QUERY_DECAY 기반
- **Modality Boost**: element_type_weights 기반 동적 계산 (0.5~2.0 범위)
- **텍스트/이미지 검색 균형**: 핵심 설정 기반 자동 조정

자세한 설정은 `app/core/config.py`의 WeightingConfig 참조

## 🚀 빠른 시작

### 1. 환경 설정
```bash
# 저장소 클론
git clone <repository-url>
cd multimodal-search

# 환경 변수 설정
cp .env.example .env
# .env 파일을 편집하여 실제 값으로 설정
```

### 2. 의존성 설치
```bash
# uv 패키지 매니저 사용 (권장)
uv pip install -e .

# 개발 의존성 포함
uv pip install -e .[dev]
```

### 3. 실행 방법

#### 로컬 개발 서버
```bash
# 개발 서버 실행
python run.py

# 또는 uvicorn 직접 실행
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### Docker 실행
```bash
# 전체 서비스 실행 (OpenSearch + App)
docker-compose up --build

# OpenSearch만 실행
docker-compose up opensearch opensearch-dashboards

# LiteLLM 포함 개발 환경
docker-compose --profile dev up
```

### 4. 접속 및 테스트
- **웹 데모**: http://localhost:8000/search
- **API 문서**: http://localhost:8000/docs
- **헬스체크**: http://localhost:8000/health
- **외부 API 상태**: http://localhost:8000/health/external-apis
- **OpenSearch 대시보드**: http://localhost:5601

#### API 엔드포인트
- **멀티모달 검색**: `POST /api/search/multimodal`
- **AI 답변 생성**: `POST /api/generation/multimodal`
- **스트리밍 검색+생성**: `POST /api/search/multimodal/stream`

## 아키텍처

### 디렉토리 구조
```
app/
├── main.py              # FastAPI 애플리케이션 (글로벌 예외 처리 미들웨어 포함)
├── core/                # 핵심 시스템 컴포넌트
│   ├── config.py        # 설정 관리
│   ├── logging.py       # 로깅 시스템 (스마트 필터링)
│   ├── security.py      # 보안 관리 (API 키 마스킹, 보안 유틸리티)
│   ├── exceptions.py    # 예외 처리 (Circuit Breaker, Retry Handler, 미들웨어)
│   ├── validators.py    # 강화된 입력 검증 (파일 시그니처, XSS 방지)
│   ├── dependencies.py  # 의존성 주입
│   └── index_mappings.py # OpenSearch 인덱스 매핑
├── models/              # Pydantic 모델
│   ├── opensearch.py    # 검색 관련 모델
│   ├── generation.py    # 답변 생성 관련 모델
│   └── features.py      # 특징 추출 모델
├── services/            # 비즈니스 로직 (병렬 처리 최적화)
│   ├── search/          # 검색 서비스 (병렬 쿼리 실행)
│   ├── generation/      # AI 답변 생성 서비스
│   ├── streaming/       # 스트리밍 통합 서비스
│   ├── embeddings/      # 임베딩 서비스 (병렬 임베딩 생성)
│   ├── analysis/        # 분석 서비스
│   └── processing/      # 전처리 서비스
├── clients/             # 외부 API 클라이언트 (보안 강화)
│   ├── llm_client.py    # LLM 클라이언트 (답변 생성용)
│   ├── embedding_client.py # 임베딩 API 클라이언트
│   └── feature_extraction_client.py # 특징 추출 API 클라이언트
└── api/routes/          # API 엔드포인트
    ├── search.py        # 검색 엔드포인트
    ├── generation.py    # 답변 생성 엔드포인트
    └── config.py        # 설정 엔드포인트
```

### OpenSearch 인덱스 구조
1. **multimodal_rag_media**: 미디어 파일 메타데이터
2. **multimodal_rag_chunk**: 청크 구조 정보
3. **multimodal_rag_element**: 검색 가능한 요소 (임베딩 포함)

## 환경 변수 설정

`.env` 파일에 다음 설정이 필요합니다:

```bash
# OpenSearch Configuration
OPENSEARCH_HOST=localhost
OPENSEARCH_PORT=9200
OPENSEARCH_USE_SSL=false
OPENSEARCH_VERIFY_CERTS=false
OPENSEARCH_USERNAME=admin
OPENSEARCH_PASSWORD=admin

# External API Configuration
EMBEDDING_API_URL=http://localhost:8080
FEATURE_EXTRACTION_API_URL=http://localhost:8081
MULTIMODAL_API_KEY=your-secure-api-key

# LiteLLM Configuration
LITELLM_URL=http://localhost:4000
LITELLM_API_KEY=your-secure-llm-key
LITELLM_MODEL=gpt-4o-mini

# Application Configuration
APP_HOST=127.0.0.1
APP_PORT=8000
LOG_LEVEL=info
DEBUG=false

# Storage Configuration
STORAGE_PATH=/storage
```

**보안 주의사항:**
- `.env` 파일은 이미 `.gitignore`에 추가되어 버전 관리에서 제외됩니다
- 프로덕션 환경에서는 환경 변수나 보안 관리 시스템을 사용하세요
- API 키는 절대 하드코딩하지 마세요

### 멀티모달 입력 지원
- 텍스트 + 이미지 + 비디오
- 텍스트 + 비디오/이미지
- 단일 모달리티 입력

### 쿼리 확장 예시
- **단순 쿼리**: "파이썬 튜토리얼" → "Python 가이드", "파이썬 프로그래밍 학습" (병렬 처리)
- **복합 쿼리**: "파이썬 머신러닝과 시각화" → 두 개념으로 분해 후 병렬 검색
- **의존 쿼리**: "최신 라이브러리와 사용법" → 1차 결과를 2차 쿼리에 반영하여 순차 처리

### OpenSearch 인덱스 설계

#### 3계층 인덱스 구조
1. **Media Meta**: 미디어 파일 메타데이터 (`media_id`, `media_type`, 파일 정보)
2. **Chunk Meta**: 청크 구조 정보 (`chunk_id`, `chunk_type`, 모달리티 정보)  
3. **Element**: 검색 대상 요소 (`element_id`, `content`, `embeddings`, 품질 점수)

## 시스템 특징

### 🔍 지능형 검색
- **적응형 쿼리 확장**: 쿼리 특성에 따른 선택적 기법 적용 (분해, 재작성, 의미 확장)
- **🆕 지능형 의존성 판단**: LLM이 쿼리 간 의존성을 자동 분석하여 실행 방식 결정
- **하이브리드 검색**: BM25 텍스트 검색 + 벡터 유사도 검색 결합
- **🆕 적응형 실행**: 독립적 쿼리는 병렬, 의존적 쿼리는 순차 처리
- **🆕 컨텍스트 보강**: 이전 검색 결과를 활용한 다음 쿼리 정확도 향상
- **폴백 메커니즘**: LLM 실패 시 원본 쿼리로 안정적 서비스 지속

### 🛡️ 시스템 안정성
- **Circuit Breaker**: 외부 API 장애 시 서비스 보호 및 빠른 복구
- **자동 재시도**: 지수 백오프를 통한 일시적 오류 극복
- **보안 강화**: API 키 마스킹 및 민감 정보 보호
- **글로벌 예외 처리**: 통합된 오류 처리 및 구조화된 응답

### ⚡ 성능 최적화
- **병렬 처리**: 임베딩 생성 및 메타데이터 조회 동시 실행
- **스마트 로깅**: 86% 볼륨 감소 및 Base64 데이터 마스킹
- **검색 로직 간소화**: 불필요한 리랭킹 과정 제거
- **실시간 모니터링**: 외부 API 상태 및 응답 시간 추적

## 주요 업데이트

### v0.3.2 - 간소화된 답변 생성 시스템 (현재)
- **🆕 고정 2회 시도 시스템**: 복잡한 재검색 로직 제거, 개선 제안 기반 재생성으로 단순화
- **🆕 첨부 이미지 통합**: 검색 결과와 첨부 이미지 캡션을 통합한 컨텍스트 생성
- **🆕 자동 캡션 보강**: origin element의 관련 caption 자동 조회 및 중복 제거
- **스트리밍 최적화**: 실시간 모니터링, 취소 가능, 5분 시간 제한
- **개선 제안 활용**: 이전 시도의 improvement_suggestions를 다음 시도에 반영

### v0.3.0 - AI 답변 생성 시스템
- **Reflection 기반 품질 관리**: 5차원 평가를 통한 답변 품질 보장 (총 50점)
- **품질 임계값**: 35점 이상 답변 수락, 이하 시 재생성 또는 최고점 선택
- **스트리밍 답변 생성**: 실시간 생성 과정 모니터링

### v0.2.0 - 지능형 검색 시스템  
- **LLM 기반 쿼리 분해**: 의존성 인식 순차/병렬 실행
- **컨텍스트 전파**: 이전 검색 결과 활용한 쿼리 보강
- **성능 최적화**: 86% 로깅 감소, Circuit Breaker 패턴

---

## 라이선스 및 기여

이 프로젝트는 멀티모달 검색 기술의 연구 및 개발 목적으로 작성되었습니다.
