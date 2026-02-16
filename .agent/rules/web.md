---
trigger: glob
globs: "**/*.html, **/*.js, **/*.css"
---

# Frontend Rules — EchoAI

> These rules apply to all `.html`, `.js`, and `.css` files in the `frontend/` directory.

## 1. Stack

- **Vanilla HTML + JavaScript** — no frameworks, no build step.
- Served as static files by FastAPI (`/static/`).
- Single `index.html` with embedded `<style>`, linked `script.js`.

## 2. Architecture

- One main class (`EchoAIClient`) owns all client-side state and logic.
- Keep methods focused: one concern per method (connection, recording, streaming, playback, UI updates).
- DOM references should be cached in the constructor, not re-queried per call.

## 3. Code Style

- **No frameworks or transpilers** — write ES6+ that runs directly in modern browsers.
- Functions aim for **≤ 30 LOC**; split when larger.
- Use `const` / `let` — never `var`.
- **camelCase** for variables and functions.
- **No magic strings** for WebSocket message types, status values, or CSS class names — use constants at the top of the file.

## 4. WebSocket & Audio

- Always guard sends with a connection check (`this.isConnected`).
- Handle `onclose` and `onerror` gracefully — show user-friendly status, schedule reconnect.
- Set timeouts for operations that could hang (audio processing, reconnects).
- Clean up resources: revoke object URLs after playback, close audio contexts, stop media streams on disconnect.

## 5. Styling

- CSS lives inside `<style>` in `index.html`.
- Use CSS custom properties (variables) for the colour palette and spacing tokens.
- Prefer `linear-gradient`, `backdrop-filter`, and CSS animations for visual effects — no JS-driven animations for decorative elements.
- **Mobile-first** responsive design with `@media` breakpoints.
- Support `prefers-color-scheme: dark`.

## 6. Error Handling

- Wrap async operations (`getUserMedia`, WebSocket sends) in `try/catch`.
- Surface errors in the conversation UI via `addMessage('error', …)` — never fail silently.
- Log to `console.error` for debugging; never expose stack traces to the user.

## 7. Performance

- Avoid DOM thrashing — batch reads/writes, use `requestAnimationFrame` for visual updates if needed.
- Throttle or debounce high-frequency events (audio buffer processing, scroll listeners).
- Use `MutationObserver` sparingly — only for the conversation auto-scroll pattern already in place.

## 8. Human-Style Code

- Zero AI trace or chatter — no "Sure!", auto-generated banners, or obvious comments.
- Skip boilerplate headers and section dividers.
- Code should read as if written by a skilled human — pragmatic, not robotic.

## 9. AI Workflow

- Before edits, write a 3–5 line plan: what changes, which file(s), any WebSocket protocol impact.
- Changes must be atomic — one logical change per edit.
- No drive-by refactors.
