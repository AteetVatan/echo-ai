#!/usr/bin/env python3
"""Development startup script for EchoAI."""

import importlib.util
import os
import shutil
import subprocess
import sys
import time
import webbrowser
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
BACKEND_HOST = "0.0.0.0"
BACKEND_PORT = 8000
BACKEND_URL = f"http://localhost:{BACKEND_PORT}"
FRONTEND_HOST = "0.0.0.0"
FRONTEND_PORT = 3000
FRONTEND_URL = f"http://localhost:{FRONTEND_PORT}"
SERVER_POLL_SECONDS = 0.5
OPEN_BROWSER_DELAY_SECONDS = 3

DEV_ENV_OVERRIDES = {
    "DEBUG": "True",
    "LOG_LEVEL": "INFO",
    "FRONTEND_URL": FRONTEND_URL,
}

STARTUP_LINES = (
    "",
    "Environment ready!",
    "",
    "Development URLs:",
    f"   Backend API: {BACKEND_URL}",
    f"   Frontend:   {FRONTEND_URL}",
    f"   API Docs:   {BACKEND_URL}/docs",
    f"   Old frontend URL redirects: {BACKEND_URL}/frontend",
    "",
    "Features:",
    "   - Hot reload enabled",
    "   - Info logging enabled",
    "   - CORS configured for development",
    "   - Next.js frontend dev server",
)


def setup_environment() -> bool:
    """Create a local env file from the template when needed."""
    print("Setting up EchoAI development environment...")
    env_file = PROJECT_ROOT / ".env"
    if env_file.exists():
        print("Environment file found")
        return True
    return _create_env_file(env_file)


def _create_env_file(env_file: Path) -> bool:
    """Create the env file from env.example."""
    template = PROJECT_ROOT / "env.example"
    if not template.exists():
        print("No env.example found. Please create .env manually.")
        return False
    shutil.copyfile(template, env_file)
    print("Created .env from env.example")
    print("Please edit .env with your API keys before continuing.")
    return False


def check_dependencies() -> bool:
    """Check whether backend runtime dependencies are importable."""
    print("Checking dependencies...")
    if _module_available("fastapi") and _module_available("uvicorn"):
        print("FastAPI and Uvicorn available")
        return True
    print("FastAPI or Uvicorn not installed")
    print("Run: pip install -r backend/requirements.txt")
    return False


def _module_available(name: str) -> bool:
    """Return True when a Python module can be imported."""
    return importlib.util.find_spec(name) is not None


def _dev_env() -> dict[str, str]:
    """Return environment variables for the backend process."""
    env = os.environ.copy()
    env.update(DEV_ENV_OVERRIDES)
    return env


def start_backend() -> subprocess.Popen[str]:
    """Start the FastAPI backend server."""
    print("Starting FastAPI backend...")
    return subprocess.Popen(_backend_command(), cwd=PROJECT_ROOT, env=_dev_env())


def _backend_command() -> list[str]:
    """Build the backend dev command."""
    return [
        sys.executable,
        "-m",
        "uvicorn",
        "backend.api.main:app",
        "--host",
        BACKEND_HOST,
        "--port",
        str(BACKEND_PORT),
        "--reload",
        "--log-level",
        "info",
    ]


def start_frontend() -> subprocess.Popen[str] | None:
    """Start the Next.js frontend development server when available."""
    frontend_dir = PROJECT_ROOT / "frontend"
    npm = _frontend_npm(frontend_dir)
    if not npm:
        return None
    print("Starting Next.js frontend...")
    return subprocess.Popen(
        _frontend_command(npm),
        cwd=frontend_dir,
        env=_frontend_env(),
    )


def _frontend_npm(frontend_dir: Path) -> str | None:
    """Return the npm executable when the frontend can run."""
    if not (frontend_dir / "package.json").exists():
        print("Frontend package.json not found; skipping frontend dev server")
        return None
    npm = shutil.which("npm")
    if npm:
        return npm
    print("npm not found; install Node.js or run the frontend manually")
    print(f"   cd frontend && npm run dev -- -H {FRONTEND_HOST} -p {FRONTEND_PORT}")
    return None


def _frontend_command(npm: str) -> list[str]:
    """Build the frontend dev command."""
    return [npm, "run", "dev", "--", "-H", FRONTEND_HOST, "-p", str(FRONTEND_PORT)]


def _frontend_env() -> dict[str, str]:
    """Return environment variables for the frontend process."""
    env = os.environ.copy()
    env["BACKEND_URL"] = BACKEND_URL
    env["PORT"] = str(FRONTEND_PORT)
    return env


def open_frontend() -> None:
    """Open the frontend in the default browser."""
    print("Opening frontend in browser...")
    time.sleep(2)
    if webbrowser.open(FRONTEND_URL):
        print("Frontend opened in browser")
        return
    print(f"Please open: {FRONTEND_URL}")


def stop_process(process: subprocess.Popen[str] | None, name: str) -> None:
    """Terminate a child process without leaving the paired server running."""
    if process is None or process.poll() is not None:
        return
    print(f"Stopping {name}...")
    process.terminate()
    _wait_or_kill(process)


def _wait_or_kill(process: subprocess.Popen[str]) -> None:
    """Wait briefly for graceful shutdown, then kill the process."""
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def run_servers() -> None:
    """Start backend and frontend, then keep them alive together."""
    processes = [("backend", start_backend()), ("frontend", start_frontend())]
    if _should_open_browser(processes):
        time.sleep(OPEN_BROWSER_DELAY_SECONDS)
        open_frontend()
    try:
        _monitor_servers(processes)
    except KeyboardInterrupt:
        print("\nDevelopment session ended")
    finally:
        for name, process in reversed(processes):
            stop_process(process, name)


def _should_open_browser(
    processes: list[tuple[str, subprocess.Popen[str] | None]],
) -> bool:
    """Return True when the frontend process exists and browser opening is enabled."""
    frontend = dict(processes).get("frontend")
    return frontend is not None and os.environ.get("OPEN_BROWSER", "1") != "0"


def _monitor_servers(processes: list[tuple[str, subprocess.Popen[str] | None]]) -> None:
    """Poll child servers until one exits."""
    while True:
        for name, process in processes:
            if process and process.poll() is not None:
                print(f"\n{name.capitalize()} exited with code {process.returncode}")
                return
        time.sleep(SERVER_POLL_SECONDS)


def main() -> None:
    """Start the development environment."""
    print("=" * 60)
    print("EchoAI Voice Chat - Development Environment")
    print("=" * 60)
    for line in STARTUP_LINES:
        print(line)
    run_servers()


if __name__ == "__main__":
    main()
