---
title: Local Codex Plugin
tags: [codex, plugin, release]
related: [m1frame, m1frame Studio]
created: 2026-10-01
---

# Local Codex Plugin

[[m1frame]] has a downloadable local Codex integration in plugins/m1frame, with a repository marketplace at .agents/plugins/marketplace.json. Runtime state remains outside installed plugin caches. The wrapper adds effect annotations, bounded sensor calls, and health-checked [[m1frame Studio]] startup.

Verified on Windows: 164 upstream offline checks, 61 regression tests, Ruff, mypy, MCP tool behavior, and a Studio demo. Live provider completion remains unverified because the test Claude CLI requests timed out; this is explicitly a preview. See CODEX-PLUGIN.md and the plugin VALIDATION.md.
