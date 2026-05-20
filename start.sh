#!/bin/bash
set -x  # Print every command for Railway deploy-log debugging
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

# ── 5. Wait for backend + frontend to be ready ──────────────
# Require the frontend to return 200 on `/` REQUIRED_HITS times in a row.
# `curl -sf` already rejects non-2xx. Multiple hits ensure Next.js has
# compiled & cached the root page bundle before Railway routes traffic —
# otherwise users get a raw 404 on first cold-start request.
echo "  Waiting for services to become ready..."
MAX_WAIT=180
WAITED=0
FRONTEND_HITS=0
REQUIRED_HITS=3
while [ $WAITED -lt $MAX_WAIT ]; do
    BACKEND_OK=0
    FRONTEND_OK=0

    curl -sf http://127.0.0.1:$BACKEND_PORT/health > /dev/null 2>&1 && BACKEND_OK=1
    if curl -sf http://127.0.0.1:3000/ > /dev/null 2>&1; then
        FRONTEND_OK=1
        FRONTEND_HITS=$((FRONTEND_HITS + 1))
    else
        FRONTEND_HITS=0
    fi

    if [ $BACKEND_OK -eq 1 ] && [ $FRONTEND_HITS -ge $REQUIRED_HITS ]; then
        echo "  Both services are ready! (waited ${WAITED}s, frontend warm after ${FRONTEND_HITS} consecutive 200s)"
        break
    fi

    sleep 2
    WAITED=$((WAITED + 2))
    [ $((WAITED % 10)) -eq 0 ] && echo "  Still waiting... (${WAITED}s) backend=$BACKEND_OK frontend_hits=$FRONTEND_HITS/$REQUIRED_HITS"
done

if [ $WAITED -ge $MAX_WAIT ]; then
    echo "  WARNING: Services did not become ready within ${MAX_WAIT}s"
    echo "    Backend reachable: $BACKEND_OK"
    echo "    Frontend consecutive 200s: $FRONTEND_HITS/$REQUIRED_HITS"
fi

echo "═══════════════════════════════════════════════════"
echo " EchoAI is ready!"
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
