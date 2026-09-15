# QA Gates — ADHD and Headroom Integration

## Gate 1 — Roadmap review

**Status: PASS WITH CONCERNS**

The design uses the correct m1frame seams and keeps both upstream integrations
optional. The principal concern is upstream API drift in Headroom and the risk of
rewriting structured model output. The build must therefore:

- lazy-import Headroom and return the original messages on every unavailable/error path;
- limit ADHD shaping to final user-facing prose, never BMAD/council JSON or wiki
  frontmatter;
- expose status and metrics so a run can prove whether an optional integration ran;
- validate both disabled and enabled-without-dependency behavior offline.

These constraints are folded into the stories and implementation below.

## Gate 2 — Results review

**Status: PASS**

Evidence:

- `python scripts/test_integrations.py`: 4/4 passed, including disabled,
  missing-dependency, fake-result metrics, and structured-output preservation.
- `python scripts/qa_validate.py`: 164/164 passed.
- `python -X utf8 wiki/lint.py`: 0 errors, 0 warnings, 0 orphans.
- `python -X utf8 m1frame/build_dashboard.py`: dashboard regenerated with no
  broken links or orphans after linking the saved query from the synthesis page.
- Council review found and the build fixed three concerns: no global ADHD
  guidance leakage into structured calls, validation of Headroom message payloads,
  and safety gating after final formatting.

The default path remains dependency-free and disabled. Headroom remains
opt-in, lazy-loaded, and passthrough-safe on missing packages or runtime errors.
