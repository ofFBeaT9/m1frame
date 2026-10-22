"""Background pipeline runs for remote hosts.

A full m1frame run can take minutes, longer than many hosts wait for one tool
call. m1frame_start launches it in the background and returns a job id at once;
m1frame_result polls it. Finished jobs persist under runs/remote_jobs/.
"""
from __future__ import annotations

import json
import threading
import time
import uuid
from collections.abc import Callable
from pathlib import Path

MAX_ACTIVE = 2


class JobStore:
    def __init__(self, directory: str | Path, runner: Callable[[str, str], str]) -> None:
        self.dir = Path(directory)
        self.runner = runner          # (goal_or_prompt, kind) -> markdown result
        self._jobs: dict[str, dict] = {}
        self._lock = threading.Lock()
        self._threads: list[threading.Thread] = []

    def _file(self, job_id: str) -> Path:
        return self.dir / f"{job_id}.json"

    def start(self, text: str, kind: str = "run") -> dict:
        with self._lock:
            active = sum(1 for j in self._jobs.values() if j["status"] == "running")
            if active >= MAX_ACTIVE:
                return {"error": f"{active} jobs already running; wait for one to finish"}
            job_id = uuid.uuid4().hex[:12]
            job = {"id": job_id, "kind": kind, "input": text[:500], "status": "running",
                   "started": time.time(), "result": None}
            self._jobs[job_id] = job
        thread = threading.Thread(target=self._work, args=(job_id, text, kind), daemon=True)
        self._threads = [t for t in self._threads if t.is_alive()] + [thread]
        thread.start()
        return {"job_id": job_id, "status": "running",
                "next": "call m1frame_result with this job_id in about a minute"}

    def _work(self, job_id: str, text: str, kind: str) -> None:
        final = dict(self._jobs[job_id])
        try:
            final["result"], final["status"] = self.runner(text, kind), "done"
        except Exception as exc:  # noqa: BLE001 — report, never crash the server
            final["result"], final["status"] = f"failed: {exc}", "failed"
        final["finished"] = time.time()
        try:   # persist first, then publish, so a finished job is always readable
            self.dir.mkdir(parents=True, exist_ok=True)
            self._file(job_id).write_text(json.dumps(final, default=str), encoding="utf-8")
        except OSError:
            pass
        self._jobs[job_id] = final

    def wait_all(self, timeout: float = 10.0) -> None:
        for thread in list(self._threads):
            thread.join(timeout)

    def get(self, job_id: str) -> dict:
        job = self._jobs.get(job_id)
        if job is None and job_id.isalnum() and self._file(job_id).is_file():
            job = json.loads(self._file(job_id).read_text(encoding="utf-8"))
        if job is None:
            return {"error": f"unknown job '{job_id}'"}
        out = dict(job)
        out["elapsed_s"] = int((job.get("finished") or time.time()) - job["started"])
        return out
