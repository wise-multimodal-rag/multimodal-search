# Multimodal Search & RAG System

## 프로젝트 개요

OpenSearch를 사용한 멀티모달 검색 및 RAG 시스템입니다. 텍스트, 이미지, 비디오, 오디오를 통합하여 검색하고, 하이브리드 검색(BM25 + 벡터 검색)과 LLM 기반 질의 분석을 지원합니다.

## 📚 기술 스택 및 아키텍처

- **Backend**: FastAPI (Python 3.11+)
- **Package Manager**: uv + pyproject.toml
- **Search Engine**: OpenSearch (벡터 검색 지원)
- **LLM**: LiteLLM (다중 모델 지원)
- **External APIs**: Embedding & Feature Extraction Services
- **Deployment**: Docker + GitLab CI/CD
- **Architecture**: 도메인 기반 모듈 구조 + 의존성 주입 패턴
- **Error Handling**: 중앙집중식 예외 처리 + Circuit Breaker 패턴
- **API Response**: 표준화된 응답 모델 + 메타데이터 통합

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

### 2. 지능형 쿼리 확장 파이프라인

```mermaid
flowchart TD
    %% 시작점
    START[원본 텍스트 쿼리] --> ENTRY[🤖 지능형 쿼리 확장]
    
    %% 핵심 처리 단계
    ENTRY --> EXPAND[쿼리 확장 & 분해<br/>LLM 기반 1-3개 쿼리 생성]
    EXPAND --> DEPENDENCY[의존성 판단<br/>순차 vs 병렬 실행 결정]
    DEPENDENCY --> INTENT[의도 분석<br/>최적 element type 선택]
    INTENT --> OUTPUT[최종 실행 계획<br/>확장 쿼리 + 가중치 + 실행방식]
    
    %% 실행 방식
    OUTPUT --> PARALLEL[병렬 실행<br/>독립적 쿼리 동시 처리]
    OUTPUT --> SEQUENTIAL[순차 실행<br/>컨텍스트 전파 활용]
    
    %% 외부 API
    EXPAND -.->|🤖 LLM 호출| LLM_API[LiteLLM 서비스]
    DEPENDENCY -.->|🤖 LLM 호출| LLM_API
    INTENT -.->|🤖 LLM 호출| LLM_API
    
    %% 스타일링
    classDef startClass fill:#e8f5e8,stroke:#4caf50,stroke-width:2px
    classDef processClass fill:#e1f5fe,stroke:#01579b,stroke-width:2px
    classDef llmClass fill:#f3e5f5,stroke:#7b1fa2,stroke-width:3px
    classDef outputClass fill:#fce4ec,stroke:#c2185b,stroke-width:2px
    classDef execClass fill:#fff3e0,stroke:#f57c00,stroke-width:2px
    classDef apiClass fill:#fff8e1,stroke:#ff8f00,stroke-width:2px
    
    class START startClass
    class ENTRY,EXPAND,DEPENDENCY,INTENT processClass
    class OUTPUT outputClass
    class PARALLEL,SEQUENTIAL execClass
    class LLM_API apiClass
```

### 3. 모달리티별 특징 보강 하이브리드 검색 파이프라인

```mermaid
flowchart TD
    %% 시작점
    START[멀티모달 입력<br/>텍스트 + 이미지] --> MODAL_CHECK{입력 모달리티 확인}
    
    %% 모달리티별 특징 추출
    MODAL_CHECK -->|텍스트만| TEXT_ONLY[텍스트 특징 건너뛰기<br/>원본 텍스트 쿼리 직접 사용]
    MODAL_CHECK -->|이미지 첨부| IMG_EXTRACT[이미지 특징 추출<br/>MultimodalFeatureExtractor]
    
    %% 이미지 특징 추출 상세
    IMG_EXTRACT --> IMG_CAPTION[이미지 캡션 생성<br/>Embedding API 호출]
    IMG_EXTRACT --> IMG_TAGS[이미지 태그 생성<br/>객체 탐지 + 분류]
    IMG_CAPTION --> IMG_FEATURES[이미지 특징 통합<br/>caption + tags]
    IMG_TAGS --> IMG_FEATURES
    
    %% 특징 기반 임베딩 생성
    TEXT_ONLY --> EMBED_GEN[임베딩 생성<br/>EmbeddingService]
    IMG_FEATURES --> EMBED_GEN
    
    EMBED_GEN --> ORIG_EMBED[원본 모달리티 임베딩<br/>text, image]
    EMBED_GEN --> FEAT_EMBED[특징 기반 임베딩<br/>image_caption 활성화]
    
    %% 검색 쿼리 보강
    IMG_FEATURES --> QUERY_ENHANCE[검색 쿼리 보강<br/>이미지 특징을 텍스트 쿼리에 통합]
    QUERY_ENHANCE --> TAG_EXTRACT[이미지 캡션 tags 추출<br/>1000자 제한]
    TAG_EXTRACT --> ENHANCED_QUERY[보강된 검색 쿼리<br/>원본 텍스트 + 이미지 tags]
    
    TEXT_ONLY --> ORIGINAL_QUERY[원본 텍스트 쿼리<br/>특징 보강 없음]
    
    %% 하이브리드 검색 실행
    ENHANCED_QUERY --> HYBRID_SEARCH[하이브리드 검색 실행<br/>OpenSearchService]
    ORIGINAL_QUERY --> HYBRID_SEARCH
    ORIG_EMBED --> HYBRID_SEARCH
    FEAT_EMBED --> HYBRID_SEARCH
    
    %% 후속 처리 생략
    HYBRID_SEARCH --> ELLIPSIS[... 검색 결과 처리<br/>점수 계산, 정렬, 결과 반환]
    
    %% 외부 API 호출
    IMG_CAPTION -.->|API 호출| IMG_API[Embedding API<br/>이미지 캡션 생성]
    IMG_TAGS -.->|API 호출| IMG_API
    ORIG_EMBED -.->|API 호출| EMB_API[Embedding API<br/>텍스트/이미지 임베딩]
    FEAT_EMBED -.->|API 호출| EMB_API
    
    %% 인덱스 구조
    HYBRID_SEARCH -.-> ELEMENT_IDX[(multimodal_rag_element<br/>content + embeddings.text/image<br/>element_type + modality)]
    
    %% 스타일링
    classDef startClass fill:#e8f5e8,stroke:#4caf50,stroke-width:2px
    classDef modalClass fill:#e1f5fe,stroke:#01579b,stroke-width:2px
    classDef featureClass fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px
    classDef searchClass fill:#fff3e0,stroke:#f57c00,stroke-width:2px
    classDef hybridClass fill:#e8f5e8,stroke:#4caf50,stroke-width:3px
    classDef resultClass fill:#fce4ec,stroke:#c2185b,stroke-width:2px
    classDef apiClass fill:#fff8e1,stroke:#ff8f00,stroke-width:2px
    classDef dbClass fill:#f1f8e9,stroke:#689f38,stroke-width:2px
    classDef improveClass fill:#f3e5ab,stroke:#827717,stroke-width:3px
    
    class START,MODAL_CHECK startClass;
    class TEXT_ONLY,IMG_EXTRACT modalClass;
    class IMG_CAPTION,IMG_TAGS,IMG_FEATURES,QUERY_ENHANCE,TAG_EXTRACT featureClass;
    class ENHANCED_QUERY,ORIGINAL_QUERY searchClass;
    class HYBRID_SEARCH hybridClass;
    class ELLIPSIS resultClass;
    class IMG_API,EMB_API apiClass;
    class ELEMENT_IDX dbClass;
```

### 4. 멀티모달 통합 및 쿼리 재작성 파이프라인

```mermaid
flowchart TD
    %% 시작점
    START[멀티모달 입력<br/>텍스트 + 이미지] --> INPUT_PARSE[입력 데이터 파싱]
    
    %% 핵심 처리 단계
    INPUT_PARSE --> FEATURE_EXTRACT[특징 추출<br/>텍스트 분석 + 이미지 분석]
    FEATURE_EXTRACT --> MULTIMODAL_FUSION[멀티모달 특징 통합<br/>모든 모달리티 정보 융합]
    MULTIMODAL_FUSION --> QUERY_REWRITE[🤖 쿼리 재작성<br/>LLM 기반 통합 쿼리 생성]
    QUERY_REWRITE --> QUALITY_CHECK[🤖 품질 검증<br/>쿼리 품질 평가]
    
    %% 최종 출력
    QUALITY_CHECK --> OUTPUT[최종 검색 쿼리<br/>SearchExecutor로 전달]
    
    %% 외부 API
    FEATURE_EXTRACT -.->|API 호출| VISION_API[Vision API<br/>이미지 분석]
    QUERY_REWRITE -.->|🤖 LLM 호출| LLM_API[LiteLLM 서비스]
    QUALITY_CHECK -.->|🤖 LLM 호출| LLM_API
    
    %% 스타일링
    classDef startClass fill:#e8f5e8,stroke:#4caf50,stroke-width:2px
    classDef processClass fill:#e1f5fe,stroke:#01579b,stroke-width:2px
    classDef fusionClass fill:#fff3e0,stroke:#f57c00,stroke-width:3px
    classDef llmClass fill:#f3e5f5,stroke:#7b1fa2,stroke-width:3px
    classDef outputClass fill:#fce4ec,stroke:#c2185b,stroke-width:2px
    classDef apiClass fill:#fff8e1,stroke:#ff8f00,stroke-width:2px
    
    class START startClass
    class INPUT_PARSE,FEATURE_EXTRACT processClass
    class MULTIMODAL_FUSION fusionClass
    class QUERY_REWRITE,QUALITY_CHECK llmClass
    class OUTPUT outputClass
    class VISION_API,LLM_API apiClass
```

### 5. 메타데이터 기반 필터링 시스템 파이프라인

메타데이터 기반 필터링 시스템은 OpenSearch의 3계층 인덱스 구조를 활용하여 체계적이고 효율적인 검색을 제공합니다. BM25 알고리즘과 한국어-영어 복합 분석기를 통해 정확한 키워드 매칭과 의미적 검색이 가능하며, element_type별 동적 가중치 시스템으로 검색 결과의 관련성을 최적화합니다.

이 시스템의 핵심은 사용자 쿼리의 의도에 따라 적절한 콘텐츠 유형만을 선별적으로 검색하는 지능형 필터링 메커니즘입니다. 예를 들어, 원본 이미지나 문서를 찾고자 할 때는 origin 필터를, 요약 정보가 필요할 때는 summary 필터를 적용하여 검색 정확도를 크게 향상시킵니다. 또한 3계층 인덱스 구조(Elements, Chunk Meta, Media Meta)를 통해 콘텐츠 레벨부터 파일 메타데이터까지 다층적 정보를 체계적으로 관리하며, 각 element_type별로 차등화된 가중치(origin 1.0, paragraph 0.8, summary 0.6, caption 0.3)를 적용하여 콘텐츠의 중요도에 따른 우선순위 검색을 지원합니다.

```mermaid
flowchart TD
    %% 시작점
    START[검색 쿼리 입력] --> ELEMENT_FILTER[Element Type 필터 설정<br/>검색 대상 콘텐츠 유형 선택]
    
    %% Element Type 필터링
    ELEMENT_FILTER --> FILTER_CHECK{적용할 필터 확인}
    FILTER_CHECK -->|origin 필터| ORIGIN_FILTER[origin 콘텐츠 필터<br/>원본 미디어 우선 검색]
    FILTER_CHECK -->|paragraph 필터| PARA_FILTER[paragraph 콘텐츠 필터<br/>텍스트 단락 중심 검색]
    FILTER_CHECK -->|summary 필터| SUMMARY_FILTER[summary 콘텐츠 필터<br/>AI 요약본 검색]
    FILTER_CHECK -->|caption 필터| CAPTION_FILTER[caption 콘텐츠 필터<br/>이미지 캡션 검색]
    
    %% 3계층 인덱스 필터링
    ORIGIN_FILTER --> INDEX_FILTER[3계층 인덱스 필터링<br/>메타데이터 기반 콘텐츠 선별]
    PARA_FILTER --> INDEX_FILTER
    SUMMARY_FILTER --> INDEX_FILTER
    CAPTION_FILTER --> INDEX_FILTER
    
    %% 인덱스별 필터링 적용
    INDEX_FILTER --> ELEMENT_IDX[(Elements Index<br/>multimodal_rag_element<br/>content + element_type + modality)]
    INDEX_FILTER --> CHUNK_IDX[(Chunk Meta Index<br/>multimodal_rag_chunk<br/>청크 구조 메타데이터)]
    INDEX_FILTER --> MEDIA_IDX[(Media Meta Index<br/>multimodal_rag_media<br/>미디어 파일 메타데이터)]
    
    %% 필터링된 결과
    ELEMENT_IDX --> FILTERED_RESULTS[필터링된 검색 결과<br/>선택된 element_type만 포함]
    CHUNK_IDX --> FILTERED_RESULTS
    MEDIA_IDX --> FILTERED_RESULTS
    
    %% 최종 출력
    FILTERED_RESULTS --> OUTPUT[메타데이터 필터링 완료<br/>다음 단계로 전달]
    
    %% 스타일링
    classDef startClass fill:#e8f5e8,stroke:#4caf50,stroke-width:2px
    classDef filterClass fill:#f3e5f5,stroke:#7b1fa2,stroke-width:3px
    classDef indexClass fill:#f3e5ab,stroke:#827717,stroke-width:2px
    classDef outputClass fill:#fff8e1,stroke:#ff8f00,stroke-width:2px
    classDef decisionClass fill:#e3f2fd,stroke:#1565c0,stroke-width:2px
    
    class START startClass;
    class ELEMENT_FILTER,ORIGIN_FILTER,PARA_FILTER,SUMMARY_FILTER,CAPTION_FILTER,INDEX_FILTER filterClass;
    class ELEMENT_IDX,CHUNK_IDX,MEDIA_IDX indexClass;
    class FILTERED_RESULTS,OUTPUT outputClass;
    class FILTER_CHECK decisionClass;
```

### 6. 하이브리드 검색 (BM25 + 벡터 유사도) 구현 파이프라인

하이브리드 검색 시스템은 전통적인 키워드 기반 검색(BM25)과 최신 벡터 유사도 검색을 결합하여 검색 정확도와 의미적 이해를 동시에 향상시킵니다. 이 시스템은 텍스트와 이미지 임베딩을 통합하여 멀티모달 검색을 지원하며, 동적 가중치 시스템을 통해 각 검색 방법의 기여도를 최적화합니다.

#### 주요 구성 요소:
- **BM25 텍스트 검색**: TF-IDF 기반 키워드 관련성 평가, 정확한 용어 매칭 보장
- **벡터 유사도 검색**: 텍스트 및 이미지 임베딩 모델을 활용한 의미적 유사도 계산
- **모달리티별 임베딩**: 텍스트(1152차원), 이미지(1152차원) 벡터 통합
- **동적 가중치 조절**: TEXT_STRENGTH와 VECTOR_BOOST를 통한 검색 균형 조정
- **Script Score 최적화**: OpenSearch 내장 함수를 활용한 고성능 벡터 연산

```mermaid
flowchart TD
    %% 시작점
    START[검색 쿼리 + 임베딩 입력] --> HYBRID_INIT[하이브리드 검색 초기화<br/>OpenSearchService]
    
    %% 검색 방법 분기
    HYBRID_INIT --> BM25_BRANCH[BM25 텍스트 검색 분기]
    HYBRID_INIT --> VECTOR_BRANCH[벡터 유사도 검색 분기]
    
    %% BM25 텍스트 검색 경로
    BM25_BRANCH --> TEXT_QUERY[텍스트 쿼리 처리<br/>multi_match + 이미지 캡션 태그 보강]
    TEXT_QUERY --> BM25_EXEC[BM25 알고리즘 실행<br/>TF-IDF 기반 관련성 계산]
    BM25_EXEC --> BM25_SCORE[BM25 점수 생성<br/>키워드 매칭 정확도]
    
    %% 벡터 검색 경로
    VECTOR_BRANCH --> EMBED_CHECK{임베딩 존재 확인}
    EMBED_CHECK -->|텍스트 임베딩| TEXT_VECTOR[텍스트 벡터 검색<br/>1152차원 텍스트 임베딩]
    EMBED_CHECK -->|이미지 임베딩| IMAGE_VECTOR[이미지 벡터 검색<br/>1152차원 이미지 임베딩]
    EMBED_CHECK -->|이미지 캡션 임베딩| CAPTION_VECTOR[캡션 벡터 검색<br/>텍스트로 매핑된 이미지 특징]
    
    %% 벡터 유사도 계산
    TEXT_VECTOR --> COSINE_SIM[Cosine 유사도 계산<br/>Script Score 함수 활용]
    IMAGE_VECTOR --> COSINE_SIM
    CAPTION_VECTOR --> COSINE_SIM
    
    %% Element Type 가중치 적용
    COSINE_SIM --> ELEMENT_WEIGHT[Element Type 가중치 적용<br/>동적 boost 계산]
    ELEMENT_WEIGHT --> VECTOR_SCORE[벡터 유사도 점수<br/>의미적 관련성 평가]
    
    %% 점수 통합
    BM25_SCORE --> SCORE_FUSION[하이브리드 점수 융합<br/>가중 평균 계산]
    VECTOR_SCORE --> SCORE_FUSION
    
    %% 가중치 시스템
    SCORE_FUSION --> WEIGHT_APPLY[가중치 시스템 적용]
    WEIGHT_APPLY --> TEXT_WEIGHT[텍스트 검색 가중치<br/>TEXT_STRENGTH × 0.5]
    WEIGHT_APPLY --> VECTOR_WEIGHT[벡터 검색 가중치<br/>VECTOR_BOOST_STRENGTH]
    
    %% 최종 점수 계산
    TEXT_WEIGHT --> FINAL_CALC[최종 하이브리드 점수<br/>BM25 × text_weight + Vector × vector_weight]
    VECTOR_WEIGHT --> FINAL_CALC
    
    %% 결과 정렬 및 출력
    FINAL_CALC --> RANKING[관련성 순 정렬<br/>하이브리드 점수 기준]
    RANKING --> OUTPUT[하이브리드 검색 결과<br/>키워드 + 의미적 정확도 보장]
    
    %% 외부 시스템 연동
    TEXT_VECTOR -.-> EMB_API[Embedding API<br/>텍스트 임베딩 모델]
    IMAGE_VECTOR -.-> EMB_API2[Embedding API<br/>이미지 임베딩 모델]
    COSINE_SIM -.-> OS_ENGINE[OpenSearch Engine<br/>Script Score 최적화]
    
    %% 스타일링
    classDef startClass fill:#e8f5e8,stroke:#4caf50,stroke-width:2px
    classDef branchClass fill:#e1f5fe,stroke:#01579b,stroke-width:2px
    classDef bm25Class fill:#fff3e0,stroke:#f57c00,stroke-width:3px
    classDef vectorClass fill:#f3e5f5,stroke:#7b1fa2,stroke-width:3px
    classDef fusionClass fill:#fce4ec,stroke:#c2185b,stroke-width:3px
    classDef weightClass fill:#f1f8e9,stroke:#689f38,stroke-width:2px
    classDef outputClass fill:#fff8e1,stroke:#ff8f00,stroke-width:2px
    classDef apiClass fill:#f3e5ab,stroke:#827717,stroke-width:2px
    classDef decisionClass fill:#e3f2fd,stroke:#1565c0,stroke-width:2px
    
    class START,HYBRID_INIT startClass;
    class BM25_BRANCH,VECTOR_BRANCH branchClass;
    class TEXT_QUERY,BM25_EXEC,BM25_SCORE bm25Class;
    class TEXT_VECTOR,IMAGE_VECTOR,CAPTION_VECTOR,COSINE_SIM,ELEMENT_WEIGHT,VECTOR_SCORE vectorClass;
    class SCORE_FUSION,FINAL_CALC fusionClass;
    class WEIGHT_APPLY,TEXT_WEIGHT,VECTOR_WEIGHT weightClass;
    class RANKING,OUTPUT outputClass;
    class EMB_API,EMB_API2,OS_ENGINE apiClass;
    class EMBED_CHECK decisionClass;
```

#### 단계별 세부 내용:

**1. 검색 초기화 단계**
- 입력된 텍스트 쿼리와 멀티모달 임베딩을 분석하여 하이브리드 검색 전략 수립
- 사용 가능한 임베딩 모달리티(텍스트, 이미지, 캡션) 확인 및 검색 분기 결정

**2. BM25 텍스트 검색**
- `multi_match` 쿼리를 통한 정확한 키워드 매칭 수행
- 이미지 캡션 태그를 텍스트 쿼리에 자동 통합하여 검색 범위 확장
- TF-IDF 알고리즘 기반 문서 관련성 점수 계산 및 정규화

**3. 벡터 유사도 검색**
- 외부 Embedding API를 통한 텍스트 및 이미지 1152차원 벡터 생성
- OpenSearch Script Score 함수를 통한 고성능 코사인 유사도 계산
- Element Type별 동적 가중치를 벡터 검색에 실시간 적용

**4. 하이브리드 점수 융합**
- BM25와 벡터 점수를 가중 평균으로 통합하여 균형잡힌 검색 결과 생성
- `TEXT_STRENGTH`와 `VECTOR_BOOST_STRENGTH` 설정을 통한 검색 방법별 기여도 조절
- 최종 하이브리드 점수 = (BM25 × 텍스트 가중치) + (벡터 × 벡터 가중치)

### 7. 동적 가중치 시스템을 통한 검색결과 재순위화 파이프라인

동적 가중치 시스템은 사용자 쿼리의 의도와 콘텐츠 특성을 분석하여 실시간으로 가중치를 조정하고 검색 결과를 재순위화합니다. 이 시스템은 Element Type별 중요도, 쿼리별 우선순위, 모달리티별 기여도를 종합적으로 고려하여 사용자에게 최적화된 검색 결과를 제공합니다.

```mermaid
flowchart TD
    %% 시작점
    START[검색 결과 입력<br/>multiple query results] --> RESULT_COLLECT[검색 결과 수집<br/>각 확장 쿼리별 결과]
    
    %% Element Type 가중치 적용
    RESULT_COLLECT --> ELEMENT_WEIGHT[Element Type 가중치 적용<br/>LLM 기반 동적 계산]
    ELEMENT_WEIGHT --> ORIGIN_WEIGHT[origin 가중치: 1.0<br/>원본 콘텐츠 최고 우선순위]
    ELEMENT_WEIGHT --> PARA_WEIGHT[paragraph 가중치: 0.8<br/>텍스트 단락 높은 중요도]
    ELEMENT_WEIGHT --> SUMMARY_WEIGHT[summary 가중치: 0.6<br/>AI 요약본 중간 중요도]
    ELEMENT_WEIGHT --> CAPTION_WEIGHT[caption 가중치: 0.3<br/>이미지 캡션 보조 정보]
    
    %% 쿼리별 가중치 적용
    ORIGIN_WEIGHT --> QUERY_WEIGHT[쿼리별 가중치 적용<br/>Query Decay System]
    PARA_WEIGHT --> QUERY_WEIGHT
    SUMMARY_WEIGHT --> QUERY_WEIGHT
    CAPTION_WEIGHT --> QUERY_WEIGHT
    
    QUERY_WEIGHT --> FIRST_QUERY[1st Query 가중치: 1.0<br/>주요 쿼리 최대 중요도]
    QUERY_WEIGHT --> SECOND_QUERY[2nd Query 가중치: 0.9<br/>부차 쿼리 높은 중요도]
    QUERY_WEIGHT --> THIRD_QUERY[3rd Query 가중치: 0.8<br/>보조 쿼리 중간 중요도]
    
    %% 점수 계산
    FIRST_QUERY --> SCORE_CALC[복합 점수 계산<br/>original_score × element_weight × query_weight]
    SECOND_QUERY --> SCORE_CALC
    THIRD_QUERY --> SCORE_CALC
    
    %% 결과 통합
    SCORE_CALC --> RESULT_MERGE[검색 결과 통합<br/>동일 문서 중복 제거]
    RESULT_MERGE --> DUPLICATE_CHECK{중복 문서 확인<br/>document_id 기준}
    DUPLICATE_CHECK -->|중복 발견| MAX_SCORE[최고 점수 유지<br/>higher score wins]
    DUPLICATE_CHECK -->|중복 없음| UNIQUE_KEEP[고유 결과 유지<br/>original score preserved]
    
    %% 최종 재순위화
    MAX_SCORE --> RERANK[동적 재순위화<br/>복합 점수 기준 정렬]
    UNIQUE_KEEP --> RERANK
    
    %% 품질 필터링
    RERANK --> QUALITY_FILTER[품질 필터링<br/>최소 점수 임계값 적용]
    QUALITY_FILTER --> THRESHOLD_CHECK{점수 임계값<br/>충족 확인}
    THRESHOLD_CHECK -->|통과| FINAL_RANK[최종 순위 결정<br/>관련성 순 내림차순 정렬]
    THRESHOLD_CHECK -->|미달| EXCLUDE[낮은 품질 결과 제외<br/>relevance threshold filtering]
    
    %% 최종 출력
    FINAL_RANK --> OUTPUT[재순위화된 검색 결과<br/>사용자 의도 최적화]
    EXCLUDE --> OUTPUT
    
    %% 가중치 설정 시스템
    ELEMENT_WEIGHT -.-> WEIGHT_CONFIG[WeightingConfig<br/>QUERY_DECAY: 0.1<br/>DEFAULT_WEIGHTS 설정]
    QUERY_WEIGHT -.-> QUERY_DECAY[Query Decay 공식<br/>weight = 1.0 - query_index × QUERY_DECAY]
    
    %% LLM 의도 분석
    ELEMENT_WEIGHT -.-> LLM_INTENT[🤖 LLM 의도 분석<br/>쿼리 특성별 가중치 동적 조정]
    
    %% 스타일링
    classDef startClass fill:#e8f5e8,stroke:#4caf50,stroke-width:2px
    classDef weightClass fill:#f3e5f5,stroke:#7b1fa2,stroke-width:3px
    classDef calcClass fill:#fff3e0,stroke:#f57c00,stroke-width:3px
    classDef mergeClass fill:#e1f5fe,stroke:#01579b,stroke-width:2px
    classDef rerankClass fill:#fce4ec,stroke:#c2185b,stroke-width:3px
    classDef outputClass fill:#fff8e1,stroke:#ff8f00,stroke-width:2px
    classDef configClass fill:#f1f8e9,stroke:#689f38,stroke-width:2px
    classDef llmClass fill:#e3f2fd,stroke:#1565c0,stroke-width:3px
    classDef decisionClass fill:#f3e5ab,stroke:#827717,stroke-width:2px
    
    class START,RESULT_COLLECT startClass;
    class ELEMENT_WEIGHT,ORIGIN_WEIGHT,PARA_WEIGHT,SUMMARY_WEIGHT,CAPTION_WEIGHT,QUERY_WEIGHT,FIRST_QUERY,SECOND_QUERY,THIRD_QUERY weightClass;
    class SCORE_CALC calcClass;
    class RESULT_MERGE,MAX_SCORE,UNIQUE_KEEP mergeClass;
    class RERANK,QUALITY_FILTER,FINAL_RANK rerankClass;
    class OUTPUT outputClass;
    class WEIGHT_CONFIG,QUERY_DECAY configClass;
    class LLM_INTENT llmClass;
    class DUPLICATE_CHECK,THRESHOLD_CHECK decisionClass;
    class EXCLUDE decisionClass;
```

#### 단계별 세부 내용:

**1. Element Type 가중치 시스템**
- **LLM 기반 동적 계산**: 사용자 쿼리 의도를 분석하여 콘텐츠 유형별 중요도 실시간 조정
- **계층적 가중치 구조**: origin(1.0) → paragraph(0.8) → summary(0.6) → caption(0.3) 순차적 중요도 적용
- **의도 맞춤 조정**: 원본 자료 검색 시 origin 강화, 요약 정보 검색 시 summary 강화

**LLM 기반 쿼리 의도 분석**
- **의미적 분석**: 쿼리의 핵심 키워드와 문맥을 분석하여 사용자가 찾고자 하는 콘텐츠 유형 예측
- **의도 분류**: 정보 탐색(information seeking), 자료 확인(fact checking), 요약 요청(summarization), 시각 자료(visual content) 등으로 구분
- **자동 가중치 조절**: 분석된 의도에 따라 element_type별 가중치를 자동으로 재계산하여 검색 정확도 향상
- **예시**: "상세한 내용을 알려줘" → paragraph 가중치 증가, "요약해줘" → summary 가중치 증가, "원본 문서 보여줘" → origin 가중치 증가

**Element Type별 자동 가중치 조절 메커니즘**
- **실시간 프롬프트 엔지니어링**: 쿼리 텍스트를 LLM에 전달하여 의도 분석 결과를 JSON 형태로 수신
- **가중치 매핑 테이블**: 분석된 의도를 기반으로 각 element_type의 boost 값을 0.1~2.0 범위 내에서 자동 계산
- **폴백 메커니즘**: LLM 분석 실패 시 휴리스틱 기반 기본 가중치(origin:1.0, paragraph:0.8, summary:0.6, caption:0.3) 적용
- **가중치 정규화**: 계산된 가중치들을 정규화하여 검색 결과의 일관성 보장
- **캐싱 최적화**: 동일한 쿼리 패턴에 대한 의도 분석 결과를 캐싱하여 응답 속도 개선

**2. Query Decay System**
- **순차적 가중치 감소**: 1st(1.0) → 2nd(0.9) → 3rd(0.8)로 쿼리 순서별 중요도 차등 적용
- **QUERY_DECAY 설정**: 기본값 0.1로 각 쿼리 간 10% 가중치 감소 적용
- **확장 쿼리 우선순위**: 주요 쿼리를 최우선으로 하여 검색 정확도 보장

**3. 복합 점수 계산**
- **다차원 가중치 융합**: original_score × element_weight × query_weight 공식 적용
- **정규화 처리**: 서로 다른 검색 알고리즘(BM25, 벡터) 점수의 일관성 있는 통합
- **동적 boost 적용**: 실시간 쿼리 분석 결과에 따른 추가 가중치 부여

**4. 중복 제거 및 결과 통합**
- **document_id 기준 중복 검출**: 동일 문서가 여러 쿼리에서 검색된 경우 식별
- **최고 점수 보존**: 중복 문서 중 가장 높은 복합 점수를 가진 결과만 유지
- **고유 결과 보존**: 중복되지 않은 결과는 원본 점수와 메타데이터 모두 보존

**5. 품질 기반 최종 재순위화**
- **관련성 임계값 필터링**: 최소 품질 기준 미달 결과 자동 제외
- **사용자 의도 최적화**: 쿼리 분석 결과를 반영한 개인화된 순위 조정
- **일관성 있는 정렬**: 복합 점수 기준 내림차순으로 최종 검색 결과 제공

### 8. 다단계 검색 실행 최적화: 순차/병렬 처리 파이프라인

다단계 검색 실행 시스템은 LLM이 분석한 쿼리 간 의존성을 기반으로 최적의 실행 전략을 자동 선택합니다. 독립적인 쿼리들은 병렬 처리로 성능을 최대화하고, 의존적인 쿼리들은 순차 처리로 컨텍스트 전파를 통한 정확도를 향상시킵니다.

```mermaid
flowchart TD
    %% 시작점
    START[확장된 검색 쿼리<br/>Query 1, Query 2, Query 3] --> DEP_CHECK{🤖 의존성 판단<br/>has_dependency?}
    
    %% 병렬 처리 경로
    DEP_CHECK -->|독립적| PARALLEL[병렬 검색 실행<br/>동시 처리로 성능 최적화]
    PARALLEL --> PAR_RESULT[병렬 결과 통합<br/>빠른 응답 시간]
    
    %% 순차 처리 경로
    DEP_CHECK -->|의존적| SEQUENTIAL[순차 검색 실행<br/>컨텍스트 전파로 정확도 향상]
    SEQUENTIAL --> SEQ_RESULT[순차 결과 통합<br/>높은 검색 정확도]
    
    %% 최종 결과
    PAR_RESULT --> OUTPUT[최적화된 검색 결과]
    SEQ_RESULT --> OUTPUT
    
    %% 외부 시스템
    PARALLEL -.-> OPENSEARCH[OpenSearch<br/>하이브리드 검색]
    SEQUENTIAL -.-> OPENSEARCH
    SEQUENTIAL -.-> NLP_ENGINE[🤖 NLP 엔진<br/>컨텍스트 추출]
    
    %% 스타일링
    classDef startClass fill:#e8f5e8,stroke:#4caf50,stroke-width:2px
    classDef decisionClass fill:#e3f2fd,stroke:#1565c0,stroke-width:2px
    classDef parallelClass fill:#e1f5fe,stroke:#01579b,stroke-width:3px
    classDef sequentialClass fill:#f3e5f5,stroke:#7b1fa2,stroke-width:3px
    classDef outputClass fill:#fce4ec,stroke:#c2185b,stroke-width:2px
    classDef apiClass fill:#fff8e1,stroke:#ff8f00,stroke-width:2px
    
    class START startClass
    class DEP_CHECK decisionClass
    class PARALLEL,PAR_RESULT parallelClass
    class SEQUENTIAL,SEQ_RESULT sequentialClass
    class OUTPUT outputClass
    class OPENSEARCH,NLP_ENGINE apiClass
```

#### 처리 방식별 상세 분석:

**병렬 처리 (Independent Parallel Processing)**
- **적용 조건**: 쿼리 간 의존성이 없는 경우 (has_dependency = false)
- **실행 방식**: asyncio.gather()를 통한 동시 비동기 처리
- **성능 이점**: 
  - 응답 시간 단축 (순차 대비 최대 60-70% 단축)
  - CPU/메모리 자원의 효율적 활용
  - 높은 처리량으로 동시 다중 검색 지원
- **최적 시나리오**: "파이썬 기초", "데이터 분석", "머신러닝" 등 독립적 주제 검색

**순차 처리 (Context-aware Sequential Processing)**
- **적용 조건**: 쿼리 간 의존성이 있는 경우 (has_dependency = true)  
- **실행 방식**: 이전 결과 → 컨텍스트 추출 → 다음 쿼리 보강 → 실행
- **정확도 이점**:
  - 컨텍스트 전파를 통한 검색 정확도 15-20% 향상
  - 의미적 연관성 강화로 관련성 높은 결과 우선 제공
  - 점진적 정보 축적을 통한 포괄적 검색 결과
- **최적 시나리오**: "최신 라이브러리" → "설치 방법" → "사용 예제" 등 단계적 정보 탐색

**컨텍스트 전파 메커니즘**
- **키워드 추출**: 이전 검색 결과에서 핵심 키워드 자동 식별
- **엔티티 인식**: 인명, 기술명, 제품명 등 중요 엔티티 추출 및 활용
- **의미적 확장**: 관련 개념과 동의어를 다음 쿼리에 자동 포함
- **가중치 조정**: 컨텍스트 정보의 중요도에 따른 동적 boost 적용

### 9. LLM 답변 생성 파이프라인

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
├── main.py                    # FastAPI 애플리케이션 진입점
├── config.py                  # 전역 설정 관리
├── version.py                 # 버전 및 빌드 정보
├── dependencies.py            # DI 컨테이너 및 의존성 등록
├── constants.py               # 전역 상수 정의
├── handlers.py                # 요청/응답 핸들러 함수
│
├── exceptions/                # 중앙집중식 예외 처리 시스템
│   ├── __init__.py           # 예외 모듈 초기화
│   ├── base.py               # 기본 예외 클래스 정의
│   ├── service.py            # 도메인별 비즈니스 예외
│   └── handlers.py           # 글로벌 예외 핸들러 + 미들웨어
│
├── schemas/                   # 표준화된 API 스키마 모델
│   ├── __init__.py           # 스키마 모듈 초기화
│   ├── common.py             # 공통 응답 모델 (ApiResponse[T])
│   ├── search.py             # 검색 관련 스키마
│   ├── generation.py         # 답변 생성 스키마
│   ├── features.py           # 특징 추출 스키마
│   └── requests.py           # 공통 요청 스키마
│
├── utils/                     # 도메인 별 유틸리티 함수
│   ├── __init__.py           # 유틸리티 모듈 초기화
│   ├── logging.py            # 스마트 로깅 시스템
│   ├── validation.py         # 입력 검증 + XSS 방지
│   ├── authentication.py     # 보안 + API 키 관리
│   ├── opensearch.py         # OpenSearch 전용 유틸리티
│   ├── serialization.py      # 데이터 직렬화 처리
│   ├── index_mappings.py     # OpenSearch 인덱스 매핑
│   └── common.py             # 공통 유틸리티 함수
│
├── src/                       # 도메인 기반 비즈니스 로직
│   ├── search/               # 검색 도메인 서비스
│   │   ├── __init__.py       # 검색 서비스 통합 인터페이스
│   │   ├── opensearch.py     # OpenSearch 핵심 엔진
│   │   ├── services.py       # 검색 서비스 통합 (SearchService)
│   │   ├── executor.py       # 검색 실행 엔진 (SearchExecutor)
│   │   ├── enricher.py       # 결과 강화 서비스 (ResultEnricher)
│   │   └── analyzers.py      # 쿼리 분석 + 확장 (QueryAnalyzer)
│   ├── generation/           # AI 답변 생성 도메인
│   │   ├── __init__.py       # 생성 서비스 인터페이스
│   │   ├── services.py       # 답변 생성 엔진 (AnswerGenerationService)
│   │   └── streaming.py      # 스트리밍 서비스 (MultimodalStreamService)
│   ├── processing/           # 데이터 처리 도메인
│   │   ├── __init__.py       # 처리 서비스 인터페이스
│   │   ├── input.py          # 입력 처리기 (InputProcessor)
│   │   ├── files.py          # 파일 전처리 서비스 (FilePreprocessingService)
│   │   └── features.py       # 멀티모달 특징 추출 (MultimodalFeatureExtractor)
│   └── embeddings/           # 임베딩 도메인
│       ├── __init__.py       # 임베딩 서비스 인터페이스
│       └── services.py       # 임베딩 생성 엔진 (EmbeddingService)
│
├── interfaces/                # 의존성 주입 + 프로토콜 정의
│   ├── __init__.py           # 인터페이스 모듈 초기화
│   ├── protocols.py          # 서비스 프로토콜 정의
│   ├── container.py          # 의존성 컨테이너
│   └── injector.py           # 의존성 주입 관리
│
├── prompts/                   # LLM 프롬프트 관리 시스템
│   ├── __init__.py           # 프롬프트 모듈 초기화
│   ├── manager.py            # Langfuse 통합 프롬프트 관리자
│   └── templates.py          # 프롬프트 템플릿 정의
│
├── handlers/                  # 요청/응답 처리 핸들러
│   ├── __init__.py           # 핸들러 모듈 초기화
│   ├── cors.py               # CORS 설정
│   ├── middleware.py         # 미들웨어 설정
│   └── common.py             # 공통 핸들러 함수
│
├── clients/                   # 외부 API 클라이언트 (보안 강화)
│   ├── __init__.py           # 클라이언트 모듈 초기화
│   ├── llm_client.py         # LLM 서비스 클라이언트
│   ├── embedding_client.py   # 임베딩 API 클라이언트
│   └── feature_extraction_client.py  # 특징 추출 API 클라이언트
│
└── api/                       # API 엔드포인트 정의
    ├── __init__.py           # API 모듈 초기화
    ├── search.py             # 검색 엔드포인트
    ├── generation.py         # 답변 생성 엔드포인트
    └── config.py             # 설정 엔드포인트
│
```

### 아키텍처 개선 사항

**도메인 기반 구조 (Domain-Driven Design)**
- 비즈니스 로직이 도메인별로 명확히 분리되어 유지보수성 향상
- `src/` 디렉토리 하위에 search, generation, processing, embeddings 도메인 구성
- 각 도메인은 독립적으로 개발 및 테스트 가능한 모듈 구조

**의존성 주입 패턴 (Dependency Injection)**
- `interfaces/` 디렉토리를 통한 프로토콜 기반 의존성 정의
- 느슨한 결합으로 테스트 용이성과 확장성 확보
- 런타임 시 구현체 자동 주입으로 코드 간소화

**중앙집중식 예외 처리 (Centralized Error Handling)**
- `exceptions/` 디렉토리의 계층적 예외 시스템
- Circuit Breaker 패턴으로 외부 API 장애 대응
- 글로벌 예외 핸들러를 통한 일관된 오류 응답

**표준화된 API 응답 (Standardized Response Models)**
- `schemas/common.py`의 `ApiResponse[T]` 제네릭 래퍼
- 모든 API가 동일한 구조로 메타데이터와 데이터 반환
- 클라이언트 개발 시 일관된 인터페이스 제공

**모던한 개발 경험 (Modern Development Experience)**
- 깔끔하고 직관적인 임포트 경로: `from app.src.search import SearchService`
- 타입 힌트와 프로토콜 기반 인터페이스로 IDE 지원 향상
- 도메인별 명확한 책임 분리로 개발 생산성 증대

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
LITELLM_TIMEOUT=180.0

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

### 지능형 검색
- **적응형 쿼리 확장**: 쿼리 특성에 따른 선택적 기법 적용 (분해, 재작성, 의미 확장)
- **지능형 의존성 판단**: LLM이 쿼리 간 의존성을 자동 분석하여 실행 방식 결정
- **하이브리드 검색**: BM25 텍스트 검색 + 벡터 유사도 검색 결합
- **적응형 실행**: 독립적 쿼리는 병렬, 의존적 쿼리는 순차 처리
- **컨텍스트 보강**: 이전 검색 결과를 활용한 다음 쿼리 정확도 향상
- **폴백 메커니즘**: LLM 실패 시 원본 쿼리로 안정적 서비스 지속

### 시스템 안정성
- **Circuit Breaker**: 외부 API 장애 시 서비스 보호 및 빠른 복구
- **자동 재시도**: 지수 백오프를 통한 일시적 오류 극복
- **보안 강화**: API 키 마스킹 및 민감 정보 보호
- **글로벌 예외 처리**: 통합된 오류 처리 및 구조화된 응답

### 성능 최적화
- **병렬 처리**: 임베딩 생성 및 메타데이터 조회 동시 실행
- **스마트 로깅**: 86% 볼륨 감소 및 Base64 데이터 마스킹
- **검색 로직 간소화**: 불필요한 리랭킹 과정 제거
- **실시간 모니터링**: 외부 API 상태 및 응답 시간 추적

### 현대적 아키텍처
- **도메인 기반 설계**: 검색, 생성, 처리, 임베딩 도메인별 명확한 분리
- **의존성 주입**: 프로토콜 기반 인터페이스로 테스트 용이성 확보
- **표준화된 API**: `ApiResponse[T]` 제네릭 래퍼로 일관된 응답 구조
- **중앙집중식 예외 처리**: 도메인별 예외와 글로벌 핸들러로 체계적 오류 관리
- **타입 안전성**: 프로토콜과 타입 힌트로 IDE 지원 및 개발 생산성 향상

## 라이선스 및 기여

이 프로젝트는 멀티모달 검색 기술의 연구 및 개발 목적으로 작성되었습니다.
