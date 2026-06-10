---
title: NEXUS Build Prompt v2.0
tags: [source, clinical, ehr, full-stack, healthcare, fhir, rbac]
related: ["[[NEXUS Clinical Platform]]"]
created: 2026-06-10
sources: ["nexus-build-prompt-v2"]
page_type: source
confidence: high
---

# NEXUS Build Prompt v2.0

**Source:** `raw/sources/nexus-build-prompt-v2.md` — a 1,326-line Master Build Prompt (council score
8.6/10, 2 red-team vetoes cleared) for **NEXUS**, a full-stack AI-native clinical intelligence
platform. Itself produced by a prior m1frame 7-pillar cycle. Ingested and executed via two further
m1frame cycles → [[NEXUS Clinical Platform]].

## Key claims / requirements (Analysis pass)
- **21 sections.** Mission axiom: every pixel/endpoint serves *patient safety* or *clinical
  efficiency* — nothing else ships.
- **Stack:** React 18 + TS + Tailwind + Zustand + React Query (frontend); Node 20 + Express 5 +
  PostgreSQL/Supabase + Redis (backend); Anthropic Claude for the AI layer; WebRTC + OHIF for calls/DICOM.
- **Three-layer RBAC** (Supabase RLS · Express middleware · React guards) over 11 roles with a full
  permission matrix; **Code Blue emergency override** (privilege ≥6, fully audited) is a stated
  patient-safety requirement and a cleared red-team veto.
- **Safety spine:** age-adjusted vital ranges → NEWS2/qSOFA auto-scoring → critical-value/sepsis/stale
  alerting → 7-year audit log.
- **AI must never block care:** mandatory graceful degraded mode ("AI Offline" badge, last-cached).
- **Interoperability:** FHIR R4 read endpoints + Bundle export for Patient/Observation/Condition/
  MedicationRequest/DiagnosticReport.
- **Breadth:** ~250 medical calculators across 18 categories, protocol library, handover (I-PASS),
  triage (ESI/MTS), bed management, consent, communication hub, patient portal, admin panel.

## Contradictions / tensions detected
- The spec targets hosted externals (Supabase, Anthropic, coturn, OHIF) that cannot be provisioned in
  an autonomous build session — resolved in the build by an offline-runnable store mirroring the §17
  schema (see [[NEXUS Clinical Platform]]).
