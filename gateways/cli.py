"""
gateways/cli.py — run a gateway from the terminal.

    python -m gateways               # local stdin gateway (fully offline)
    python -m gateways --telegram    # long-poll a Telegram bot (needs TELEGRAM_BOT_TOKEN)

The Telegram poller is real (Bot API getUpdates/sendMessage via httpx); it is the
same `GatewayRouter` the webhook and CLI use, so behaviour is identical everywhere.
"""
from __future__ import annotations

import os
import sys
import time

from .handlers import make_default_handler
from .router import GatewayRouter, InboundMessage


def _status() -> dict:
    return {"mode": "gateway-cli", "pillars": 7, "backend": os.environ.get("M1_BACKEND", "config")}


def run_cli() -> None:
    router = GatewayRouter(handler=make_default_handler(), status_fn=_status)
    print("m1frame gateway (cli) — type /help or a message; Ctrl-D to exit.\n")
    try:
        for line in sys.stdin:
            text = line.rstrip("\n")
            if not text:
                continue
            print(router.handle(InboundMessage(text=text, platform="cli")).text + "\n")
    except KeyboardInterrupt:
        pass


def run_telegram(poll_timeout: int = 25) -> None:
    import httpx

    from . import adapters
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        sys.exit("Set TELEGRAM_BOT_TOKEN to run the Telegram gateway.")
    base = f"https://api.telegram.org/bot{token}"
    router = GatewayRouter(handler=make_default_handler(), status_fn=_status)
    offset = None
    print("m1frame gateway (telegram) — polling…")
    while True:
        try:
            params = {"timeout": poll_timeout}
            if offset is not None:
                params["offset"] = offset
            r = httpx.get(f"{base}/getUpdates", params=params, timeout=poll_timeout + 10)
            for upd in r.json().get("result", []):
                offset = upd["update_id"] + 1
                msg = adapters.telegram_parse(upd)
                if not msg:
                    continue
                out = router.handle(msg)
                httpx.post(f"{base}/sendMessage", json=adapters.telegram_format(out), timeout=10)
        except Exception as e:  # noqa: BLE001 — keep the poller alive
            print("telegram poll error:", e)
            time.sleep(3)


if __name__ == "__main__":
    run_telegram() if "--telegram" in sys.argv else run_cli()
