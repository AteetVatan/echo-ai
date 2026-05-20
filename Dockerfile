# ============================================================
# Stage 1: Build the Next.js frontend
# ============================================================
FROM node:20-alpine AS frontend-builder

WORKDIR /app/frontend

# Install dependencies first (layer caching)
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

# Copy frontend source
COPY frontend/ .

# ECHOAI_API_KEY is a runtime env var — used by Next.js API route proxies
# (no longer inlined into client JS via NEXT_PUBLIC_*)

# Build the standalone Next.js app
RUN npm run build


# ============================================================
# Stage 2: Combined runtime (Python + Node + nginx)
# ============================================================
FROM python:3.11-slim-bookworm

LABEL org.opencontainers.image.title="EchoAI" \
      org.opencontainers.image.description="Voice chat with AI Clone — FastAPI + Next.js + RAG behind nginx" \
      org.opencontainers.image.source="https://github.com/AteetVatan/echo-ai"

WORKDIR /app

# ── System dependencies (single layer) ────────────────────────
# nodejs from NodeSource is needed for the Next.js standalone runtime.
# Build deps (gcc/g++/libffi-dev/libssl-dev) stay in the image because
# some pip packages may still compile on import; stripping them is a
# separate, riskier optimization.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates curl gnupg \
        gcc g++ libffi-dev libssl-dev \
        nginx gettext-base \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# ── Python runtime config ─────────────────────────────────────
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# ── Python deps + ML model preloads (single ~600MB layer) ────
# pip install MUST succeed (chained with `&&`). Model preloads are
# wrapped in `{ ... || echo; }` groups so a download failure becomes a
# warning (models lazy-load at runtime) without masking a real pip error.
COPY backend/requirements.txt .
RUN pip install --upgrade pip \
    && pip install -r requirements.txt \
    && { python -c "\
from faster_whisper import WhisperModel; \
WhisperModel('small', device='cpu', compute_type='int8')" \
        || echo "WARN: Whisper preload failed; will download at runtime"; } \
    && { python -c "\
from transformers import AutoModel, AutoTokenizer; \
AutoTokenizer.from_pretrained('sentence-transformers/all-MiniLM-L6-v2'); \
AutoModel.from_pretrained('sentence-transformers/all-MiniLM-L6-v2'); \
print('Embedding model cached OK')" \
        || echo "WARN: Embedding model preload failed; will download at runtime"; }

# ── Application code (selective; no leaked dev artifacts) ─────
# /app needs at runtime: backend/ (FastAPI), rag_persona_db/ (RAG corpus),
# frontend_standalone/ (built Next.js, copied below).
COPY backend/ ./backend/
COPY rag_persona_db/ ./rag_persona_db/

# ── Built frontend from Stage 1 ───────────────────────────────
# Standalone output: .next/standalone/ contains server.js + node_modules
COPY --from=frontend-builder /app/frontend/.next/standalone ./frontend_standalone
# Static assets must live at <standalone>/.next/static
COPY --from=frontend-builder /app/frontend/.next/static ./frontend_standalone/.next/static
# Public assets must live at <standalone>/public
COPY --from=frontend-builder /app/frontend/public ./frontend_standalone/public

# ── nginx config + startup script + runtime dirs ──────────────
COPY nginx.conf /etc/nginx/nginx.conf.template
COPY start.sh /app/start.sh
RUN sed -i 's/\r$//' /etc/nginx/nginx.conf.template /app/start.sh \
    && chmod +x /app/start.sh \
    && mkdir -p /app/logs /var/log/nginx

# ── Health check ──────────────────────────────────────────────
HEALTHCHECK --interval=30s --timeout=30s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8080}/health || exit 1

EXPOSE 8080

ENTRYPOINT ["/app/start.sh"]
