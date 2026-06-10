# Council Red-Team — Cycle 1 (clinical-safety lens)

Independent adversarial audit of the built code. Score: **6.5/10**. Verbatim findings
preserved; resolutions tracked in QA_GATE.md (Cycle 2). Verified-correct items retained.

## Findings (ranked)
- **C1 (critical)** CHA₂DS₂-VASc score-1 recommendation is sex-blind — a woman whose only
  point is female sex is low-risk (no anticoagulation), but the calc said "consider."
- **H1/L1 (high)** A *second*, unvalidated NEWS2/qSOFA implementation lives in `calculators.ts`
  (`computeNews2Quick`). It coerces missing inputs via `Number()` (NaN→ spurious +3 or dropped
  point) and loses the single-red `low-medium` escalation band. Two implementations, two answers.
- **H2 (high)** Wells PE interpretation conflated PERC with a low Wells follow-up.
- **H3 (high)** `/monitoring/board` skipped `requirePermission("read_chart")` and reimplemented
  its own filter instead of the `authorizePatientAccess` choke-point — contradicts the
  single-RLS-gate claim; `med_tech` (no read_chart) could reach it.
- **M1 (med)** NEWS2 scored even with most vitals null — partial scores are clinically misleading.
- **M2 (med)** Code Blue `accessed_sections` declared but never populated (forensic overclaim).
- **M3 (med)** Code Blue extend/end were not audited; extension was unbounded.
- **M4 (med)** Saving a calculator result to a chart did not check patient-level authorization.
- **L2 (low)** `aiHealth().online`/`lastHealthy` could report stale-good after live failures.
- **L3 (low)** Calculators coerced inputs with `Number()`; malformed input → `Infinity`/`NaN` results.

## Verified correct (kept as-is)
NEWS2 component cutoffs & bands (RCP 2017), oxygen +2, consciousness +3, red_score logic;
`authorizePatientAccess` core gate (scoped role denied without active Code Blue); Code Blue
*invocation* gate (priv≥6 + reason + ≥10-char note + audit + alert); MAP, anion gap, corrected
Ca, Cockcroft-Gault (×0.85 female), CKD-EPI 2021 race-free, Parkland, Shock Index, GCS formulas;
AI degraded mode never throws/blocks.

## Resolution: ship all C/H/M fixes in Cycle 2 (fix, don't caveat). L2/L3 also folded in.
