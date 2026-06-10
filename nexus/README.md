# NEXUS Clinical Intelligence Platform

> Full-stack, AI-native clinical platform built from `NEXUS_v2_FINAL.md` (Master Build Prompt v2.0)
> via **two full m1frame 7-pillar cycles**. *Every patient. Every signal. Every second.*

This is a runnable, tested implementation of the spec's **safety spine** — age-adjusted vitals →
NEWS2/qSOFA → alerts → audit → three-layer RBAC → Code Blue override → FHIR R4 export — plus a
cited medical-calculator engine, protocol library, monitoring console, and an AI engine that
**degrades gracefully and never blocks care**. It runs fully offline with an in-memory data layer
that mirrors the spec's PostgreSQL schema, so the same domain logic ports to Supabase unchanged.

## Quick start

```bash
# 1. API server (port 4000) — seeds 11 users, 3 wards, 12 patients on boot
cd server && npm install && npm run dev

# 2. Web app (port 3000) — proxies /api to the server
cd web && npm install && npm run dev
```

Open http://localhost:3000 and sign in.

## Demo accounts (password: `Demo1234!`)

| Email | Role | What you'll see |
|---|---|---|
| `physician@nexus.demo` | Attending physician | All 12 patients, AI trajectory, Code Blue |
| `nurse@nexus.demo` | Registered nurse | Only the 2 ICU patients on her care team |
| `medtech@nexus.demo` | Medical technician | No chart access (lab/imaging entry only) |
| `admin@nexus.demo` | Hospital administrator | Audit log, analytics, user management |
| `patient@nexus.demo` | Patient | Own record only |

Use the **demo role-switcher** in the top bar to flip perspective instantly (spec §21).

## What's implemented (proven by tests + a running app)

- **Three-layer RBAC** from one shared permission matrix (`domain/rbac.ts`) consumed by the data
  layer (`authorizePatientAccess`), Express middleware, and React guards — no layer can drift.
- **NEWS2 + qSOFA** age-aware scoring (`domain/news2.ts`), validated against RCP 2017 / Sepsis-3
  worked examples, computed on every vitals entry, raising sepsis/critical/threshold alerts.
- **Code Blue override** (spec §2.3): privilege ≥6 + reason + ≥10-char note → 30-min audited
  session (extend capped at 180 min, every invocation/extend/end logged + admin-alerted).
- **Audit log** of every mutating action; admin-readable + CSV export; 🔴 Code Blue rows highlighted.
- **FHIR R4** read endpoints (Patient, Observation, Condition, MedicationRequest, DiagnosticReport)
  + full-patient `$everything` Bundle.
- **Medical calculators**: a cited engine — NEWS2, qSOFA, GCS, MAP, Shock Index, Cockcroft-Gault,
  CKD-EPI 2021, BMI, Parkland, Anion Gap, Corrected Calcium, CHA₂DS₂-VASc, Wells PE.
- **AI engine** with mandatory degraded mode — with no `ANTHROPIC_API_KEY` it returns a structured
  "AI Offline" result and never throws; 60s health poll in the UI.
- **Monitoring board** (NEWS2 badges, heartbeat sparklines, stale indicators) + 3-pane console;
  **Alert Centre**; **Protocols** with staleness banners; dark-mode design tokens (spec §16).

## Architecture

```
nexus/
  server/   Express 5 + TypeScript (strict). In-memory store mirrors spec §17 schema.
    src/domain/      rbac, news2, vitalRanges, calculators, fhir, types  (pure, unit-tested)
    src/db/          store (authorize() = the RLS choke-point) + seed
    src/services/    ai (degraded mode), vitalsService (scoring + alerting)
    src/routes/      auth, patients, clinical, admin, fhir
    src/tests/       41 vitest + supertest tests (safety spine)
  web/      React 18 + Vite + Tailwind + Zustand + React Query + Router
```

## Tests

```bash
cd server && npm test        # 41 tests: NEWS2/qSOFA, RBAC, Code Blue, FHIR, calculators, AI
cd server && npm run typecheck
cd web && npm run build      # tsc strict + vite production build
```

## Configuration

All env vars are optional with safe local defaults (see spec §19). Set `ANTHROPIC_API_KEY` to take
the AI engine online; without it the app is fully functional in degraded mode. `ENABLE_DEMO_MODE`
(default on) enables the role-switcher.

## Scope honesty

This delivery implements the safety-critical core and scaffolds the breadth. **Out of scope** (typed
seams, not faked): live WebRTC/coturn video, real OHIF/DICOM rendering, hosted Supabase provisioning,
live Anthropic calls (offline mode proven instead), HL7 v2.5 socket ingest, barcode hardware. The
in-memory store implements the exact §17 table shapes so a Supabase adapter is a drop-in replacement.

Built with the m1frame pipeline — see `studies/nexus/` for the BMAD roadmap, QA gates, red-team
council review, and final report.
