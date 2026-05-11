"""
agents/metrics.py — Prometheus-compatible metrics for the m1frame pipeline.

Thread-safe collector that tracks latency, call counts, errors, and token usage
per pillar. Exposes a /metrics HTTP endpoint in Prometheus text format so any
Grafana or alerting stack can scrape it.

Usage:
    mc = MetricsCollector()
    mc.expose_http(port=9090)       # background thread, non-blocking

    with mc.timer("bmad"):
        result = bmad.plan(goal)

    print(mc.to_prometheus())

Module singleton:
    from agents.metrics import get_metrics
    get_metrics().record("council", ms=420)
"""
from __future__ import annotations

import time
import threading
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Dict, Generator, Optional


# ── Per-pillar data ───────────────────────────────────────────────────────────

@dataclass
class PillarMetrics:
    pillar: str
    calls: int = 0
    errors: int = 0
    total_ms: float = 0.0
    tokens_in: int = 0
    tokens_out: int = 0

    @property
    def avg_ms(self) -> float:
        return self.total_ms / max(self.calls, 1)

    @property
    def error_rate(self) -> float:
        return self.errors / max(self.calls, 1)

    @property
    def total_tokens(self) -> int:
        return self.tokens_in + self.tokens_out


# ── Collector ─────────────────────────────────────────────────────────────────

class MetricsCollector:
    """
    Thread-safe metrics collector for all m1frame pillars.

    Records:
      - call counts and error counts per pillar
      - total + average latency per pillar
      - token usage (in + out) per pillar

    Exposes Prometheus text format via expose_http().
    """

    def __init__(self) -> None:
        self._pillars: Dict[str, PillarMetrics] = {}
        self._lock = threading.Lock()
        self._start = time.time()
        self._http_server: Optional[object] = None

    # ── Recording API ─────────────────────────────────────────────────────────

    def record(
        self,
        pillar: str,
        ms: float,
        error: bool = False,
        tokens_in: int = 0,
        tokens_out: int = 0,
    ) -> None:
        with self._lock:
            if pillar not in self._pillars:
                self._pillars[pillar] = PillarMetrics(pillar=pillar)
            m = self._pillars[pillar]
            m.calls += 1
            m.total_ms += ms
            m.tokens_in += tokens_in
            m.tokens_out += tokens_out
            if error:
                m.errors += 1

    @contextmanager
    def timer(self, pillar: str) -> Generator[None, None, None]:
        """Context manager that records timing automatically."""
        t0 = time.perf_counter()
        error = False
        try:
            yield
        except Exception:
            error = True
            raise
        finally:
            ms = (time.perf_counter() - t0) * 1000
            self.record(pillar, ms=ms, error=error)

    # ── Query API ─────────────────────────────────────────────────────────────

    def get(self, pillar: str) -> PillarMetrics:
        with self._lock:
            return self._pillars.get(pillar, PillarMetrics(pillar=pillar))

    def all_pillars(self) -> Dict[str, PillarMetrics]:
        with self._lock:
            return dict(self._pillars)

    def uptime_s(self) -> float:
        return round(time.time() - self._start, 1)

    # ── Prometheus output ─────────────────────────────────────────────────────

    def to_prometheus(self) -> str:
        lines = [
            "# HELP m1frame_uptime_seconds Time since collector started",
            "# TYPE m1frame_uptime_seconds gauge",
            f"m1frame_uptime_seconds {self.uptime_s()}",
            "",
            "# HELP m1frame_pillar_calls_total Total LLM calls per pillar",
            "# TYPE m1frame_pillar_calls_total counter",
        ]
        with self._lock:
            pillars = dict(self._pillars)

        for name, m in pillars.items():
            lines.append(f'm1frame_pillar_calls_total{{pillar="{name}"}} {m.calls}')

        lines += [
            "",
            "# HELP m1frame_pillar_errors_total Total errors per pillar",
            "# TYPE m1frame_pillar_errors_total counter",
        ]
        for name, m in pillars.items():
            lines.append(f'm1frame_pillar_errors_total{{pillar="{name}"}} {m.errors}')

        lines += [
            "",
            "# HELP m1frame_pillar_latency_ms_avg Average latency ms per pillar",
            "# TYPE m1frame_pillar_latency_ms_avg gauge",
        ]
        for name, m in pillars.items():
            lines.append(f'm1frame_pillar_latency_ms_avg{{pillar="{name}"}} {m.avg_ms:.1f}')

        lines += [
            "",
            "# HELP m1frame_pillar_tokens_total Total tokens (in+out) per pillar",
            "# TYPE m1frame_pillar_tokens_total counter",
        ]
        for name, m in pillars.items():
            lines.append(f'm1frame_pillar_tokens_total{{pillar="{name}"}} {m.total_tokens}')

        return "\n".join(lines)

    # ── HTTP server ───────────────────────────────────────────────────────────

    def expose_http(self, port: int = 9090) -> None:
        """Start a background HTTP /metrics endpoint (non-blocking)."""
        from http.server import BaseHTTPRequestHandler, HTTPServer

        collector = self

        class _Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                if self.path == "/metrics":
                    body = collector.to_prometheus().encode()
                    self.send_response(200)
                    self.send_header(
                        "Content-Type",
                        "text/plain; version=0.0.4; charset=utf-8",
                    )
                    self.end_headers()
                    self.wfile.write(body)
                else:
                    self.send_response(404)
                    self.end_headers()

            def log_message(self, *args) -> None:
                pass  # suppress default access log

        server = HTTPServer(("", port), _Handler)
        self._http_server = server
        t = threading.Thread(target=server.serve_forever, daemon=True)
        t.name = f"m1frame-metrics-{port}"
        t.start()

    def stop_http(self) -> None:
        if self._http_server:
            self._http_server.shutdown()  # type: ignore[attr-defined]
            self._http_server = None


# ── Module-level singleton ────────────────────────────────────────────────────

_default: Optional[MetricsCollector] = None
_singleton_lock = threading.Lock()


def get_metrics() -> MetricsCollector:
    """Return the process-level MetricsCollector singleton."""
    global _default
    if _default is None:
        with _singleton_lock:
            if _default is None:
                _default = MetricsCollector()
    return _default
