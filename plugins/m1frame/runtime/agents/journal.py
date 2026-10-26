"""Run journal: every pipeline run is visible in Studio, wherever it started.

Studio records the runs it starts itself. Runs started elsewhere (Claude through
MCP, the remote server on a Pi, the /v1 API, Telegram, the command line) used to
leave nothing Studio could show. The journal writes those runs to disk as they
happen, in the same event format Studio streams:

    runs/live/<run_id>.meta.json      status, goal, source (while running)
    runs/live/<run_id>.events.jsonl   one event per line, appended as emitted
    runs/<run_id>.json                the finished run, Studio's persisted format

Studio lists both and tails the .jsonl of a running run, so you can watch a run
that Claude started from your phone. Writing is best-effort: a journal failure
never affects the run. Disable with M1FRAME_JOURNAL=0.
"""
from __future__ import annotations

import datetime
import json
import os
import threading
from pathlib import Path

from agents.events import Event

ROOT = Path(__file__).resolve().parent.parent


def runs_dir() -> Path:
    return Path(os.environ.get("M1FRAME_RUNS_DIR") or ROOT / "runs")


def enabled() -> bool:
    return os.environ.get("M1FRAME_JOURNAL", "1").lower() not in {"0", "false", "no", "off"}


def _now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def _atomic_write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(payload, default=str), encoding="utf-8")
    os.replace(tmp, path)


class RunJournal:
    def __init__(self, run_id: str, goal: str, source: str | None = None) -> None:
        self.run_id = run_id[:8]
        self.goal = goal
        self.source = source or os.environ.get("M1FRAME_RUN_SOURCE") or "pipeline"
        self.started_at = _now()
        self.events: list[dict] = []
        self.final: dict = {}
        self._lock = threading.Lock()
        base = runs_dir()
        self.meta_path = base / "live" / f"{self.run_id}.meta.json"
        self.events_path = base / "live" / f"{self.run_id}.events.jsonl"
        self.final_path = base / f"{self.run_id}.json"
        self._ok = True
        try:
            _atomic_write(self.meta_path, self._record("running"))
            self.events_path.write_text("", encoding="utf-8")
        except OSError:
            self._ok = False

    def _record(self, status: str) -> dict:
        return {"run_id": self.run_id, "goal": self.goal, "status": status, "mode": "live",
                "source": self.source, "started_at": self.started_at,
                "finished_at": None, "score": self.final.get("score"),
                "output": self.final.get("output"), "approved": self.final.get("passed"),
                "error": None}

    def emit(self, event: str, **data) -> None:
        pillar = data.pop("pillar", None)
        if event == "final":
            self.final = {k: data.get(k) for k in ("output", "score", "passed")}
        wire = Event(type=event, data=data, pillar=pillar).to_dict()
        with self._lock:
            self.events.append(wire)
            if not self._ok:
                return
            try:
                with self.events_path.open("a", encoding="utf-8") as f:
                    f.write(json.dumps(wire, default=str) + "\n")
            except OSError:
                self._ok = False

    def finish(self, result: dict | None = None, error: BaseException | None = None) -> None:
        if error is not None:
            status = "error"
        else:
            approved = (result or {}).get("approved", self.final.get("passed"))
            status = "needs_review" if approved is False else "complete"
        record = self._record(status)
        record.update(finished_at=_now(), events=list(self.events),
                      error=str(error)[:500] if error is not None else None)
        if result:
            verdict = result.get("verdict")
            record["output"] = result.get("output", record["output"])
            record["score"] = getattr(verdict, "consensus_score", record["score"])
            record["approved"] = result.get("approved", record["approved"])
            record["receipt"] = result.get("receipt")
        if not any(e.get("type") in {"done", "error"} for e in self.events[-2:]):
            record["events"].append(Event(type="error" if error else "done",
                                          data={"message": str(error)} if error else {}).to_dict())
        try:
            _atomic_write(self.final_path, record)
            for path in (self.meta_path, self.events_path):
                path.unlink(missing_ok=True)
        except OSError:
            pass


# ── Readers (used by Studio) ──────────────────────────────────────────────────

def read_live(run_id: str) -> dict | None:
    """A running external run with its events so far, or None."""
    base = runs_dir() / "live"
    meta = base / f"{run_id}.meta.json"
    if not run_id.isalnum() or not meta.is_file():
        return None
    try:
        run = json.loads(meta.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    run["events"] = read_events(run_id)[0]
    return run


def read_events(run_id: str, offset: int = 0) -> tuple[list[dict], int]:
    """Events appended after byte `offset`; returns (events, new_offset)."""
    path = runs_dir() / "live" / f"{run_id}.events.jsonl"
    if not run_id.isalnum() or not path.is_file():
        return [], offset
    try:
        with path.open("rb") as f:
            f.seek(offset)
            chunk = f.read()
    except OSError:
        return [], offset
    end = chunk.rfind(b"\n") + 1          # only whole lines; a half-written one waits
    events = []
    for line in chunk[:end].splitlines():
        try:
            events.append(json.loads(line))
        except ValueError:
            continue
    return events, offset + end


def read_final(run_id: str) -> dict | None:
    path = runs_dir() / f"{run_id}.json"
    if not run_id.isalnum() or not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def list_live() -> list[str]:
    base = runs_dir() / "live"
    if not base.is_dir():
        return []
    return [p.name.split(".")[0] for p in base.glob("*.meta.json")]
