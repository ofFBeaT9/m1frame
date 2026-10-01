# Final Report — m1frame Optional Modules

## Verdict

**Ship.** m1frame now includes two opt-in integrations: an ADHD-friendly output
formatter derived from `i-have-adhd`, and a lazy Headroom adapter for optional
context compression.

## Evidence

- Added `modules/adhd.py` with action-first guidance and conservative final-prose
  formatting. Structured JSON, YAML, XML, and fenced code are preserved.
- Added `modules/headroom.py` with explicit availability, token metrics, result
  validation, and original-message fallback.
- Wired configuration, `LLMClient`, workflow final output, API chat, tool status,
  README, and wiki knowledge graph.
- Added the `headroom` optional dependency extra without changing the base
  installation.
- `scripts/test_integrations.py`: 4/4 passed.
- Full offline suite: 164/164 passed.
- Wiki lint: 0 errors, 0 warnings, 0 orphans.
- Dashboard regenerated successfully with 0 broken links and 0 orphans.

## Caveats

Headroom compression quality and savings depend on the installed release, model,
content type, and configured ratio. It is disabled by default and should be
measured in each deployment. Live API streaming receives ADHD system guidance;
workflow and demo output also apply the deterministic final formatter.

## Reusable lessons

Keep prompt skills and runtime libraries separate: translate stable behavior into
a dependency-free adapter, and lazy-load heavy optional packages at the narrowest
provider-neutral seam. Apply presentation transforms only after synthesis and
before safety validation; validate third-party output before forwarding it.

## Next step

Install `pip install -e ".[headroom]"`, enable the module in a deployment
configuration, and compare `client.last_compression` metrics on representative
long-context runs.
