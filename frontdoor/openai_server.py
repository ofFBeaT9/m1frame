"""OpenAI-compatible endpoint: make m1frame look like a *model* to any app.

Anything that lets you set a custom OpenAI base URL (Open WebUI, LibreChat, LM Studio
chat, Msty, Jan, Cursor/Continue/Cline, n8n, your own scripts, the openai SDK) can now
send prompts into m1frame, and every prompt goes through FrontDoor.

    python -m frontdoor serve --port 8765
    base_url = http://localhost:8765/v1     api_key = $M1FRAME_PROXY_KEY (or anything if unset)
    model    = m1frame (agent decides) | m1frame-full (always full pipeline) | m1frame-chat (no tools)
"""

import json
import os
import time
import uuid

MODELS = {"m1frame": "auto", "m1frame-full": "full", "m1frame-chat": "chat"}


def _text(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):  # OpenAI content parts
        return "\n".join(p.get("text", "") for p in content if isinstance(p, dict) and p.get("type") == "text")
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
        prompt = "Client instructions:\n" + "\n".join(b for b in system_bits if b) + "\n\nRequest:\n" + prompt
    history = [{"role": m["role"], "content": _text(m.get("content"))} for m in turns[:-1]]
    return prompt, history


def build_app(frontdoor_factory=None):
    from fastapi import FastAPI, HTTPException, Request
    from fastapi.responses import JSONResponse, StreamingResponse

    if frontdoor_factory is None:
        def frontdoor_factory():
            from frontdoor.agent import FrontDoor
            from llm_client import LLMClient
            return FrontDoor(LLMClient())   # dangerous tools stay denied over HTTP
    app = FastAPI(title="m1frame OpenAI-compatible front door")
    key = os.environ.get("M1FRAME_PROXY_KEY")

    def _auth(request: Request):
        if key and request.headers.get("authorization", "") != f"Bearer {key}":
            raise HTTPException(401, "invalid api key")

    @app.get("/v1/models")
    def models(request: Request):
        _auth(request)
        now = int(time.time())
        return {"object": "list", "data": [
            {"id": m, "object": "model", "created": now, "owned_by": "m1frame"} for m in MODELS]}

    @app.post("/v1/chat/completions")
    async def chat(request: Request):
        _auth(request)
        body = await request.json()
        mode = MODELS.get(body.get("model", "m1frame"), "auto")
        try:
            prompt, history = split_messages(body.get("messages") or [])
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc
        result = frontdoor_factory().handle(prompt, history=history, mode=mode)
        answer = result.answer
        if body.get("m1frame_receipt", True):
            answer += f"\n\n---\n_m1frame: {result.receipt()}_"
        cid, now, model = f"chatcmpl-{uuid.uuid4().hex[:24]}", int(time.time()), body.get("model", "m1frame")

        if body.get("stream"):
            def gen():
                base = {"id": cid, "object": "chat.completion.chunk", "created": now, "model": model}
                yield "data: " + json.dumps({**base, "choices": [{"index": 0, "delta": {"role": "assistant",
                                             "content": answer}, "finish_reason": None}]}) + "\n\n"
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

    return app
