# -----------------------------------------------------------------------------
# Base Stage: Common dependencies and setup
# -----------------------------------------------------------------------------
FROM python:3.11-slim as base

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies and create app user
RUN apt-get update && apt-get install -y \
    --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --shell /bin/bash --uid 1000 app

# Install uv package manager (latest version with dependency groups support)
RUN pip install --no-cache-dir uv>=0.5.0

# Set working directory
WORKDIR /app

# Copy dependency files first (for better layer caching)
COPY --chown=app:app pyproject.toml ./

# -----------------------------------------------------------------------------
# Development Stage: Includes development tools
# -----------------------------------------------------------------------------
FROM base as development

# Set Docker-specific environment variables
ENV APP_HOST=0.0.0.0 \
    APP_PORT=8000 \
    DEBUG=true

# Install runtime dependencies first
RUN uv pip install --system -e .

# Install development tools separately
RUN uv pip install --system pyright>=1.1.408 ruff>=0.15.0

# Create necessary directories
RUN mkdir -p logs app_logs \
    && chown -R app:app /app

# Copy application code
COPY --chown=app:app app/ ./app/
COPY --chown=app:app static/ ./static/
COPY --chown=app:app templates/ ./templates/
COPY --chown=app:app run.py ./

# Switch to non-root user
USER app

# Expose port
EXPOSE 8000

# Default command for development
CMD ["python", "run.py"]

# -----------------------------------------------------------------------------
# Production Stage: Minimal runtime dependencies only
# -----------------------------------------------------------------------------
FROM base as production

# Set Docker-specific environment variables
ENV APP_HOST=0.0.0.0 \
    APP_PORT=8000 \
    DEBUG=false

# Install only runtime dependencies
RUN uv pip install --system -e .

# Create necessary directories with minimal permissions
RUN mkdir -p logs app_logs \
    && chown -R app:app /app \
    && chmod 755 /app

# Copy application code
COPY --chown=app:app app/ ./app/
COPY --chown=app:app static/ ./static/
COPY --chown=app:app templates/ ./templates/
COPY --chown=app:app run.py ./

# Remove unnecessary files and clean up
RUN apt-get autoremove -y \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && rm -rf /tmp/* \
    && rm -rf /root/.cache

# Switch to non-root user
USER app

# Expose port
EXPOSE 8000

# Production command with unified logging
CMD ["python", "run.py"]

# -----------------------------------------------------------------------------
# Default target is production
# -----------------------------------------------------------------------------
FROM production