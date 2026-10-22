# Portable m1frame

m1frame's pillars were always provider-neutral, but the part that *absorbs a prompt and
decides to use them* lived in `AGENTS.md`, `CLAUDE.md` and a `UserPromptSubmit` hook. Only
coding hosts (Claude Code, Codex) read those, so everywhere else a prompt was just a prompt,
and non-Claude models silently skipped their tool calls. The front door fixes both.

## Architecture: one runtime, four doors

m1frame is not a skill *or* an MCP server. It is a **runtime** (the Python package that
actually plans, debates, investigates, executes, reviews and remembers). Each surface below
is a thin door into that same runtime, chosen by where the prompt comes from.

```
                         ┌──────────────── m1frame runtime ────────────────┐
  chat apps ── /v1 API ──┤                                                 │
  (Open WebUI, Jan,      │   FrontDoor (main agent, any backend)           │
   LibreChat, n8n, SDK)  │     ├─ chat → direct answer                     │
                         │     ├─ auto → tools + wiki + context + pipeline │
  agent hosts ── MCP ────┤     └─ full → wiki recall → m1frame_run         │
  (Claude, Codex, Cursor,│                                                 │
   Gemini CLI, ChatGPT)  │   pipeline: BMAD → Council → OpenPlanter →      │
                         │   Miras → Karpathy → QA gate + red-team → Wiki  │
  messaging ── gateways ─┤                                                 │
  (Telegram/Slack/Discord)│  tools · learned skills · guardrails · receipts│
                         │                                                 │
  you ── CLI / Studio ───┤                                                 │
                         └─────────────────────────────────────────────────┘
       skill (SKILL.md) = instructions that teach a host *when* to open the MCP door
```

| Door | Use it when | Who drives |
|---|---|---|
| **MCP server** (`mcp_server.py`) | The host is already an agent (Claude Desktop/Code, Codex, Cursor, Gemini CLI, ChatGPT connectors). Primary door. | Host model calls `m1frame_run` / `m1frame_agent` / tools |
| **OpenAI-compatible API** (`/v1`) | The app only knows how to talk to a model | m1frame's FrontDoor |
| **Gateways** | Messages from Telegram / Slack / Discord / webhooks | m1frame's FrontDoor |
| **CLI + Studio** | You, directly; Studio to watch runs live | m1frame's FrontDoor / pipeline |
| **Skill** (`plugins/m1frame/skills/m1frame/SKILL.md`) | Hosts that support skills: tells the host when and how to use the MCP door | Host model |

Why not a skill alone: a skill is instructions; it can't run a council or keep a wiki
without something executing it, so it only works as well as the host model obeys it.
Why not MCP alone: MCP gives tools, but a host still has to decide to use them. The MCP
server now ships the routing contract as **server instructions**, which every MCP host
receives at connect time; the skill reinforces it where skills exist; and `m1frame_agent`
lets a weak or busy host hand the whole prompt to m1frame's own agent.

To reach m1frame from other devices and from hosted AIs (Claude, ChatGPT), see
**[REMOTE.md](REMOTE.md)**.

## Use it

```bash
pip install -r requirements.txt
python -m frontdoor chat                         # REPL; /run <goal> forces the pipeline, /quick skips tools
python -m frontdoor ask "plan a FastAPI service" --backend ollama
python -m frontdoor serve --port 8765            # standalone OpenAI-compatible API
python api/server.py                             # Studio on :8080, also serves /v1
python mcp_server.py                             # MCP (stdio); --http for remote/mobile
python -m gateways --telegram                    # TELEGRAM_BOT_TOKEN; messages go through the agent
```

`pip install -e .` also installs `m1frame-agent` (same as `python -m frontdoor`).

### As a "model" in any chat app

| setting  | standalone `serve` | Studio server |
|---|---|---|
| base URL | `http://localhost:8765/v1` | `http://localhost:8080/v1` |
| API key  | `M1FRAME_PROXY_KEY` (required beyond loopback) | `M1FRAME_API_TOKEN` |
| model    | `m1frame` · `m1frame-full` · `m1frame-chat` | same |

The brain is whatever `backend:` says in `config.yaml`. Point the app at m1frame, and
m1frame at the model.

### Over MCP

| Tool / prompt | What it does |
|---|---|
| `m1frame_agent(prompt, mode)` | Hand the whole prompt to m1frame's agent; returns answer + receipt |
| `m1frame_run(goal)` | Full 7-pillar pipeline |
| `m1frame_ask`, `m1frame_context`, `m1frame_list_tools`, `m1frame_list_skills`, `m1frame_call_tool` | Recall, inventory, tools |
| prompt `m1frame` | Slash-command style entry in hosts that show MCP prompts |

## Configuration

```yaml
frontdoor:
  default_mode: auto       # auto | full | chat
  max_steps: 8             # tool calls per prompt before a forced final answer
  tool_result_max_chars: 6000
  gateways: true           # route plain gateway messages through the agent
```

`controller.enabled: true` with `require_full_workflow` makes every door run the full
pipeline and refuse `chat`, consistent with `CONTROLLER.md`.

## Safety

- Dangerous tools (e.g. `write_file`) are denied unless approved: the REPL asks; HTTP, MCP
  `m1frame_agent` and gateways always deny. Model output can never approve.
- Prompts on the direct paths pass the input guardrail; tool results pass the ingest
  guardrail (secrets redacted, injection quarantined); direct answers pass the output
  guardrail. The pipeline applies its own gates.
- Studio webhooks start pipeline runs asynchronously and reply with the run id.

## What changed for non-Claude models

- `agents/tool_loop.py` required the whole reply to be bare JSON. GPT, Gemini, Llama, Qwen
  and Gemma usually fence it or add a preamble, so tool calls were treated as final
  answers. `frontdoor/protocol.py` finds the call anywhere in the reply and accepts the
  common key variants (`tool`, `name` + `parameters`).
- `--backend` overrides now carry through to the pipeline run.

## Limits

- Small local models (≈7B and below) choose tools less reliably in `auto`; use `full`.
- `council.judge_model` still only applies on `claude`/`claudecli`.
- Streaming returns the finished answer as one chunk (the pipeline is multi-stage).
- Tests: `python -m unittest scripts.test_frontdoor` (offline). Live-provider behaviour
  still needs verification per backend.
