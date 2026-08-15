"""
sensors/gate.py — fuse a measurement into m1frame's QA gate.

The council scores a run 0–10 by argument. Sentrux scores the artefact 0–10000 by
measurement. Dividing by 1000 puts them on one scale, which is the whole trick.

The important design decision is what happens when they disagree. By default the
sensor is **advisory**: the measurement is always reported but never applied — the
council's verdict stands unchanged, in both directions. It must not worsen a verdict
(installing a binary should not silently change the meaning of every run in an
existing workspace) and it must not improve one either (a code metric does not get to
overrule the council's judgement upward). Set `enforce=True` to give the sensor real
veto power: an explicit, opt-in choice, visible in `GateVerdict.enforced`.

A verdict always shows its work: both scores, which inputs were present, and why.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .sentrux import SensorResult

PASS_THRESHOLD = 7.0        # structural score (0–10) at or above which structure is fine
CONCERN_THRESHOLD = 5.0     # below this, structure is a FAIL

_SEVERITY = {"PASS": 0, "CONCERNS": 1, "FAIL": 2}


@dataclass(frozen=True)
class GateVerdict:
    verdict: str                       # PASS | CONCERNS | FAIL
    basis: str                         # fused | council-only | sensor-only | none
    council_score: float | None = None
    structural_score: float | None = None
    enforced: bool = False
    reasons: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"verdict": self.verdict, "basis": self.basis,
                "council_score": self.council_score,
                "structural_score": self.structural_score,
                "enforced": self.enforced, "reasons": list(self.reasons)}


def _classify(score: float, pass_at: float, concern_at: float) -> str:
    if score >= pass_at:
        return "PASS"
    if score >= concern_at:
        return "CONCERNS"
    return "FAIL"


class StructuralGate:
    """Turn a `SensorResult` into a verdict, and fuse it with the council's."""

    def __init__(self, pass_threshold: float = PASS_THRESHOLD,
                 concern_threshold: float = CONCERN_THRESHOLD,
                 enforce: bool = False) -> None:
        self.pass_threshold = float(pass_threshold)
        self.concern_threshold = float(concern_threshold)
        self.enforce = bool(enforce)

    @staticmethod
    def structural_score(result: SensorResult) -> float | None:
        """Sentrux's 0–10000 signal on m1frame's 0–10 scale, or None if absent."""
        qs = result.quality_signal if isinstance(result, SensorResult) else None
        if qs is None:
            return None
        return round(max(0, min(10000, qs)) / 1000.0, 3)

    def judge(self, result: SensorResult) -> GateVerdict:
        """The sensor's own verdict, ignoring the council."""
        if not getattr(result, "available", False):
            return GateVerdict("CONCERNS", "none", None, None, self.enforce,
                               [result.error or "sensor unavailable"])
        score = self.structural_score(result)
        if score is None:
            return GateVerdict("CONCERNS", "none", None, None, self.enforce,
                               [result.error or "sensor returned no quality_signal"])
        v = _classify(score, self.pass_threshold, self.concern_threshold)
        return GateVerdict(v, "sensor-only", None, score, self.enforce,
                           [f"structural score {score:.3f}/10 -> {v}"])

    def fuse(self, council_score: float | None, result: SensorResult | None) -> GateVerdict:
        """Combine an LLM consensus score with a measurement.

        Advisory by default: the fused verdict is never more severe than the
        council's unless `enforce=True`.
        """
        reasons: list[str] = []
        c_verdict = None
        if council_score is not None:
            c_verdict = _classify(float(council_score), self.pass_threshold,
                                  self.concern_threshold)
            reasons.append(f"council {float(council_score):.2f}/10 -> {c_verdict}")

        s_score = self.structural_score(result) if result is not None else None
        s_available = bool(result is not None and getattr(result, "available", False))

        if s_score is None:
            # No measurement: fall back cleanly. An absent sensor changes nothing.
            if not s_available and result is not None:
                reasons.append(result.error or "sensor unavailable — council score stands")
            elif result is not None:
                reasons.append("sensor returned no quality_signal — council score stands")
            if c_verdict is None:
                return GateVerdict("CONCERNS", "none", None, None, self.enforce,
                                   reasons or ["no council score and no sensor reading"])
            return GateVerdict(c_verdict, "council-only", council_score, None,
                               self.enforce, reasons)

        s_verdict = _classify(s_score, self.pass_threshold, self.concern_threshold)
        reasons.append(f"structural {s_score:.3f}/10 -> {s_verdict}")

        if c_verdict is None:
            return GateVerdict(s_verdict, "sensor-only", None, s_score, self.enforce, reasons)

        if self.enforce:
            # Opt-in veto: the harsher of the two wins.
            fused = max(c_verdict, s_verdict, key=lambda v: _SEVERITY[v])
            reasons.append(f"enforce=True -> harsher verdict wins -> {fused}")
        else:
            # Advisory: the measurement is *reported*, never applied. It must not
            # worsen the verdict (that would change every run's meaning the day
            # someone installs a binary) and must not improve it either (a code
            # metric does not get to overrule the council's judgement upward).
            fused = c_verdict
            reasons.append(
                f"advisory (enforce=False) -> reported only, council verdict stands -> {fused}")
        return GateVerdict(fused, "fused", council_score, s_score, self.enforce, reasons)
