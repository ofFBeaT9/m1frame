"""
gateways/adapters.py — per-platform translation + delivery.

Each adapter is two *pure* functions — `parse(payload) -> InboundMessage` and
`format(OutboundMessage) -> payload` — so they're trivially unit-tested offline.
`deliver()` does the real network send (Telegram Bot API, Slack/Discord incoming
webhooks), best-effort and SSRF-guarded; it's exercised live, not in the suite.
"""
from __future__ import annotations

import os

from agents.net import safe_url

from .router import InboundMessage, OutboundMessage


# ── Telegram ──────────────────────────────────────────────────────────────────
def telegram_parse(update: dict) -> InboundMessage | None:
    m = (update or {}).get("message") or (update or {}).get("edited_message") or {}
    text = m.get("text")
    if not text:
        return None
    chat, frm = m.get("chat", {}), m.get("from", {})
    return InboundMessage(text=text, platform="telegram",
                          user=str(frm.get("username") or frm.get("id") or "tg"),
                          channel=str(chat.get("id", "")),
                          meta={"update_id": (update or {}).get("update_id")})


def telegram_format(out: OutboundMessage) -> dict:
    return {"chat_id": out.channel, "text": out.text, "disable_web_page_preview": True}


# ── Slack (Events API) ────────────────────────────────────────────────────────
def slack_parse(payload: dict) -> InboundMessage | None:
    ev = (payload or {}).get("event", payload or {})
    text = ev.get("text")
    if not text:
        return None
    return InboundMessage(text=text, platform="slack",
                          user=str(ev.get("user", "slack")),
                          channel=str(ev.get("channel", "")))


def slack_format(out: OutboundMessage) -> dict:
    return {"channel": out.channel, "text": out.text}


# ── Discord ───────────────────────────────────────────────────────────────────
def discord_parse(payload: dict) -> InboundMessage | None:
    text = (payload or {}).get("content")
    if not text:
        return None
    a = (payload or {}).get("author", {})
    return InboundMessage(text=text, platform="discord",
                          user=str(a.get("username", "discord")),
                          channel=str((payload or {}).get("channel_id", "")))


def discord_format(out: OutboundMessage) -> dict:
    return {"content": out.text}


# ── generic webhook / CLI (the default) ───────────────────────────────────────
def generic_parse(payload: dict) -> InboundMessage | None:
    payload = payload or {}
    text = payload.get("text") or payload.get("message")
    if not text:
        return None
    return InboundMessage(text=str(text), platform=str(payload.get("platform", "webhook")),
                          user=str(payload.get("user", "anon")),
                          channel=str(payload.get("channel", "default")))


def generic_format(out: OutboundMessage) -> dict:
    return {"text": out.text, "channel": out.channel, "platform": out.platform}


ADAPTERS = {
    "telegram": (telegram_parse, telegram_format),
    "slack": (slack_parse, slack_format),
    "discord": (discord_parse, discord_format),
}


def parse(platform: str, payload: dict) -> InboundMessage | None:
    fn = ADAPTERS.get(platform, (generic_parse, generic_format))[0]
    msg = fn(payload)
    if msg is not None and platform not in ADAPTERS:
        msg.platform = platform        # generic adapter carries the route's platform
    return msg


def format_out(platform: str, out: OutboundMessage) -> dict:
    fn = ADAPTERS.get(platform, (generic_parse, generic_format))[1]
    return fn(out)


def deliver(out: OutboundMessage) -> bool:
    """Best-effort real delivery using env-configured credentials. Returns True
    if a send was attempted successfully. Never raises."""
    try:
        import httpx
    except Exception:
        return False
    try:
        p = out.platform
        if p == "telegram":
            token = os.environ.get("TELEGRAM_BOT_TOKEN")
            if not token:
                return False
            url = f"https://api.telegram.org/bot{token}/sendMessage"
            httpx.post(url, json=telegram_format(out), timeout=10)
            return True
        if p in ("slack", "discord"):
            hook = os.environ.get(f"{p.upper()}_WEBHOOK_URL")
            if not hook or not safe_url(hook):
                return False
            httpx.post(hook, json=format_out(p, out), timeout=10)
            return True
        hook = out.meta.get("reply_url") if out.meta else None
        if hook and safe_url(hook):
            httpx.post(hook, json=generic_format(out), timeout=10)
            return True
        return False
    except Exception:  # noqa: BLE001 — delivery is best-effort
        return False
