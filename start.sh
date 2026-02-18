#!/bin/bash
set -e

echo "═══════════════════════════════════════════════════"
echo " EchoAI — Starting Combined Service"
echo "═══════════════════════════════════════════════════"

# Default PORT if not set by Railway
export PORT="${PORT:-8080}"
echo "  PORT=$PORT"

# ── 1. Inject $PORT into nginx config ─────────────────────────────
echo "  Configuring nginx on port $PORT..."
envsubst '${PORT}' < /etc/nginx/nginx.conf.template > /etc/nginx/nginx.conf

# ── 2. Start FastAPI backend (background) ─────────────────────────
echo "  Starting FastAPI backend on :8000..."
cd /app
python -m uvicorn src.api.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --log-level "${LOG_LEVEL:-info}" \
    --no-access-log &
BACKEND_PID=$!

# ── 3. Start Next.js frontend (background) ───────────────────────
echo "  Starting Next.js frontend on :3000..."
cd /app/frontend_standalone
PORT=3000 HOSTNAME=0.0.0.0 node server.js &
FRONTEND_PID=$!

# ── 4. Wait briefly, then start nginx (foreground) ───────────────
sleep 2
echo "  Starting nginx reverse proxy on :$PORT..."
echo "═══════════════════════════════════════════════════"
echo " EchoAI is ready!"
echo "═══════════════════════════════════════════════════"
nginx -g "daemon off;" &
NGINX_PID=$!

# ── 5. Wait for any process to exit ──────────────────────────────
# If any process dies, bring down the whole container so Railway restarts it
wait -n $BACKEND_PID $FRONTEND_PID $NGINX_PID
echo "A process exited. Shutting down..."
kill $BACKEND_PID $FRONTEND_PID $NGINX_PID 2>/dev/null || true
exit 1
