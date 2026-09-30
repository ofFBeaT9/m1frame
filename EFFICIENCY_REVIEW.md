# M1Frame efficiency and reliability review

Reviewed 2026-09-28; changes released locally as version 1.9.0.

Historical audit: the follow-up in [FULL_SYSTEM_QA.md](FULL_SYSTEM_QA.md) connects
full Studio chat and bounded story tool execution in v1.10.0, superseding those
limitations below.

The main problems found were information loss and disconnected capabilities.
Adding more skills or personas would not fix these defects.

## Scope and findings

The review traced Studio chat, the streaming provider adapter, BMAD planning,
Miras execution, Karpathy synthesis, council review, wiki retrieval, skill recall,
scientific skill loading, and the boundary between the tool registry and model calls.
It also checked configuration, the Claude command workflow, and offline CI coverage.

| Path | Observed behavior | Change |
| --- | --- | --- |
| Studio chat | Browser sent only the newest message; API ignored prior messages; stream adapter had no history support. | Send recent turns and preserve history on every streaming backend. Cap prior content at 24,000 characters; accept only user/assistant roles. |
| Story handoffs | Each prior output was cut to 500 characters, with a 3,000-character total prefix. | Supply declared dependency outputs in a shared 16,000-character budget, retaining both ends when clipping. Independent stories receive no unrelated outputs. |
| Synthesis | Only the first 4,000 characters of all stories reached synthesis. | Share a configurable 32,000-character budget across every story. Mark omissions explicitly. |
| Council | Judge and red-team saw only the first 2,000 characters. | Both receive the complete candidate output, as reviewers already did. This increases review input for long outputs to avoid blind approval. |
| Memory | Workflow wrote wiki pages but did not recall them before planning; search required a literal match of the entire question. | Rank meaningful query terms, boost title matches, and recall up to three pages in a 6,000-character budget before planning/execution. No extra model call. |
| Execution reliability | Failed stories were considered completed dependencies; malformed graphs could silently omit work. | Reject invalid graphs before execution and stop on story failure. Independent calls already running in a parallel batch may finish. |
| Redundant generation | Default non-streaming synthesis always performed another rewrite. | One synthesis call by default; `karpathy.refine: true` restores the extra rewrite. |
| Story verbosity | Every story was required to emit a reasoning transcript. | Ask for deliverables, concise decisions, and evidence-based execution claims. |

`miras.context_max_chars` and `karpathy.synthesis_max_chars` are character budgets,
not exact token limits. Reduce them for small-context local models; increase them
for large deliverables. Clipping remains lossy, but it is explicit and distributes
space across outputs instead of silently dropping the end of the workflow.
Dependencies must name the deliverables a story actually needs; handoffs now follow
those declarations in both sequential and parallel modes.

## Remaining architectural limits

- Ordinary Studio chat is a streaming answer with keyword wiki grounding. It does
  not invoke the seven-pillar workflow or autonomously execute the tool registry.
- Miras story execution is a text-generation call. MCP/HTTP tools are callable by
  a tool-capable host, but are not an autonomous execution loop inside these calls.
  The Claude slash command describes a separate host-orchestrated workflow.
- Scientific skills supply instructions and supporting resources. Their presence
  does not install scientific dependencies or execute their scripts.
- Wiki retrieval is lexical, not semantic by default. Synonyms can still miss.
  The new workflow recall uses this inexpensive lexical path.
- Learned skills use keyword matching and short approach text. The optional local
  optimizer rewards keyword coverage, which is not evidence of improved task quality.
- The full workflow still performs planning, council deliberation, execution,
  synthesis, and wiki ingestion. It is expensive for trivial requests. Automatic
  task routing needs a separate quality evaluation before changing that contract.
- Wiki generation itself still clips source excerpts. This patch improves recall
  and handoffs; it does not establish lossless long-document memory.
- The default council remains sequential. Raising concurrency on a local model
  can increase memory pressure; there is no measured hardware benchmark here.

These changes do not alter the intelligence or configuration of the Codex host.
They repair the repository's own runtime paths.

## Validation

- 164/164 existing offline QA checks.
- 8/8 scientific integration tests.
- 14/14 new regression tests covering bounded context, dependency handoffs,
  graph validation, failure propagation, all three streaming adapter paths,
  the HTTP chat endpoint, natural-language wiki search, and workflow recall.
- The workflow regression verifies five calls with council/wiki generation mocked:
  one planner, three stories, and one synthesis. The default extra rewrite is absent.
- Ruff and mypy checks; Studio JavaScript syntax check.

Tests use mock models and temporary fixtures. No paid live-model requests were made;
answer-quality uplift, GPU utilization, latency, and token-cost savings have not been
benchmarked. Initial sandbox temporary-directory failures were rerun with the needed
Windows filesystem access.
