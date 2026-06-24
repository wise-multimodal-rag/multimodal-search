"""OpenSearch utilities and index mappings configuration."""

from typing import Any, Dict


def get_opensearch_mappings() -> Dict[str, Any]:
    """Get all OpenSearch index mappings"""
    return {
        "media_meta": get_media_meta_mapping(),
        "chunk_meta": get_chunk_meta_mapping(),
        "elements": get_elements_mapping(),
    }


def get_media_meta_mapping() -> Dict[str, Any]:
    """Get media_meta index mapping"""
    return {
        "settings": {"index": {"number_of_shards": 1, "number_of_replicas": 1}},
        "mappings": {
            "dynamic": "false",
            "properties": {
                "media_id": {"type": "keyword"},
                "media_type": {"type": "keyword"},
                "mime_type": {"type": "keyword"},
                "title": {"type": "text", "analyzer": "standard"},
                "source_uri": {"type": "keyword"},
                "file_size_bytes": {"type": "long"},
                "duration_seconds": {"type": "float"},
                "width_pixels": {"type": "integer"},
                "height_pixels": {"type": "integer"},
                "language_primary": {"type": "keyword"},
                "chunk_count": {"type": "integer"},
                "element_count": {"type": "integer"},
                "metadata_flat": {"type": "object", "enabled": False},
                "owner": {"type": "keyword"},
                "visibility": {"type": "keyword"},
                "tags": {"type": "keyword"},
                "created_at": {"type": "date"},
                "updated_at": {"type": "date"},
            },
        },
    }


def get_chunk_meta_mapping() -> Dict[str, Any]:
    """Get chunk_meta index mapping"""
    return {
        "settings": {"index": {"number_of_shards": 2, "number_of_replicas": 1}},
        "mappings": {
            "dynamic": "false",
            "properties": {
                "chunk_id": {"type": "keyword"},
                "media_id": {"type": "keyword"},
                "chunk_seq": {"type": "integer"},
                "chunk_type": {"type": "keyword"},
                "modality_set": {"type": "keyword"},
                "element_count": {"type": "integer"},
                "label": {"type": "text"},
                "tags": {"type": "keyword"},
                "created_at": {"type": "date"},
                "updated_at": {"type": "date"},
            },
        },
    }


def get_elements_mapping() -> Dict[str, Any]:
    """Get elements index mapping"""
    return {
        "settings": {
            "index": {"knn": True, "number_of_shards": 3, "number_of_replicas": 1},
            "analysis": {
                "analyzer": {
                    "ko_en": {
                        "type": "custom",
                        "tokenizer": "nori_tokenizer",
                        "filter": ["lowercase", "nori_part_of_speech", "nori_number"],
                    }
                }
            },
        },
        "mappings": {
            "dynamic": "false",
            "properties": {
                "element_id": {"type": "keyword"},
                "chunk_id": {"type": "keyword"},
                "media_id": {"type": "keyword"},
                "description": {"type": "text", "analyzer": "ko_en"},
                "modality": {"type": "keyword"},
                "element_type": {"type": "keyword"},
                "content_type": {"type": "keyword"},
                "content": {
                    "type": "text",
                    "analyzer": "ko_en",
                    "fields": {"exact": {"type": "keyword", "ignore_above": 2048}},
                },
                "embeddings": {
                    "properties": {
                        "text": {
                            "type": "knn_vector",
                            "dimension": 2048,
                            "method": {"name": "hnsw", "space_type": "cosinesimil"},
                        },
                        "image": {
                            "type": "knn_vector",
                            "dimension": 2048,
                            "method": {"name": "hnsw", "space_type": "cosinesimil"},
                        },
                        "video": {
                            "type": "knn_vector",
                            "dimension": 2048,
                            "method": {"name": "hnsw", "space_type": "cosinesimil"},
                        },
                        "audio": {
                            "type": "knn_vector",
                            "dimension": 2048,
                            "method": {"name": "hnsw", "space_type": "cosinesimil"},
                        },
                    }
                },
                "quality_scores": {"properties": {"combined_static": {"type": "rank_feature"}}},
                "element_seq": {"type": "integer"},
                "language": {"type": "keyword"},
                "tags": {"type": "keyword"},
                "created_at": {"type": "date"},
                "updated_at": {"type": "date"},
            },
        },
    }
