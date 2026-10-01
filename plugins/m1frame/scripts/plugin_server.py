"""Codex integration fixes around the unchanged upstream MCP server."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

from mcp.types import ToolAnnotations


def configure_server(upstream):
    server = upstream.mcp

    def scan_architecture(path: str = ".", council_score: float | None = None, timeout: int = 10) -> str:
        """Measure architecture using the optional Sentrux CLI, or report why unavailable."""
        from sensors.tools import client, gate
        try:
            reading = client(timeout=max(1, min(60, timeout))).scan(path)
        except ValueError as exc:
            return f"path rejected: {exc}"
        verdict = gate().fuse(council_score, reading)
        return json.dumps({
            "sensor": reading.to_dict(), "verdict": verdict.to_dict(),
            "installation_guidance": "For the Rust Sentrux project use https://github.com/sentrux/sentrux and its release instructions. The PyPI package named sentrux is unrelated.",
        }, indent=2)

    def open_studio(port: int = 8080) -> str:
        """Start local m1frame Studio and return its URL only after its health check passes."""
        if not 1024 <= port <= 65535:
            raise ValueError("Choose a port from 1024 to 65535.")
        url = f"http://127.0.0.1:{port}"
        token = os.environ.get("M1FRAME_API_TOKEN")
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

        def health():
            request = urllib.request.Request(url + "/health", headers=headers)
            try:
                with opener.open(request, timeout=1) as response:
                    payload = json.load(response)
                if payload.get("status") == "ok" and "can_run_live" in payload and "version" in payload:
                    return payload
                raise RuntimeError("This port is occupied by another service; choose another port.")
            except urllib.error.HTTPError as exc:
                raise RuntimeError(f"A service on this port returned HTTP {exc.code}; choose another port or check Studio authentication.") from None
            except urllib.error.URLError:
                return None

        ready = health()
        if ready:
            return json.dumps({"url": url, "status": "already_running", "can_run_live": ready["can_run_live"]})
        root = Path(upstream.ROOT)
        log = root / "studio-server.log"
        env = dict(os.environ, HOST="127.0.0.1", PORT=str(port), PYTHONUTF8="1")
        with log.open("ab") as output:
            process = subprocess.Popen(
                [sys.executable, str(root / "api/server.py")], cwd=root, env=env,
                stdin=subprocess.DEVNULL, stdout=output, stderr=output,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )
        for _ in range(40):
            if process.poll() is not None:
                raise RuntimeError(f"Studio exited with code {process.returncode}; inspect {log}.")
            ready = health()
            if ready:
                return json.dumps({"url": url, "status": "running", "pid": process.pid, "can_run_live": ready["can_run_live"]})
            time.sleep(0.25)
        process.terminate()
        process.wait(timeout=5)
        raise RuntimeError(f"Studio did not become ready; inspect {log}.")

    # Generic dispatch can include writes and network access, so declare its
    # broadest capabilities even when an individual request is read-only.
    effects = {
        "m1frame_context": (True, False, False),
        "m1frame_run": (False, True, True),
        "m1frame_ask": (True, False, False),
        "m1frame_list_tools": (True, False, False),
        "m1frame_call_tool": (False, True, True),
        "m1frame_list_skills": (True, False, False),
        "m1frame_scan_architecture": (True, False, False),
        "m1frame_optimize_skill": (True, False, False),
        "m1frame_open_studio": (False, False, False),
    }
    replacements = {"m1frame_scan_architecture": scan_architecture, "m1frame_open_studio": open_studio}
    for name, (read_only, destructive, open_world) in effects.items():
        function = replacements.get(name, getattr(upstream, name))
        server.remove_tool(name)
        server.add_tool(function, name=name, annotations=ToolAnnotations(
            readOnlyHint=read_only, destructiveHint=destructive, openWorldHint=open_world,
        ))
    return server
