# Main-agent controller

The main agent receives the user's goal and constraints, invokes the full m1frame workflow, and uses actual tools to implement and verify the result. This is a routing policy and execution contract, not a claim that every host prompt already passes through the workflow.

## Execution

`User goal -> main agent -> full m1frame workflow -> reviewed result and execution receipt -> main-agent actions and verification`

Enable `controller.enabled: true` in the managed runtime's config. The portable default remains false so installations without the optional dependencies retain their existing behavior. The enabled policy requires the full workflow and rejects quick/skip bypasses. Explicit configuration changes can relax that policy.

- Headroom inspects every model request through LLMClient, including CLI and streaming paths. Required but unavailable or failed compression blocks dispatch. Protected user input may produce no compression; inspection does not guarantee token savings.
- SkillOpt evaluates transient execution guidance before each admitted workflow goal. It preserves mandatory constraints and never rewrites the user's goal. Its bounded objective measures procedural checklist coverage, not factual accuracy or answer quality. It does not perform a full trajectory-based optimization experiment on each request. Required adapter failure blocks the workflow; no silent local fallback.
- BMAD plans, Council brainstorms and reviews, OpenPlanter investigates every goal, and Miras carries execution state. Output filtering removes reasoning blocks from user-visible text; prompting is not a guarantee of deterministic answers.
- Wiki recall precedes planning. Only approved, checked output can enter the two-pass wiki ingestion and learning path. Rejected or failed runs do not fabricate completed persistence.
- Scientific instructions are selected when relevant; no match is recorded explicitly. Sentrux reports structural measurements separately from answer quality. ADHD shaping cleans final prose. Missing external capabilities remain visible rather than being reported as executed.
- Durable receipts record per-module status and actual Headroom/SkillOpt evaluations. A failed stage can prevent later stages from running.

## Codex prompt routing

The plugin supplies a UserPromptSubmit hook in `hooks/hooks.json`; the implementation is `runtime/scripts/prompt_route.py`. A project hook can point to the installed managed-runtime script. It reads only local controller policy, emits constant routing instructions, and does not export or echo prompt text. Internal CLI calls carry a recursion guard.

Codex must discover and trust the hook before it runs. Review it through the host's hooks controls (`/hooks` in the CLI); a source change can require renewed trust. See [official hook documentation](https://learn.chatgpt.com/docs/hooks). This hook guides the main agent; it does not independently execute model calls or guarantee host-model obedience. Do not self-mark it trusted. Source plugin changes require a supported reload/update; editing an installed cache is not deployment.

For the strongest application-level entry contract, use Studio's Full workflow or the m1frame workflow endpoint: these enforce the enabled runtime policy directly. A dedicated main-agent application could provide a stricter entry gate for all submissions, but it is not implemented here. A provider proxy alone would compress calls without orchestrating planning, investigation and review, so it would not meet the full requirement.

## Verification and limits

Controller regressions cover policy enforcement, required dependency failures, goal preservation, streaming accounting, API bypass rejection and prompt privacy. An offline full-workflow fixture uses real installed Headroom and SkillOpt with simulated model responses: all 17 model requests were checked, one SkillOpt evaluation completed, and the execution receipt included all modules. The scientific selector and structural sensor also executed. This proves local integration, not live model quality or all scientific workloads.

Live end-to-end verification still depends on provider capacity, external service configuration and valid source material. Do not claim completion from module availability alone.
