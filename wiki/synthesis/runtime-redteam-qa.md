---
title: Runtime Red-Team QA
tags: [synthesis, security, runtime, qa]
related: ["[[m1frame Optional Modules]]", "[[Headroom Context Compression]]"]
created: 2026-09-30
sources: ["REDTEAM_QA.md", "scripts/test_redteam.py"]
page_type: synthesis
confidence: high
---

# Runtime Red-Team QA

Analysis of code and adversarial regression cases identified failures at API,
network, file, computation, timer and persistence boundaries. Version 1.10.1
repairs the reproduced cases and retains the full Studio workflow and host-agent
instructions. The release evidence is in the root REDTEAM_QA.md report.

[[m1frame Optional Modules]] remain opt-in. [[Headroom Context Compression]] must
preserve system messages and the latest user request; failure returns an untouched
copy. Compression availability is separate from the local context budget guard.

The API is a single-owner service: local by default, token-protected remotely.
MCP HTTP needs an authenticated proxy for remote clients. Passing offline tests
does not establish live-provider quality, optional package support or absence of
all defects. No provider authentication was modified or exercised in this audit.
