"""
agents/logger.py — Structured JSON logging with pillar trace IDs.

Every workflow run gets a unique 8-char trace_id. Each pillar event is written
as a JSON line to logs/m1frame_YYYY-MM-DD.jsonl so the full run is replayable
and machine-parseable (Grafana Loki, jq, etc.).

Usage:
    logger = PillarLogger()
    logger.info("bmad", "plan_complete", stories=3)
    logger.timing("miras", ms=320.5, story_id=2)
    logger.error("council", "parse_failed", exc="JSONDecodeError")
"""
from __future__ import annotations

import json
import time
import uuid
import datetime
from pathlib import Path
from typing import Any, Optional


class PillarLogger:
    """
    Append-only structured JSON logger for a single m1frame workflow run.

    Each call writes one JSON object to a .jsonl file. The file is safe to
    tail -f and grep. One file per calendar day; all runs share it via the
    trace_id field.
    """

    def __init__(
        self,
        log_dir: str = "logs",
        trace_id: Optional[str] = None,
    ) -> None:
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.trace_id = trace_id or str(uuid.uuid4())[:8]
        self._log_file = self.log_dir / f"m1frame_{datetime.date.today().isoformat()}.jsonl"
        self._run_start = time.monotonic()

    # ── Log-level helpers ─────────────────────────────────────────────────────

    def info(self, pillar: str, event: str, **kwargs: Any) -> None:
        self._write(pillar, event, "info", **kwargs)

    def error(self, pillar: str, event: str, **kwargs: Any) -> None:
        self._write(pillar, event, "error", **kwargs)

    def warn(self, pillar: str, event: str, **kwargs: Any) -> None:
        self._write(pillar, event, "warn", **kwargs)

    def timing(self, pillar: str, ms: float, **kwargs: Any) -> None:
        self._write(pillar, "timing", "metric", latency_ms=round(ms, 2), **kwargs)

    # ── Read-back ─────────────────────────────────────────────────────────────

    def read(self, n: int = 50) -> list[dict]:
        """Return the last n log entries for today's log file."""
        if not self._log_file.exists():
            return []
        lines = self._log_file.read_text(encoding="utf-8").strip().splitlines()
        parsed = []
        for line in lines[-n:]:
            try:
                parsed.append(json.loads(line))
            except json.JSONDecodeError:
                pass
        return parsed

    def read_trace(self) -> list[dict]:
        """Return all entries for this run's trace_id."""
        return [e for e in self.read(n=1000) if e.get("trace") == self.trace_id]

    # ── Private ───────────────────────────────────────────────────────────────

    def _write(self, pillar: str, event: str, level: str, **kwargs: Any) -> None:
        entry: dict[str, Any] = {
            "ts": datetime.datetime.utcnow().isoformat() + "Z",
            "trace": self.trace_id,
            "pillar": pillar,
            "event": event,
            "level": level,
            "elapsed_s": round(time.monotonic() - self._run_start, 3),
        }
        entry.update(kwargs)
        with self._log_file.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, default=str) + "\n")

    def __repr__(self) -> str:
        return f"<PillarLogger trace={self.trace_id} log={self._log_file}>"
