"""OpenAI-compatible endpoint: make m1frame look like a *model* to any app.

Anything that lets you set a custom OpenAI base URL (Open WebUI, LibreChat, LM Studio
chat, Msty, Jan, Cursor/Continue/Cline, n8n, your own scripts, the openai SDK) can now
send prompts into m1frame, and every prompt goes through FrontDoor.

    python -m frontdoor serve --port 8765          (standalone, key: M1FRAME_PROXY_KEY)
    python api/server.py                           (Studio also serves /v1, key: M1FRAME_API_TOKEN)
    base_url = http://localhost:8765/v1
    model    = m1frame (agent decides) | m1frame-full (always full pipeline) | m1frame-chat (no tools)
"""
# No `from __future__ import annotations`: FastAPI must resolve `Request` at runtime.

import hmac
import json
import os
import time
import uuid

MODELS = {"m1frame": "auto", "m1frame-full": "full", "m1frame-chat": "chat"}
LOOPBACK = {"127.0.0.1", "localhost", "::1"}


def _text(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):  # OpenAI content parts
        return "\n".join(p.get("text", "") for p in content
                         if isinstance(p, dict) and p.get("type") == "text")
    return ""


def split_messages(messages: list[dict]) -> tuple[str, list[dict]]:
    """Last user message -> prompt; earlier user/assistant turns -> history.
    Client system prompts are folded into the prompt as user-level instructions
    (they must not override m1frame's own routing contract)."""
    system_bits = [_text(m.get("content")) for m in messages if m.get("role") == "system"]
    turns = [m for m in messages if m.get("role") in ("user", "assistant")]
    if not turns or turns[-1].get("role") != "user":
        raise ValueError("the last message must be from the user")
    prompt = _text(turns[-1].get("content"))
    if any(system_bits):
        prompt = ("Client instructions:\n" + "\n".join(b for b in system_bits if b)
                  + "\n\nRequest:\n" + prompt)
    history = [{"role": m["role"], "content": _text(m.get("content"))} for m in turns[:-1]]
    return prompt, history


def default_factory():
    from frontdoor.agent import FrontDoor
    return FrontDoor.from_config()          # dangerous tools stay denied over HTTP


def register_routes(app, frontdoor_factory=None, check_auth=None) -> None:
    """Add /v1/models and /v1/chat/completions to an existing FastAPI app.
    `check_auth(request)` may raise HTTPException; pass None when middleware already
    authenticates (the Studio server does)."""
    from fastapi import HTTPException, Request
    from fastapi.concurrency import run_in_threadpool
    from fastapi.responses import JSONResponse, StreamingResponse

    factory = frontdoor_factory or default_factory
    auth = check_auth or (lambda _r: None)

    @app.get("/v1/models")
    def models(request: Request):
        auth(request)
        now = int(time.time())
        return {"object": "list", "data": [
            {"id": m, "object": "model", "created": now, "owned_by": "m1frame"} for m in MODELS]}

    @app.post("/v1/chat/completions")
    async def chat(request: Request):
        auth(request)
        try:
            body = await request.json()
        except ValueError as exc:
            raise HTTPException(400, "invalid JSON body") from exc
        mode = MODELS.get(body.get("model", "m1frame"), "auto")
        try:
            prompt, history = split_messages(body.get("messages") or [])
            # The pipeline is slow and synchronous; keep the event loop free.
            result = await run_in_threadpool(lambda: factory().handle(prompt, history=history, mode=mode))
        except ValueError as exc:      # bad messages or controller policy refusal
            raise HTTPException(400, str(exc)) from exc
        answer = result.answer
        if body.get("m1frame_receipt", True):
            answer += f"\n\n---\n_m1frame: {result.receipt()}_"
        cid, now = f"chatcmpl-{uuid.uuid4().hex[:24]}", int(time.time())
        model = body.get("model", "m1frame")

        if body.get("stream"):
            def gen():
                base = {"id": cid, "object": "chat.completion.chunk", "created": now, "model": model}
                yield "data: " + json.dumps({**base, "choices": [{"index": 0, "delta": {
                    "role": "assistant", "content": answer}, "finish_reason": None}]}) + "\n\n"
                yield "data: " + json.dumps({**base, "choices": [{"index": 0, "delta": {},
                                             "finish_reason": "stop"}]}) + "\n\n"
                yield "data: [DONE]\n\n"
            return StreamingResponse(gen(), media_type="text/event-stream")

        return JSONResponse({
            "id": cid, "object": "chat.completion", "created": now, "model": model,
            "choices": [{"index": 0, "message": {"role": "assistant", "content": answer},
                         "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
            "m1frame": {"mode": result.mode, "tools": [s.tool for s in result.steps],
                        "workflow": result.workflow},
        })


def build_app(frontdoor_factory=None, key: str | None = None):
    """Standalone app. Requires `Authorization: Bearer <key>` when a key is set."""
    from fastapi import FastAPI, HTTPException

    key = key if key is not None else os.environ.get("M1FRAME_PROXY_KEY", "")
    app = FastAPI(title="m1frame OpenAI-compatible front door")

    def check(request):
        if not key:
            return
        supplied = request.headers.get("authorization", "")
        supplied = supplied[7:] if supplied.startswith("Bearer ") else ""
        if not hmac.compare_digest(key.encode(), supplied.encode()):
            raise HTTPException(401, "invalid api key")

    register_routes(app, frontdoor_factory, check)
    return app
