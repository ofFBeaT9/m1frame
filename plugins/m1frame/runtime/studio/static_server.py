"""Allowlisted local demo server; repository source and secrets are never public."""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parent.parent
PUBLIC = {"m1frame-studio.html", "studio/demo_run.json", "m1frame/dashboard.html"}


class PublicHandler(SimpleHTTPRequestHandler):
    def send_head(self):
        path = unquote(urlsplit(self.path).path).lstrip("/")
        if not path:
            path = "m1frame-studio.html"
            self.path = "/" + path
        target = (ROOT / path).resolve()
        if (path not in PUBLIC or ROOT not in target.parents
                or target != ROOT / path or self.headers.get("Host", "").split(":")[0]
                not in {"localhost", "127.0.0.1"}):
            self.send_error(404)
            return None
        return super().send_head()

    def list_directory(self, path):
        self.send_error(404)
        return None


def serve(port=8080):
    handler = partial(PublicHandler, directory=str(ROOT))
    with ThreadingHTTPServer(("127.0.0.1", port), handler) as server:
        print(f"m1frame demo: http://127.0.0.1:{server.server_port}")
        server.serve_forever()
