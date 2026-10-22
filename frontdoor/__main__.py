"""python -m frontdoor [chat|ask|serve] — the portable entry points.

  python -m frontdoor chat                      interactive REPL (every prompt routed)
  python -m frontdoor ask "plan a FastAPI app"  one-shot
  python -m frontdoor serve --port 8765         OpenAI-compatible API for any app
  --backend ollama|openrouter|openai|claude|claudecli|lmstudio|...   override config.yaml
  --mode auto|full|chat                         default: frontdoor.default_mode in config.yaml
"""
from __future__ import annotations

import argparse
import json
import os
import sys


def _approve_cli(name: str, args: dict) -> bool:
    print(f"\n[approval] tool '{name}' wants to run with {json.dumps(args)[:300]}")
    return input("allow? [y/N] ").strip().lower() == "y"


def main(argv=None) -> None:
    p = argparse.ArgumentParser(prog="frontdoor", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    for name in ("chat", "ask", "serve"):
        sp = sub.add_parser(name)
        sp.add_argument("--backend", default=None)
        sp.add_argument("--config", default="config.yaml")
        if name != "serve":
            sp.add_argument("--mode", default=None, choices=["auto", "full", "chat"])
        if name == "ask":
            sp.add_argument("prompt")
        if name == "serve":
            sp.add_argument("--host", default="127.0.0.1")
            sp.add_argument("--port", type=int, default=8765)
    a = p.parse_args(argv)

    from frontdoor.agent import FrontDoor

    if a.cmd == "serve":
        from frontdoor.openai_server import LOOPBACK, build_app
        if a.host not in LOOPBACK and not os.environ.get("M1FRAME_PROXY_KEY"):
            p.error("binding beyond loopback requires M1FRAME_PROXY_KEY")
        import uvicorn
        app = build_app(lambda: FrontDoor.from_config(a.backend, a.config))
        print(f"m1frame front door on http://{a.host}:{a.port}/v1 "
              "(models: m1frame, m1frame-full, m1frame-chat)")
        uvicorn.run(app, host=a.host, port=a.port)
        return

    interactive = sys.stdin.isatty()
    fd = FrontDoor.from_config(a.backend, a.config, approve=_approve_cli if interactive else None)
    if a.cmd == "ask":
        try:
            r = fd.handle(a.prompt, mode=a.mode)
        except ValueError as exc:
            sys.exit(str(exc))
        print(r.answer, f"\n\n[{r.receipt()}]", sep="")
        return

    print("m1frame front door — /run <goal> forces the full pipeline, "
          "/quick <q> skips tools, Ctrl-D exits.")
    history: list[dict] = []
    while True:
        try:
            line = input("\nyou › ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return
        if not line:
            continue
        try:
            r = fd.handle(line, history=history, mode=a.mode)
        except ValueError as exc:
            print(f"\nm1frame › {exc}")
            continue
        print(f"\nm1frame › {r.answer}\n[{r.receipt()}]")
        history += [{"role": "user", "content": line}, {"role": "assistant", "content": r.answer}]
        history = history[-20:]


if __name__ == "__main__":
    main()
