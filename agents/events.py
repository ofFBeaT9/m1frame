"""
agents/events.py — m1frame Studio event bus.

A tiny, dependency-free pub/sub layer that lets the (blocking, threaded)
m1frame pipeline stream structured progress events to async consumers (the
Studio SSE endpoint) and sync consumers (recorders, the demo replayer, tests).

Why this exists
---------------
`scripts/run_workflow.run_workflow()` is a synchronous, blocking function that
makes network calls. The Studio needs to show what each of the 7 pillars is
doing *while it happens*. So the pipeline runs in a worker thread and pushes
small structured `Event`s into an `EventBus`; the API's SSE endpoint drains an
`asyncio.Queue` fed by that bus on the event loop.

The SAME `Event` schema is produced by three sources — the live pipeline, a
recorded run (Runs tab replay), and the bundled demo fixture — so the frontend
has exactly one renderer.

Design notes
------------
* `emit()` is thread-safe: async subscribers receive events via
  `loop.call_soon_threadsafe`, so the pipeline thread never touches the loop.
* Late subscribers are replayed the full history, so connecting the SSE stream a
  few milliseconds after the run starts still shows pillar 1.
* Nothing here imports FastAPI/anyio — it works in plain Python and in tests.
"""
from __future__ import annotations

import itertools
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

# Reserved top-level keys that payload `data` may not override.
_RESERVED = ("type", "ts", "seq", "pillar")
_seq_counter = itertools.count(1)


def _now_ms() -> int:
    return int(time.time() * 1000)


@dataclass
class Event:
    """One structured progress event. `data` is flattened into the wire dict."""
    type: str
    data: dict = field(default_factory=dict)
    pillar: Optional[str] = None
    ts: int = field(default_factory=_now_ms)
    seq: int = field(default_factory=lambda: next(_seq_counter))

    def to_dict(self) -> dict:
        """Flat JSON the frontend reads as `e.type`, `e.pillar`, `e.<field>`."""
        out: dict[str, Any] = {"type": self.type, "ts": self.ts, "seq": self.seq}
        if self.pillar is not None:
            out["pillar"] = self.pillar
        for k, v in self.data.items():
            if k not in _RESERVED:
                out[k] = v
        return out


# Callable threaded through the pipeline: emit(type, pillar=..., **data) -> None
Emitter = Callable[..., None]


class EventBus:
    """Thread-safe fan-out of `Event`s to async and sync subscribers.

    A bus is created per run. `emit()` may be called from any thread (the
    pipeline worker); async subscribers each own an `asyncio.Queue` bound to the
    loop they subscribed from.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._async_subs: list[tuple[Any, Any]] = []          # (loop, asyncio.Queue)
        self._sync_subs: list[Callable[[Event], None]] = []
        self._history: list[Event] = []
        self.closed = False
        self._done = False

    # ── subscribe ──────────────────────────────────────────────────────────────

    def subscribe_async(self):
        """Return an `asyncio.Queue` fed on the *current* running loop.

        Replays history first so a late subscriber still sees the whole run.
        Call from inside a running event loop (e.g. the SSE handler).
        """
        import asyncio

        loop = asyncio.get_running_loop()
        q: "asyncio.Queue[Event]" = asyncio.Queue()
        with self._lock:
            for ev in self._history:
                q.put_nowait(ev)
            self._async_subs.append((loop, q))
        return q

    def unsubscribe_async(self, q) -> None:
        with self._lock:
            self._async_subs = [(l, qq) for (l, qq) in self._async_subs if qq is not q]

    def subscribe_sync(self, fn: Callable[[Event], None]) -> None:
        """Register a synchronous callback (used by recorders/tests). Replays history."""
        with self._lock:
            history = list(self._history)
            self._sync_subs.append(fn)
        for ev in history:
            fn(ev)

    # ── emit ───────────────────────────────────────────────────────────────────

    def emit(self, type: str, pillar: Optional[str] = None, **data: Any) -> Event:
        ev = Event(type=type, data=data, pillar=pillar)
        with self._lock:
            self._history.append(ev)
            if type == "done":
                self._done = True
            async_subs = list(self._async_subs)
            sync_subs = list(self._sync_subs)
        for loop, q in async_subs:
            try:
                loop.call_soon_threadsafe(q.put_nowait, ev)
            except RuntimeError:
                pass  # loop already closed — drop silently
        for fn in sync_subs:
            try:
                fn(ev)
            except Exception:
                pass  # a bad subscriber must never break the pipeline
        return ev

    def close(self) -> None:
        """Emit a terminal `done` exactly once (idempotent, race-safe).

        No-op if a `done` was already emitted (e.g. by the pipeline itself), so a
        defensive `bus.close()` in a `finally` never produces a duplicate.
        """
        with self._lock:
            if self.closed or self._done:
                self.closed = True
                return
            self.closed = True
            self._done = True
        self.emit("done")

    @property
    def history(self) -> list[Event]:
        with self._lock:
            return list(self._history)

    def history_dicts(self) -> list[dict]:
        return [e.to_dict() for e in self.history]


def make_emitter(bus: Optional[EventBus]) -> Emitter:
    """Adapt an `EventBus` (or None) into a plain `emit(type, **data)` callable.

    Passing `emit=None` to the pipeline yields a no-op, so instrumentation is
    zero-cost and behaviour is byte-identical when nobody is watching.
    """
    if bus is None:
        def _noop(type: str, pillar: Optional[str] = None, **data: Any) -> None:
            return None
        return _noop

    def _emit(type: str, pillar: Optional[str] = None, **data: Any) -> None:
        bus.emit(type, pillar=pillar, **data)

    return _emit
