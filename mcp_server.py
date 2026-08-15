#!/usr/bin/env python3
"""
mcp_server.py — m1frame as an MCP server for Claude Code (and any MCP client).

Exposes the whole framework over stdio so Claude Code's agent can:
  • run the 7-pillar deliberation on a goal               → m1frame_run
  • ask the grounded knowledge graph (offline, cited)     → m1frame_ask
  • call any of m1frame's 40 auditable tools              → m1frame_call_tool
  • discover tools / learned skills                       → m1frame_list_tools / m1frame_list_skills
  • launch the interactive Studio UI                      → m1frame_open_studio

Register it with Claude Code (already wired in .mcp.json at the repo root):
    claude mcp add m1frame -- python mcp_server.py
or just open this project in Claude Code — `.mcp.json` is picked up automatically.

The `mcp` dependency is optional and only needed to RUN the server:
    pip install mcp
The rest of m1frame works without it.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

try:
    from mcp.server.fastmcp import FastMCP
except Exception:  # noqa: BLE001
    sys.exit("The m1frame MCP server needs the MCP SDK. Install it with:  pip install mcp")

mcp = FastMCP("m1frame")

# ── Studio (UI) helpers — auto-start + a reachable URL for phones ──────────────
_STUDIO_BIND = os.environ.get("M1_STUDIO_BIND", "127.0.0.1")


def _studio_url(port: int = 8080) -> str:
    host = os.environ.get("M1_STUDIO_HOST") or (
        "localhost" if _STUDIO_BIND in ("127.0.0.1", "0.0.0.0") else _STUDIO_BIND)
    return f"http://{host}:{int(port)}"


def _start_studio(port: int = 8080) -> None:
    """Start the Studio web server in the background so the UI loads automatically."""
    import subprocess
    env = {**os.environ, "PORT": str(int(port)), "HOST": _STUDIO_BIND}
    try:
        subprocess.Popen([sys.executable, str(ROOT / "api" / "server.py")],
                         env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, cwd=str(ROOT))
    except Exception:  # noqa: BLE001
        pass


@mcp.tool()
def m1frame_run(goal: str, skip_council: bool = False, skip_wiki: bool = False) -> str:
    """Run m1frame's full 7-pillar deliberation on a goal and return the verdict.

    Use this for any non-trivial decision, design, or investigation where you want
    a *deliberated, grounded* answer rather than a one-shot reply: BMAD planning →
    council brainstorm → investigation → multi-agent execution → chain-of-thought
    refinement → a council QA gate with an independent red-team → knowledge-graph
    ingest. Uses m1frame's configured backend (set `backend: claudecli` in
    config.yaml to run on your Claude Code login with no API key).

    Args:
        goal: The question or task to deliberate (e.g. "Should we use REST or gRPC?").
        skip_council: Skip the council brainstorm + QA gate (faster, less rigorous).
        skip_wiki: Skip writing the result into the knowledge graph.

    Returns: Markdown with the final answer, the council score, and pass/fail.
    """
    from scripts.run_workflow import run_workflow
    res = run_workflow(goal=goal, verbose=False, skip_council=skip_council,
                       skip_wiki=skip_wiki)
    verdict = res.get("verdict")
    state = res.get("state")
    output = ((verdict.approved_output if verdict and getattr(verdict, "approved_output", None)
               else (state.final_output() if state else "")) or "(no output)")
    score = getattr(verdict, "consensus_score", None) if verdict else None
    passed = getattr(verdict, "passed", None) if verdict else None
    head = f"**Score:** {score}/10  ·  **Gate:** {'PASS' if passed else 'review'}\n\n" if verdict else ""
    return head + output


@mcp.tool()
def m1frame_ask(question: str, max_pages: int = 3) -> str:
    """Answer a question grounded in m1frame's knowledge graph, with citations.

    Fast and offline (no LLM call) — keyword-retrieves the most relevant wiki
    pages and returns their key lines plus a citation list. Use this to recall
    what prior m1frame runs concluded before deciding anything.

    Args:
        question: What to look up in the knowledge graph.
        max_pages: How many pages to cite (default 3).
    """
    from gateways.handlers import grounded_answer
    return grounded_answer(question, max_pages=max_pages)


@mcp.tool()
def m1frame_list_tools() -> list:
    """List m1frame's built-in agent tools (name, description, schema, dangerous?).

    These are 40 small, auditable, offline tools (calculator, json/csv/yaml,
    hashing, regex, diff, sandboxed file ops, etc.). Call one with m1frame_call_tool.
    """
    from tools import default_registry
    return default_registry().list()


@mcp.tool()
def m1frame_call_tool(name: str, args: dict | None = None, approve: bool = False) -> str:
    """Invoke one of m1frame's built-in tools by name.

    Args:
        name: Tool name (see m1frame_list_tools), e.g. "calculator", "sha256".
        args: Keyword arguments for the tool, e.g. {"expression": "2*(3+4)"}.
        approve: Must be true to run a tool marked `dangerous` (e.g. write_file).

    Returns: The tool's result as a string (JSON-encoded if structured).
    """
    import json

    from tools import default_registry
    reg = default_registry()
    if name not in reg:
        return f"unknown tool '{name}'. Use m1frame_list_tools to see options."
    try:
        result = reg.call(name, args or {}, approved=approve)
    except PermissionError as e:
        return f"{e}. Re-call with approve=true to run this dangerous tool."
    except Exception as e:  # noqa: BLE001
        return f"tool error: {e}"
    return result if isinstance(result, str) else json.dumps(result, ensure_ascii=False)


@mcp.tool()
def m1frame_list_skills() -> list:
    """List the council-vetted skills m1frame has learned (title, score, uses, approach)."""
    from dataclasses import asdict

    from agents.skills import SkillLibrary
    return [asdict(s) for s in SkillLibrary().all()]


@mcp.tool()
def m1frame_scan_architecture(path: str = ".", council_score: float | None = None) -> str:
    """Measure the architectural quality of code with the Sentrux sensor, and fuse the
    measurement with a council score into one QA verdict.

    Gives objective structural evidence (0-10000 across modularity, acyclicity, depth,
    equality, redundancy) next to m1frame's LLM judgement. Requires the optional
    Sentrux binary (`pip install sentrux`); without it this reports availability
    cleanly rather than failing.

    Args:
        path: Directory to scan, inside the workspace (default: repo root).
        council_score: Optional 0-10 council score to fuse the measurement with.
    """
    import json

    # Use the config-honouring constructors so this surface agrees with the HTTP
    # API and the ToolRegistry — sensors.enforce must not mean different things
    # depending on which door you came through.
    from sensors.tools import client, gate
    try:
        result = client().scan(path)
    except ValueError as e:
        return f"path rejected: {e}"
    verdict = gate().fuse(council_score, result)
    if not result.available:
        return (f"Sentrux is not installed — no structural measurement taken.\n"
                f"Install with: pip install sentrux\n"
                f"Verdict basis: {verdict.basis} ({verdict.verdict})")
    return json.dumps({"sensor": result.to_dict(), "verdict": verdict.to_dict()}, indent=2)


@mcp.tool()
def m1frame_optimize_skill(text: str, keywords: list[str] | None = None,
                           rounds: int = 12) -> str:
    """Improve a skill document so it covers the given keywords concisely, keeping an
    edit only when it measurably scores better (the SkillOpt mechanic).

    Runs on m1frame's dependency-free optimiser by default; delegates to Microsoft
    SkillOpt when that package is installed and exposes a compatible entry point.

    Args:
        text: The skill text to improve.
        keywords: Concepts the optimised skill should cover.
        rounds: How many bounded edits to propose (default 12).
    """
    import json

    from optimizers.tools import skill_optimize
    out = skill_optimize(text, keywords or [], rounds=rounds)
    return json.dumps({k: out[k] for k in
                       ("tier", "before_score", "after_score", "improved",
                        "accepted", "rounds", "after", "error")}, indent=2)


@mcp.tool()
def m1frame_open_studio(port: int = 8080) -> str:
    """Launch the interactive m1frame Studio UI (real-time deliberation theatre)
    in the background and return its URL. Open the URL in a browser to watch runs,
    browse the knowledge graph, chat, and inspect skills.

    Args:
        port: Port to serve on (default 8080).
    """
    _start_studio(port)
    url = _studio_url(port)
    return (f"m1frame Studio is starting → {url}\n"
            "Open it in a browser — on a phone, just tap the link. It's a mobile-responsive "
            "deliberation theatre: watch runs, browse the knowledge graph, chat, and inspect skills.")


def main(argv: list[str] | None = None) -> None:
    """stdio by default; `--http` serves MCP over HTTP so a phone's Claude app can
    connect by URL, and auto-starts the mobile-responsive Studio UI."""
    import argparse
    p = argparse.ArgumentParser(description="m1frame MCP server (Claude Code / mobile)")
    p.add_argument("--http", action="store_true",
                   help="Serve MCP over HTTP (mobile/remote clients connect by URL)")
    p.add_argument("--host", default="0.0.0.0", help="HTTP bind host (default 0.0.0.0)")
    p.add_argument("--port", type=int, default=8765, help="MCP HTTP port (default 8765)")
    p.add_argument("--studio-port", type=int, default=8080, help="Studio UI port (default 8080)")
    p.add_argument("--no-studio", action="store_true", help="Do not auto-start the Studio UI")
    args = p.parse_args(argv)

    if args.http:
        global _STUDIO_BIND
        _STUDIO_BIND = args.host
        os.environ["M1_STUDIO_BIND"] = args.host
        if not args.no_studio:
            _start_studio(args.studio_port)
        mcp.settings.host, mcp.settings.port = args.host, args.port
        bar = "-" * 60
        print(bar)
        print("  m1frame -- mobile / remote access")
        print(bar)
        print(f"  MCP endpoint : http://{args.host}:{args.port}/mcp")
        print(f"  Studio UI    : {_studio_url(args.studio_port)}")
        print(f"  Add to Claude: claude mcp add --transport http m1frame http://<this-host>:{args.port}/mcp")
        print("  On a phone   : Claude app -> Settings -> Connectors/MCP -> add that URL,")
        print("                 then ask m1frame anything and tap the Studio link to watch.")
        print(bar)
        mcp.run(transport="streamable-http")
    else:
        if os.environ.get("M1_AUTOSTART_STUDIO") and not args.no_studio:
            _start_studio(args.studio_port)
        mcp.run()   # stdio (Claude Code picks this up from .mcp.json)


if __name__ == "__main__":
    main()
