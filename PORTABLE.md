# Portable front door

m1frame's pillars were already provider-neutral, but the part that *absorbs a prompt
and decides to use them* lived in `AGENTS.md`, `CLAUDE.md` and a `UserPromptSubmit`
hook. Only coding hosts (Claude Code, Codex) read those, so everywhere else a prompt
was just a prompt. `frontdoor/` moves that contract into the runtime.

```
any app / CLI / gateway
        │  prompt
        ▼
  FrontDoor (any backend in config.yaml)
        ├─ chat  → answer directly
        ├─ auto  → tool loop: registry tools + wiki_query + m1frame_context + m1frame_run
        └─ full  → wiki recall → m1frame_run (enforced, no model choice involved)
        ▼
  answer + receipt of what actually ran
```

## Use it

```bash
pip install -r requirements.txt
python -m frontdoor chat                         # REPL; /run <goal> forces the pipeline, /quick skips tools
python -m frontdoor ask "plan a FastAPI service" --backend ollama
python -m frontdoor serve --port 8765            # OpenAI-compatible API
```

`serve` makes m1frame look like a model. In any app with a custom OpenAI base URL
(Open WebUI, LibreChat, Jan, Msty, Continue, Cline, n8n, the `openai` SDK):

| setting  | value |
|---|---|
| base URL | `http://localhost:8765/v1` |
| API key  | value of `M1FRAME_PROXY_KEY` (any string if unset) |
| model    | `m1frame` (agent decides) · `m1frame-full` (always full pipeline) · `m1frame-chat` (no tools) |

The brain is whatever `backend:` says in `config.yaml` — Claude, OpenAI, OpenRouter,
Ollama, LM Studio, vLLM… Point the app at m1frame, and m1frame at the model.

## What changed for non-Claude models

- **Tool calls no longer silently fail.** `agents/tool_loop.py` required the whole reply
  to be bare JSON. GPT, Gemini, Llama, Qwen and Gemma usually fence it or add a preamble,
  so tool calls were treated as final answers. `frontdoor/protocol.py` finds the call
  anywhere in the reply and accepts the common key drifts (`tool`, `name` + `parameters`).
- **Routing doesn't depend on the host obeying instructions.** `full` mode and
  `m1frame-full` call the pipeline directly.
- Dangerous tools (e.g. `write_file`) stay denied unless approved: the REPL asks; HTTP denies.

## Limits

- Weak local models (≈7B and below) choose tools less reliably in `auto`; use `full` for them.
- `judge_model` routing still applies only on `claude`/`claudecli`; other backends use one model.
- Streaming sends the finished answer as one chunk (the pipeline is multi-stage).
- Tests: `python -m unittest scripts.test_frontdoor` (offline, 18 tests).
