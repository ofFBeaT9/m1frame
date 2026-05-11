"""
agents/scheduler.py — Autonomous investigation scheduler (cron mode).

Schedules recurring OpenPlanter investigation runs at configurable intervals.
Uses threading.Timer for lightweight, zero-dependency scheduling. Jobs persist
across process restarts via workspace/schedule.json.

Usage:
    from agents.scheduler import InvestigationScheduler

    scheduler = InvestigationScheduler(llm_client, workspace="workspace")
    scheduler.add("daily_vendors", "Cross-reference vendor payments vs lobbying", interval_hours=24)
    scheduler.start()          # non-blocking; fires in background threads
    scheduler.stop()           # cancel all pending timers

    # One-shot manual run:
    summary = scheduler.run_now("daily_vendors")
"""
from __future__ import annotations

import json
import threading
import datetime
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Callable, Optional


@dataclass
class ScheduledJob:
    job_id: str
    task: str
    interval_hours: float
    enabled: bool = True
    last_run: Optional[str] = None           # ISO-8601 UTC datetime
    next_run: Optional[str] = None           # ISO-8601 UTC datetime
    run_count: int = 0
    last_result_summary: str = ""


class InvestigationScheduler:
    """
    Lightweight scheduler for autonomous OpenPlanter investigation runs.

    Jobs persist to workspace/schedule.json so they survive process restarts.
    Each job fires its own daemon threading.Timer — no external dependencies.

    Callbacks:
      on_complete(job_id: str, summary: str) is called after each run.
    """

    _MANIFEST = "schedule.json"

    def __init__(
        self,
        llm_client,
        workspace: str = "workspace",
        on_complete: Optional[Callable[[str, str], None]] = None,
    ) -> None:
        self.llm = llm_client
        self.workspace = Path(workspace)
        self.workspace.mkdir(parents=True, exist_ok=True)
        self.on_complete = on_complete
        self._jobs: dict[str, ScheduledJob] = {}
        self._timers: dict[str, threading.Timer] = {}
        self._lock = threading.Lock()
        self._load()

    # ── Public API ────────────────────────────────────────────────────────────

    def add(self, job_id: str, task: str, interval_hours: float = 24.0) -> ScheduledJob:
        """Register or update a recurring investigation job."""
        with self._lock:
            job = ScheduledJob(
                job_id=job_id,
                task=task,
                interval_hours=interval_hours,
                next_run=_iso_after(interval_hours),
            )
            self._jobs[job_id] = job
            self._save()
        return job

    def remove(self, job_id: str) -> bool:
        """Remove a job and cancel its pending timer. Returns True if it existed."""
        with self._lock:
            timer = self._timers.pop(job_id, None)
            if timer:
                timer.cancel()
            removed = self._jobs.pop(job_id, None) is not None
            if removed:
                self._save()
        return removed

    def enable(self, job_id: str) -> None:
        with self._lock:
            if job_id in self._jobs:
                self._jobs[job_id].enabled = True
                self._save()

    def disable(self, job_id: str) -> None:
        with self._lock:
            if job_id in self._jobs:
                self._jobs[job_id].enabled = False
                self._save()

    def start(self) -> None:
        """Arm timers for all enabled jobs based on their next_run time."""
        with self._lock:
            for job in list(self._jobs.values()):
                if job.enabled:
                    self._arm(job)

    def stop(self) -> None:
        """Cancel all pending timers without removing job definitions."""
        with self._lock:
            for timer in self._timers.values():
                timer.cancel()
            self._timers.clear()

    def run_now(self, job_id: str) -> str:
        """Immediately execute a job and return its result summary."""
        with self._lock:
            job = self._jobs.get(job_id)
        if job is None:
            raise KeyError(f"Unknown job: {job_id!r}")
        return self._execute(job)

    def list_jobs(self) -> list[ScheduledJob]:
        with self._lock:
            return list(self._jobs.values())

    def get_job(self, job_id: str) -> Optional[ScheduledJob]:
        with self._lock:
            return self._jobs.get(job_id)

    # ── Private — timer lifecycle ─────────────────────────────────────────────

    def _arm(self, job: ScheduledJob) -> None:
        delay = _seconds_until(job.next_run)
        timer = threading.Timer(delay, self._fire, args=[job.job_id])
        timer.daemon = True
        timer.name = f"m1frame-sched-{job.job_id}"
        timer.start()
        self._timers[job.job_id] = timer

    def _fire(self, job_id: str) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
        if job is None or not job.enabled:
            return

        summary = self._execute(job)

        with self._lock:
            job.last_result_summary = summary[:500]
            job.last_run = _utc_now_iso()
            job.next_run = _iso_after(job.interval_hours)
            job.run_count += 1
            self._save()
            if job.enabled:
                self._arm(job)

    def _execute(self, job: ScheduledJob) -> str:
        from agents.openplanter import OpenPlanterAgent
        planter = OpenPlanterAgent(self.llm, workspace=str(self.workspace))
        try:
            result = planter.investigate(job.task)
            summary = result.report()
        except Exception as exc:
            summary = f"[ERROR] {exc}"
        out = self.workspace / f"{job.job_id}_latest.md"
        out.write_text(f"# {job.task}\n\nRun: {_utc_now_iso()}\n\n{summary}", encoding="utf-8")
        if self.on_complete:
            try:
                self.on_complete(job.job_id, summary)
            except Exception:
                pass
        return summary

    # ── Persistence ───────────────────────────────────────────────────────────

    def _load(self) -> None:
        manifest = self.workspace / self._MANIFEST
        if not manifest.exists():
            return
        try:
            data = json.loads(manifest.read_text(encoding="utf-8"))
            for jd in data.get("jobs", []):
                self._jobs[jd["job_id"]] = ScheduledJob(**jd)
        except Exception:
            pass

    def _save(self) -> None:
        manifest = self.workspace / self._MANIFEST
        data = {"jobs": [asdict(j) for j in self._jobs.values()]}
        manifest.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def __repr__(self) -> str:
        return f"<InvestigationScheduler jobs={len(self._jobs)} workspace={self.workspace}>"


# ── Helpers ───────────────────────────────────────────────────────────────────

def _utc_now_iso() -> str:
    return datetime.datetime.utcnow().isoformat() + "Z"


def _iso_after(hours: float) -> str:
    dt = datetime.datetime.utcnow() + datetime.timedelta(hours=hours)
    return dt.isoformat() + "Z"


def _seconds_until(iso_str: Optional[str]) -> float:
    if not iso_str:
        return 0.0
    try:
        target = datetime.datetime.fromisoformat(iso_str.rstrip("Z"))
        delta = (target - datetime.datetime.utcnow()).total_seconds()
        return max(delta, 0.0)
    except (ValueError, TypeError):
        return 0.0
