# Miras persistence record — cycle 3 (durable in-repo record)

## Decision (force: high)
Demo trust claims are legitimate iff every mechanism is real-but-bounded and the bound is stated
as loudly as the feature (Honest Scope Labels). An inaccurate honesty label is the worst defect
class — it spends credibility earned elsewhere — so the red-team checks labels as claims.

## Reusable lessons
1. Patient-facing surfaces need an ADVOCATE lens, not just clinical/engineering ones — it
   produced the cycle's most reframing finding ("a data printout where a frightened patient
   needs a companion") and five cheap, high-value fixes.
2. A digital screener must never answer a distressed person with bare JSON: every questionnaire
   response carries a support message; near-max scores escalate severity and carry crisis
   signposting in the SAME response.
3. Releasing data to patients is a communication act: require the plain-language comment at the
   release choke-point (422 without), not as UI guidance.
4. Hash chains: re-verify on every restore; state plainly that tail truncation is invisible to a
   bare chain and expose {length, head_hash} for external anchoring.
5. Flags the UI never offers still need server gates (forged is_urgent) — the API surface is the
   security boundary, never the form.
6. Infra honesty: when a sub-agent is killed (session limits), record it and run its checklist
   directly — never silently re-attribute or skip the work.

source_agent: dev+advocate+red-team · date: 2026-06-11 · study: nexus-v13-reach-trust
