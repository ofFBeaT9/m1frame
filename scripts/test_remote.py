"""Offline tests for remote m1frame (OAuth-protected MCP + /v1). No network, no API key."""
import base64
import hashlib
import re
import secrets
import tempfile
import time
import unittest
from urllib.parse import parse_qs, urlparse

try:
    import mcp_server  # noqa: F401
    HAVE_MCP = True
except SystemExit:
    HAVE_MCP = False

BASE = "http://127.0.0.1:8770"
PW = "correct-horse-battery"
ACCEPT = {"Accept": "application/json, text/event-stream"}
INIT = {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
    "protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "t", "version": "1"}}}


def pkce():
    verifier = secrets.token_urlsafe(48)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    return verifier, challenge


@unittest.skipUnless(HAVE_MCP, "mcp SDK not installed")
class RemoteServerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def client(self, **kw):
        from starlette.testclient import TestClient

        from remote.server import build
        app, server, provider = build(BASE, kw.pop("password", PW), self.tmp.name,
                                      api_token="k" * 20, **kw)
        tc = TestClient(app, base_url=BASE, follow_redirects=False)
        tc.__enter__()
        self.addCleanup(tc.__exit__, None, None, None)
        return tc, server, provider

    def register(self, c, redirect="https://claude.ai/api/mcp/auth_callback"):
        r = c.post("/register", json={"client_name": "Claude", "redirect_uris": [redirect],
                                      "grant_types": ["authorization_code", "refresh_token"],
                                      "response_types": ["code"], "token_endpoint_auth_method": "none"})
        return r

    def authorize(self, c, client_id, redirect="https://claude.ai/api/mcp/auth_callback"):
        verifier, challenge = pkce()
        r = c.get("/authorize", params={"response_type": "code", "client_id": client_id,
                  "redirect_uri": redirect, "code_challenge": challenge,
                  "code_challenge_method": "S256", "state": "xyz", "scope": "m1frame",
                  "resource": f"{BASE}/mcp"})
        self.assertEqual(r.status_code, 302, r.text)
        login = r.headers["location"]
        self.assertTrue(login.startswith(f"{BASE}/login?req="))
        page = c.get(login.replace(BASE, ""))
        self.assertIn("Connect to m1frame", page.text)
        self.assertIn("claude.ai", page.text)
        req = re.search(r'name="req" value="([^"]+)"', page.text).group(1)
        return req, verifier

    def connect(self, c):
        cid = self.register(c).json()["client_id"]
        req, verifier = self.authorize(c, cid)
        r = c.post("/login", data={"req": req, "password": PW, "action": "allow"})
        self.assertEqual(r.status_code, 302)
        q = parse_qs(urlparse(r.headers["location"]).query)
        self.assertEqual(q["state"], ["xyz"])
        tok = c.post("/token", data={"grant_type": "authorization_code", "code": q["code"][0],
                     "redirect_uri": "https://claude.ai/api/mcp/auth_callback", "client_id": cid,
                     "code_verifier": verifier})
        self.assertEqual(tok.status_code, 200, tok.text)
        return cid, tok.json()

    def test_discovery_metadata(self):
        c, *_ = self.client()
        meta = c.get("/.well-known/oauth-authorization-server").json()
        self.assertIn("registration_endpoint", meta)
        prm = c.get("/.well-known/oauth-protected-resource/mcp").json()
        self.assertEqual(prm["resource"], f"{BASE}/mcp")

    def test_full_flow_then_mcp_initialize(self):
        c, *_ = self.client()
        unauth = c.post("/mcp", json=INIT, headers=ACCEPT)
        self.assertEqual(unauth.status_code, 401)
        self.assertIn("resource_metadata", unauth.headers.get("www-authenticate", ""))
        _, tokens = self.connect(c)
        ok = c.post("/mcp", json=INIT, headers={**ACCEPT, "Authorization": f"Bearer {tokens['access_token']}"})
        self.assertEqual(ok.status_code, 200, ok.text)
        self.assertIn("m1frame_start", ok.text)        # routing instructions reach the host

    def test_code_is_single_use(self):
        c, *_ = self.client()
        cid = self.register(c).json()["client_id"]
        req, verifier = self.authorize(c, cid)
        code = parse_qs(urlparse(c.post("/login", data={"req": req, "password": PW, "action": "allow"})
                                 .headers["location"]).query)["code"][0]
        body = {"grant_type": "authorization_code", "code": code, "client_id": cid, "code_verifier": verifier,
                "redirect_uri": "https://claude.ai/api/mcp/auth_callback"}
        self.assertEqual(c.post("/token", data=body).status_code, 200)
        self.assertEqual(c.post("/token", data=body).status_code, 400)

    def test_wrong_password_then_lockout(self):
        c, *_ = self.client()
        cid = self.register(c).json()["client_id"]
        req, _ = self.authorize(c, cid)
        from remote import auth
        statuses = [c.post("/login", data={"req": req, "password": "nope-nope-nope", "action": "allow"}).status_code
                    for _ in range(auth.MAX_FAILS + 1)]
        self.assertEqual(statuses[0], 401)
        self.assertEqual(statuses[-1], 429)
        # Even the right password is refused during lockout.
        self.assertEqual(c.post("/login", data={"req": req, "password": PW, "action": "allow"}).status_code, 429)

    def test_deny_returns_access_denied(self):
        c, *_ = self.client()
        cid = self.register(c).json()["client_id"]
        req, _ = self.authorize(c, cid)
        r = c.post("/login", data={"req": req, "action": "deny"})
        self.assertIn("error=access_denied", r.headers["location"])

    def test_refresh_rotates(self):
        c, *_ = self.client()
        cid, tokens = self.connect(c)
        body = {"grant_type": "refresh_token", "refresh_token": tokens["refresh_token"], "client_id": cid}
        first = c.post("/token", data=body)
        self.assertEqual(first.status_code, 200, first.text)
        self.assertEqual(c.post("/token", data=body).status_code, 400)   # old refresh token is spent

    def test_tokens_survive_restart(self):
        c, _, provider = self.client()
        _, tokens = self.connect(c)
        from remote.auth import OwnerOAuthProvider
        again = OwnerOAuthProvider(BASE, PW, provider.path)
        self.assertTrue(again.access_valid(tokens["access_token"]))
        self.assertNotIn(tokens["access_token"], provider.path.read_text())   # hashed at rest

    def test_revoke_all(self):
        c, _, provider = self.client()
        _, tokens = self.connect(c)
        provider.revoke_all()
        r = c.post("/mcp", json=INIT, headers={**ACCEPT, "Authorization": f"Bearer {tokens['access_token']}"})
        self.assertEqual(r.status_code, 401)

    def test_redirect_allowlist(self):
        c, *_ = self.client(allowed_redirect_hosts=["claude.ai"])
        self.assertEqual(self.register(c).status_code, 201)
        self.assertEqual(self.register(c, "https://evil.example/cb").status_code, 400)

    def test_weak_password_rejected(self):
        with self.assertRaises(ValueError):
            self.client(password="short")

    def test_v1_auth(self):
        c, *_ = self.client()
        self.assertEqual(c.get("/v1/models").status_code, 401)
        self.assertEqual(c.get("/v1/models", headers={"Authorization": "Bearer " + "k" * 20}).status_code, 200)
        _, tokens = self.connect(c)
        self.assertEqual(c.get("/v1/models", headers={"Authorization": f"Bearer {tokens['access_token']}"})
                         .status_code, 200)

    def test_tool_surface(self):
        import asyncio
        _, server, _ = self.client()
        tools = {t.name: t for t in asyncio.run(server.list_tools())}
        self.assertNotIn("m1frame_open_studio", tools)
        for name in ("m1frame_run", "m1frame_agent", "m1frame_start", "m1frame_result", "m1frame_call_tool"):
            self.assertIn(name, tools)
        for t in tools.values():
            self.assertIsInstance(t.annotations.readOnlyHint, bool)
        # Every tool runs off the event loop so one long pipeline can't freeze the server.
        self.assertTrue(all(t.is_async for t in server._tool_manager.list_tools()))

    def test_calculator_through_mcp_tool(self):
        import asyncio
        _, server, _ = self.client()
        out = asyncio.run(server.call_tool("m1frame_call_tool",
                                           {"name": "calculator", "args": {"expression": "6*7"}}))
        self.assertIn("42", str(out))


class JobStoreTests(unittest.TestCase):
    def test_background_job_lifecycle(self):
        from remote.jobs import JobStore
        with tempfile.TemporaryDirectory() as d:
            store = JobStore(d, lambda text, kind: f"{kind}:{text}")
            job = store.start("plan x")
            for _ in range(100):
                if store.get(job["job_id"])["status"] != "running":
                    break
                time.sleep(0.02)
            done = store.get(job["job_id"])
            self.assertEqual((done["status"], done["result"]), ("done", "run:plan x"))
            store.wait_all()
            fresh = JobStore(d, lambda *_: "")
            self.assertEqual(fresh.get(job["job_id"])["result"], "run:plan x")   # persisted

    def test_concurrency_cap_and_failures(self):
        import threading

        from remote.jobs import MAX_ACTIVE, JobStore
        gate = threading.Event()
        with tempfile.TemporaryDirectory() as d:
            store = JobStore(d, lambda *_: gate.wait(5) and "ok")
            for _ in range(MAX_ACTIVE):
                self.assertIn("job_id", store.start("x"))
            self.assertIn("error", store.start("x"))
            gate.set()
            failing = JobStore(d, lambda *_: 1 / 0)
            bad = failing.start("y")["job_id"]
            for _ in range(100):
                if failing.get(bad)["status"] != "running":
                    break
                time.sleep(0.02)
            self.assertEqual(failing.get(bad)["status"], "failed")
            self.assertIn("unknown job", store.get("../etc")["error"])
            store.wait_all()
            failing.wait_all()


if __name__ == "__main__":
    unittest.main()
