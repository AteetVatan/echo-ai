#!/bin/bash
# Do NOT use `set -e` — we manage errors explicitly so Railway sees logs.

echo "═══════════════════════════════════════════════════"
echo " EchoAI — Starting Combined Service"
echo "═══════════════════════════════════════════════════"

# Default PORT if not set by Railway
export PORT="${PORT:-8080}"
echo "  PORT=$PORT"

# Internal port for the FastAPI backend (must differ from $PORT)
BACKEND_PORT=8000
if [ "$PORT" = "$BACKEND_PORT" ]; then
    BACKEND_PORT=8001
fi
echo "  BACKEND_PORT=$BACKEND_PORT"

# ── 1. Inject $PORT into nginx config ─────────────────────────────
echo "  Configuring nginx on port $PORT..."
export BACKEND_PORT
envsubst '${PORT} ${BACKEND_PORT}' < /etc/nginx/nginx.conf.template > /etc/nginx/nginx.conf

# Validate nginx config before starting anything
echo "  Testing nginx config..."
nginx -t 2>&1 || { echo "ERROR: nginx config test failed!"; }

# ── 2. Start nginx FIRST (foreground-ready, but backgrounded) ─────
# Nginx starts almost instantly and will serve /health directly,
# allowing Railway's healthcheck to pass while backend warms up.
echo "  Starting nginx reverse proxy on :$PORT..."
nginx -g "daemon off;" &
NGINX_PID=$!
sleep 1

# Verify nginx is alive
if ! kill -0 $NGINX_PID 2>/dev/null; then
    echo "ERROR: nginx failed to start! Check /var/log/nginx/error.log:"
    cat /var/log/nginx/error.log 2>/dev/null || echo "  (no error log found)"
    exit 1
fi
echo "  nginx is running (PID $NGINX_PID) ✓"

# ── 3. Start FastAPI backend (background) ─────────────────────────
echo "  Starting FastAPI backend on :$BACKEND_PORT..."
cd /app
LOG_LEVEL="${LOG_LEVEL:-info}"
LOG_LEVEL="${LOG_LEVEL,,}"   # uvicorn requires lowercase
python -m uvicorn src.api.main:app \
    --host 0.0.0.0 \
    --port "$BACKEND_PORT" \
    --log-level "$LOG_LEVEL" \
    --no-access-log &
BACKEND_PID=$!

# ── 4. Start Next.js frontend (background) ───────────────────────
echo "  Starting Next.js frontend on :3000..."
cd /app/frontend_standalone
PORT=3000 HOSTNAME=0.0.0.0 node server.js &
FRONTEND_PID=$!

echo "═══════════════════════════════════════════════════"
echo " EchoAI is ready!  (backend warming up in background)"
echo "═══════════════════════════════════════════════════"

# ── 5. Wait for any process to exit ──────────────────────────────
# If any process dies, bring down the whole container so Railway restarts it
wait -n $BACKEND_PID $FRONTEND_PID $NGINX_PID
EXIT_CODE=$?
echo "A process exited (code $EXIT_CODE). Shutting down..."

# Log which process died
kill -0 $NGINX_PID   2>/dev/null || echo "  nginx exited"
kill -0 $BACKEND_PID 2>/dev/null || echo "  backend exited"
kill -0 $FRONTEND_PID 2>/dev/null || echo "  frontend exited"

kill $BACKEND_PID $FRONTEND_PID $NGINX_PID 2>/dev/null || true
exit 1
