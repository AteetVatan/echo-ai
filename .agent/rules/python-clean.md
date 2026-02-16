---
trigger: glob
globs: "**/*.py, *.py"
---

# Python Rules — EchoAI

> These rules apply to ALL `.py` files in this repository.

## 1. Architecture

| Layer | Path | May import | Owns |
|-------|------|-----------|------|
| **Agents & Services** (logic) | `src/agents/`, `src/services/` | stdlib, typing, LangChain, LLM clients, audio libs | RAG agent, LLM orchestration, STT/TTS pipelines |
| **API** (entry-points) | `src/api/` | agents + services + FastAPI | HTTP/WebSocket endpoints, connection management |
| **Database** (persistence) | `src/db/` | stdlib, sqlite3, SQLAlchemy | DB operations, caching, vector store |
| **Utilities** (shared) | `src/utils/` | stdlib, typing | config, logging, audio helpers, performance monitoring |
| **Tests** | `tests/` | any src module + test libs | fixtures, assertions |

- `src/api/` endpoints should stay thin — delegate to agents/services.
- `src/services/` functions should receive **typed objects** where practical, not raw dicts/JSON.

## 2. Code Style & Standards

- **PEP 8 + Google docstring style.**
- **Formatter / linter**: use any PEP 8-compliant formatter (e.g. `black`, `ruff`).
- **Small diffs** — touch only what the task requires.
- **No new deps or external API calls** unless explicitly required by the task.

## 3. Functions

- Aim for **≤ 15 LOC** per function body; split when larger.
- One clear responsibility per function.

## 4. Constants & Strings

- **No magic numbers or strings.** Use `const`, `Enum`, or `Literal`.
- **No hardcoded strings** for: dict keys, event names, job statuses, error codes,
  log messages, prompt templates, CLI command names, route paths.
- Every such string must be **defined once** (in a constants module, `Enum`, or `Literal`)
  and referenced everywhere else.

```python
# BAD
status = "fetching"

# GOOD
class JobStatus(str, Enum):
    QUEUED = "queued"
    FETCHING = "fetching"
    ...
status = JobStatus.FETCHING
```

## 5. Function Arguments

- **No positional booleans.** Use `*` to force keyword-only.
- **> 3 params → dataclass or Pydantic model.**

```python
# BAD
def fetch(url, True, 30):
    ...

# GOOD
def fetch(url: str, *, follow_redirects: bool = True, timeout_s: int = 30) -> ...:
    ...
```

## 6. SOLID Principles

| Principle | Guideline |
|-----------|-----------|
| **SRP** | One reason to change per module / class. |
| **OCP** | Extend via new classes / strategies, not editing existing ones. |
| **LSP** | Subtypes must be substitutable for their base. |
| **ISP** | Slim `Protocol` interfaces; no god-protocols. |
| **DIP** | Core depends on abstractions (`Protocol`); infra injects concrete implementations. |

## 7. Type Safety & Boundaries

- **Type-hint all public APIs.** Avoid `Any` where possible.
- **Boundary crossing**: raw `dict` / JSON → Pydantic model or dataclass
  where practical. Service/agent functions should receive typed objects.
- **Settings**: centralise env-var access in `src/utils/config.py`.
  Avoid scattering `os.getenv` calls across modules.
- **No dynamic hacks**: no `getattr` / `setattr` / `__dict__` manipulation
  in service/agent code.

## 8. Async / IO

- **Prefer `asyncio`** where the project already uses async (FastAPI, WebSockets).
- **Always set timeouts** on HTTP calls, DB queries, and external API calls
  (OpenAI, ElevenLabs, Mistral).
- **Retries**: only for safe/idempotent operations (e.g. TTS/STT calls).
- **Cleanup**: use `async with` / `contextlib.asynccontextmanager`.
  Never leave connections or sessions dangling.

## 9. Error Handling

- Maintain a **domain exception hierarchy** under `src/`.
- **Catch specific exceptions** — never bare `except:` or `except Exception:` without re-raise.
- **Re-raise with context**: `raise AppError("…") from e`.
- **Never swallow errors silently.**

## 10. Logging

- Use the standard **`logging`** module (configured in `src/utils/logging.py`).
- Include contextual identifiers (session ID, request ID) where available.
- **Never log secrets, tokens, or PII.**

## 11. Testing

- Framework: **`pytest`** (add `pytest-asyncio` when testing async code).
- Follow **AAA pattern** (Arrange → Act → Assert).
- `src/agents/`, `src/services/`, `src/utils/` → unit tests (no DB, no network).
- `src/db/`, `src/api/` → integration tests (mark with `@pytest.mark.integration`).

## 12. Human-Style Code

- **Zero AI trace or chatter** — no "Sure!", "Here's the code", auto-generated banners,
  or "# This function does X" obvious comments.
- Skip boilerplate headers and section dividers.
- Use **idiomatic Python naming**: `snake_case` functions/vars, `PascalCase` classes.
- Code should read as if written by a skilled human — pragmatic, not robotic.

## 13. AI Workflow Rules

- **Before making edits**: write a 3–5 line plan stating:
  - What will change.
  - Which layer (core vs infra) is affected.
  - Any boundary implications.
- **Changes must be atomic** — one logical change per edit.
- **No drive-by refactors** — don't "improve" unrelated code while fixing a bug.