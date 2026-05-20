"""EchoAI backend entry point.

Run from the repo root:
    python -m backend.main
    python backend/main.py

Env vars (all optional):
    BACKEND_HOST   default: 0.0.0.0
    BACKEND_PORT   default: 8000
    RELOAD         default: 0   ("1" enables hot reload)
    LOG_LEVEL      default: info
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import uvicorn


def main() -> None:
    uvicorn.run(
        "backend.api.main:app",
        host=os.getenv("BACKEND_HOST", "0.0.0.0"),
        port=int(os.getenv("BACKEND_PORT", "8000")),
        reload=os.getenv("RELOAD", "0") == "1",
        log_level=os.getenv("LOG_LEVEL", "info").lower(),
    )


if __name__ == "__main__":
    main()
