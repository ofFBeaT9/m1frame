# m1frame for Codex — local preview

Nine MCP tools, persistent local knowledge, and the m1frame workflow skill. Published by [ofFBeaT9](https://github.com/ofFBeaT9) from [m1frame](https://github.com/ofFBeaT9/m1frame). MIT licensed source; model-provider usage can incur separate charges.

![m1frame observatory icon](assets/observatory-icon.png)

## Install

Requirements: Codex with local plugin support, Git, and Python 3.10+ available as `python`.

```sh
git clone --branch m1frame-plugin-v0.1.0 --single-branch https://github.com/ofFBeaT9/m1frame.git m1frame-plugin
cd m1frame-plugin
python plugins/m1frame/scripts/setup.py
codex plugin marketplace add .
codex plugin add m1frame@m1frame-local
```

Start a new Codex chat and select **m1frame**. If the marketplace is not visible in the app, restart it. The marketplace name is `m1frame-local`; the plugin identifier is `m1frame`.

Alternatively, extract `m1frame-marketplace.zip`, open a terminal in its top-level folder, and run the last three commands. The smaller `m1frame-plugin.zip` contains just the plugin for your own marketplace; it does not include a marketplace catalog.

Setup installs dependencies into an isolated `.venv` under `~/Documents/Codex/m1frame-data`; the launcher automatically uses it. On Windows this is inside your user profile's Documents/Codex directory. No model key is needed for setup or offline tools. If Python is not available as `python`, use its actual executable for setup and set the MCP command in both mcp.json and .mcp.json to that executable before installation.

## Configure live workflows

Edit config.yaml in the persistent runtime to select a provider and an available model. Use the adjacent .env.example to create a local .env with your provider key, or supply environment variables. Keep credentials out of the plugin folder and Git.

Full workflows may make multiple paid model calls. Live provider execution is **not verified in this preview**: a tiny request through the test computer's existing Claude CLI login timed out. The full pipeline passed offline mock tests. Studio's bundled demo is recorded example content, not a live provider result.

## Try it

- “Show my m1frame tools and skills.”
- “Ask m1frame about architecture decisions in its knowledge base.”
- “Use m1frame to deliberate on this goal: …”
- “Open m1frame Studio.”

Bundled wiki pages and learned recipes are upstream examples, not your history. Studio starts only when requested, binds to loopback, and reports its URL after a health check. It may end when the parent MCP session closes; request it again in a later chat.

## State and updates

State lives under M1FRAME_HOME when set, otherwise ~/Documents/Codex/m1frame-data. Set M1FRAME_HOME to an absolute existing complete m1frame checkout or a new directory before setup and before launching Codex. Existing runtime files are never overwritten by setup or plugin updates.

The wrapper adds no analytics or remote account service. Live workflows send prompts and relevant context to your configured provider; individual tools may make network requests when invoked. Wiki, skills, runs and logs are stored locally. Review files before sharing them. This is a local single-user integration.

Back up your runtime and update it separately, or select a new M1FRAME_HOME for a fresh bundled copy. Removing the plugin does not delete persistent data.

## Tools and limits

Includes m1frame_context, m1frame_run, m1frame_ask, m1frame_list_tools, m1frame_call_tool, m1frame_list_skills, m1frame_scan_architecture, m1frame_optimize_skill, and m1frame_open_studio.

The wrapper declares tool effects, preserves approval gates, bounds sensor timeouts, and checks Studio startup. Sentrux is optional: the Rust project and the similarly named PyPI package are different tools. Skill optimization returns revised text without automatically saving it.

This public GitHub marketplace is not a reviewed universal ChatGPT/Codex directory listing. It does not run in ChatGPT web/mobile by itself.

## Verification and support

See [VALIDATION.md](VALIDATION.md). Run tests/check_mcp.py with the Python executable in your runtime's .venv to repeat the offline checks. Tests use temporary data and need permission for subprocesses and loopback networking.

Report problems at [m1frame issues](https://github.com/ofFBeaT9/m1frame/issues), with your OS, Python/plugin versions and a redacted error. Never include keys or private wiki content.

The unchanged bundled runtime is version 1.10.1, commit fbb06dd5cb066d26627e3dc88868312016cebdbe. Integration fixes live in scripts/plugin_server.py. Plugin version: 0.1.0. See LICENSE for upstream attribution and terms.
