"""python -m frontdoor [chat|ask|serve] — the portable entry points.

  python -m frontdoor chat                      interactive REPL (every prompt routed)
  python -m frontdoor ask "plan a FastAPI app"  one-shot
  python -m frontdoor serve --port 8765         OpenAI-compatible API for any app
  --backend ollama|openrouter|openai|claude|claudecli|lmstudio|...   override config.yaml
  --mode auto|full|chat
"""
from __future__ import annotations

import argparse
import json
import sys


def _approve_cli(name: str, args: dict) -> bool:
    print(f"\n[approval] tool '{name}' wants to run with {json.dumps(args)[:300]}")
    return input("allow? [y/N] ").strip().lower() == "y"


def _frontdoor(backend: str | None, interactive: bool):
    from frontdoor.agent import FrontDoor
    from llm_client import LLMClient
    return FrontDoor(LLMClient(override_backend=backend),
                     approve=_approve_cli if interactive else None)


def main(argv=None) -> None:
    p = argparse.ArgumentParser(prog="frontdoor")
    sub = p.add_subparsers(dest="cmd", required=True)
    for name in ("chat", "ask", "serve"):
        sp = sub.add_parser(name)
        sp.add_argument("--backend", default=None)
        if name != "serve":
            sp.add_argument("--mode", default="auto", choices=["auto", "full", "chat"])
        if name == "ask":
            sp.add_argument("prompt")
        if name == "serve":
            sp.add_argument("--host", default="127.0.0.1")
            sp.add_argument("--port", type=int, default=8765)
    a = p.parse_args(argv)

    if a.cmd == "serve":
        import uvicorn

        from frontdoor.agent import FrontDoor
        from frontdoor.openai_server import build_app
        from llm_client import LLMClient
        app = build_app(lambda: FrontDoor(LLMClient(override_backend=a.backend)))
        print(f"m1frame front door on http://{a.host}:{a.port}/v1  (models: m1frame, m1frame-full, m1frame-chat)")
        uvicorn.run(app, host=a.host, port=a.port)
        return

    fd = _frontdoor(a.backend, interactive=sys.stdin.isatty())
    if a.cmd == "ask":
        r = fd.handle(a.prompt, mode=a.mode)
        print(r.answer, f"\n\n[{r.receipt()}]", sep="")
        return

    print("m1frame front door — /run <goal> forces the full pipeline, /quick <q> skips tools, Ctrl-D exits.")
    history: list[dict] = []
    while True:
        try:
            line = input("\nyou › ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return
        if not line:
            continue
        r = fd.handle(line, history=history, mode=a.mode)
        print(f"\nm1frame › {r.answer}\n[{r.receipt()}]")
        history += [{"role": "user", "content": line}, {"role": "assistant", "content": r.answer}]
        history = history[-20:]


if __name__ == "__main__":
    main()
