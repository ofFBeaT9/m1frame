"""Offline integration checks. Run with the plugin's configured Python interpreter."""
import asyncio
import json
import os
from pathlib import Path
import socket
import signal
import sys
import tempfile
from datetime import timedelta

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def check(plugin, runtime):
    env = dict(os.environ, M1FRAME_HOME=str(runtime), PYTHONUTF8="1", PYTHONDONTWRITEBYTECODE="1")
    for key in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "OPENROUTER_API_KEY", "M1FRAME_API_TOKEN"):
        env.pop(key, None)
    params = StdioServerParameters(command=sys.executable, args=[str(plugin / "scripts/launch.py")], env=env)
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write, read_timeout_seconds=timedelta(seconds=45)) as client:
            await client.initialize()
            tools = await client.list_tools()
            assert len(tools.tools) == 9
            for tool in tools.tools:
                assert all(isinstance(getattr(tool.annotations, field), bool) for field in
                           ("readOnlyHint", "destructiveHint", "openWorldHint"))

            async def call(name, args):
                result = await client.call_tool(name, args)
                return result, "\n".join(getattr(c, "text", "") for c in result.content)

            for name, args in [("m1frame_context", {"query": "offline verification"}),
                               ("m1frame_list_tools", {}), ("m1frame_list_skills", {}),
                               ("m1frame_ask", {"question": "What is m1frame?", "max_pages": 1})]:
                result, text = await call(name, args)
                assert not result.isError and text, name
            result, text = await call("m1frame_call_tool", {"name": "calculator", "args": {"expression": "2*(3+4)"}})
            assert not result.isError and text == "14"
            payload = {"name": "write_file", "args": {"path": "verification.txt", "content": "test fixture"}}
            result, text = await call("m1frame_call_tool", payload)
            assert "approv" in text.lower() and not (runtime / "verification.txt").exists()
            result, text = await call("m1frame_call_tool", dict(payload, approve=True))
            assert not result.isError and (runtime / "verification.txt").read_text() == "test fixture"
            result, text = await call("m1frame_call_tool", {"name": "read_file", "args": {"path": "../outside.txt"}})
            assert "error" in text.lower() or "outside" in text.lower()
            result, text = await call("m1frame_call_tool", {"name": "nonexistent_tool"})
            assert "unknown tool" in text.lower()
            result, text = await call("m1frame_optimize_skill", {"text": "Test test the code with tests.", "keywords": ["test", "code"], "rounds": 3})
            score = json.loads(text)
            assert not result.isError and score["after_score"] >= score["before_score"]
            result, text = await call("m1frame_scan_architecture", {"path": "agents", "timeout": 2})
            assert not result.isError and "sensor" in json.loads(text)
            with socket.socket() as sock:
                sock.bind(("127.0.0.1", 0))
                port = sock.getsockname()[1]
            result, text = await call("m1frame_open_studio", {"port": port})
            assert not result.isError and json.loads(text)["status"] == "running", text
            studio_pid = json.loads(text)["pid"]
            result, text = await call("m1frame_open_studio", {"port": port})
            assert not result.isError and json.loads(text)["status"] == "already_running"
            result, text = await call("m1frame_open_studio", {"port": -1})
            assert result.isError
            os.kill(studio_pid, signal.SIGTERM)
            result, text = await call("m1frame_run", {"goal": "Reply with one line.", "skip_council": True, "skip_wiki": True})
            assert result.isError, "Missing credentials must not produce a fabricated success"
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as client:
            await client.initialize()
            assert (runtime / "verification.txt").read_text() == "test fixture"
    print("PASS: discovery, annotations, offline tools, write approval, traversal rejection, optimizer, sensor availability, Studio lifecycle, missing credentials, persistence")


if __name__ == "__main__":
    plugin_path = Path(__file__).resolve().parents[1]
    with tempfile.TemporaryDirectory(prefix="m1frame-plugin-check-") as directory:
        asyncio.run(check(plugin_path, Path(directory) / "runtime"))
