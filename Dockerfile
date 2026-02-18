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

# Build arg — Next.js inlines NEXT_PUBLIC_* at build time
ARG NEXT_PUBLIC_ECHOAI_API_KEY=""
ENV NEXT_PUBLIC_ECHOAI_API_KEY=$NEXT_PUBLIC_ECHOAI_API_KEY

# Build the standalone Next.js app
RUN npm run build


# ============================================================
# Stage 2: Combined runtime (Python + Node + nginx)
# ============================================================
FROM python:3.11-slim

WORKDIR /app

# ── System dependencies ───────────────────────────────────────
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libffi-dev \
    libssl-dev \
    curl \
    nginx \
    gettext-base \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js 20 for Next.js standalone runtime
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# ── Python dependencies ──────────────────────────────────────
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONPATH=/app

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# ── Copy backend application ─────────────────────────────────
COPY . .

# ── Copy built frontend from Stage 1 ─────────────────────────
# Standalone output: .next/standalone/ contains server.js + node_modules
COPY --from=frontend-builder /app/frontend/.next/standalone ./frontend_standalone
# Static assets must live at <standalone>/.next/static
COPY --from=frontend-builder /app/frontend/.next/static ./frontend_standalone/.next/static
# Public assets must live at <standalone>/public
COPY --from=frontend-builder /app/frontend/public ./frontend_standalone/public

# ── Create necessary directories ─────────────────────────────
RUN mkdir -p src/db/chroma_db \
    && mkdir -p src/db/self_info_knowledge \
    && mkdir -p src/db/self_info_knowledge_v2 \
    && mkdir -p audio_cache \
    && mkdir -p logs \
    && mkdir -p /var/log/nginx

# ── nginx config ─────────────────────────────────────────────
COPY nginx.conf /etc/nginx/nginx.conf.template

# ── Startup script ───────────────────────────────────────────
COPY start.sh /app/start.sh
RUN chmod +x /app/start.sh

# ── Pre-download Faster-Whisper model (avoids cold-start) ────
RUN python -c "from faster_whisper import WhisperModel; WhisperModel('small', device='cpu', compute_type='int8')" \
    || echo "Warning: Could not pre-download Whisper model (will download at runtime)"

# ── Health check ─────────────────────────────────────────────
HEALTHCHECK --interval=30s --timeout=30s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8080}/health || exit 1

# ── Entrypoint ───────────────────────────────────────────────
ENTRYPOINT ["/app/start.sh"]