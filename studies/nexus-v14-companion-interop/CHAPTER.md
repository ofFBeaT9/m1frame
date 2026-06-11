# Chapter: NEXUS v1.4 "Companion & Interop"
date: 2026-06-11
topic: Cycle 4 — portal companion surfaces, per-user signing keys, audit journal,
HL7 v2.5 ORU ingest, calculator long tail, print-redirect residual; ship v1.4.0.

## Phase 0 — Recall
- Queue (cycle-3 FINAL_REPORT, council-ranked): portal companion #1 (advocate), per-user keys
  (non-repudiation path), HL7 ingest, calculator tail, print redirect residual.
- Lessons in force: API surface is the security boundary; honesty labels are claims the red-team
  checks; advocate lens on patient-facing work; degraded-mode (offline) safety for anything AI;
  zero-new-deps verifiable; sub-agent failures recorded faithfully.
- Honesty boundaries fixed up front: Ed25519 keys are CUSTODIAL (server holds private keys) —
  per-user separation + public verifiability, not full non-repudiation; the audit journal closes
  the crash window for the LEGAL RECORD only (other tables keep the 10s snapshot window);
  diagnosis explainer is curated-text-first with AI enrichment when online — never AI-gated.
