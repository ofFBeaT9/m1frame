"""
api/server.py — FastAPI REST API for m1frame.

Endpoints:
  GET  /health                  → status, uptime, backend
  POST /run                     → submit a goal; returns run_id (async)
  GET  /run/{run_id}            → poll status + output
  GET  /runs                    → list all runs
  POST /wiki/ingest             → ingest text into LLM Wiki
  GET  /wiki/query?q=...        → query the wiki
  GET  /wiki/pages              → list all wiki pages
  GET  /metrics                 → Prometheus text metrics
  GET  /schedule                → list scheduled investigation jobs
  POST /schedule                → add a scheduled job
  DELETE /schedule/{job_id}     → remove a job

Webhook:
  Include "webhook_url" in POST /run — the server POSTs the full result dict
  to that URL when the pipeline finishes (best-effort, non-blocking).

Start:
  python api/server.py
  # or:
  uvicorn api.server:app --host 0.0.0.0 --port 8080 --reload

Requires: pip install fastapi uvicorn httpx
"""
from __future__ import annotations

import sys
import time
import uuid
import datetime
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

# ── Optional FastAPI import ───────────────────────────────────────────────────
try:
    from fastapi import BackgroundTasks, FastAPI, HTTPException
    from fastapi.responses import PlainTextResponse
    from pydantic import BaseModel
    _FASTAPI = True
except ImportError:
    _FASTAPI = False
    BaseModel = object  # type: ignore[assignment,misc]

from agents.metrics import get_metrics
from agents.logger import PillarLogger
from llm_client import LLMClient, load_config


# ── Request / response models ─────────────────────────────────────────────────

if _FASTAPI:
    class RunRequest(BaseModel):
        goal: str
        backend: Optional[str] = None
        skip_council: bool = False
        skip_wiki: bool = False
        skip_openplanter: bool = False
        webhook_url: Optional[str] = None

    class WikiIngestRequest(BaseModel):
        text: str
        topic_hint: str = ""
        source_name: str = ""

    class ScheduleJobRequest(BaseModel):
        job_id: str
        task: str
        interval_hours: float = 24.0


# ── In-memory run store ───────────────────────────────────────────────────────

_RUNS: dict[str, dict] = {}


def _new_run(goal: str) -> str:
    run_id = str(uuid.uuid4())[:8]
    _RUNS[run_id] = {
        "run_id": run_id,
        "goal": goal,
        "status": "queued",
        "started_at": None,
        "finished_at": None,
        "output": None,
        "error": None,
    }
    return run_id


# ── App factory ───────────────────────────────────────────────────────────────

def create_app() -> "FastAPI":
    if not _FASTAPI:
        raise ImportError("Run: pip install fastapi uvicorn httpx")

    cfg = load_config()
    metrics = get_metrics()
    _logger = PillarLogger()

    app = FastAPI(
        title="m1frame API",
        description="Portable multi-agent AI OS — REST interface",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # ── /health ───────────────────────────────────────────────────────────────
    @app.get("/health")
    async def health():
        return {
            "status": "ok",
            "version": "1.0.0",
            "backend": cfg.get("backend", "claude"),
            "uptime_s": metrics.uptime_s(),
            "runs_total": len(_RUNS),
            "ts": datetime.datetime.utcnow().isoformat() + "Z",
        }

    # ── POST /run ─────────────────────────────────────────────────────────────
    @app.post("/run", status_code=202)
    async def submit_run(req: RunRequest, background_tasks: BackgroundTasks):
        run_id = _new_run(req.goal)
        _logger.info("api", "run_queued", run_id=run_id, goal=req.goal[:80])
        background_tasks.add_task(_execute_run, run_id, req, cfg, metrics, _logger)
        return {"run_id": run_id, "status": "queued", "poll": f"/run/{run_id}"}

    # ── GET /run/{run_id} ─────────────────────────────────────────────────────
    @app.get("/run/{run_id}")
    async def get_run(run_id: str):
        if run_id not in _RUNS:
            raise HTTPException(status_code=404, detail="run_id not found")
        return _RUNS[run_id]

    # ── GET /runs ─────────────────────────────────────────────────────────────
    @app.get("/runs")
    async def list_runs():
        return list(_RUNS.values())

    # ── POST /wiki/ingest ─────────────────────────────────────────────────────
    @app.post("/wiki/ingest")
    async def wiki_ingest(req: WikiIngestRequest):
        from agents.wiki import LLMWiki
        client = LLMClient()
        wiki = LLMWiki(client, config=cfg.get("wiki"))
        page = wiki.ingest(req.text, topic_hint=req.topic_hint, source_name=req.source_name)
        return {
            "title": page.title,
            "filename": page.filename,
            "page_type": page.page_type,
            "tags": page.tags,
        }

    # ── GET /wiki/query ───────────────────────────────────────────────────────
    @app.get("/wiki/query")
    async def wiki_query(q: str):
        from agents.wiki import LLMWiki
        client = LLMClient()
        wiki = LLMWiki(client, config=cfg.get("wiki"))
        answer = wiki.query(q)
        return {"question": q, "answer": answer}

    # ── GET /wiki/pages ───────────────────────────────────────────────────────
    @app.get("/wiki/pages")
    async def wiki_pages():
        from agents.wiki import LLMWiki
        client = LLMClient()
        wiki = LLMWiki(client, config=cfg.get("wiki"))
        return {"pages": wiki.list_pages()}

    # ── GET /metrics ──────────────────────────────────────────────────────────
    @app.get("/metrics", response_class=PlainTextResponse)
    async def prometheus_metrics():
        return metrics.to_prometheus()

    # ── GET /schedule ─────────────────────────────────────────────────────────
    @app.get("/schedule")
    async def list_schedule():
        from agents.scheduler import InvestigationScheduler
        from dataclasses import asdict
        client = LLMClient()
        sched = InvestigationScheduler(client)
        return {"jobs": [asdict(j) for j in sched.list_jobs()]}

    # ── POST /schedule ────────────────────────────────────────────────────────
    @app.post("/schedule", status_code=201)
    async def add_schedule(req: ScheduleJobRequest):
        from agents.scheduler import InvestigationScheduler
        from dataclasses import asdict
        client = LLMClient()
        sched = InvestigationScheduler(client)
        job = sched.add(req.job_id, req.task, req.interval_hours)
        return {"job": asdict(job)}

    # ── DELETE /schedule/{job_id} ─────────────────────────────────────────────
    @app.delete("/schedule/{job_id}")
    async def remove_schedule(job_id: str):
        from agents.scheduler import InvestigationScheduler
        client = LLMClient()
        sched = InvestigationScheduler(client)
        if not sched.remove(job_id):
            raise HTTPException(status_code=404, detail="job_id not found")
        return {"removed": job_id}

    return app


# ── Background pipeline execution ─────────────────────────────────────────────

async def _execute_run(
    run_id: str,
    req: "RunRequest",
    cfg: dict,
    metrics: "MetricsCollector",
    logger: "PillarLogger",
) -> None:
    from scripts.run_workflow import run_workflow
    _RUNS[run_id]["status"] = "running"
    _RUNS[run_id]["started_at"] = datetime.datetime.utcnow().isoformat() + "Z"
    t0 = time.time()

    try:
        results = run_workflow(
            goal=req.goal,
            backend=req.backend,
            skip_council=req.skip_council,
            skip_wiki=req.skip_wiki,
            skip_openplanter=req.skip_openplanter,
            verbose=False,
        )
        output = ""
        verdict = results.get("verdict")
        if verdict and getattr(verdict, "approved_output", ""):
            output = verdict.approved_output
        elif results.get("state"):
            output = results["state"].final_output()

        _RUNS[run_id]["status"] = "complete"
        _RUNS[run_id]["output"] = output[:8000]
        logger.info("api", "run_complete", run_id=run_id)
    except Exception as exc:
        _RUNS[run_id]["status"] = "error"
        _RUNS[run_id]["error"] = str(exc)
        logger.error("api", "run_failed", run_id=run_id, exc=str(exc))
    finally:
        _RUNS[run_id]["finished_at"] = datetime.datetime.utcnow().isoformat() + "Z"
        ms = (time.time() - t0) * 1000
        metrics.record("pipeline", ms=ms, error=_RUNS[run_id]["status"] == "error")

    if req.webhook_url and _RUNS[run_id]["status"] == "complete":
        await _fire_webhook(req.webhook_url, _RUNS[run_id])


async def _fire_webhook(url: str, payload: dict) -> None:
    """POST run result to a webhook URL — non-fatal on any error."""
    try:
        import httpx
        async with httpx.AsyncClient(timeout=10.0) as client:
            await client.post(url, json=payload)
    except Exception:
        pass


# ── Create the module-level app instance ──────────────────────────────────────
# Imported by uvicorn: `uvicorn api.server:app`
if _FASTAPI:
    app = create_app()
else:
    app = None  # type: ignore[assignment]


# ── CLI launcher ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    try:
        import uvicorn
        uvicorn.run("api.server:app", host="0.0.0.0", port=8080, reload=False, log_level="info")
    except ImportError:
        print("Run: pip install fastapi uvicorn httpx")
