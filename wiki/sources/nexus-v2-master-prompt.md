---
title: NEXUS v2 Master Prompt
tags: [source, clinical, ehr, build-prompt]
related: ["[[NEXUS Clinical Platform]]", "[[NEXUS v2 Gap Cycle]]", "[[m1frame]]"]
created: 2026-06-10
page_type: source
confidence: high
---

# NEXUS v2 Master Prompt

A 21-section, council-approved **Master Build Prompt v2.0** for the [[NEXUS Clinical Platform]]
(raw text preserved unmodified at `wiki/raw/sources/nexus-v2-master-prompt.md`). Produced via a full
[[m1frame]] 7-pillar cycle; self-reports a projected council score of 8.6/10 after v1 scored 6.8 and
failed the QA gate on two red-team vetoes (Code Blue override, MAR underspecification).

## What it specifies
Full-stack AI-native clinical platform: 11-role RBAC with a Code Blue emergency override, patient
records + CPOE with order-entry safety checks, MAR with controlled-substance witness protocol, labs
with critical-value alerting/escalation, imaging/DICOM, a 200+ medical calculator suite, protocols
library with staleness tracking, I-PASS shift handover, AI engine with mandatory degraded mode,
monitoring console, triage (ESI/MTS), bed management, consent, print/FHIR export, chat/video,
patient portal, admin panel, dark-only design system, PostgreSQL data architecture, and a 12-patient
demo seed.

## Reliability note
The build sections are precise and falsifiable (ranges, formulas, schemas). The *metadata/history*
claims are less reliable — see the contradiction recorded in [[NEXUS v2 Gap Cycle]]: veto #1 was
already closed in code when the spec still listed it as open.
