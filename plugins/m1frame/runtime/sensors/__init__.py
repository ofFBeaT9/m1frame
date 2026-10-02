"""
sensors/ — objective measurement for m1frame.

m1frame's QA gate has always been an LLM consensus score: a judgement. This module
adds the other kind of evidence — a *measurement* of the artefact itself — and fuses
the two into one auditable verdict that shows its work.

The first sensor is Sentrux (https://github.com/sentrux/sentrux, MIT): a Rust
architectural analyser that scores a codebase 0–10000 across modularity, acyclicity,
depth, equality and redundancy.

Honest scope: m1frame does **not** bundle, vendor or reimplement Sentrux. This is an
adapter. With the binary installed it gives you real numbers; without it every entry
point returns `available=False` and the rest of m1frame carries on exactly as before.
Zero new hard dependencies — the point of m1frame is that it owes nothing to anyone.

    from sensors import SentruxClient, StructuralGate
    r = SentruxClient().scan(".")
    if r.available:
        print(r.data["quality_signal"])
"""
from __future__ import annotations

from .gate import GateVerdict, StructuralGate
from .sentrux import SensorResult, SentruxClient

__all__ = ["SensorResult", "SentruxClient", "StructuralGate", "GateVerdict"]
