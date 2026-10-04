"""Launch the unchanged upstream server with persistent local state."""
import importlib.util
import os
import shutil
import sys
from pathlib import Path


def runtime_path():
    supplied = os.environ.get("M1FRAME_HOME")
    root = Path(supplied).expanduser() if supplied else Path.home() / "Documents" / "Codex" / "m1frame-data"
    if not root.is_absolute():
        raise RuntimeError("M1FRAME_HOME must be an absolute path.")
    return root.resolve()


def prepare_runtime():
    required = {"mcp": "mcp>=1.2,<2", "yaml": "pyyaml", "dotenv": "python-dotenv", "filelock": "filelock", "regex": "regex"}
    missing = [package for module, package in required.items() if importlib.util.find_spec(module) is None]
    if missing:
        raise RuntimeError("Missing dependencies: " + ", ".join(missing) + ". Install runtime/requirements.txt using this Python interpreter.")
    root = runtime_path()
    from filelock import FileLock
    root.parent.mkdir(parents=True, exist_ok=True)
    with FileLock(str(root) + ".init.lock", timeout=60):
        if root.exists():
            if not (root / "mcp_server.py").is_file() or not (root / "config.yaml").is_file():
                raise RuntimeError(f"{root} exists but is not an m1frame checkout. Choose a new M1FRAME_HOME or a complete existing checkout.")
        else:
            bundled = Path(__file__).resolve().parent.parent / "runtime"
            shutil.copytree(bundled, root)
            print(f"m1frame runtime initialized at {root}", file=sys.stderr)
    return root

def main():
    managed = runtime_path() / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    if managed.is_file() and Path(sys.executable).absolute() != managed.absolute():
        os.execv(str(managed), [str(managed), str(Path(__file__).resolve())])
    root = prepare_runtime()
    os.chdir(root)
    sys.path.insert(0, str(root))
    os.environ.pop("M1_AUTOSTART_STUDIO", None)
    os.environ["M1_STUDIO_BIND"] = "127.0.0.1"
    from plugin_server import configure_server

    import mcp_server
    configure_server(mcp_server).run()

if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"m1frame startup failed: {exc}", file=sys.stderr)
        sys.exit(1)
