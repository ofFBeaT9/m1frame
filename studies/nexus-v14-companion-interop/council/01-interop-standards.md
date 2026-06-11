# Council Paper 1 — Interoperability & Standards (checklist self-executed)

PROCESS NOTE: the lens agent was killed by a session limit at spawn (0 tokens) — second
occurrence after cycle 3; the checklist was executed directly, findings folded, and the
independent red-team (which did run) re-verified the same ground.

(a) HL7 parser vs v2.5: MSH-9 at split index 8 CORRECT (MSH-1 is the separator); PID-3
repetition (~) + component (^) handling correct; OBR-4 coded-element text-preferred correct.
Narrow-but-honest: SN structured numerics and escape sequences (\F\, \S\) are not decoded —
non-NM rows are skipped BY NAME (never NaN'd); both now in the README honest label. No factual
defect.
(b) Ed25519 scheme: **FOLDED FIX** — canonicalPayload sorted keys with localeCompare
(locale-dependent collation could break cross-host re-verification); replaced with code-unit
comparison. Replacer recurses into array elements (JSON.stringify replacer semantics) — nested
objects in arrays canonicalize correctly. Signer resolution: MAR signer = administered_by_id
(witness is content, not signer) — correct. Kind strings consistent between sign/verify sites.
(c) Journal: JSON.stringify escapes control characters, so NDJSON lines are single-line by
construction; shorter-journal-than-snapshot is skipped (no overwrite); torn tails tolerated.
Verdict: one folded fix, two labels added; no factual defects remaining.
