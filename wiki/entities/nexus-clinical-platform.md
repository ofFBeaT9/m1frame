---
title: NEXUS Clinical Platform
tags: [entity, project, clinical, ehr, fmed]
related: ["[[NEXUS v2 Master Prompt]]", "[[NEXUS v2 Gap Cycle]]", "[[Clinical Safety Loops]]", "[[m1frame]]"]
created: 2026-06-10
sources: ["nexus-v2-master-prompt"]
page_type: entity
confidence: high
---

# NEXUS Clinical Platform

A demo-grade, full-stack clinical intelligence platform (repo: **fmed**) implementing the
[[NEXUS v2 Master Prompt]]. Express + TypeScript (strict) server with an in-memory store whose
`authorizePatientAccess()` is the single data-layer choke-point, plus a React/Vite dark-mode web app.
*Every patient. Every signal. Every second.*

## State after v1.1 "Safety Loops" (2026-06-10)
- **v1 spine:** three-layer RBAC (one shared matrix), NEWS2/qSOFA auto-alerting with age-adjusted
  ranges, Code Blue override (privilege ≥6, 30-min audited sessions), full audit log + CSV export,
  13 cited calculators, protocols with staleness bands, FHIR R4 `$everything`, AI degraded mode.
- **v1.1 added the [[Clinical Safety Loops]]:** CPOE safety checks (allergy cross-reactivity
  hard/soft stops, offline interaction table, pediatric dose limits, renal flags, duplicate
  detection, resident co-signature), MAR with controlled-substance two-person witness + waste +
  scan-to-confirm, lab critical-value alerting with acknowledgement read receipts and 30-minute
  escalation sweeps, and I-PASS handover with receiver synthesis. 66 tests green; versions 1.1.0.
- **Deliberately open:** triage/ESI, bed board, consent workflow, patient portal UI, chat/video,
  imaging/DICOM, notes engine — breadth deferred behind safety depth per [[NEXUS v2 Gap Cycle]].

Both the spec and the upgrade cycle were produced by the [[m1frame]] pipeline.
