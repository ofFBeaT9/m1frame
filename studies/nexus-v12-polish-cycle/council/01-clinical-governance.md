# Council Paper 1 — Clinical Governance & Documentation (score 7.5/10, pre-fix)

(a) Notes engine: finalize lock is hard (updateDraft 409s on final); amendments append-only with
independent author attribution; every transition audited; grep confirms no writer of db.notes
outside notesService. Two findings: **G1** — 24h co-sign deadline existed only as a comment, not
machine-enforced; **G2** — draft section merge could blank content via explicit empty strings.

(b) ESI: v4 waterfall structure faithful (life-saving → high-risk → resources); override
discipline correctly enforced (422 without reason, audited); ESI-1 alert fires. **G3 (patient
safety)** — danger-zone thresholds undertriaged vs the handbook: SpO2 <85 (should be <90),
RR >40 (should be >36), HR entirely absent (<40/>180), SBP 70 vs handbook 80.

(c) Calculator audit: 10/11 formula-accurate against citations (CURB-65, Wells DVT, HEART,
HAS-BLED, MELD-Na incl. UNOS bounds + the meld>11 sodium conditional, Child-Pugh, APGAR, Centor,
FENa, Osmolality). **G4** — Corrected Na arithmetically correct per Katz 1.6 but should surface
the Hillier 2.4 variant used in severe hyperglycaemia.

(d) All six v1.1 residuals verified genuinely retired in code (file:line cited for each).

DISPOSITION (folded in-cycle): G1 → cosignOverdueSweep() raising overdue_cosign alerts + audit
rows, lazy on notes reads, test added. G2 → blank section values ignored on draft merge.
G3 → thresholds aligned to handbook (HR <40/>180, RR <8/>36, SpO2 <90, SBP <80) + 5 regression
assertions. G4 → both factors now shown in the interpretation.
