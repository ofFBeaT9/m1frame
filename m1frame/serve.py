#!/usr/bin/env python3
"""Minimal static server for the m1frame dashboard. Binds the port given by the
PORT env var (Claude Preview autoPort) and serves the repo root so the dashboard's
../<artifact> links resolve. Run directly: PORT=8080 python m1frame/serve.py
"""
import os
import http.server
import socketserver

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PORT = int(os.environ.get("PORT", "8080"))

os.chdir(ROOT)


class Handler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path in ("/", ""):
            self.send_response(302)
            self.send_header("Location", "/m1frame/dashboard.html")
            self.end_headers()
            return
        return super().do_GET()


with socketserver.TCPServer(("127.0.0.1", PORT), Handler) as httpd:
    print(f"m1frame static server on http://127.0.0.1:{PORT}  (root={ROOT})")
    httpd.serve_forever()
