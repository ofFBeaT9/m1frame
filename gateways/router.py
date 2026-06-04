"""
gateways/router.py — transport-agnostic message routing for m1frame.

One router turns an inbound message from *any* platform (Telegram, Slack, Discord,
a webhook, the CLI) into an m1frame reply. Platform adapters only translate
payloads; all the behaviour — commands, chat, full deliberation — lives here, so
every channel behaves identically and is tested once.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Callable, Optional

HELP = (
    "🛰️ *m1frame gateway*\n"
    "/help — this message\n"
    "/status — pillars, mode, uptime\n"
    "/ping — liveness check\n"
    "/run <goal> — full 7-pillar deliberation (watch it in Studio)\n"
    "anything else — grounded chat over the knowledge graph"
)


@dataclass
class InboundMessage:
    text: str
    user: str = "anon"
    channel: str = "default"
    platform: str = "cli"
    meta: dict = field(default_factory=dict)


@dataclass
class OutboundMessage:
    text: str
    channel: str = "default"
    platform: str = "cli"
    meta: dict = field(default_factory=dict)


class GatewayRouter:
    """Route an InboundMessage to a reply. `handler(InboundMessage) -> str` does
    the heavy lifting (chat or a pipeline run); local commands never touch it, so
    the router is fully testable offline with a mock handler (or none)."""

    def __init__(self,
                 handler: Optional[Callable[["InboundMessage"], str]] = None,
                 status_fn: Optional[Callable[[], dict]] = None) -> None:
        self.handler = handler
        self.status_fn = status_fn
        self.started = time.time()

    def handle(self, msg: "InboundMessage") -> "OutboundMessage":
        reply = self._dispatch(msg, (msg.text or "").strip())
        return OutboundMessage(text=reply, channel=msg.channel, platform=msg.platform,
                               meta={"in_reply_to": msg.user})

    def _dispatch(self, msg: "InboundMessage", text: str) -> str:
        low = text.lower()
        if low in ("/help", "help", "/start", "start"):
            return HELP
        if low in ("/ping", "ping"):
            return "pong ✓ — m1frame gateway is up"
        if low in ("/status", "status"):
            up = int(time.time() - self.started)
            st = {}
            try:
                st = self.status_fn() if self.status_fn else {}
            except Exception:  # noqa: BLE001 — status is best-effort
                st = {}
            body = "\n".join(f"- {k}: {v}" for k, v in st.items())
            return (f"m1frame status\n{body}\n- gateway uptime: {up}s"
                    if st else f"m1frame gateway · uptime {up}s")
        if not text:
            return "Send a message, or /help."
        run_mode = low == "/run" or low.startswith("/run ")
        goal = text[4:].strip() if run_mode else text
        if not goal:
            return "Usage: /run <goal>"
        if self.handler is None:
            return "(no handler wired — construct GatewayRouter(handler=...))"
        try:
            return self.handler(InboundMessage(
                text=goal, user=msg.user, channel=msg.channel, platform=msg.platform,
                meta={"mode": "run" if run_mode else "chat"}))
        except Exception as e:  # noqa: BLE001 — a handler error must never crash the gateway
            return f"(m1frame hit an error: {e})"
