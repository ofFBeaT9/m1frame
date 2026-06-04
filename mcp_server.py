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
    from agents.skills import SkillLibrary
    from dataclasses import asdict
    return [asdict(s) for s in SkillLibrary().all()]


@mcp.tool()
def m1frame_open_studio(port: int = 8080) -> str:
    """Launch the interactive m1frame Studio UI (real-time deliberation theatre)
    in the background and return its URL. Open the URL in a browser to watch runs,
    browse the knowledge graph, chat, and inspect skills.

    Args:
        port: Port to serve on (default 8080).
    """
    import subprocess
    env = {**os.environ, "PORT": str(int(port))}
    try:
        subprocess.Popen([sys.executable, str(ROOT / "api" / "server.py")],
                         env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         cwd=str(ROOT))
    except Exception as e:  # noqa: BLE001
        return f"could not start Studio: {e}"
    return f"m1frame Studio starting → http://localhost:{port}  (open it in a browser)"


if __name__ == "__main__":
    mcp.run()
