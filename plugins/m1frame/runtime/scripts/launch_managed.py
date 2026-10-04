"""Launch the configured persistent m1frame runtime, independent of caller cwd."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def runtime_command() -> tuple[Path, list[str]]:
    root = Path(os.environ.get("M1FRAME_HOME") or
                Path.home() / "Documents" / "Codex" / "m1frame-data").expanduser()
    if not root.is_absolute():
        raise RuntimeError("M1FRAME_HOME must be an absolute path")
    root = root.resolve()
    python = root / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    for required in (python, root / "mcp_server.py", root / "config.yaml"):
        if not required.is_file():
            raise RuntimeError(f"Managed runtime is incomplete: missing {required}")
    return root, [str(python), str(root / "mcp_server.py")]


def main() -> int:
    root, command = runtime_command()
    env = dict(os.environ, PYTHONUTF8="1", M1_STUDIO_BIND="127.0.0.1")
    env.pop("M1_AUTOSTART_STUDIO", None)
    return subprocess.call(command, cwd=root, env=env)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, RuntimeError) as exc:
        print(f"m1frame startup failed: {exc}", file=sys.stderr)
        sys.exit(1)
