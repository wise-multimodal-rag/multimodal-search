# multimodal-search

## 프로젝트 개요

Opensearch를 사용한 멀티모달 검색 및 멀티모달 RAG 시스템 구축

![Multimodal RAG Multi Index Workflow.png](Multimodal%20RAG%20Multi%20Index%20Workflow.png)

## 주요 기능 요구사항

### Embedding 및 Feature Extraction은 API를 통해서 진행한다.

API 명세는 아래와 같다.

- Text Feature Extraction

1. API 기본정보

Endpoint : ${ip:port}/extraction/text/summarization

Http method : POST

Description : 텍스트에서 핵심 내용을 요약하여 추출

2. 요청 파라미터

Request Body

Required: text(string)

Optional: summary_type(string: "extractive"|"abstractive", default: "abstractive"),
max_length(integer, default : 200)
language(string, default: "ko")

3. 응답 형태

// 성공 시 (200)
{
"status": "success",
"data": {
"summary": "AI 기술 발전으로 인한 업무 자동화가 가속화되고 있으며, 기업들은 효율성 증대와 비용 절감 효과를 얻고 있다."
}
}

// 실패 시 (400/500)
{
"status": "error",
"message": "텍스트가 너무 짧아 요약할 수 없습니다.",
"error_code": "TEXT_TOO_SHORT"
}

1. API 기본정보

Endpoint : ${ip:port}/extraction/text/keyword

Http method : POST

Description : 텍스트에서 핵심 키워드 추출

2. 요청 파라미터

Request Body

Required: text(string)

Optional: max_keywords(int, default: 10),
min_score(float, default: 0.3),
include_phrases(boolean, default: false)

3. 응답 형태

// 성공 시 (200)
{
"status": "success",
"data": {
"keywords": [
{"word": "머신러닝", "score": 0.78},
{"word": "알고리즘", "score": 0.72},
{"word": "데이터", "score": 0.69},
{"word": "모델", "score": 0.64},
{"word": "학습", "score": 0.62}
],
"ngram_range"= 1
}
}

// ngram = (1,2) (200)
{
"status": "success",
"data": {
"keywords": [
{"word": "딥러닝 모델", "score": 0.8234},
{"word": "자연어 처리", "score": 0.7891},
{"word": "머신러닝", "score": 0.7834},
{"word": "인공지능 기술", "score": 0.7456},
{"word": "신경망 구조", "score": 0.7123},
{"word": "데이터", "score": 0.6892}
],
"ngram_range"= 2
}
}

// 텍스트 너무 짧음
{
"status": "error",
"message": "텍스트가 너무 짧습니다.",
"error_code": "TEXT_TOO_SHORT"
}

// 키워드 추출 실패
{
"status": "error",
"message": "키워드를 추출할 수 없습니다.",
"error_code": "NO_KEYWORDS_FOUND"
}

// 파라미터 오류
{
"status": "error",
"message": "잘못된 파라미터입니다.",
"error_code": "INVALID_PARAMETER"
}

1. API 기본정보

Endpoint : ${ip:port}/extraction/text/classify

Http method : POST

Description  : 텍스트의 문서 유형을 분류( 계약서, 보고서, 이메일 등)

2. 요청 파라미터

Request Body

Required: text(string)

Optional: top_k(number, default: 3)

3. 응답 형태

// 성공 시 (200)
{
"status": "success",
"data": {
"predictions": [
{"category": "contract", "confidence": 0.89},
{"category": "report", "confidence": 0.08},
{"category": "email", "confidence": 0.03}
]
}
}

// 분류 실패
{
"status": "error",
"message": "문서 유형을 분류할 수 없습니다.",
"error_code": "CLASSIFICATION_FAILED"
}

1. API 기본정보

Endpoint : ${ip:port}/extraction/text/entities

Http method : POST

Description : 텍스트에서 사람명, 회사명, 지명 등 개체명을 추출

2. 요청 파라미터

Request Body

Required: text(string)

Optional: entity_types(array; ["PERSON", "ORG", "LOC", "MISC"])
min_confidence(float, default:0.7)

3. 응답 형태

// 성공 시 (200)
{
"status": "success",
"data": {
"entities": [
{
"text": "삼성전자",
"label": "ORG",
"confidence": 0.95,
"start": 15,
"end": 19,
"context": "...에서 삼성전자가 발표한..."
},
{
"text": "김철수",
"label": "PERSON",
"confidence": 0.88,
"start": 30,
"end": 33,
"context": "...대표 김철수는 말했다..."
}
],
"entity_count": 2,
"model": "kobert-ner"
}
}

// 실패 시 - 개체명 없음
{
"status": "error",
"message": "개체명을 찾을 수 없습니다.",
"error_code": "NO_ENTITIES_FOUND"
}

1. API 기본정보

Endpoint : ${ip:port}/extraction/text/sentiment

Http method : POST

Description : 텍스트의 감정을 분석하여 긍정/부정/중립으로 분류

2. 요청 파라미터

Request Body

Required: text(string)

Optional: detail_level(string; "simple"|"detailed", default: "simple")

3. 응답 형태

// 성공 시 (200) - simple
{
"status": "success",
"data": {
"sentiment": "positive",
"confidence": 0.87
}
}

// 감정 분석 실패
{
"status": "error",
"message": "감정을 분석할 수 없습니다.",
"error_code": "SENTIMENT_ANALYSIS_FAILED"
}

// 텍스트 부족
{
"status": "error",
"message": "텍스트가 너무 짧습니다.",
"error_code": "TEXT_TOO_SHORT"
}

- Image Caption

1. API 기본정보

Endpoint : ${ip:port}/extraction/image/caption

Http method : POST

Description : 이미지를 분석하여 상세한 자연어 설명을 생성

2. 요청 파라미터

Request Body

Required: image(binary; multipart/form-data)

Optional: detail_level(string; "brief"|"detailed", default: "detailed"),
language(string, default: "ko"),
focus(string; "general"|"objects"|"scene"|"people")

3. 응답 형태

// 성공 시 (200)
{
"status": "success",
"data": {
"caption": "밝은 햇살이 비치는 공원에서 골든 리트리버가 나무 벤치에 앉아 카메라를 바라보고 있다. 주변에는 푸른 나무들과 잔디밭이 펼쳐져 있어 평화로운 분위기를 자아낸다.",
"confidence": 0.87
}
}

// 실패 시 (400/500)
{
"status": "error",
"message": "지원되지 않는 이미지 형식입니다.",
"error_code": "UNSUPPORTED_FORMAT"
}

// 성공 시 - 전체 옵션 포함 (200)
{
"status": "success",
"data": {
"caption": "밝은 햇살이 비치는 공원에서 골든 리트리버가 나무 벤치에 앉아 카메라를 바라보고 있다. 주변에는 푸른 나무들과 잔디밭이 펼쳐져 있어 평화로운 분위기를 자아낸다.",
"confidence": 0.87,
"objects": [
{"name": "골든 리트리버", "confidence": 0.94},
{"name": "나무 벤치", "confidence": 0.89},
{"name": "나무", "confidence": 0.92},
{"name": "잔디밭", "confidence": 0.85}
],
"scene_type": "outdoor_park",
"language": "ko",
"processing_time": 1250.5
}
}

// 실패 시 (400/500)
{
"status": "error",
"message": "이미지 처리 중 오류가 발생했습니다.",
"error_code": "PROCESSING_ERROR"
}

- Image Object Detection

1. API 기본 정보

엔드포인트 URL: ${ip:port}/analysis/image/detection

HTTP 메소드: POST

간단한 용도 설명 (한 줄): 이미지에서 객체를 탐지

2. 요청 파라미터

Request Body

필수: image(binary; multipart/form-data)

3. 응답 형태

// 성공 시 (200)
{
"status": "success",
"data": {
"source_info": {
"width": 1920,
"height": 1080
},
"objects": [
{
"id": "obj_001",
"label": {
"id": 0,
"name": "person"
},
"confidence": 0.9543,
"bbox": {
"format": "xywh",
"x": 123.4,
"y": 567.8,
"width": 234.5,
"height": 345.6
}
}
]
}
}

// 실패 시 (400/500)
{
"status": "error",
"message": "지원하지 않는 이미지 형식입니다"
}

1. API 기본 정보

엔드포인트 URL: ${ip:port}/analysis/image/captioning

HTTP 메소드: POST

간단한 용도 설명 (한 줄): 이미지를 분석하여 자연어 캡션이나 설명을 생성

2. 요청 파라미터

Request Body

필수: image_file(string$binary; multipart/form-data)

3. 응답 형태

// 성공 시 (200)
{
"status": "success",
"data": {
"caption": "골든 리트리버가 나무로 만든 공원 벤치에 조용히 앉아 있습니다. 배경에는 푸른 나뭇잎과 자연스러운 공원 풍경이 보입니다.",
"confidence": 0.8734,
"tags": ["개", "벤치", "공원", "동물", "야외"]
}
}

// 실패 시 (400/500)
{
"status": "error",
"message": "이미지 처리 중 오류가 발생했습니다"
}

- Text Embedding

1. API 기본 정보

엔드포인트 URL: ${ip:port}/embedding/text

HTTP 메소드: POST

간단한 용도 설명 (한 줄): 텍스트를 벡터로 임베딩하는 데 사용

2. 요청 파라미터

Request Body

필수: text(string)

3. 응답 형태

// 성공 시 (200)
{
"status": "success",
"data": {
"embedding": [0.2345, -0.6789, 0.1234, ...],
"dimension": 384,
"model": "sentence-transformer-multilingual"
}
}
// 실패 시 (400/500)
{
"status": "error",
"message": "텍스트가 비어있습니다"
}

- Image Embedding

1. API 기본 정보

엔드포인트 URL: ${ip:port}/embedding/image

HTTP 메소드: POST

간단한 용도 설명 (한 줄): 이미지를 업로드해 벡터로 임베딩하는 데 사용

2. 요청 파라미터

Request Body

필수: image(binary; multipart/form-data)

3. 응답 형태

// 성공 시 (200)
{
"status": "success",
"data": {
"embedding": [0.1234, -0.5678, 0.9012, ...],
"dimension": 512,
"model": "vision-transformer-base"
}
}
// 실패 시 (400/500)
{
"status": "error",
"message": "이미지 파일이 필요합니다"
}

1. API 기본 정보

엔드포인트 URL: ${ip:port}/embedding/image/storage

HTTP 메소드: POST

간단한 용도 설명 (한 줄): 스토리지에 저장된 이미지를 벡터로 임베딩하는 데 사용

2. 요청 파라미터

Request Body

필수: storage_path(string)

3. 응답 형태

// 성공 시 (200)
{
"status": "success",
"data": {
"embedding": [0.1234, -0.5678, 0.9012, ...],
"dimension": 512,
"model": "vision-transformer-base"
}
}
// 실패 시 (400/500)
{
"status": "error",
"message": "스토리지 경로에서 이미지를 찾을 수 없습니다"
}

- Document AI Workflow

API 기본정보

Endpoint : ${ip:port}/parsing/document/ocr

Http method : POST

Description : 문서 이미지에서 텍스트를 추출

요청 파라미터

Request Body

Required: document(binary; multipart/form-data)
Optional: language(string, default: "ko"),
detect_layout(boolean, default: true),
output_format(string; "text"|"structured", default: "structured")

응답 형태

// 성공 시 (200)
{
"status": "success",
"data": {
"extracted_text": "문서에서 추출된 전체 텍스트...",
"text_blocks": [
{
"text": "제목: 계약서",
"bbox": [[100, 50], [300, 50], [300, 80], [100, 80]], // PaddleOCR 4점 좌표
"confidence": 0.95
}
],
"ocr_engine": "paddleocr",
"language": "ko",
"confidence": 0.92,
"processing_time_ms": 2340
}
}

// 실패 시 (400/500)
{
"status": "error",
"message": "OCR 처리할 수 없는 이미지 형식입니다",
"error_code": "UNSUPPORTED_IMAGE_FORMAT"
}

API 기본정보

Endpoint : ${ip:port}/parsing/document/layout

Http method : POST

Description : 문서의 레이아웃 구조를 분석 (제목, 본문, 표, 이미지 영역 구분)

요청 파라미터

Request Body

Required: document(binary; multipart/form-data)
Optional: extract_images(boolean, default: true),
extract_tables(boolean, default: true),
confidence_threshold(float, default: 0.7)

응답 형태

// 성공 시 (200)
{
"status": "success",
"data": {
"layout_elements": [
{
"type": "title",
"bbox": {"x": 100, "y": 50, "width": 400, "height": 50},
"confidence": 0.95,
"text": "월간 매출 보고서"
},
{
"type": "table",
"bbox": {"x": 50, "y": 200, "width": 500, "height": 300},
"confidence": 0.89,
"table_id": "table_001"
},
{
"type": "image",
"bbox": {"x": 300, "y": 600, "width": 200, "height": 150},
"confidence": 0.92,
"image_id": "img_001"
}
],
"extracted_images": ["img_001"],
"extracted_tables": ["table_001"],
"total_elements": 3
}
}

// 실패 시 (400/500)
{
"status": "error",
"message": "문서 레이아웃을 분석할 수 없습니다",
"error_code": "LAYOUT_ANALYSIS_FAILED"
}

API 기본정보

Endpoint : ${ip:port}/parsing/document/extract

Http method : POST

Description : 문서에서 표와 이미지를 추출하여 별도 파일로 저장 추출

요청 파라미터

Request Body

Required: document(binary; multipart/form-data)
Optional: extract_type(array; ["table", "image"], default: ["table", "image"]),
table_format(string; "csv"|"json", default: "csv"),
image_format(string; "png"|"jpg", default: "png")

응답 형태

// 성공 시 (200)
{
"status": "success",
"data": {
"extracted_tables": [
{
"table_id": "table_001",
"file_path": "/storage/tables/table_001.csv",
"rows": 15,
"columns": 4,
"confidence": 0.88
}
],
"extracted_images": [
{
"image_id": "img_001",
"file_path": "/storage/images/img_001.png",
"width": 800,
"height": 600,
"confidence": 0.92
}
],
"total_extractions": 2
}
}

// 실패 시 (400/500)
{
"status": "error",
"message": "추출할 표나 이미지를 찾을 수 없습니다",
"error_code": "NO_EXTRACTABLE_CONTENT"
}

### 인풋은 텍스트, 이미지, 오디오, 비디오 모두 가능하고, 동시에 들어올 수 있다.

예시: input = 텍스트, 이미지, 비디오 | 텍스트, 비디오 | 텍스트, 이미지, ...

### Opensearch Index는 media_meta, chunk_meta, elements로 총 3개로 구성되어있다.

3.1. Media Meta 인덱스

설계 목적
미디어 파일의 기본 정보와 기술적 메타데이터를 저장하여 필터링 및 집계 기능을 제공합니다.

3.1.1. 스키마

{
"settings": {
"index": { "number_of_shards": 1, "number_of_replicas": 1 }
},
"mappings": {
"dynamic": "false",
"properties": {
// === 식별자/기본 ===
"media_id":     { "type": "keyword" }, // PK
"media_type": { "type": "keyword" }, // 비즈니스 도메인 분류 video|audio|image|document|web|other
"mime_type": { "type": "keyword" }, // 기술적 파일 타입 video/mp4, application/pdf, image/jpeg 등
"title":        { "type": "text", "analyzer": "ko_en" }, // 표시/검색 보조(필요시)
"source_uri":   { "type": "keyword" }, // 원본 접근 경로

      // === 핵심 검색/필터 속성 (자주 사용되는 것만) ===
      "file_size_bytes": { "type": "long" },           // 모든 미디어
      "duration_seconds": { "type": "float" },          // video/audio 검색
      "width_pixels": { "type": "integer" },            // image/video 필터
      "height_pixels": { "type": "integer" },           // image/video 필터  
      "language_primary": { "type": "keyword" },        // 언어 필터
      
      // === 집계/현황 요약 ===
      "chunk_count": { "type": "integer" },
      "element_count": { "type": "integer" },
      
      // === 확장 가능한 세부 메타데이터 ===
      "metadata_flat": { 
        "type": "flattened"
        // 여기에 들어갈 수 있는 것들:
        // - checksum_md5, checksum_sha256
        // - bitrate_kbps, frame_rate, codec
        // - color_depth, dpi, exif_data  
        // - page_count, word_count, author
        // - sample_rate_hz, audio_channels
      },
      

      // === 운영 ===
      "owner": { "type": "keyword" },
      "visibility": { "type": "keyword" },          // public|internal|restricted
      "tags":        { "type": "keyword" },     // [Optional] 접근제어/도메인/민감도 라벨 등
      "created_at":  { "type": "date" },
      "updated_at":  { "type": "date" }
    }

}
}

{
"media_id": "vid_001",
"media_type": "video",
"duration_seconds": 1800.5,
"width_pixels": 1920,
"height_pixels": 1080,
"language_primary": "ko",
"file_size_bytes": 524288000,
"metadata_flat": {
"bitrate_kbps": 5000,
"frame_rate": 29.97,
"codec": "h264",
"audio_codec": "aac",
"sample_rate_hz": 48000,
"audio_channels": 2,
"creation_date": "2024-01-15T10:30:00Z",
"camera_model": "Sony FX3"
}
}

3.1.2. 주요 필드 구성

식별자 및 분류

media_id: 기본키

media_type: 비즈니스 도메인 분류 (video|audio|image|document|web|other)

mime_type: 기술적 파일 타입 (video/mp4, application/pdf 등)

검색 및 필터링 속성
자주 사용되는 검색 조건만 개별 필드로 구성:

file_size_bytes: 파일 크기 기반 필터링

duration_seconds: 비디오/오디오 길이 필터

width_pixels, height_pixels: 이미지/비디오 해상도 필터

language_primary: 언어별 필터링

확장 가능한 메타데이터

metadata_flat: flattened 타입으로 다양한 기술적 메타데이터 저장

체크섬, 비트레이트, 프레임레이트, 코덱 정보

EXIF 데이터, 샘플레이트, 오디오 채널 등

확장성을 위해 구조화되지 않은 데이터도 유연하게 저장 가능

3.2. Chunk Meta 인덱스

설계 목적
미디어 내의 의미 단위 청크에 대한 구조적 정보를 제공하여 계층적 탐색을 지원합니다.

3.2.1. 스키마

{
"settings": {
"index": { "number_of_shards": 2, "number_of_replicas": 1 }
},
"mappings": {
"dynamic": "false",
"properties": {
// === 식별자 ===
"chunk_id":   { "type": "keyword" }, // PK
"media_id":   { "type": "keyword" }, // 부모 Media (routing key로 권장)

      // === 구조/유형 ===
      "chunk_seq":  { "type": "integer" },      // Media 내 순서(0..N). 0은 개요(overview) 등으로 규약 가능
      "chunk_type": { "type": "keyword" },      // overview|section|scene|figure|table|paragraph|clip|...

      // === 구성 요약 ===
      "modality_set":  { "type": "keyword" },   // ["text","image","video","audio","table"] 중 다값
      "element_count": { "type": "integer" },   // 이 Chunk에 속한 Element 개수 (정합성 체크/페이지네이션 힌트)

      // === 표시/운영 보조(선택) ===
      "label":      { "type": "text" },         // [Optianl] "Figure 3", "Scene 2" 등 가벼운 표시용
      "tags":       { "type": "keyword" },      // [Optianl] 경량 필터(섹션명, 권한, 도메인 등)
      "created_at": { "type": "date" },
      "updated_at": { "type": "date" }
    }

}
}

3.2.2. 주요 특징

구조적 정보

chunk_seq: 미디어 내 순서 (0은 개요 등 특수 용도로 사용 가능)

chunk_type: 청크 유형 (overview|section|scene|figure|table|paragraph|clip)

modality_set: 포함된 모달리티 목록 (다중값 지원)

성능 최적화

element_count: 페이지네이션 힌트 및 정합성 체크용

media_id를 routing key로 활용 권장

3.3. Element 인덱스

설계 목적
실제 검색이 수행되는 핵심 인덱스로, 벡터 검색과 텍스트 검색을 모두 지원합니다.

3.3.1. 스키마

{
"settings": {
"index": { "knn": true, "number_of_shards": 3, "number_of_replicas": 1 },
"analysis": {
"analyzer": {
"ko_en": {
"type":"custom",
"tokenizer":"nori_tokenizer",
"filter":["lowercase","nori_part_of_speech","nori_number"]
}
}
}
},
"mappings": {
"dynamic": "false",
"properties": {
// === 공통 식별자 ===
"element_id":   { "type": "keyword" }, // PK
"chunk_id":     { "type": "keyword" }, // 부모 Chunk
"media_id":     { "type": "keyword" }, // 루트 Media
"description": { "type": "text", "analyzer": "ko_en" }, // 주석, 설명

      // === 내용(단일 필드) ===
      "modality":     { "type": "keyword" },                // text|image|video|audio -> FIXED
      "element_type": { "type": "keyword" },                // summary|stt|caption|ocr|paragraph|table|chart|...
      // uri:이미지,비디오,오디오 | plain:순수 텍스트 | json,markdown: 표, 문서 등
      "content_type": { "type": "keyword" },                // plain|uri|json|markdown|... 
      "content": { "type": "text", "analyzer": "ko_en",     // [S1] BM25 (text일 때)
        "fields": { "exact": { "type":"keyword", "ignore_above": 2048 } }  // only when content_type=uri
      },
      
      // === 1차 검색용 임베딩 (모달별 중 해당 1개만 사용) ===
       "embeddings": {
        "properties": { // 4개의 모달리티 중 Element 별 1개만 활성화
          "text":  { "type":"knn_vector", "dimension":384, "method":{"name":"hnsw","space_type":"cosinesimil"} },
          "image": { "type":"knn_vector", "dimension":512, "method":{"name":"hnsw","space_type":"cosinesimil"} },
          "video": { "type":"knn_vector", "dimension":512, "method":{"name":"hnsw","space_type":"cosinesimil"} },
          "audio": { "type":"knn_vector", "dimension":512, "method":{"name":"hnsw","space_type":"cosinesimil"} }
          // 필요 시 확장 가능...
          // "imageV2": { "type":"knn_vector", "dimension":768, "method":{"name":"hnsw","space_type":"cosinesimil"} }
        }
      },
  
      // === 2차 리랭크/표시 보조 ===
      "quality_scores": {
          "properties": { // 0~1 정규화 권장
            // "content_quality": { "type": "rank_feature" },     // 텍스트/이미지 품질
            "extraction_confidence": { "type": "rank_feature" }, // OCR/STT 신뢰도  
            // "structural_importance": { "type": "rank_feature" }, // 문서 구조상 중요도
            // "completeness": { "type": "rank_feature" },         // 내용 완전성
            // "combined_static": { "type": "rank_feature" }       // 위 4개의 가중 평균
          }
      }
        
      // === 공통 메타 ===
      "element_seq":     { "type": "integer" },
      "language":     { "type": "keyword" },                // [Opional] "ko"|"en"|...|"unknown"
      "created_at":   { "type": "date" },
      "updated_at":   { "type": "date" },
      "tags":         { "type": "keyword" }                 // [Opional] 경량 필터/통계(권한/도메인/민감도 등)
    }

}
}

3.3.2. 주요 특징

내용 저장 구조: 단일 내용 필드 접근법

content: 모든 유형의 내용을 단일 필드에 저장

content_type: 내용 형식 구분 (plain|uri|json|markdown)

modality: 모달리티 구분 (text|image|video|audio)

element_type: 세부 유형(유연하게 확장 가능)

text: summary|stt|caption|ocr|paragraph|table|chart|…

image: origin|cropped|detected_object|table|chart|…

임베딩 저장 전략: Nested 구조 설계

Element 당 해당 모달리티 임베딩 1개만 활성화

차원이 다른 임베딩 모델 동시 지원

모델 변경 시 기존 임베딩 유지하며 새 임베딩 추가 가능

버전 관리 방식의 임베딩 저장 (예: imageV2 필드 추가)

품질 점수 시스템: 확장 가능한 품질 지표

extraction_confidence: OCR/STT 신뢰도

content_quality: 텍스트/이미지 품질 점수 (확장 예정)

structural_importance: 문서 구조상 중요도 (확장 예정)

completeness: 내용 완전성 점수 (확장 예정)

combined_static: 종합 품질 점수 (확장 예정)

모든 점수는 0~1로 정규화하여 저장할 것을 권장합니다.

### 뽑힌 element를 기준으로 Chunk meta와 Media meta도 return 한다.

element의 상위 chunk_id, media_id로 chunk meta와 media meta를 조회하여 함께 반환한다.
하지만 점수는 element를 고른 opensearch 결과 점수를 기준으로 정렬해서 반환한다.
chunk meta와 media meta는 request body의 옵션 여부를 선택해서 반환 여부를 결정할 수 있다.

### 질의 의도 분석은 LLM을 사용한다.
프롬프트 작성 필수: element_type에 대한 설명 제공
질의 의도 분석은 어떤 element_type을 선택할지 LLM에게 묻는 방식으로 구현한다.
element_type은 여러 개 선택이 가능하다.
최대한 많은 element_type을 선택하도록 프롬프트를 작성한다.
선택된 element_type은 opensearch 쿼리의 필터로 사용된다.

### 질의 의도 분석으로 뽑힌 element_type을 기준으로 feature extraction을 진행한다.
feature extraction api를 통해서 진행한 결과는 opensearch 쿼리 검색에 사용된다.

### 최종 검색 쿼리는 feature extraction 결과와 질의 의도 분석 결과를 조합해서 만든다.
LLM을 이용한다.
프롬프트를 상세히 작성한다.

### 로그
LLM 요청과 응답에 대한 로그를 남긴다.
길어지는 로그는 debug level로 설정한다.
디폴트 로그 레벨은 info로 설정한다.

### 간단한 chatbot 프론트 구성
static 디렉토리 하위에 간단한 HTML, CSS, JS로 구성한다.

## 사용할 툴

### Embedding API

위 명세 참고

### Feature Extraction API

위 명세 참고

### Opensearch

### Litellm

LLM 호출용
litellm_url, litellm_api_key, litellm_model 등 환경변수로 선택할 수 있도록 개발

## 프레임워크

FastAPI

uv 라이브러리 관리도구 사용 (pyproject.toml)

## 배포환경

Docker 이미지를 GitLab Container Registry에 푸시한다.
이미지 푸시하는 과정을 gitlab ci를 통해서 진행한다.
