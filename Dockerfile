# syntax=docker/dockerfile:1
FROM python:3.14-slim AS base

COPY --from=ghcr.io/astral-sh/uv:0.13.7 /uv /bin/uv

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:$PATH" \
    HF_HOME=/opt/hf \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Dependencies first, so code changes don't invalidate this (heavy) layer.
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --no-dev

# Bake the embedding model into the image: no download at startup, works offline.
RUN python -c "from sentence_transformers import SentenceTransformer; \
SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')"

COPY app ./app


FROM base AS test
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project
COPY tests ./tests
CMD ["pytest", "-v"]


FROM base AS runtime
RUN useradd --system --uid 1000 app && chown -R app /opt/hf
USER app
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
