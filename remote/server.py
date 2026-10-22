"""Remote m1frame: one HTTPS service that any AI on any device can connect to.

    /mcp                 MCP (streamable HTTP), OAuth-protected. Add this URL as a custom
                         connector in Claude, ChatGPT (developer mode), Cursor, Gemini CLI...
    /login               owner sign-in page shown during a connector's OAuth flow
    /.well-known/...     OAuth discovery, /register (DCR), /authorize, /token, /revoke
    /v1/...              OpenAI-compatible API for chat apps (M1FRAME_API_TOKEN or an OAuth token)
    /health              liveness

It serves the same tools as mcp_server.py (minus the local-only Studio launcher), runs
them off the event loop so a long pipeline never freezes other clients, and adds
m1frame_start / m1frame_result for runs that outlast a host's tool timeout.
"""
from __future__ import annotations

import asyncio
import functools
import hmac
import os
from pathlib import Path
from urllib.parse import urlparse

import anyio

from remote.auth import SCOPE, OwnerOAuthProvider, login_page
from remote.jobs import JobStore

LOCAL_ONLY_TOOLS = {"m1frame_open_studio"}   # starts a process on the server; not for remote hosts
EFFECTS = {   # (readOnly, destructive, openWorld) — mirrors plugins/m1frame/scripts/plugin_server.py
    "m1frame_context": (True, False, False), "m1frame_run": (False, True, True),
    "m1frame_agent": (False, True, True), "m1frame_ask": (True, False, False),
    "m1frame_list_tools": (True, False, False), "m1frame_call_tool": (False, True, True),
    "m1frame_list_skills": (True, False, False), "m1frame_scan_architecture": (True, False, False),
    "m1frame_optimize_skill": (True, False, False),
    "m1frame_start": (False, True, True), "m1frame_result": (True, False, False),
}
REMOTE_NOTE = """

Remote use: a full pipeline can take several minutes. If this host may time out on long
tool calls, use m1frame_start (returns a job id immediately) and then m1frame_result."""


def _threaded(fn):
    """Run a sync tool in a worker thread so the server stays responsive."""
    @functools.wraps(fn)
    async def wrapper(*args, **kwargs):
        return await anyio.to_thread.run_sync(functools.partial(fn, *args, **kwargs))
    return wrapper


def _client_ip(request) -> str:
    for header in ("cf-connecting-ip", "x-forwarded-for"):
        value = request.headers.get(header)
        if value:
            return value.split(",")[0].strip()
    return request.client.host if request.client else "?"


def build(public_url: str, owner_password: str, state_dir: str | Path = "runs",
          api_token: str = "", allowed_redirect_hosts: list[str] | None = None, upstream=None):
    """Return (asgi_app, fastmcp_server, oauth_provider)."""
    from mcp.server.auth.settings import AuthSettings, ClientRegistrationOptions, RevocationOptions
    from mcp.server.fastmcp import FastMCP
    from mcp.types import ToolAnnotations
    from pydantic import AnyHttpUrl
    from starlette.responses import HTMLResponse, JSONResponse, RedirectResponse
    from starlette.routing import Mount

    if upstream is None:
        import mcp_server as upstream
    public_url = public_url.rstrip("/")
    state_dir = Path(state_dir)
    provider = OwnerOAuthProvider(public_url, owner_password, state_dir / "remote_auth.json",
                                  allowed_redirect_hosts)
    auth = AuthSettings(
        issuer_url=AnyHttpUrl(public_url), resource_server_url=AnyHttpUrl(f"{public_url}/mcp"),
        client_registration_options=ClientRegistrationOptions(
            enabled=True, valid_scopes=[SCOPE], default_scopes=[SCOPE]),
        revocation_options=RevocationOptions(enabled=True),
        required_scopes=[SCOPE], validate_token_resource=False)
    server = FastMCP("m1frame", instructions=upstream.ROUTING_INSTRUCTIONS + REMOTE_NOTE,
                     auth_server_provider=provider, auth=auth, host="0.0.0.0")

    # Same tools as the local server, executed in threads.
    for tool in upstream.mcp._tool_manager.list_tools():
        if tool.name in LOCAL_ONLY_TOOLS:
            continue
        ro, de, ow = EFFECTS.get(tool.name, (False, True, True))
        fn = tool.fn if tool.is_async else _threaded(tool.fn)
        server._tool_manager._tools[tool.name] = tool.model_copy(update={
            "fn": fn, "is_async": True,
            "annotations": ToolAnnotations(readOnlyHint=ro, destructiveHint=de, openWorldHint=ow)})
    for prompt in upstream.mcp._prompt_manager.list_prompts():
        server.add_prompt(prompt)

    def runner(text: str, kind: str) -> str:
        if kind == "agent":
            return upstream.m1frame_agent(text, mode="auto")
        return upstream.m1frame_run(text)
    jobs = JobStore(state_dir / "remote_jobs", runner)

    def annotations(name):
        ro, de, ow = EFFECTS[name]
        return ToolAnnotations(readOnlyHint=ro, destructiveHint=de, openWorldHint=ow)

    @server.tool(annotations=annotations("m1frame_start"))
    def m1frame_start(goal: str, mode: str = "full") -> dict:
        """Start m1frame in the background and return a job id immediately.

        Use this instead of m1frame_run when the host might time out on a long call.

        Args:
            goal: The user's goal or prompt, verbatim.
            mode: "full" runs the 7-pillar pipeline; "auto" lets m1frame's agent decide.
        """
        return jobs.start(goal, "agent" if mode == "auto" else "run")

    @server.tool(annotations=annotations("m1frame_result"))
    def m1frame_result(job_id: str) -> dict:
        """Check a job started with m1frame_start. status: running | done | failed."""
        return jobs.get(job_id)

    # Every tool (including the two above) runs off the event loop.
    for name, tool in list(server._tool_manager._tools.items()):
        if not tool.is_async:
            server._tool_manager._tools[name] = tool.model_copy(
                update={"fn": _threaded(tool.fn), "is_async": True})

    # ── owner sign-in (part of the OAuth authorize step) ─────────────────
    @server.custom_route("/login", methods=["GET", "POST"])
    async def login(request):
        if request.method == "GET":
            req = request.query_params.get("req", "")
            form = {}
        else:
            form = dict(await request.form())
            req = str(form.get("req", ""))
        pending = provider.pending(req)
        if pending is None:
            return HTMLResponse("<p>This sign-in link expired. Start the connection again from "
                                "your app.</p>", status_code=400)
        client = await provider.get_client(pending[0])
        name = (client.client_name if client else None) or "An app"
        host = urlparse(str(pending[1].redirect_uri)).hostname or "?"
        if request.method == "GET":
            return HTMLResponse(login_page(name, host, req))
        if form.get("action") == "deny":
            target = provider.deny(req)
            return RedirectResponse(target, status_code=302) if target else HTMLResponse("Denied.")
        ip = _client_ip(request)
        if provider.locked_out(ip):
            return HTMLResponse(login_page(name, host, req, "Too many attempts. Try again in 15 minutes."),
                                status_code=429)
        if not provider.check_password(str(form.get("password", "")), ip):
            await asyncio.sleep(1)
            return HTMLResponse(login_page(name, host, req, "Wrong password."), status_code=401)
        return RedirectResponse(provider.approve(req), status_code=302)

    @server.custom_route("/health", methods=["GET"])
    async def health(_request):
        return JSONResponse({"status": "ok", "mcp": f"{public_url}/mcp", "v1": f"{public_url}/v1"})

    app = server.streamable_http_app()

    # ── OpenAI-compatible /v1 for chat apps ──────────────────────────────
    from fastapi import FastAPI, HTTPException

    from frontdoor.openai_server import register_routes
    v1 = FastAPI(title="m1frame /v1", docs_url=None, redoc_url=None, openapi_url=None)

    def check(request):
        header = request.headers.get("authorization", "")
        token = header[7:] if header.startswith("Bearer ") else ""
        if token and ((api_token and hmac.compare_digest(api_token.encode(), token.encode()))
                      or provider.access_valid(token)):
            return
        raise HTTPException(401, "send Authorization: Bearer <M1FRAME_API_TOKEN>")

    register_routes(v1, check_auth=check, prefix="")
    app.router.routes.append(Mount("/v1", app=v1))
    return app, server, provider


def main(argv=None) -> None:
    import argparse
    p = argparse.ArgumentParser(prog="python -m remote", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--public-url", default=os.environ.get("M1FRAME_PUBLIC_URL", ""),
                   help="HTTPS address people reach this server at (env M1FRAME_PUBLIC_URL)")
    p.add_argument("--host", default=os.environ.get("HOST", "0.0.0.0"))
    p.add_argument("--port", type=int, default=int(os.environ.get("PORT", "8765")))
    p.add_argument("--state-dir", default=os.environ.get("M1FRAME_STATE_DIR", "runs"))
    p.add_argument("--revoke-all", action="store_true", help="sign out every connected app and exit")
    a = p.parse_args(argv)
    from dotenv import load_dotenv
    load_dotenv(Path(".env").resolve(), override=False)   # same .env the model keys live in
    if not a.public_url:
        a.public_url = os.environ.get("M1FRAME_PUBLIC_URL", "")
    if "HOST" in os.environ and a.host == "0.0.0.0":
        a.host = os.environ["HOST"]
    if "PORT" in os.environ and a.port == 8765:
        a.port = int(os.environ["PORT"])

    password = os.environ.get("M1FRAME_OWNER_PASSWORD", "")
    if not a.public_url:
        p.error("set M1FRAME_PUBLIC_URL (e.g. https://m1frame.example.com)")
    allowed = [h for h in os.environ.get("M1FRAME_ALLOWED_REDIRECT_HOSTS", "").split(",") if h.strip()]
    try:
        app, _server, provider = build(a.public_url, password, a.state_dir,
                                       os.environ.get("M1FRAME_API_TOKEN", ""), allowed)
    except ValueError as exc:
        p.error(str(exc))
    if a.revoke_all:
        print(f"Revoked {provider.revoke_all()} tokens. Every app must sign in again.")
        return
    import uvicorn
    url = a.public_url.rstrip("/")
    print("-" * 64)
    print("  m1frame remote")
    print(f"  MCP connector URL : {url}/mcp")
    print(f"  Chat-app base URL : {url}/v1   (key: M1FRAME_API_TOKEN)")
    print(f"  Listening on      : {a.host}:{a.port}")
    print("-" * 64)
    uvicorn.run(app, host=a.host, port=a.port, proxy_headers=True, forwarded_allow_ips="*")
