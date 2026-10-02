# Install the m1frame Codex plugin

This is the public local preview. It provides nine MCP tools, a workflow skill, persistent local state, an isolated dependency setup, and a custom observatory icon.

```sh
python plugins/m1frame/scripts/setup.py
codex plugin marketplace add .
codex plugin add m1frame@m1frame-local
```

Then start a new Codex chat. See [full setup and configuration](plugins/m1frame/README.md) and [verified checks and remaining limits](plugins/m1frame/VALIDATION.md). Live execution completed on a free model, but its council rejected the report. Offline, browser, semantic-search and optional-adapter checks passed. This is a GitHub marketplace preview, not a universal-directory listing.

Update existing runtime code with `python plugins/m1frame/scripts/setup.py --upgrade-runtime`. See [module audit](MODULE-AUDIT.md) for repaired bugs and remaining live-test requirements.
