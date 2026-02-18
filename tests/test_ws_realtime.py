"""
WebSocket integration test for EchoAI Real-time AI Conversations.

Tests the full backend pipeline:
  WS connect → session_id → text chat → context follow-up → ping/pong → clear → edge cases

Usage:
    # Make sure backend is running first (python run_dev.py)
    pip install websockets  # if not installed
    python tests/test_ws_realtime.py
"""

import asyncio
import json
import time
import sys

try:
    import websockets
except ImportError:
    print("❌  Missing dependency: pip install websockets")
    sys.exit(1)

WS_URL = "ws://localhost:8000/ws/voice"
TIMEOUT = 30  # seconds per recv (RAG + TTS can be slow)

# ── helpers ──────────────────────────────────────────────────────────────────

passed = 0
failed = 0


def ok(label: str, detail: str = ""):
    global passed
    passed += 1
    print(f"  ✅  {label}" + (f"  —  {detail}" if detail else ""))


def fail(label: str, detail: str = ""):
    global failed
    failed += 1
    print(f"  ❌  {label}" + (f"  —  {detail}" if detail else ""))


async def recv_json(ws, label: str = "message"):
    """Receive and parse a JSON message with timeout."""
    raw = await asyncio.wait_for(ws.recv(), timeout=TIMEOUT)
    return json.loads(raw)


# ── test cases ───────────────────────────────────────────────────────────────

async def test_connection(ws) -> str:
    """T1: Should receive a connection message with session_id."""
    msg = await recv_json(ws, "connection")
    if msg.get("type") == "connection" and msg.get("session_id"):
        ok("Connection", f"session_id={msg['session_id'][:8]}…")
        return msg["session_id"]
    else:
        fail("Connection", f"unexpected: {msg}")
        return ""


async def test_ping_pong(ws):
    """T2: Ping should return pong."""
    await ws.send(json.dumps({"type": "ping"}))
    msg = await recv_json(ws, "pong")
    if msg.get("type") == "pong":
        ok("Ping/Pong")
    else:
        fail("Ping/Pong", f"expected pong, got: {msg}")


async def test_text_message(ws) -> str:
    """T3: Send a text message, expect processing + text_response."""
    question = "What is your work experience?"
    await ws.send(json.dumps({"type": "text", "text": question}))

    # Should get 'processing' first
    msg = await recv_json(ws, "processing")
    if msg.get("type") != "processing":
        fail("Text → processing", f"expected processing, got: {msg.get('type')}")
        return ""
    ok("Text → processing")

    # Then 'text_response'
    start = time.time()
    msg = await recv_json(ws, "text_response")
    latency = time.time() - start

    if msg.get("type") != "text_response":
        fail("Text → response", f"expected text_response, got: {msg.get('type')}")
        return ""

    response = msg.get("response_text", "")
    audio = msg.get("audio")
    has_audio = audio is not None and len(audio) > 0

    if not response:
        fail("Text → response", "empty response_text")
        return ""

    ok("Text → response", f"{latency:.1f}s | {len(response)} chars | audio={'yes' if has_audio else 'null'}")
    return response


async def test_context_followup(ws):
    """T4: Follow-up question should reference prior context."""
    await ws.send(json.dumps({"type": "text", "text": "Tell me more about that"}))

    # processing
    msg = await recv_json(ws, "processing")
    if msg.get("type") != "processing":
        fail("Follow-up → processing", f"got: {msg.get('type')}")
        return

    # response
    start = time.time()
    msg = await recv_json(ws, "text_response")
    latency = time.time() - start

    response = msg.get("response_text", "")
    if not response:
        fail("Follow-up → response", "empty response")
        return

    # A good contextual response should NOT say "I don't have information"
    is_fallback = "don't have specific information" in response.lower()
    if is_fallback:
        fail("Follow-up → context", "got fallback response — context memory may not be working")
    else:
        ok("Follow-up → context", f"{latency:.1f}s | context-aware response")


async def test_empty_message(ws):
    """T5: Empty text should return an error."""
    await ws.send(json.dumps({"type": "text", "text": "   "}))
    msg = await recv_json(ws, "error")
    if msg.get("type") == "error":
        ok("Empty text → error", msg.get("message", ""))
    else:
        fail("Empty text → error", f"expected error, got: {msg.get('type')}")


async def test_clear_history(ws):
    """T6: Clear history should succeed silently (no response expected).
    Then a follow-up should NOT have context."""
    await ws.send(json.dumps({"type": "clear_history"}))
    # No response expected — give it a moment
    await asyncio.sleep(0.5)
    ok("Clear history", "sent (no crash)")

    # Now ask a context-dependent question — should NOT have prior context
    await ws.send(json.dumps({"type": "text", "text": "Tell me more about that"}))
    msg = await recv_json(ws, "processing")  # processing
    msg = await recv_json(ws, "text_response")  # response

    response = msg.get("response_text", "")
    # After clearing, "tell me more about that" has no context — any response is OK
    # as long as it didn't crash
    if response:
        ok("Post-clear response", f"got response ({len(response)} chars)")
    else:
        fail("Post-clear response", "empty response")


async def test_unknown_type(ws):
    """T7: Unknown message type should return an error."""
    await ws.send(json.dumps({"type": "totally_invalid_type_xyz"}))
    msg = await recv_json(ws, "error")
    if msg.get("type") == "error":
        ok("Unknown type → error", msg.get("message", ""))
    else:
        fail("Unknown type → error", f"expected error, got: {msg.get('type')}")


async def test_rapid_messages(ws):
    """T8: Send 3 messages rapidly — all should get responses."""
    questions = [
        "What programming languages do you know?",
        "What is your education?",
        "What projects have you worked on?",
    ]

    for q in questions:
        await ws.send(json.dumps({"type": "text", "text": q}))

    responses_received = 0
    # Expect 3 × (processing + text_response) = 6 messages
    for _ in range(6):
        try:
            msg = await recv_json(ws, "rapid")
            if msg.get("type") == "text_response":
                responses_received += 1
        except asyncio.TimeoutError:
            break

    if responses_received == 3:
        ok("Rapid messages", f"all {responses_received}/3 responses received")
    else:
        fail("Rapid messages", f"only {responses_received}/3 responses received")


# ── main ─────────────────────────────────────────────────────────────────────

async def main():
    print(f"\n{'═' * 60}")
    print(f"  EchoAI WebSocket Integration Tests")
    print(f"  Target: {WS_URL}")
    print(f"{'═' * 60}\n")

    try:
        async with websockets.connect(WS_URL) as ws:
            # Core flow
            print("── Core Flow ──")
            session_id = await test_connection(ws)
            await test_ping_pong(ws)
            await test_text_message(ws)
            await test_context_followup(ws)

            # Edge cases
            print("\n── Edge Cases ──")
            await test_empty_message(ws)
            await test_unknown_type(ws)
            await test_clear_history(ws)

            # Stress
            print("\n── Stress ──")
            await test_rapid_messages(ws)

    except ConnectionRefusedError:
        print("❌  Cannot connect — is the backend running? (python run_dev.py)")
        sys.exit(1)
    except Exception as e:
        print(f"❌  Unexpected error: {e}")
        sys.exit(1)

    # Summary
    total = passed + failed
    print(f"\n{'═' * 60}")
    print(f"  Results: {passed}/{total} passed", end="")
    if failed:
        print(f"  |  {failed} FAILED ⚠️")
    else:
        print(f"  |  ALL PASSED ✅")
    print(f"{'═' * 60}\n")

    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    asyncio.run(main())
