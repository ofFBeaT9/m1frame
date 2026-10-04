"""Run the local, allowlisted static demo server."""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from studio.static_server import serve  # noqa: E402

if __name__ == "__main__":
    serve(int(os.environ.get("PORT", "8080")))
