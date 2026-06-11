# Miras persistence record — cycle 2 (no miras MCP mounted; durable in-repo record)

## Decision (force: high)
"Spotless" is a definable, testable release state: zero documented-but-unfixed defects
(Residual Retirement), every council/red-team finding folded in-cycle WITH a regression test,
all gates PASS, professional surfaces per role. It is NOT spec parity — re-scope the remainder
out loud.

## Reusable lessons
1. Council prescriptions are hypotheses, tests are the arbiter: the engineering lens's own fix
   (read_chart gate) failed against the patient role's truthy "own" scope; the corrected gate
   then failed the red-team (write_vitals admitted med_tech). Two evidence-driven corrections.
2. Threshold tables in clinical rules engines (ESI danger zones, lab criticals) must be diffed
   line-by-line against the cited source — "structurally faithful" is not "numerically faithful".
3. When spawning a review lens in parallel with a dev agent, brief the lens on in-flight work or
   snapshot after delivery — otherwise it reports already-resolved gaps.
4. Express 4 path quirk: "$" in route strings is a regex anchor; serve FHIR $-operations via a
   URL-rewrite registered at the TOP of the router with an explicit ordering-contract comment.
5. Lazy sweeps generalized again (cosign deadline) — third use of the pattern, now the house
   style for timed obligations in demo-grade systems.

source_agent: dev+council(3)+red-team · date: 2026-06-11 · study: nexus-v12-polish-cycle
