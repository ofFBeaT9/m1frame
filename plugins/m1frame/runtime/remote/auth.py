"""Single-owner OAuth 2.1 authorization server for remote m1frame.

Claude (web/desktop/mobile), ChatGPT developer-mode connectors, Cursor and other MCP
hosts connect to remote servers with OAuth + Dynamic Client Registration. This
provider implements that for one owner: any host may *register*, but a host only
gets a token after the owner signs in on m1frame's own login page with
M1FRAME_OWNER_PASSWORD and sees which app and redirect host is asking.

State (registered clients, hashed tokens) persists in a JSON file so connectors
survive restarts. Tokens are stored as SHA-256 hashes only.
"""
from __future__ import annotations

import hashlib
import hmac
import html
import json
import secrets
import threading
import time
from pathlib import Path
from urllib.parse import urlparse

from mcp.server.auth.provider import (
    AccessToken,
    AuthorizationCode,
    AuthorizationParams,
    AuthorizeError,
    RefreshToken,
    RegistrationError,
    TokenError,
    construct_redirect_uri,
)
from mcp.shared.auth import OAuthClientInformationFull, OAuthToken

SCOPE = "m1frame"
CODE_TTL = 300                 # authorization codes: 5 minutes
LOGIN_TTL = 600                # pending login pages: 10 minutes
ACCESS_TTL = 24 * 3600         # access tokens: 1 day (hosts refresh silently)
REFRESH_TTL = 60 * 24 * 3600   # refresh tokens: 60 days, rotated on use
MAX_CLIENTS = 100
MAX_FAILS, LOCKOUT = 8, 900    # failed logins per IP before a 15-minute lockout


def _h(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


class OwnerOAuthProvider:
    def __init__(self, issuer_url: str, owner_password: str, state_file: str | Path,
                 allowed_redirect_hosts: list[str] | None = None) -> None:
        if len(owner_password or "") < 12:
            raise ValueError("M1FRAME_OWNER_PASSWORD must be at least 12 characters")
        self.issuer = issuer_url.rstrip("/")
        self._password = owner_password.encode()
        self.allowed_hosts = {h.strip().lower() for h in (allowed_redirect_hosts or []) if h.strip()}
        self.path = Path(state_file)
        self._lock = threading.Lock()
        self._pending: dict[str, tuple[float, str, AuthorizationParams]] = {}
        self._codes: dict[str, AuthorizationCode] = {}
        self._fails: dict[str, tuple[int, float]] = {}
        self._state: dict[str, dict[str, dict]] = {"clients": {}, "access": {}, "refresh": {}}
        if self.path.is_file():
            try:
                self._state.update(json.loads(self.path.read_text(encoding="utf-8")))
            except (OSError, ValueError):
                pass

    # ── persistence ──────────────────────────────────────────────────────
    def _save(self) -> None:
        now = time.time()
        for kind in ("access", "refresh"):
            self._state[kind] = {k: v for k, v in self._state[kind].items()
                                 if not v.get("expires_at") or v["expires_at"] > now}
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self._state), encoding="utf-8")
        tmp.replace(self.path)
        try:
            self.path.chmod(0o600)
        except OSError:
            pass

    # ── clients (Dynamic Client Registration) ───────────────────────────
    async def get_client(self, client_id: str) -> OAuthClientInformationFull | None:
        raw = self._state["clients"].get(client_id)
        return OAuthClientInformationFull.model_validate(raw) if raw else None

    async def register_client(self, client_info: OAuthClientInformationFull) -> None:
        for uri in client_info.redirect_uris or []:
            host = (urlparse(str(uri)).hostname or "").lower()
            if self.allowed_hosts and host not in self.allowed_hosts:
                raise RegistrationError("invalid_redirect_uri",
                                        f"redirect host '{host}' is not in M1FRAME_ALLOWED_REDIRECT_HOSTS")
        if not client_info.client_id:
            raise RegistrationError("invalid_client_metadata", "missing client_id")
        with self._lock:
            if len(self._state["clients"]) >= MAX_CLIENTS:
                raise RegistrationError("invalid_client_metadata", "client registration limit reached")
            self._state["clients"][client_info.client_id] = client_info.model_dump(mode="json")
            self._save()

    # ── authorization: hand off to the owner login page ─────────────────
    async def authorize(self, client: OAuthClientInformationFull, params: AuthorizationParams) -> str:
        req = secrets.token_urlsafe(24)
        with self._lock:
            now = time.time()
            self._pending = {k: v for k, v in self._pending.items() if v[0] > now}
            self._pending[req] = (now + LOGIN_TTL, str(client.client_id or ""), params)
        return f"{self.issuer}/login?req={req}"

    def pending(self, req: str) -> tuple[str, AuthorizationParams] | None:
        item = self._pending.get(req or "")
        if not item or item[0] < time.time():
            return None
        return item[1], item[2]

    def locked_out(self, ip: str) -> bool:
        """Per-client lockout plus a global one, since client IPs behind a tunnel or
        proxy can be spoofed or shared."""
        now = time.time()
        count, until = self._fails.get(ip, (0, 0.0))
        g_count, g_until = self._fails.get("*", (0, 0.0))
        return (count >= MAX_FAILS and until > now) or (g_count >= MAX_FAILS * 4 and g_until > now)

    def check_password(self, supplied: str, ip: str) -> bool:
        ok = hmac.compare_digest(self._password, (supplied or "").encode())
        if ok:
            self._fails.pop(ip, None)
        else:
            for key in (ip, "*"):
                count, until = self._fails.get(key, (0, 0.0))
                count = count if until > time.time() else 0
                self._fails[key] = (count + 1, time.time() + LOCKOUT)
        return ok

    def access_valid(self, token: str) -> bool:
        raw = self._state["access"].get(_h(token or ""))
        return raw is not None and raw["expires_at"] > time.time()

    def approve(self, req: str) -> str:
        """Owner signed in: mint a code and return the client's redirect URL."""
        with self._lock:
            item = self._pending.pop(req, None)
        if not item or item[0] < time.time():
            raise AuthorizeError("access_denied", "login request expired; start again from your app")
        _, client_id, params = item
        code = secrets.token_urlsafe(32)
        self._codes[code] = AuthorizationCode(
            code=code, scopes=params.scopes or [SCOPE], expires_at=time.time() + CODE_TTL,
            client_id=client_id, code_challenge=params.code_challenge,
            redirect_uri=params.redirect_uri,
            redirect_uri_provided_explicitly=params.redirect_uri_provided_explicitly,
            resource=params.resource, subject="owner")
        return construct_redirect_uri(str(params.redirect_uri), code=code, state=params.state)

    def deny(self, req: str) -> str | None:
        with self._lock:
            item = self._pending.pop(req, None)
        if not item:
            return None
        params = item[2]
        return construct_redirect_uri(str(params.redirect_uri), error="access_denied", state=params.state)

    # ── codes and tokens ─────────────────────────────────────────────────
    async def load_authorization_code(self, client: OAuthClientInformationFull,
                                      authorization_code: str) -> AuthorizationCode | None:
        code = self._codes.get(authorization_code)
        if not code or code.client_id != client.client_id or code.expires_at < time.time():
            return None
        return code

    def _issue(self, client_id: str, scopes: list[str], resource: str | None) -> OAuthToken:
        access, refresh = secrets.token_urlsafe(40), secrets.token_urlsafe(40)
        now = int(time.time())
        with self._lock:
            self._state["access"][_h(access)] = {"client_id": client_id, "scopes": scopes,
                                                 "expires_at": now + ACCESS_TTL, "resource": resource}
            self._state["refresh"][_h(refresh)] = {"client_id": client_id, "scopes": scopes,
                                                   "expires_at": now + REFRESH_TTL, "resource": resource}
            self._save()
        return OAuthToken(access_token=access, token_type="Bearer", expires_in=ACCESS_TTL,
                          refresh_token=refresh, scope=" ".join(scopes))

    async def exchange_authorization_code(self, client: OAuthClientInformationFull,
                                          authorization_code: AuthorizationCode) -> OAuthToken:
        if self._codes.pop(authorization_code.code, None) is None:
            raise TokenError("invalid_grant", "authorization code already used")
        return self._issue(str(client.client_id), authorization_code.scopes, authorization_code.resource)

    async def load_refresh_token(self, client: OAuthClientInformationFull,
                                 refresh_token: str) -> RefreshToken | None:
        raw = self._state["refresh"].get(_h(refresh_token))
        if not raw or raw["client_id"] != client.client_id or raw["expires_at"] < time.time():
            return None
        return RefreshToken(token=refresh_token, client_id=raw["client_id"], scopes=raw["scopes"],
                            expires_at=raw["expires_at"], resource=raw.get("resource"), subject="owner")

    async def exchange_refresh_token(self, client: OAuthClientInformationFull, refresh_token: RefreshToken,
                                     scopes: list[str]) -> OAuthToken:
        with self._lock:
            if self._state["refresh"].pop(_h(refresh_token.token), None) is None:
                raise TokenError("invalid_grant", "refresh token already used")
        return self._issue(str(client.client_id), scopes or refresh_token.scopes, refresh_token.resource)

    async def load_access_token(self, token: str) -> AccessToken | None:
        raw = self._state["access"].get(_h(token or ""))
        if not raw or raw["expires_at"] < time.time():
            return None
        return AccessToken(token=token, client_id=raw["client_id"], scopes=raw["scopes"],
                           expires_at=raw["expires_at"], resource=raw.get("resource"), subject="owner")

    async def revoke_token(self, token) -> None:
        with self._lock:
            for kind in ("access", "refresh"):
                self._state[kind].pop(_h(token.token), None)
            self._save()

    def revoke_all(self) -> int:
        """Sign every connected app out (CLI: python -m remote --revoke-all)."""
        with self._lock:
            n = len(self._state["access"]) + len(self._state["refresh"])
            self._state["access"], self._state["refresh"] = {}, {}
            self._save()
        return n


def login_page(client_name: str, redirect_host: str, req: str, error: str = "") -> str:
    e = html.escape
    err = f'<p class="err">{e(error)}</p>' if error else ""
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>m1frame sign-in</title>
<style>
:root{{--bg:#0d1117;--card:#161b22;--fg:#e6edf3;--mute:#8b949e;--acc:#34e7e4;--err:#ff7b72}}
@media (prefers-color-scheme:light){{:root{{--bg:#f6f8fa;--card:#fff;--fg:#1f2328;--mute:#59636e;--acc:#0e7490;--err:#cf222e}}}}
body{{margin:0;min-height:100vh;display:grid;place-items:center;background:var(--bg);color:var(--fg);
font:16px/1.5 system-ui,-apple-system,Segoe UI,sans-serif;padding:16px;box-sizing:border-box}}
form{{background:var(--card);padding:28px;border-radius:14px;max-width:380px;width:100%;
box-shadow:0 4px 24px #0003}}
h1{{font-size:20px;margin:0 0 8px}} p{{margin:0 0 16px;color:var(--mute)}} b{{color:var(--fg)}}
input{{width:100%;box-sizing:border-box;padding:12px;border-radius:8px;border:1px solid var(--mute);
background:transparent;color:var(--fg);font-size:16px;margin-bottom:14px}}
.row{{display:flex;flex-direction:row-reverse;gap:10px}} button{{flex:1;padding:12px;border-radius:8px;border:0;font-size:16px;cursor:pointer}}
.ok{{background:var(--acc);color:#000;font-weight:600}} .no{{background:transparent;color:var(--fg);
border:1px solid var(--mute)}} .err{{color:var(--err)}}
</style></head><body><form method="post" action="/login">
<h1>Connect to m1frame</h1>
<p><b>{e(client_name or "An app")}</b> wants to use your m1frame. After sign-in it will send you
back to <b>{e(redirect_host)}</b>. Only continue if you started this.</p>{err}
<input type="hidden" name="req" value="{e(req)}">
<input type="password" name="password" placeholder="Owner password" autocomplete="current-password" autofocus>
<div class="row"><button class="ok" name="action" value="allow">Allow</button>
<button class="no" name="action" value="deny">Deny</button></div>
</form></body></html>"""
