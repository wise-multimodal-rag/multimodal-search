from typing import Dict, List, Any, Optional
from fastapi import UploadFile
from loguru import logger

from app.models.opensearch import SearchResult, SearchResponse, Element, ChunkMeta, MediaMeta
from app.models.requests import FeatureExtractionResponse
from app.services.opensearch_service import OpenSearchService
from app.clients.llm_client import LLMClient
from app.clients.embedding_client import EmbeddingClient
from app.clients.feature_extraction_client import FeatureExtractionClient


class SearchService:
    def __init__(
        self,
        opensearch_service: OpenSearchService = None,
        llm_client: LLMClient = None,
        embedding_client: EmbeddingClient = None,
        feature_extraction_client: FeatureExtractionClient = None
    ):
        self.available_element_types = [
            # Text modality
            "paragraph", "title", "summary", "stt", "caption", "scene", 
            "ocr", "table", "translation",
            # Image modality  
            "origin", "cropped", "detected_object", "chart", "diagram", 
            "keyframe", "thumbnail",
            # Video modality
            "clip", "segment", 
            # Audio modality
            "speech", "music", "sound_effect", "ambient"
        ]
        # Use dependency injection or fallback to defaults
        self.opensearch_service = opensearch_service or OpenSearchService()
        self.llm_client = llm_client or LLMClient()
        self.embedding_client = embedding_client or EmbeddingClient()
        self.feature_extraction_client = feature_extraction_client or FeatureExtractionClient()


    async def search_multimodal(
        self,
        text_query: Optional[str] = None,
        image_file: Optional[UploadFile] = None,
        video_file: Optional[UploadFile] = None,
        audio_file: Optional[UploadFile] = None,
        include_chunk_meta: bool = True,
        include_media_meta: bool = True,
        max_results: int = 10,
        offset: int = 0
    ) -> SearchResponse:
        """멀티모달 검색 오케스트레이션"""
        logger.info("Processing multimodal search request")
        
        start_time = self._get_current_time_ms()
        
        try:
            # Step 1: 입력 모달리티 분석 및 처리
            modalities_data = await self._process_multimodal_inputs(
                text_query, image_file, video_file, audio_file
            )
            
            # Step 2: 텍스트가 있으면 질의 의도 분석
            query_analysis = None
            if text_query:
                query_analysis = await self._analyze_query_intent(text_query)
                if not query_analysis:
                    # Fallback to all element types
                    selected_element_types = self.available_element_types
                    query_analysis = {
                        "selected_element_types": selected_element_types,
                        "reasoning": "Query analysis failed, using all element types",
                        "confidence": 0.5
                    }
                else:
                    selected_element_types = query_analysis["selected_element_types"]
            else:
                # 텍스트 없으면 모든 타입 허용
                selected_element_types = self.available_element_types
                query_analysis = {
                    "selected_element_types": selected_element_types,
                    "reasoning": "No text query provided, using all element types",
                    "confidence": 0.5
                }
            
            logger.info(f"Selected element types: {selected_element_types}")
            
            # Step 3: 멀티모달 특징 추출
            extracted_features = await self._extract_features_multimodal(modalities_data, selected_element_types)
            
            # Step 4: 멀티모달 임베딩 생성
            embeddings = await self._generate_multimodal_embeddings(modalities_data)
            
            # Step 5: 검색 쿼리 생성
            search_query = text_query or "multimodal search"  # 기본 쿼리
            if text_query and extracted_features:
                enhanced_query = await self._build_enhanced_query(
                    text_query, selected_element_types, extracted_features
                )
                if enhanced_query:
                    search_query = enhanced_query
            
            # Step 6: OpenSearch 검색 실행
            search_results = await self.opensearch_service.search_elements(
                query=search_query,
                element_types=selected_element_types,
                embeddings=embeddings,
                size=max_results,
                from_=offset,
                filters=None
            )
            
            # Step 7: 결과 enrichment
            enriched_results = await self._enrich_search_results(
                search_results,
                include_chunk_meta,
                include_media_meta
            )
            
            end_time = self._get_current_time_ms()
            
            # 입력 모달리티 정보 추가
            input_modalities = list(modalities_data.keys())
            
            return SearchResponse(
                query=f"Multimodal search ({', '.join(input_modalities)}): {search_query}",
                total_hits=search_results["hits"]["total"]["value"],
                max_score=search_results["hits"]["max_score"] or 0.0,
                results=enriched_results,
                took_ms=end_time - start_time,
                element_types_used=selected_element_types,
                query_analysis=query_analysis
            )
            
        except Exception as e:
            logger.error(f"Multimodal search failed: {e}")
            raise

    async def _process_multimodal_inputs(
        self,
        text_query: Optional[str],
        image_file: Optional[UploadFile],
        video_file: Optional[UploadFile],
        audio_file: Optional[UploadFile]
    ) -> Dict[str, Any]:
        """멀티모달 입력 처리 및 특징 추출"""
        modalities_data = {}
        
        # 텍스트 처리
        if text_query:
            modalities_data["text"] = {
                "query": text_query,
                "type": "text"
            }
        
        # 이미지 처리 (인코딩만)
        if image_file:
            try:
                image_data = await image_file.read()
                
                # 이미지를 base64로 인코딩
                import base64
                base64_image = base64.b64encode(image_data).decode('utf-8')
                
                modalities_data["image"] = {
                    "filename": image_file.filename,
                    "content_type": image_file.content_type,
                    "size": len(image_data),
                    "base64_data": base64_image,
                    "type": "image"
                }
                
                logger.info(f"Processed image: {image_file.filename}")
                
            except Exception as e:
                logger.error(f"Failed to process image: {e}")
                modalities_data["image"] = {"error": str(e), "type": "image"}
        
        # 비디오 처리 (인코딩만)
        if video_file:
            try:
                video_data = await video_file.read()
                
                # 비디오를 base64로 인코딩
                import base64
                base64_video = base64.b64encode(video_data).decode('utf-8')
                
                modalities_data["video"] = {
                    "filename": video_file.filename,
                    "content_type": video_file.content_type,
                    "size": len(video_data),
                    "base64_data": base64_video,
                    "type": "video"
                }
                logger.info(f"Processed video: {video_file.filename}")
                
            except Exception as e:
                logger.error(f"Failed to process video: {e}")
                modalities_data["video"] = {"error": str(e), "type": "video"}
        
        # 오디오 처리 (인코딩만)
        if audio_file:
            try:
                audio_data = await audio_file.read()
                
                # 오디오를 base64로 인코딩  
                import base64
                base64_audio = base64.b64encode(audio_data).decode('utf-8')
                
                modalities_data["audio"] = {
                    "filename": audio_file.filename,
                    "content_type": audio_file.content_type,
                    "size": len(audio_data),
                    "base64_data": base64_audio,
                    "type": "audio"
                }
                logger.info(f"Processed audio: {audio_file.filename}")
                
            except Exception as e:
                logger.error(f"Failed to process audio: {e}")
                modalities_data["audio"] = {"error": str(e), "type": "audio"}
        
        return modalities_data
    
    async def _generate_multimodal_embeddings(self, modalities_data: Dict[str, Any]) -> Dict[str, List[float]]:
        """멀티모달 임베딩 생성"""
        embeddings = {}
        
        try:
            # 텍스트 임베딩
            if "text" in modalities_data:
                text_query = modalities_data["text"]["query"]
                text_embedding = await self.embedding_client.get_text_embedding(text_query)
                if text_embedding:
                    embeddings["text"] = text_embedding
            
            # 멀티모달 임베딩은 특징 추출 단계에서 분석된 결과를 활용
            # 여기서는 단순히 텍스트 기반 임베딩만 생성
            
            logger.debug(f"Generated embeddings for modalities: {list(embeddings.keys())}")
            return embeddings
            
        except Exception as e:
            logger.error(f"Multimodal embedding generation failed: {e}")
            return {}

    async def _analyze_query_intent(self, query: str) -> Optional[Dict[str, Any]]:
        """Analyze query intent using LLM with fallback strategy"""
        try:
            result = await self.llm_client.analyze_query_intent(query, self.available_element_types)
            if result:
                return result
            else:
                logger.warning("LLM query analysis returned None, using fallback strategy")
                return self._fallback_query_analysis(query)
        except Exception as e:
            logger.error(f"Query intent analysis failed: {e}, using fallback strategy")
            return self._fallback_query_analysis(query)
    
    def _fallback_query_analysis(self, query: str) -> Dict[str, Any]:
        """Fallback query analysis using simple heuristics"""
        query_lower = query.lower()
        selected_types = []
        
        # Simple keyword-based heuristics
        if any(word in query_lower for word in ["요약", "summary", "정리"]):
            selected_types.extend(["summary", "paragraph"])
        if any(word in query_lower for word in ["표", "table", "데이터", "data"]):
            selected_types.append("table")
        if any(word in query_lower for word in ["이미지", "image", "사진", "그림"]):
            selected_types.extend(["origin", "cropped", "detected_object", "chart", "diagram"])
        if any(word in query_lower for word in ["비디오", "video", "영상", "동영상"]):
            selected_types.extend(["clip", "segment", "keyframe", "thumbnail"])
        if any(word in query_lower for word in ["음성", "audio", "소리", "오디오"]):
            selected_types.extend(["speech", "music", "sound_effect"])
        if any(word in query_lower for word in ["텍스트", "text", "문서", "document"]):
            selected_types.extend(["paragraph", "title", "ocr"])
        
        # If no specific types identified, use a reasonable default set
        if not selected_types:
            selected_types = ["paragraph", "title", "summary", "origin", "chart"]
        
        # Remove duplicates while preserving order
        selected_types = list(dict.fromkeys(selected_types))
        
        return {
            "selected_element_types": selected_types,
            "reasoning": f"Fallback analysis based on keywords in query: {query[:50]}...",
            "confidence": 0.6
        }

    async def _extract_features_multimodal(self, modalities_data: Dict[str, Any], element_types: List[str]) -> Dict[str, Any]:
        """Extract features from all modalities based on selected element types"""
        features = {}
        
        try:
            # 각 모달리티별로 특징 추출
            if "text" in modalities_data:
                text_features = await self._extract_text_features(modalities_data["text"], element_types)
                features.update(text_features)
            
            if "image" in modalities_data:
                image_features = await self._extract_image_features(modalities_data["image"], element_types)
                features.update(image_features)
            
            if "video" in modalities_data:
                video_features = await self._extract_video_features(modalities_data["video"], element_types)
                features.update(video_features)
            
            if "audio" in modalities_data:
                audio_features = await self._extract_audio_features(modalities_data["audio"], element_types)
                features.update(audio_features)
            
            logger.debug(f"Extracted multimodal features: {list(features.keys())}")
            return features
            
        except Exception as e:
            logger.error(f"Multimodal feature extraction failed: {e}")
            return {}

    async def _extract_text_features(self, text_data: Dict[str, Any], element_types: List[str]) -> Dict[str, Any]:
        """Extract features from text modality"""
        features = {}
        
        try:
            text_query = text_data["query"]
            
            # 키워드 추출 (모든 타입에 유용)
            keywords_result = await self.feature_extraction_client.extract_keywords(text_query)
            if keywords_result:
                features["text_keywords"] = keywords_result
            
            # 엔티티 추출 (구조화된 콘텐츠용)
            if any(t in element_types for t in ["paragraph", "title", "summary", "ocr", "stt", "caption"]):
                entities_result = await self.feature_extraction_client.extract_entities(text_query)
                if entities_result:
                    features["text_entities"] = entities_result
            
            # 긴 쿼리의 경우 요약 생성
            if len(text_query) > 100:
                summary_result = await self.feature_extraction_client.extract_text_summary(text_query)
                if summary_result:
                    features["text_summary"] = summary_result
            
            # 텍스트 분류
            classification_result = await self.feature_extraction_client.classify_text(text_query)
            if classification_result:
                features["text_classification"] = classification_result
            
            return features
            
        except Exception as e:
            logger.error(f"Text feature extraction failed: {e}")
            return {}

    async def _extract_image_features(self, image_data: Dict[str, Any], element_types: List[str]) -> Dict[str, Any]:
        """Extract features from image modality"""
        features = {}
        
        try:
            # 이미지 관련 element_types가 선택된 경우에만 분석 수행
            if not any(t in element_types for t in ["caption", "origin", "cropped", "detected_object", "chart", "diagram"]):
                return features
            
            if "base64_data" not in image_data:
                return features
            
            base64_image = image_data["base64_data"]
            
            # 이미지 캡션 생성
            import base64
            image_bytes = base64.b64decode(base64_image)
            caption_result = await self.feature_extraction_client.generate_image_caption(image_bytes)
            
            if caption_result and "caption" in caption_result:
                image_caption = caption_result["caption"]
                
                # 캡션에서 키워드 추출
                caption_keywords = await self.feature_extraction_client.extract_keywords(image_caption)
                if caption_keywords:
                    features["image_keywords"] = caption_keywords
                
                # 캡션에서 엔티티 추출
                caption_entities = await self.feature_extraction_client.extract_entities(image_caption)
                if caption_entities:
                    features["image_entities"] = caption_entities
            
            # 객체 탐지 (detected_object가 선택된 경우)
            if "detected_object" in element_types:
                detection_result = await self.feature_extraction_client.detect_objects(image_bytes)
                if detection_result and "objects" in detection_result:
                    features["image_objects"] = detection_result["objects"]
            
            return features
            
        except Exception as e:
            logger.error(f"Image feature extraction failed: {e}")
            return {}

    async def _extract_video_features(self, video_data: Dict[str, Any], element_types: List[str]) -> Dict[str, Any]:
        """Extract features from video modality"""
        features = {}
        
        try:
            # 비디오 관련 element_types가 선택된 경우에만 LLM 분석 수행
            if not any(t in element_types for t in ["scene", "clip", "segment", "keyframe", "thumbnail"]):
                return features
            
            if "base64_data" not in video_data:
                return features
            
            base64_video = video_data["base64_data"]
            content_type = video_data["content_type"]
            
            # LLM을 통한 비디오 분석
            video_analysis = await self._analyze_video_with_llm(base64_video, content_type)
            
            if video_analysis:
                # 비디오 설명에서 키워드 추출
                if "description" in video_analysis:
                    video_keywords = await self.feature_extraction_client.extract_keywords(video_analysis["description"])
                    if video_keywords:
                        features["video_keywords"] = video_keywords
                
                # 비디오 특징 정보 직접 활용
                if "key_scenes" in video_analysis:
                    features["video_scenes"] = video_analysis["key_scenes"]
                if "detected_objects" in video_analysis:
                    features["video_objects"] = video_analysis["detected_objects"]
                if "activities" in video_analysis:
                    features["video_activities"] = video_analysis["activities"]
            
            return features
            
        except Exception as e:
            logger.error(f"Video feature extraction failed: {e}")
            return {}

    async def _extract_audio_features(self, audio_data: Dict[str, Any], element_types: List[str]) -> Dict[str, Any]:
        """Extract features from audio modality"""
        features = {}
        
        try:
            # 오디오 관련 element_types가 선택된 경우에만 LLM 분석 수행
            if not any(t in element_types for t in ["speech", "stt", "music", "sound_effect", "ambient"]):
                return features
            
            if "base64_data" not in audio_data:
                return features
            
            base64_audio = audio_data["base64_data"]
            content_type = audio_data["content_type"]
            
            # LLM을 통한 오디오 분석
            audio_analysis = await self._analyze_audio_with_llm(base64_audio, content_type)
            
            if audio_analysis:
                # STT 결과에서 키워드 추출
                if "transcription" in audio_analysis and audio_analysis["transcription"]:
                    transcription = audio_analysis["transcription"]
                    
                    stt_keywords = await self.feature_extraction_client.extract_keywords(transcription)
                    if stt_keywords:
                        features["audio_keywords"] = stt_keywords
                    
                    # STT 결과에서 엔티티 추출
                    stt_entities = await self.feature_extraction_client.extract_entities(transcription)
                    if stt_entities:
                        features["audio_entities"] = stt_entities
                
                # 오디오 특징 정보 직접 활용
                if "detected_sounds" in audio_analysis:
                    features["audio_sounds"] = audio_analysis["detected_sounds"]
                if "type" in audio_analysis:
                    features["audio_type"] = audio_analysis["type"]
            
            return features
            
        except Exception as e:
            logger.error(f"Audio feature extraction failed: {e}")
            return {}

    async def _analyze_video_with_llm(self, base64_video: str, content_type: str) -> Optional[Dict[str, Any]]:
        """LLM을 통한 비디오 분석 (필요시에만 호출)"""
        try:
            VIDEO_ANALYSIS_PROMPT = """이 비디오를 분석하여 다음 정보를 JSON 형식으로 제공하세요:
{
    "description": "비디오 내용 설명",
    "key_scenes": ["장면1 설명", "장면2 설명"],
    "detected_objects": ["객체1", "객체2"],
    "activities": ["활동1", "활동2"],
    "audio_present": true/false,
    "duration_estimate": "추정 길이(초)"
}"""

            messages = [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": VIDEO_ANALYSIS_PROMPT},
                        {
                            "type": "video_url",
                            "video_url": {
                                "url": f"data:{content_type};base64,{base64_video}"
                            }
                        }
                    ]
                }
            ]

            response = await self.llm_client.complete(messages, temperature=0.3, max_tokens=1000)
            if response:
                import json
                try:
                    return json.loads(response.strip())
                except json.JSONDecodeError:
                    return {"description": response, "analysis_type": "text_only"}
            return None
            
        except Exception as e:
            logger.error(f"Video analysis with LLM failed: {e}")
            return None

    async def _analyze_audio_with_llm(self, base64_audio: str, content_type: str) -> Optional[Dict[str, Any]]:
        """LLM을 통한 오디오 분석 (필요시에만 호출)"""
        try:
            AUDIO_ANALYSIS_PROMPT = """이 오디오를 분석하여 다음 정보를 JSON 형식으로 제공하세요:
{
    "type": "speech/music/sound_effect/ambient",
    "description": "오디오 내용 설명",
    "transcription": "음성이 있다면 텍스트 변환",
    "detected_sounds": ["소리1", "소리2"],
    "language": "언어 (있다면)",
    "quality": "음질 평가",
    "duration_estimate": "추정 길이(초)"
}"""

            messages = [
                {
                    "role": "user", 
                    "content": [
                        {"type": "text", "text": AUDIO_ANALYSIS_PROMPT},
                        {
                            "type": "audio_url",
                            "audio_url": {
                                "url": f"data:{content_type};base64,{base64_audio}"
                            }
                        }
                    ]
                }
            ]

            response = await self.llm_client.complete(messages, temperature=0.3, max_tokens=1000)
            if response:
                import json
                try:
                    return json.loads(response.strip())
                except json.JSONDecodeError:
                    return {"description": response, "analysis_type": "text_only"}
            return None
            
        except Exception as e:
            logger.error(f"Audio analysis with LLM failed: {e}")
            return None

    async def _generate_embeddings(self, query: str, features: Dict[str, Any]) -> Dict[str, List[float]]:
        """Generate embeddings for vector search"""
        embeddings = {}
        
        try:
            # Always generate text embedding
            text_embedding = await self.embedding_client.get_text_embedding(query)
            if text_embedding:
                embeddings["text"] = text_embedding
            
            # Generate enhanced text embedding using extracted features if available
            if features.get("keywords"):
                # Extract keywords from the result structure
                keywords_list = features["keywords"].get("keywords", []) if isinstance(features["keywords"], dict) else []
                keywords_text = " ".join([kw.get("word", "") for kw in keywords_list[:5] if isinstance(kw, dict)])
                if keywords_text:
                    enhanced_query = f"{query} {keywords_text}"
                    enhanced_embedding = await self.embedding_client.get_text_embedding(enhanced_query)
                    if enhanced_embedding:
                        # Use enhanced embedding if available, fallback to original
                        embeddings["text"] = enhanced_embedding
            
            logger.debug(f"Generated embeddings for modalities: {list(embeddings.keys())}")
            return embeddings
            
        except Exception as e:
            logger.error(f"Embedding generation failed: {e}")
            return {}

    async def _build_enhanced_query(
        self, 
        original_query: str, 
        element_types: List[str], 
        features: Dict[str, Any]
    ) -> Optional[str]:
        """Build enhanced search query using LLM"""
        try:
            return await self.llm_client.build_search_query(original_query, element_types, features)
        except Exception as e:
            logger.error(f"Enhanced query building failed: {e}")
            return None

    async def _enrich_search_results(
        self,
        search_results: Dict[str, Any],
        include_chunk_meta: bool,
        include_media_meta: bool
    ) -> List[SearchResult]:
        """Enrich search results with chunk and media metadata"""
        enriched_results = []
        
        for hit in search_results["hits"]["hits"]:
            element_data = hit["_source"]
            element = Element(**element_data)
            
            chunk_meta = None
            media_meta = None
            
            # Get chunk metadata if requested
            if include_chunk_meta:
                chunk_data = await self.opensearch_service.get_chunk_meta(element.chunk_id)
                if chunk_data:
                    chunk_meta = ChunkMeta(**chunk_data)
            
            # Get media metadata if requested
            if include_media_meta:
                media_data = await self.opensearch_service.get_media_meta(element.media_id)
                if media_data:
                    media_meta = MediaMeta(**media_data)
            
            result = SearchResult(
                element=element,
                chunk_meta=chunk_meta,
                media_meta=media_meta,
                score=hit["_score"]
            )
            
            enriched_results.append(result)
        
        return enriched_results

    def _get_current_time_ms(self) -> int:
        """Get current time in milliseconds"""
        import time
        return int(time.time() * 1000)


