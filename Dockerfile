# Production-ready Dockerfile for GFP CoreX Multi-Config API
FROM python:3.12-slim

# ── Environment ────────────────────────────────────────────────────────────────
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    POETRY_VERSION=1.8.2 \
    POETRY_HOME="/opt/poetry" \
    POETRY_CACHE_DIR="/opt/poetry/cache"

# Add Poetry to PATH (POETRY_HOME/bin — NOT POETRY_VENV)
ENV PATH="$POETRY_HOME/bin:$PATH"

# ── System dependencies ────────────────────────────────────────────────────────
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        curl \
        build-essential \
        libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# ── Install Poetry + configure (single layer → PATH is guaranteed) ─────────────
RUN curl -sSL https://install.python-poetry.org | python3 - \
    && poetry config virtualenvs.create false \
    && poetry --version

# ── Application ────────────────────────────────────────────────────────────────
WORKDIR /app

# Copy only dependency files first (Docker layer cache optimisation)
COPY pyproject.toml poetry.lock ./

# Install production dependencies only (--only main replaces deprecated --no-dev)
RUN poetry install --only main --no-interaction --no-ansi

# Copy application source
COPY . .

# ── Security: run as non-root ──────────────────────────────────────────────────
RUN adduser --disabled-password --gecos '' appuser \
    && chown -R appuser:appuser /app
USER appuser

# ── Runtime ───────────────────────────────────────────────────────────────────
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "src.gfpcorex.main:app", "--host", "0.0.0.0", "--port", "8000"]