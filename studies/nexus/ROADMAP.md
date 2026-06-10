# NEXUS Clinical Intelligence Platform — m1frame ROADMAP

> Produced by the m1frame 7-pillar pipeline (Cycle 1 of 2). Personas labelled.
> Source spec: `NEXUS_v2_FINAL.md` (Master Build Prompt v2.0, council score 8.6/10).

## 0. Recall (miras)

No prior NEXUS build in memory. Constraints surfaced from the spec that must not be re-litigated:
- **Patient safety is master #1, clinical efficiency #2. Nothing else ships.**
- **The app must be fully functional without AI** (graceful degraded mode, never blocking).
- **RBAC at three layers** — a single-layer escalation must not grant access.
- **Code Blue override** is a safety requirement, always logged, always visible.
- **Every user action is audited** (7-year retention).

Reality anchor for *this* delivery: the spec targets hosted Supabase + Anthropic + coturn + OHIF.
A single autonomous build session cannot provision those externals, and the delivery must *run and be
tested here*. Decision (see QA gate): ship a **self-contained, offline-runnable** implementation of the
safety-critical core with an in-memory data layer that mirrors the Section 17 schema, so the same domain
logic drops onto Supabase later without change. AI degrades to offline mode by default (no key required) —
which the spec already mandates as a first-class state.

## 1. Analyst — Project Brief

**Problem.** Clinicians need one console that fuses EHR, live monitoring, calculators, protocols, and
advisory AI without ever letting AI or network failure block care. The risk is not "too few features" —
it is an unsafe feature: a missed critical value, a silent stale-vitals gap, an un-audited override.

**Core hypothesis.** A correct, tested **safety spine** (age-adjusted vitals → NEWS2/qSOFA → alerts →
audit → RBAC → Code Blue) is worth more than a broad-but-shallow clone of all 21 sections. Build the spine
end-to-end and prove it; scaffold the breadth around it.

**Grounded anchors.** NEWS2 (RCP 2017), qSOFA (Sepsis-3, JAMA 2016), age-banded vital ranges (spec §3.8),
FHIR R4 resource shapes (spec §1.2/§17), I-PASS handover (spec §6).

## 2. PM — PRD

**Goal.** A running, tested full-stack NEXUS slice demonstrating every load-bearing safety requirement of
Section 21, with the breadth scaffolded coherently.

**Functional requirements (must, Cycle 1 + 2):**
- FR1 JWT auth, 11 demo roles, role-switch demo mode.
- FR2 Three-layer RBAC: data-layer guard (store), Express middleware, React route/element guards — driven by
  one shared permission matrix (spec §2.2).
- FR3 Patient registry + encounters + auto category tag (neonatal…geriatric) from DOB.
- FR4 Vitals capture with age-adjusted ranges; **NEWS2 + qSOFA auto-calculated** on every entry.
- FR5 Critical-value & sepsis & stale-vitals **alerting** with acknowledge/escalate + audit.
- FR6 **Code Blue override** (reason + note, 30-min session, full audit, admin notify, top-bar badge).
- FR7 **Audit log** of every mutating action; admin-readable, CSV-exportable.
- FR8 **FHIR R4 read endpoints** for Patient, Observation, Condition, MedicationRequest, DiagnosticReport + Bundle export.
- FR9 **Medical calculator suite** — generic engine + a real, cited library (NEWS2, qSOFA, GCS, MAP, Shock Index,
  CrCl Cockcroft-Gault, CKD-EPI, BMI, Parkland, Anion Gap, Corrected Ca, CHA₂DS₂-VASc, Wells PE, …).
- FR10 **AI engine** with mandatory degraded mode (offline badge, last-cached, never blocks).
- FR11 Protocol library (categories, staleness banners).
- FR12 Monitoring board (patient cards, NEWS2 badge, sparkline, stale indicator) + 3-pane console.
- FR13 Seed: 11 users, 3 wards, 12 patients with the spec's vitals trajectories.

**Non-functional:** TypeScript strict; dark-mode design tokens (spec §16); audit never skipped; AI never
blocks; tests green; dashboard load logic O(patients); RTL scaffold present.

**Out of scope (explicit, this delivery):** live WebRTC/coturn calls, real OHIF/DICOM rendering, hosted
Supabase provisioning, real Anthropic key calls (offline mode proven instead), HL7 v2.5 socket ingest,
barcode hardware. All are scaffolded with typed seams, not faked as "done."

**Success metric:** `npm test` green on the safety spine; `npm run build` green on web; app boots and serves
the monitoring board + FHIR export with seed data; QA gate 2 ≥ 8.0.

## 3. Architect — Technical Design

- **Monorepo** `nexus/` → `server/` (Express 5 + TS, vitest+supertest) and `web/` (React 18 + Vite + TS + Tailwind + Zustand + React Query + Router).
- **Data layer** `server/src/db/store.ts`: typed in-memory store whose tables mirror Section 17 columns
  exactly (`vitals`, `patients`, `encounters`, `alerts`, `audit_log`, `code_blue_sessions`, …). One
  `authorize()` choke-point = the "RLS" layer. Swapping to Supabase = reimplement the store interface only.
- **Permission matrix** `domain/rbac.ts` is the single source of truth consumed by middleware *and* shipped
  to the client for element guards — guarantees the three layers can't drift.
- **Vitals → scores** `domain/news2.ts`, `domain/vitalRanges.ts` pure functions (fully unit-tested, deterministic).
- **Alerts** raised inside the vitals write path (critical value, qSOFA≥2 sepsis, stale) → audited.
- **Code Blue** `routes/codeblue.ts` opens a `code_blue_sessions` row consulted by `authorize()`.
- **FHIR** `domain/fhir.ts` pure mappers domain→FHIR R4; routes are thin.
- **AI** `services/ai.ts`: if no `ANTHROPIC_API_KEY` → returns `{offline:true, cached?}` — never throws,
  never blocks. 60s health poll on client.
- **Falsifiable claims:** NEWS2 matches RCP worked examples; qSOFA fires at ≥2; a nurse cannot read an
  unassigned chart at any layer unless a live Code Blue session exists; FHIR validates against R4 shapes.

## 4. Scrum Master — Epic + Stories

**Epic: Ship the NEXUS safety spine + scaffolded breadth, tested.**
- S1 Store + seed mirroring §17 → AC: 11 users/3 wards/12 patients load; categories auto-tagged. ✅C1
- S2 Auth + RBAC matrix + 3 guards → AC: matrix drives all layers; cross-team read denied. ✅C1
- S3 Vitals + NEWS2 + qSOFA + age ranges → AC: RCP examples pass; sepsis fires. ✅C1
- S4 Alerts + ack/escalate + audit → AC: critical value persists until ack. ✅C1
- S5 Code Blue override → AC: opens session, audits, expires 30 min. ✅C1
- S6 Audit log + admin read + CSV → AC: every mutation logged. ✅C1
- S7 FHIR R4 reads + Bundle → AC: 5 resources valid. ✅C2
- S8 Calculator engine + cited library → AC: results match references. ✅C2
- S9 AI degraded mode → AC: no key ⇒ offline badge, no throw. ✅C1
- S10 Web: login, role-switch, monitoring board, console, calculators, protocols, audit, admin, portal. ✅C2
- S11 Protocols + staleness. ✅C2
- S12 Tests + build green; README + run guide. ✅C2
