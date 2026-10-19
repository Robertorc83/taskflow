# syntax=docker/dockerfile:1

# ---- build: resolve and install dependencies with uv into /app/.venv -------------------------
FROM python:3.12-slim AS build
COPY --from=ghcr.io/astral-sh/uv:0.10.4 /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never
WORKDIR /app

# Dependencies first (cached layer), then the project itself.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY src ./src
RUN uv sync --frozen --no-dev

# ---- runtime: no build tools, non-root user ---------------------------------------------------
FROM python:3.12-slim AS runtime
RUN groupadd --system app && useradd --system --gid app --home /app app
WORKDIR /app
COPY --from=build --chown=app:app /app/.venv /app/.venv
COPY --chown=app:app alembic.ini ./
COPY --chown=app:app alembic ./alembic
COPY --chown=app:app src ./src
# Fail closed: the image assumes production (refuses the dev JWT secret, never seeds demo users)
# and trusts no proxy headers unless FORWARDED_ALLOW_IPS names the reverse proxy.
ENV PATH="/app/.venv/bin:$PATH" PYTHONUNBUFFERED=1 \
    ENVIRONMENT=production SEED_DEMO_DATA=false FORWARDED_ALLOW_IPS=127.0.0.1
USER app
EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=3s --start-period=20s \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health')"
CMD ["sh", "-c", "alembic upgrade head && python -m taskmanager.seed && uvicorn taskmanager.main:app --host 0.0.0.0 --port 8000 --proxy-headers"]
