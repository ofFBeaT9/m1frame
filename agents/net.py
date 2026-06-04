"""
agents/net.py — shared network-safety helpers (no third-party deps).

`safe_url()` is the single SSRF guard used by the API webhook sender and by the
messaging gateways' outbound replies, so the policy lives in exactly one place.
"""
from __future__ import annotations

import ipaddress
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
        host = u.hostname.lower()
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
