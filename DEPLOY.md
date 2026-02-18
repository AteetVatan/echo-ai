# 🚀 EchoAI — Deploy to Railway (Step-by-Step)

This guide walks you through deploying EchoAI to **Railway** from **GitHub** using Docker.

---

## Prerequisites

- A [GitHub](https://github.com) account with the `echo-ai` repo pushed
- A [Railway](https://railway.app) account (sign up with GitHub)
- Your API keys ready (DeepSeek, OpenAI, Mistral)

---

## Step 1: Push Latest Code to GitHub

Make sure all deployment files are committed and pushed:

```bash
git add .
git commit -m "Add Railway deployment config"
git push origin main
```

**New/modified files that must be in the repo:**

| File | Purpose |
|------|---------|
| `Dockerfile` | Multi-stage build (frontend + backend + nginx) |
| `nginx.conf` | Reverse proxy config |
| `start.sh` | Startup script |
| `railway.toml` | Railway service config |
| `frontend/next.config.ts` | Has `output: "standalone"` |

---

## Step 2: Create a Railway Project

1. Go to [railway.app](https://railway.app) and sign in with GitHub
2. Click **"New Project"**
3. Select **"Deploy from GitHub Repo"**
4. Authorize Railway to access your GitHub repos (if not already)
5. Select your **`echo-ai`** repository
6. Railway auto-detects the `Dockerfile` and `railway.toml` → click **"Deploy Now"**

> ⚠️ The first deploy will **fail** because we haven't set environment variables yet. That's expected — proceed to Step 3.

---

## Step 3: Set Environment Variables

In the Railway dashboard, click on your **service** → **Variables** tab.

### 🔑 Required Variables (from `.env`)

Click **"+ New Variable"** or use **"RAW Editor"** to paste multiple at once.

| Variable | Value | Notes |
|----------|-------|-------|
| `DEEPSEEK_API_KEY` | `sk-your-key-here` | Primary LLM |
| `OPENAI_API_KEY` | `sk-proj-your-key-here` | STT fallback (Whisper API) |
| `MISTRAL_API_KEY` | `your-mistral-key` | Fallback LLM |
| `ALLOWED_ORIGINS` | `https://YOUR-APP.up.railway.app` | **Set after first deploy** (use your Railway URL) |
| `ECHOAI_API_KEY` | `your-auth-key` | Backend auth key |

### ⚙️ Optional Variables (sensible defaults exist)

| Variable | Default | Set if... |
|----------|---------|-----------|
| `HF_TOKEN` | *(empty)* | Using gated HuggingFace models |
| `DEEPSEEK_MODEL` | `deepseek-chat` | You want a different model |
| `MISTRAL_MODEL` | `mistral-small` | You want a different model |
| `OPENAI_MODEL` | `gpt-4o-mini` | You want a different model |
| `EDGE_TTS_VOICE` | `en-US-AndrewMultilingualNeural` | You want a different voice |
| `LOG_LEVEL` | `INFO` | Change to `DEBUG` for troubleshooting |
| `SUPABASE_URL` | *(empty)* | Using Supabase cloud DB |
| `SUPABASE_ANON_KEY` | *(empty)* | Using Supabase cloud DB |
| `SUPABASE_DB_PASSWORD` | *(empty)* | Using Supabase cloud DB |
| `SUPABASE_DB_URL` | *(empty)* | Using Supabase cloud DB |
| `SUPABASE_SERVICE_ROLE_KEY` | *(empty)* | Using Supabase cloud DB |

### 🔨 Build Variable (from `frontend/.env.local`)

This one is special — it must be available at **build time**:

1. In the Variables tab, click **"+ New Variable"**
2. Set the name to: `NEXT_PUBLIC_ECHOAI_API_KEY`
3. Set the value to: the **same value** as `ECHOAI_API_KEY`
4. **Important:** Enable the toggle **"Available at build time"** (or add it under the "Build" section)

> 💡 **Why?** Next.js inlines `NEXT_PUBLIC_*` variables into the JavaScript bundle during `npm run build`. If you only set it as a runtime variable, the frontend won't see it.

---

## Step 4: Configure Networking

Railway auto-assigns a port via the `PORT` environment variable. The `start.sh` script uses this automatically.

1. In your service settings, go to **Settings** → **Networking**
2. Click **"Generate Domain"** to get a public URL (e.g., `echoai-production.up.railway.app`)
3. **Copy this URL** — you'll need it for `ALLOWED_ORIGINS`

---

## Step 5: Update ALLOWED_ORIGINS

Now that you have your Railway URL:

1. Go back to **Variables**
2. Set `ALLOWED_ORIGINS` to: `https://YOUR-APP.up.railway.app`
   (Replace `YOUR-APP` with your actual Railway subdomain)

> You can add multiple origins separated by commas:
> `https://your-app.up.railway.app,http://localhost:3000,http://localhost:8000`

---

## Step 6: Redeploy

After setting all variables:

1. Go to the **Deployments** tab
2. Click **"Redeploy"** (or push a new commit to trigger auto-deploy)
3. Watch the build logs — it will take **10-15 minutes** on first build (PyTorch, Transformers, etc.)
4. Once deployed, the logs should show:

```
═══════════════════════════════════════════════════
 EchoAI — Starting Combined Service
═══════════════════════════════════════════════════
  Configuring nginx on port ...
  Starting FastAPI backend on :8000...
  Starting Next.js frontend on :3000...
  Starting nginx reverse proxy on :...
═══════════════════════════════════════════════════
 EchoAI is ready!
═══════════════════════════════════════════════════
```

---

## Step 7: Verify Deployment

Open your Railway URL in the browser:

| URL | Expected |
|-----|----------|
| `https://YOUR-APP.up.railway.app/` | Frontend loads (EchoAI chat page) |
| `https://YOUR-APP.up.railway.app/health` | `{"status": "healthy", ...}` |
| `https://YOUR-APP.up.railway.app/docs` | Swagger API docs |

### Test the chat:
1. Open the frontend URL
2. Type a message like "What are your skills?"
3. Verify you get a response from the AI

---

## Quick Reference: All Variables Summary

Use Railway's **RAW Editor** to paste these all at once (replace values with your actual keys):

```env
# ── Required ──────────────────────────────────
DEEPSEEK_API_KEY=sk-your-key
OPENAI_API_KEY=sk-proj-your-key
MISTRAL_API_KEY=your-mistral-key
ECHOAI_API_KEY=your-auth-key
ALLOWED_ORIGINS=https://your-app.up.railway.app

# ── Optional ──────────────────────────────────
HF_TOKEN=
DEEPSEEK_MODEL=deepseek-chat
MISTRAL_MODEL=mistral-small
OPENAI_MODEL=gpt-4o-mini
EDGE_TTS_VOICE=en-US-AndrewMultilingualNeural
LOG_LEVEL=INFO

# ── Supabase (only if using cloud DB) ─────────
SUPABASE_URL=
SUPABASE_ANON_KEY=
SUPABASE_SERVICE_ROLE_KEY=
SUPABASE_DB_PASSWORD=
SUPABASE_DB_URL=
```

And as a **Build Variable**:
```
NEXT_PUBLIC_ECHOAI_API_KEY=your-auth-key
```

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Build fails with OOM | Railway Pro plan needed (8GB RAM). Check build logs for "Killed" errors. |
| App crashes on startup | Check **Variables** — all 3 API keys must be set. Check logs for `ValidationError`. |
| Frontend loads but chat doesn't work | Check `ALLOWED_ORIGINS` includes your Railway URL. Check `ECHOAI_API_KEY` matches `NEXT_PUBLIC_ECHOAI_API_KEY`. |
| WebSocket connection fails | Railway supports WebSocket natively. Check browser console for WS errors. Ensure nginx is routing `/ws/` correctly. |
| Slow first response after deploy | Normal — vector index rebuilds on cold start (~30-60s). Subsequent requests are fast. |
| "Rate limit exceeded" | Default is 30 req/min. Adjust `RATE_LIMIT_PER_MINUTE` in variables if needed. |
| Model download hangs at startup | Whisper model is pre-downloaded during build. If it fails, `HF_TOKEN` may help for gated models. |

---

## Auto-Deploy from GitHub

Railway auto-deploys on every push to your default branch. To change this:

1. **Settings** → **Source** → **Branch**: pick which branch triggers deploys
2. You can also disable auto-deploy and use manual deploys from the dashboard

---

## Architecture Overview

```
Browser → Railway (single container)
           ├── nginx (:$PORT)  ← Railway's public port
           │   ├── /api/*  → FastAPI (:8000)
           │   ├── /ws/*   → FastAPI (:8000) [WebSocket]
           │   └── /*      → Next.js (:3000)
           ├── FastAPI backend (Python)
           └── Next.js frontend (Node.js standalone)
```
