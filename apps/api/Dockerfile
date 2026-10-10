# Read-only API: FastAPI + SQLAlchemy (async) + asyncpg.
# Build from the repository root: docker build -f apps/api/Dockerfile -t periodic-3d-api apps/api
FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

COPY --from=ghcr.io/astral-sh/uv:0.8 /uv /usr/local/bin/uv

WORKDIR /app
# Dependencies first: this layer stays cached while the code changes.
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev --no-install-project
COPY src ./src
RUN uv sync --frozen --no-dev

RUN useradd --system --uid 10001 api
USER api

ENV PATH="/app/.venv/bin:$PATH" \
    P3D_CORS_ORIGINS="*"
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=4)"

# 2 workers fit a small VM (1 vCPU, 1 GB). Raise with: docker run -e WEB_CONCURRENCY=4 …
CMD ["sh", "-c", "uvicorn p3d_api.main:app --host 0.0.0.0 --port 8000 --workers ${WEB_CONCURRENCY:-2} --proxy-headers --forwarded-allow-ips='*'"]
