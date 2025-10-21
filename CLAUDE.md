# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a multimodal search and RAG system using OpenSearch. The system processes text, images, audio, and video content through external APIs for embedding and feature extraction, then performs hybrid search combining text and vector search capabilities.

**Key Features:**
- Multi-modal content search (text, image, video, audio)
- Hybrid search combining BM25 and vector similarity
- LLM-powered query intent analysis
- Feature extraction through external APIs
- Three-tier OpenSearch index structure (media_meta, chunk_meta, elements)

## Technology Stack

- **Framework**: FastAPI with Python 3.11
- **Package Manager**: uv with pyproject.toml
- **Search Engine**: OpenSearch with vector search capabilities
- **LLM Integration**: LiteLLM for multiple model support
- **External APIs**: Embedding and Feature Extraction services
- **Containerization**: Docker with GitLab CI/CD

## Development Commands

### Local Development
```bash
# Install dependencies
uv pip install -e .

# Run development server
uv run run.py

# Run with uvicorn directly
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Code Quality
```bash
# Install dev dependencies
uv pip install -e .[dev]

# Code formatting and linting
uv run -m isort app/
uv run -m pyright app/
```

### Docker
```bash
# Build and run with Docker Compose
docker-compose up --build

# Run specific services
docker-compose up opensearch opensearch-dashboards
docker-compose --profile dev up  # Include LiteLLM
```

## Architecture

### Directory Structure
```
app/
├── main.py              # FastAPI application entry point
├── core/                # Core configuration and logging
├── models/              # Pydantic models for requests/responses
├── services/            # Business logic (search, opensearch)
├── clients/             # External API clients (embedding, feature extraction, LLM)
└── api/routes/          # API endpoints
```

### OpenSearch Indices
1. **media_meta**: File metadata and technical information
2. **chunk_meta**: Structural chunk information within media
3. **elements**: Searchable content elements with embeddings

### Search Flow
1. Query intent analysis using LLM
2. Feature extraction (keywords, entities, summary)
3. Embedding generation for vector search
4. Hybrid search execution in OpenSearch
5. Result enrichment with metadata

## Configuration

### Environment Variables
Key settings in `.env`:
- `OPENSEARCH_HOST`, `OPENSEARCH_PORT`: OpenSearch connection
- `EMBEDDING_API_URL`: External embedding service
- `FEATURE_EXTRACTION_API_URL`: External feature extraction service  
- `LITELLM_URL`, `LITELLM_MODEL`: LLM service configuration
- `LOG_LEVEL`: Logging level (info/debug)

### External API Dependencies
The system requires external APIs for:
- Text/image embedding generation
- Feature extraction (summarization, keyword extraction, etc.)
- Document parsing and OCR
- LLM inference through LiteLLM

## Key Implementation Notes

- Search service orchestrates the complete search pipeline
- LLM client handles query analysis and search query enhancement
- OpenSearch service manages index operations and hybrid queries
- All external API calls are async with proper error handling
- Comprehensive logging for debugging and monitoring

## Deployment

- GitLab CI/CD pipeline builds Docker images and pushes to GitLab Registry
- Docker Compose configuration for local development
- Health checks and proper container lifecycle management