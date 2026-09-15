# m1frame Integration Roadmap

## Topic

Integrate the output-shaping ideas from [i-have-adhd](https://github.com/ayghri/i-have-adhd)
and the optional context-compression API from
[headroom](https://github.com/headroomlabs-ai/headroom) into m1frame without making
either dependency mandatory.

## Analyst — Project Brief

**Problem.** m1frame currently has a strong multi-agent pipeline, but final responses
can be verbose and long contexts are sent unchanged. The two upstream projects address
different seams: i-have-adhd defines actionable response-shaping rules, while Headroom
provides `compress(messages, ...)` and measurable compression results.

**Grounded anchors.**

- i-have-adhd `skills/i-have-adhd/SKILL.md` defines ten rules, including leading with
  the next action, numbered steps, capped lists, matter-of-fact errors, and a concrete
  next step.
- Headroom exposes a pure Python `compress(messages, model=...)` API returning
  compressed messages and token metrics; `headroom-ai` is Python 3.10+ and optional.
- m1frame already centralizes model calls in `LLMClient`, uses optional modules such as
  sensors/optimizers, and validates offline through `scripts/qa_validate.py`.

**Hypothesis.** A dependency-free ADHD formatter plus an optional Headroom adapter at
the `LLMClient` seam will improve actionability and reduce context size while keeping
the default installation and existing offline behavior unchanged.

## PM — Product Requirements

**Goal.** Add two production-safe modules that are discoverable, configurable, tested,
and documented across CLI/API/MCP usage.

**Functional requirements.**

1. `modules.adhd` provides deterministic output shaping, system guidance, and a
   conservative opt-in formatter that preserves structured intermediate outputs.
2. `modules.headroom` provides optional dependency detection, message compression,
   metrics, and a no-op fallback with explicit availability status.
3. `LLMClient` uses Headroom only when enabled and installed, and never fails a run
   solely because the optional package is absent or compression fails.
4. Final user-facing workflow output and live chat can use ADHD shaping when enabled;
   BMAD/council JSON and wiki markdown remain unmodified.
5. Configuration, README, wiki pages, and validation artifacts describe the behavior.

**Non-functional requirements.** Python 3.10+, no network required for tests, no
secret handling changes, bounded compression work, clear errors in diagnostics, and
backward-compatible defaults.

**Success metrics.** Existing QA remains green; new tests cover enabled/disabled and
missing-dependency paths; a sample run proves both modules report status; wiki lint
reports zero errors and zero orphans; dashboard build succeeds.

**Out of scope.** Vendoring either upstream repository, forcing heavy ML dependencies,
rewriting all intermediate agent prompts, or changing model-provider behavior when
the modules are disabled.

## Architect — Technical Design

### `modules/adhd.py`

- Constants for the upstream rules and a compact system-instruction helper.
- `ADHDFormatter` with `format(text, mode=...)`, preserving empty text, fenced code,
  JSON, YAML frontmatter, and markdown headings.
- Conservative formatting: normalize excessive preamble/closer language only when
  explicitly enabled; do not reauthor model content.
- `status()` returns enabled/available/source metadata for API and test inspection.

### `modules/headroom.py`

- `HeadroomAdapter` accepts config and lazily imports `headroom.compress`.
- `compress_messages(messages, model=...)` returns a stable result object with
  messages, availability, token metrics, and error text.
- Missing package and runtime failures are explicit status results; callers retain the
  original messages.
- No compression of prompts by default; when enabled, compress only the assembled
  request immediately before provider dispatch and preserve the existing history API.

### Integration seams

- `LLMClient` owns both adapters because it is the single provider-neutral call seam.
- Config adds `adhd` and `headroom` sections, both disabled by default.
- `run_workflow` formats only the final approved output when ADHD is enabled.
- API chat applies the same final shaping to live and demo replies.
- Tool registry exposes read-only module status and compression helpers without
  granting filesystem/network powers.

## Scrum Master — Epic and Stories

### Epic: Optional actionability and context efficiency

1. **Story 1 — Add module contracts**
   - AC: both modules import with no optional package installed.
   - AC: status and result shapes are typed and deterministic.
2. **Story 2 — Wire provider seam**
   - AC: disabled config is byte-compatible with current message construction.
   - AC: enabled Headroom path retains original messages on unavailable/error.
3. **Story 3 — Wire user-facing output**
   - AC: ADHD formatter affects final workflow/chat output only when enabled.
   - AC: intermediate JSON and wiki pages are not altered.
4. **Story 4 — Validate and document**
   - AC: targeted tests and full QA pass.
   - AC: README, config, wiki, roadmap gates, and final report are updated.
   - AC: dashboard renders and branch is pushed.

## Risks and mitigations

- **Headroom API/version drift:** lazy import and attribute-based result extraction;
  no hard dependency and explicit fallback.
- **Formatting damage:** conservative rules and protected structured-content detection.
- **Performance:** compression is opt-in and executes once per provider request.
- **Protocol artifact drift:** record evidence in QA gates and final report, then run
  wiki lint and dashboard generation before publishing.
