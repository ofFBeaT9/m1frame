"""
agents/net.py — shared network-safety helpers (no third-party deps).

`safe_url()` is the single SSRF guard used by the API webhook sender and by the
messaging gateways' outbound replies, so the policy lives in exactly one place.
"""
from __future__ import annotations

import http.client
import ipaddress
import json
import socket
import ssl
from urllib.parse import urlparse

_BLOCK_HOSTS = {"localhost", "metadata.google.internal", "metadata"}


def safe_url(url: str) -> bool:
    """True only for an http(s) URL whose host is not loopback / private /
    link-local / reserved / multicast / a known metadata endpoint.

    IP *literals* are checked directly. A hostname that resolves to a private IP
    via DNS is not re-resolved here (no blocking DNS in the hot path) — a
    documented limitation; pair with network egress rules for hard isolation.
    """
    try:
        u = urlparse(url)
        if u.scheme not in ("http", "https") or not u.hostname:
            return False
        host = u.hostname.lower().rstrip(".")
        if u.username or u.password:
            return False
        if host in _BLOCK_HOSTS:
            return False
        try:
            ip = ipaddress.ip_address(host)
            if (ip.is_private or ip.is_loopback or ip.is_link_local
                    or ip.is_reserved or ip.is_multicast or ip.is_unspecified):
                return False
        except ValueError:
            pass  # not an IP literal — a regular hostname
        return True
    except Exception:
        return False


def public_request(url: str, payload: dict | None = None, max_bytes: int = 100000) -> tuple[int, bytes]:
    """Resolve once and pin a public address; preserve TLS hostname verification.

    Redirects and proxy environment variables are deliberately not followed.
    Response reads are bounded. Used for untrusted tool/webhook destinations.
    """
    if not safe_url(url):
        raise ValueError("blocked URL: public HTTP(S) required")
    parsed = urlparse(url)
    host = parsed.hostname
    assert host
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    addresses = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    if not addresses or any(not ipaddress.ip_address(a[4][0]).is_global
                            or ipaddress.ip_address(a[4][0]).is_multicast for a in addresses):
        raise ValueError("blocked URL: DNS returned a non-public address")
    family, kind, proto, _, address = addresses[0]
    sock = socket.socket(family, kind, proto)
    sock.settimeout(10)
    connection = http.client.HTTPConnection(host, port, timeout=10)
    try:
        sock.connect(address)
        if parsed.scheme == "https":
            sock = ssl.create_default_context().wrap_socket(sock, server_hostname=host)
        connection.sock = sock
        path = parsed.path or "/"
        if parsed.query:
            path += "?" + parsed.query
        body = json.dumps(payload).encode() if payload is not None else None
        headers = {"Content-Type": "application/json"} if body else {}
        connection.request("POST" if payload is not None else "GET", path, body, headers)
        response = connection.getresponse()
        return response.status, response.read(max(1, min(max_bytes, 1000000)))
    finally:
        connection.close()
        sock.close()
