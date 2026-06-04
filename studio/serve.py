#!/usr/bin/env python3
"""
studio/serve.py — zero-dependency static server for m1frame Studio.

The no-pip, no-key fallback: serves the repo root over http so the Studio's
`fetch('studio/*.json')` calls resolve, and the bundled demo replays entirely
client-side. For live runs / SSE / chat, use the FastAPI server instead
(`python api/server.py`).

Run:  python studio/serve.py        (PORT env honoured; Claude Preview autoPort)
"""
import http.server
import os
import socketserver
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PORT = int(os.environ.get("PORT", "8080"))
os.chdir(ROOT)


class Handler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path in ("/", ""):
            self.send_response(302)
            self.send_header("Location", "/m1frame-studio.html")
            self.end_headers()
            return
        return super().do_GET()

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def log_message(self, *args):
        pass


with socketserver.TCPServer(("127.0.0.1", PORT), Handler) as httpd:
    print(f"m1frame Studio (static) → http://127.0.0.1:{PORT}/m1frame-studio.html  [demo only]")
    httpd.serve_forever()
