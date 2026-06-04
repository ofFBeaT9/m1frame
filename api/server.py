"""
api/server.py — FastAPI backend for m1frame + m1frame Studio.

Classic REST (unchanged):
  GET  /health                  → status, uptime, backend, can_run_live
  GET  /run/{run_id}            → poll status + recorded events
  GET  /runs                    → list all runs
  POST /wiki/ingest             → ingest text into the LLM Wiki
  GET  /wiki/query?q=...        → query the wiki (LLM, or keyword fallback w/o key)
  GET  /wiki/pages              → rich page list (title/type/tags/body)
  GET  /metrics                 → Prometheus text metrics
  GET/POST/DELETE /schedule     → scheduled investigation jobs

Studio additions:
  GET  /                        → serves m1frame-studio.html
  GET  /studio/demo_run.json    → the bundled demo fixture
  POST /run                     → start a run; mode=live|demo (auto-demo w/o key)
  GET  /run/{run_id}/events     → Server-Sent Events stream of pipeline progress
  POST /chat                    → SSE token stream, grounded in the wiki
  GET  /wiki/graph              → knowledge-graph nodes + links
  GET  /memories                → miras memory snapshot
  GET  /metrics.json            → structured per-pillar metrics
  GET  /config, PATCH /config   → one-click backend/model switch

Start:
  uvicorn api.server:app --host 0.0.0.0 --port 8080
  # or: python api/server.py
Requires: pip install fastapi uvicorn httpx pyyaml
"""
from __future__ import annotations

import asyncio
import datetime
import json
import os
import re
import sys
import threading
import time
import uuid
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# ── Optional FastAPI import ───────────────────────────────────────────────────
try:
    from fastapi import FastAPI, HTTPException, Body
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import FileResponse, PlainTextResponse, StreamingResponse
    from pydantic import BaseModel
    _FASTAPI = True
except ImportError:
    _FASTAPI = False
    BaseModel = object  # type: ignore[assignment,misc]

from agents.events import EventBus, make_emitter
from agents.logger import PillarLogger
from agents.metrics import get_metrics
from llm_client import LLMClient, load_config

STUDIO_HTML = ROOT / "m1frame-studio.html"
DEMO_FIXTURE = ROOT / "studio" / "demo_run.json"
LOCAL_BACKENDS = {"ollama", "vllm", "lmstudio"}
ALL_BACKENDS = ["claude", "openai", "openrouter", "nous", "novita", "nvidia_nim",
                "ollama", "vllm", "lmstudio"]
SSE_HEADERS = {"Cache-Control": "no-cache", "Connection": "keep-alive",
               "X-Accel-Buffering": "no"}


# ── Request models ────────────────────────────────────────────────────────────

if _FASTAPI:
    class RunRequest(BaseModel):
        goal: str
        backend: Optional[str] = None
        mode: Optional[str] = None          # live | demo (auto-demo without a key)
        speed: float = 1.0                  # demo replay speed multiplier
        skip_council: bool = False
        skip_wiki: bool = False
        skip_openplanter: bool = False
        parallel: bool = False
        self_critique: bool = False
        webhook_url: Optional[str] = None
        learn_skills: bool = True

    class SkillSuggestRequest(BaseModel):
        goal: str

    class ToolCallRequest(BaseModel):
        name: str
        args: dict = {}
        approve: bool = False               # required for tools marked dangerous

    class WikiIngestRequest(BaseModel):
        text: str
        topic_hint: str = ""
        source_name: str = ""

    class ScheduleJobRequest(BaseModel):
        job_id: str
        task: str
        interval_hours: float = 24.0

    class ChatRequest(BaseModel):
        message: str = ""
        messages: list[dict] = []           # [{role, content}, ...]
        ground: bool = True

    class ConfigPatch(BaseModel):
        backend: Optional[str] = None
        model: Optional[str] = None


# ── In-memory run store ───────────────────────────────────────────────────────

_RUNS: dict[str, dict] = {}
_MAX_RUNS = 200          # rolling window — bounds memory on long-lived servers


def _new_run(goal: str) -> str:
    # Evict oldest completed runs so _RUNS + their EventBus history stay bounded.
    while len(_RUNS) >= _MAX_RUNS:
        oldest = next(iter(_RUNS))
        _RUNS.pop(oldest, None)
    run_id = str(uuid.uuid4())[:8]
    _RUNS[run_id] = {
        "run_id": run_id, "goal": goal, "status": "queued", "mode": None,
        "started_at": datetime.datetime.utcnow().isoformat() + "Z",
        "finished_at": None, "score": None, "output": None, "error": None,
        "events": [], "bus": None, "task": None,
    }
    return run_id


def _public(run: dict) -> dict:
    """Run dict safe to JSON-serialize (drops the EventBus / task handles)."""
    return {k: v for k, v in run.items() if k not in ("bus", "task")}


# ── Disk-backed run store (survives restarts; replayable in Studio) ────────────
_RUNS_DIR = Path(__file__).resolve().parent.parent / "runs"


def _persist_run(run: dict) -> None:
    """Atomically write a completed run's full event trace to runs/<id>.json."""
    import json as _json
    import os as _os
    try:
        _RUNS_DIR.mkdir(parents=True, exist_ok=True)
        path = _RUNS_DIR / f"{run['run_id']}.json"
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(_json.dumps(_public(run)), encoding="utf-8")
        _os.replace(tmp, path)
    except Exception:  # noqa: BLE001 — persistence is best-effort, never fatal to a run
        pass


def _load_persisted_runs(limit: int = 50) -> int:
    """Load the most recent persisted runs into memory on startup."""
    import json as _json
    if not _RUNS_DIR.exists():
        return 0
    n = 0
    files = sorted(_RUNS_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    for f in files[:limit]:
        try:
            d = _json.loads(f.read_text(encoding="utf-8"))
            rid = d.get("run_id")
            if rid and rid not in _RUNS:
                d["bus"], d["task"] = None, None
                _RUNS[rid] = d
                n += 1
        except Exception:  # noqa: BLE001
            continue
    return n


def _can_run_live(cfg: dict, backend: Optional[str] = None) -> bool:
    b = backend or cfg.get("backend", "claude")
    if b in LOCAL_BACKENDS:
        return True
    env = cfg.get(b, {}).get("api_key_env")
    return bool(env and os.environ.get(env))


_MODEL_RE = re.compile(r"^[A-Za-z0-9._/-]{1,80}$")   # PATCH /config: no ':' (YAML), no spaces/newlines


def _persist_config(backend: Optional[str], model: Optional[str]) -> None:
    """Best-effort update of config.yaml that preserves comments (line walk)."""
    path = ROOT / "config.yaml"
    if not path.exists():
        return
    if model is not None and not _MODEL_RE.match(model):
        return  # ignore unsafe model strings — never write them to disk
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    target = backend
    if backend:
        for i, ln in enumerate(lines):
            if re.match(r"^backend:\s*", ln):
                lines[i] = re.sub(r"^(backend:\s*)\S+", rf"\g<1>{backend}", ln)
                break
    if model and target:
        in_block = False
        for i, ln in enumerate(lines):
            if re.match(rf"^{re.escape(target)}:\s*$", ln):
                in_block = True
                continue
            if in_block:
                if re.match(r"^\S", ln):           # left the block
                    break
                if re.match(r"^\s+model:\s*", ln):
                    indent = ln[:len(ln) - len(ln.lstrip())]
                    lines[i] = f"{indent}model: {model}\n"
                    break
    path.write_text("".join(lines), encoding="utf-8")


# ── App factory ───────────────────────────────────────────────────────────────

def create_app() -> "FastAPI":
    if not _FASTAPI:
        raise ImportError("Run: pip install fastapi uvicorn httpx")

    cfg = load_config()
    metrics = get_metrics()
    logger = PillarLogger()

    app = FastAPI(
        title="m1frame Studio API",
        description="Portable multi-agent AI OS — real-time REST + SSE interface",
        version="1.5.0", docs_url="/docs", redoc_url="/redoc",
    )
    app.add_middleware(
        CORSMiddleware, allow_origins=["*"], allow_methods=["*"],
        allow_headers=["*"], allow_credentials=False,
    )
    _load_persisted_runs()   # restore prior runs so Runs history survives restarts

    # ── UI ──────────────────────────────────────────────────────────────────────
    @app.get("/", include_in_schema=False)
    async def studio_index():
        if STUDIO_HTML.exists():
            return FileResponse(STUDIO_HTML, media_type="text/html")
        return PlainTextResponse("m1frame-studio.html not found. Build the UI first.", 404)

    @app.get("/studio/demo_run.json", include_in_schema=False)
    async def demo_fixture():
        if DEMO_FIXTURE.exists():
            return FileResponse(DEMO_FIXTURE, media_type="application/json")
        raise HTTPException(404, "demo_run.json not found — run: python studio/build_demo.py")

    # ── health / config ─────────────────────────────────────────────────────────
    @app.get("/health")
    async def health():
        return {
            "status": "ok", "version": "1.5.0",
            "backend": cfg.get("backend", "claude"),
            "can_run_live": _can_run_live(cfg),
            "uptime_s": metrics.uptime_s(), "runs_total": len(_RUNS),
            "ts": datetime.datetime.utcnow().isoformat() + "Z",
        }

    @app.get("/config")
    async def get_config():
        return {
            "backend": cfg.get("backend"),
            "model": cfg.get(cfg.get("backend", "claude"), {}).get("model"),
            "backends": ALL_BACKENDS,
            "models": {b: cfg.get(b, {}).get("model") for b in ALL_BACKENDS},
            "can_run_live": _can_run_live(cfg),
            "default_mode": "live" if _can_run_live(cfg) else "demo",
        }

    @app.patch("/config")
    async def patch_config(req: "ConfigPatch"):
        if req.backend:
            if req.backend not in ALL_BACKENDS:
                raise HTTPException(400, f"unknown backend '{req.backend}'")
            cfg["backend"] = req.backend
        if req.model:
            if not _MODEL_RE.match(req.model):
                raise HTTPException(400, "invalid model string")
            cfg.setdefault(cfg["backend"], {})["model"] = req.model
        _persist_config(req.backend, req.model)
        logger.info("api", "config_patched", backend=cfg.get("backend"))
        return await get_config()

    # ── runs ─────────────────────────────────────────────────────────────────────
    @app.post("/run", status_code=202)
    async def submit_run(req: "RunRequest"):
        run_id = _new_run(req.goal)
        run = _RUNS[run_id]
        bus = EventBus()
        run["bus"] = bus
        bus.subscribe_sync(lambda ev, r=run: r["events"].append(ev.to_dict()))

        mode = (req.mode or "").lower()
        want_live = mode == "live" or (mode != "demo" and _can_run_live(cfg, req.backend))
        if want_live and mode != "demo":
            run["mode"] = "live"
            run["task"] = asyncio.create_task(_run_live(run_id, req, bus))
        else:
            run["mode"] = "demo"
            run["task"] = asyncio.create_task(_replay_demo(run_id, bus, req.speed))
        logger.info("api", "run_started", run_id=run_id, mode=run["mode"], goal=req.goal[:80])
        return {"run_id": run_id, "mode": run["mode"], "events": f"/run/{run_id}/events"}

    @app.get("/run/{run_id}")
    async def get_run(run_id: str):
        if run_id not in _RUNS:
            raise HTTPException(404, "run_id not found")
        return _public(_RUNS[run_id])

    @app.get("/runs")
    async def list_runs():
        return [_public(r) for r in _RUNS.values()]

    @app.get("/runs/search")
    async def search_runs(q: str = ""):
        ql = (q or "").lower().strip()
        hits = []
        for r in _RUNS.values():
            hay = (r.get("goal", "") + " " + (r.get("output") or "")).lower()
            if not ql or ql in hay:
                hits.append(_public(r))
        return hits

    @app.get("/run/{run_id}/events", include_in_schema=False)
    async def run_events(run_id: str):
        if run_id not in _RUNS:
            raise HTTPException(404, "run_id not found")
        bus: EventBus = _RUNS[run_id]["bus"]

        async def gen():
            q = bus.subscribe_async()
            try:
                yield ": connected\n\n"   # prime the stream
                while True:
                    ev = await q.get()
                    yield f"data: {json.dumps(ev.to_dict())}\n\n"
                    if ev.type in ("done", "error"):
                        break
            finally:
                bus.unsubscribe_async(q)

        return StreamingResponse(gen(), media_type="text/event-stream", headers=SSE_HEADERS)

    # ── chat (SSE token stream) ───────────────────────────────────────────────────
    @app.post("/chat", include_in_schema=False)
    async def chat(req: "ChatRequest"):
        user_msg = req.message or (req.messages[-1]["content"] if req.messages else "")
        history = req.messages[:-1] if req.messages else []

        async def gen():
            from studio.data import keyword_answer
            # Ground in the knowledge graph
            citations, ctx = [], ""
            if req.ground:
                ka = keyword_answer(user_msg)
                ctx, citations = ka["answer"], ka["citations"]

            if not _can_run_live(cfg):
                # Demo mode: stream the grounded keyword answer with a typewriter feel
                reply = ctx or "Run a goal first to populate the knowledge graph."
                for tok in re.findall(r"\S+\s*", reply):
                    await asyncio.sleep(0.012)
                    yield f"data: {json.dumps({'type': 'token', 'chunk': tok})}\n\n"
                yield f"data: {json.dumps({'type': 'done', 'citations': citations})}\n\n"
                return

            # Live mode: stream real tokens, bridging the sync generator → async queue
            loop = asyncio.get_running_loop()
            q: asyncio.Queue = asyncio.Queue()
            stop = threading.Event()   # set when the client disconnects → stop producing
            system = ("You are m1frame, a deliberative multi-agent assistant. Answer crisply and "
                      "ground claims in the provided knowledge-graph context when present.")
            prompt = user_msg if not ctx else f"Knowledge-graph context:\n{ctx}\n\nQuestion: {user_msg}"

            def produce():
                try:
                    client = LLMClient()
                    for chunk in client.stream(prompt=prompt, system=system):
                        if stop.is_set():
                            return
                        loop.call_soon_threadsafe(q.put_nowait, ("token", chunk))
                except Exception as exc:
                    loop.call_soon_threadsafe(q.put_nowait, ("error", str(exc)))
                loop.call_soon_threadsafe(q.put_nowait, ("end", None))

            threading.Thread(target=produce, daemon=True).start()
            try:
                while True:
                    kind, val = await q.get()
                    if kind == "token":
                        yield f"data: {json.dumps({'type': 'token', 'chunk': val})}\n\n"
                    elif kind == "error":
                        yield f"data: {json.dumps({'type': 'error', 'message': val})}\n\n"
                        break
                    else:
                        yield f"data: {json.dumps({'type': 'done', 'citations': citations})}\n\n"
                        break
            finally:
                stop.set()   # client gone or done — let the producer thread exit

        return StreamingResponse(gen(), media_type="text/event-stream", headers=SSE_HEADERS)

    # ── wiki / graph / memories / metrics ─────────────────────────────────────────
    @app.post("/wiki/ingest")
    async def wiki_ingest(req: "WikiIngestRequest"):
        from agents.wiki import LLMWiki
        wiki = LLMWiki(LLMClient(), config=cfg.get("wiki"))
        page = wiki.ingest(req.text, topic_hint=req.topic_hint, source_name=req.source_name)
        return {"title": page.title, "filename": page.filename,
                "page_type": page.page_type, "tags": page.tags}

    @app.get("/wiki/query")
    async def wiki_query(q: str):
        if not _can_run_live(cfg):
            from studio.data import keyword_answer
            ka = keyword_answer(q)
            return {"question": q, "answer": ka["answer"], "citations": ka["citations"]}
        from agents.wiki import LLMWiki
        wiki = LLMWiki(LLMClient(), config=cfg.get("wiki"))
        return {"question": q, "answer": wiki.query(q)}

    @app.get("/wiki/pages")
    async def wiki_pages():
        from studio.data import wiki_pages as _wp
        return {"pages": _wp()}

    @app.get("/wiki/graph")
    async def wiki_graph():
        from studio.data import wiki_graph as _wg
        return _wg()

    @app.get("/memories")
    async def memories():
        from studio.data import load_memories
        return {"memories": load_memories()}

    # ── skills (council-vetted learning loop) ─────────────────────────────────────
    def _skill_lib():
        from agents.skills import SkillLibrary
        return SkillLibrary(threshold=float((cfg.get("council") or {}).get("consensus_threshold", 7.0)))

    @app.get("/skills")
    async def list_skills():
        from dataclasses import asdict
        lib = _skill_lib()
        return {"skills": [asdict(s) for s in lib.all()], "threshold": lib.threshold}

    @app.post("/skills/suggest")
    async def suggest_skills(req: "SkillSuggestRequest"):
        from dataclasses import asdict
        return {"skills": [asdict(s) for s in _skill_lib().suggest(req.goal)]}

    @app.delete("/skills/{skill_id}")
    async def remove_skill(skill_id: str):
        if not _skill_lib().remove(skill_id):
            raise HTTPException(404, "skill_id not found")
        return {"removed": skill_id}

    # ── messaging gateways (one router, many platforms) ───────────────────────────
    from gateways.router import GatewayRouter, OutboundMessage
    from gateways import adapters as _gw_adapters
    from gateways.handlers import grounded_answer

    def _gw_status():
        return {"backend": cfg.get("backend"), "pillars": 7,
                "can_run_live": _can_run_live(cfg), "runs": len(_RUNS)}
    _gw_router = GatewayRouter(handler=lambda m: grounded_answer(m.text), status_fn=_gw_status)

    @app.get("/gateway/status")
    async def gateway_status():
        return {"platforms": list(_gw_adapters.ADAPTERS.keys()) + ["webhook", "cli"],
                "status": _gw_status()}

    @app.post("/gateway/{platform}/webhook")
    async def gateway_webhook(platform: str, payload: dict = Body(default={})):
        # Slack URL-verification handshake
        if isinstance(payload, dict) and payload.get("type") == "url_verification":
            return {"challenge": payload.get("challenge")}
        msg = _gw_adapters.parse(platform, payload)
        if msg is None:
            return {"ok": True, "skipped": "no text"}
        text = (msg.text or "").strip()
        _tl = text.lower()
        if (_tl == "/run" or _tl.startswith("/run ")) and text[4:].strip():
            res = await submit_run(RunRequest(goal=text[4:].strip()))
            out = OutboundMessage(text=f"▸ started deliberation · run {res['run_id']} ({res['mode']}). "
                                       f"Watch it live in Studio.", channel=msg.channel, platform=platform)
        else:
            out = _gw_router.handle(msg)
        delivered = _gw_adapters.deliver(out)       # best-effort; needs platform creds
        return {"ok": True, "reply": out.text, "delivered": delivered,
                "payload": _gw_adapters.format_out(platform, out)}

    # ── model registry ────────────────────────────────────────────────────────────
    @app.get("/backends")
    async def list_backends():
        out = []
        for b in ALL_BACKENDS:
            bc = cfg.get(b, {}) or {}
            out.append({"name": b, "model": bc.get("model"), "local": b in LOCAL_BACKENDS,
                        "key_env": bc.get("api_key_env"), "ready": _can_run_live(cfg, b),
                        "active": b == cfg.get("backend")})
        return {"backends": out, "active": cfg.get("backend")}

    # ── tool surface ──────────────────────────────────────────────────────────────
    from tools import default_registry as _tool_registry

    @app.get("/tools")
    async def list_tools():
        return {"tools": _tool_registry().list()}

    @app.post("/tools/call")
    async def call_tool(req: "ToolCallRequest"):
        reg = _tool_registry()
        if req.name not in reg:
            raise HTTPException(404, f"unknown tool '{req.name}'")
        try:
            return {"name": req.name, "result": reg.call(req.name, req.args, approved=req.approve)}
        except PermissionError as e:
            raise HTTPException(403, str(e))   # dangerous tool needs approve=true
        except Exception as e:  # noqa: BLE001
            raise HTTPException(400, f"tool error: {e}")

    @app.get("/metrics", response_class=PlainTextResponse)
    async def prometheus_metrics():
        return metrics.to_prometheus()

    @app.get("/metrics.json")
    async def metrics_json():
        return {
            "uptime_s": metrics.uptime_s(),
            "runs_total": len(_RUNS),
            "pillars": {name: {"calls": m.calls, "errors": m.errors,
                               "avg_ms": round(m.avg_ms, 1), "total_ms": round(m.total_ms, 1),
                               "tokens": m.total_tokens}
                        for name, m in metrics.all_pillars().items()},
        }

    # ── scheduler ─────────────────────────────────────────────────────────────────
    @app.get("/schedule")
    async def list_schedule():
        from agents.scheduler import InvestigationScheduler
        from dataclasses import asdict
        sched = InvestigationScheduler(LLMClient())
        return {"jobs": [asdict(j) for j in sched.list_jobs()]}

    @app.post("/schedule", status_code=201)
    async def add_schedule(req: "ScheduleJobRequest"):
        from agents.scheduler import InvestigationScheduler
        from dataclasses import asdict
        sched = InvestigationScheduler(LLMClient())
        job = sched.add(req.job_id, req.task, req.interval_hours)
        return {"job": asdict(job)}

    @app.delete("/schedule/{job_id}")
    async def remove_schedule(job_id: str):
        from agents.scheduler import InvestigationScheduler
        sched = InvestigationScheduler(LLMClient())
        if not sched.remove(job_id):
            raise HTTPException(404, "job_id not found")
        return {"removed": job_id}

    # ── run executors (closures capture cfg/metrics/logger) ───────────────────────
    async def _run_live(run_id: str, req: "RunRequest", bus: EventBus) -> None:
        from scripts.run_workflow import run_workflow
        run = _RUNS[run_id]
        run["status"] = "running"
        t0 = time.time()
        emit = make_emitter(bus)
        loop = asyncio.get_running_loop()

        def work():
            return run_workflow(
                goal=req.goal, backend=req.backend,
                skip_council=req.skip_council, skip_wiki=req.skip_wiki,
                skip_openplanter=req.skip_openplanter, verbose=False,
                parallel=req.parallel, self_critique=req.self_critique, emit=emit,
                learn_skills=req.learn_skills,
            )

        try:
            results = await loop.run_in_executor(None, work)
            verdict = results.get("verdict")
            run["output"] = (verdict.approved_output if verdict and verdict.approved_output
                             else (results["state"].final_output() if results.get("state") else ""))[:8000]
            run["score"] = verdict.consensus_score if verdict else None
            run["status"] = "complete"
            logger.info("api", "run_complete", run_id=run_id)
        except Exception as exc:
            run["status"] = "error"
            run["error"] = str(exc)
            bus.emit("error", message=str(exc))
            bus.emit("done")
            logger.error("api", "run_failed", run_id=run_id, exc=str(exc))
        finally:
            run["finished_at"] = datetime.datetime.utcnow().isoformat() + "Z"
            metrics.record("pipeline", ms=(time.time() - t0) * 1000,
                           error=run["status"] == "error")
            _persist_run(run)  # survives restarts; replayable in Studio
            bus.close()  # idempotent — guarantees the SSE stream terminates
        if req.webhook_url and run["status"] == "complete":
            await _fire_webhook(req.webhook_url, _public(run))

    async def _replay_demo(run_id: str, bus: EventBus, speed: float) -> None:
        run = _RUNS[run_id]
        run["status"] = "running"
        speed = max(0.1, min(speed or 1.0, 20.0))
        try:
            fixture = json.loads(DEMO_FIXTURE.read_text(encoding="utf-8"))
            for row in fixture.get("events", []):
                row = dict(row)
                await asyncio.sleep(min(row.pop("delay_ms", 0) / 1000.0 / speed, 4.0))
                etype = row.pop("type")
                pillar = row.pop("pillar", None)
                row.pop("seq", None)
                bus.emit(etype, pillar=pillar, **row)
                if etype == "final":
                    run["output"] = row.get("output", "")[:8000]
                    run["score"] = row.get("score")
            run["status"] = "complete"
        except FileNotFoundError:
            bus.emit("error", message="demo_run.json missing — run python studio/build_demo.py")
            run["status"] = "error"
        finally:
            run["finished_at"] = datetime.datetime.utcnow().isoformat() + "Z"
            _persist_run(run)  # demo runs persist too, so Runs history is real
            bus.close()  # idempotent — terminates the SSE stream on every path

    return app


# ── webhook delivery ──────────────────────────────────────────────────────────

def _safe_webhook(url: str) -> bool:
    """Block SSRF on outbound webhooks. Delegates to the shared guard in
    agents.net so the API and the messaging gateways enforce one policy."""
    from agents.net import safe_url
    return safe_url(url)


async def _fire_webhook(url: str, payload: dict) -> None:
    if not _safe_webhook(url):
        return
    try:
        import httpx
        async with httpx.AsyncClient(timeout=10.0) as client:
            await client.post(url, json=payload)
    except Exception:
        pass


# ── Module-level app (uvicorn: api.server:app) ────────────────────────────────
if _FASTAPI:
    app = create_app()
else:
    app = None  # type: ignore[assignment]


if __name__ == "__main__":
    try:
        import uvicorn
        port = int(os.environ.get("PORT", load_config().get("api", {}).get("port", 8080)))
        # Bind localhost by default (the Studio is a local dev tool with an
        # unauthenticated config-write endpoint). Override with HOST=0.0.0.0.
        host = os.environ.get("HOST", "127.0.0.1")
        uvicorn.run("api.server:app", host=host, port=port, reload=False, log_level="info")
    except ImportError:
        print("Run: pip install fastapi uvicorn httpx")
