"""Create an isolated Python environment for the local plugin, without API keys."""
import os
import shutil
import subprocess
import sys
import venv
from pathlib import Path

from launch import runtime_path


def main():
    root = runtime_path()
    package = Path(__file__).resolve().parent.parent
    if root.exists():
        if not (root / "mcp_server.py").is_file() or not (root / "config.yaml").is_file():
            raise RuntimeError("Existing runtime directory is incomplete; choose another M1FRAME_HOME.")
    else:
        shutil.copytree(package / "runtime", root)
    environment = root / ".venv"
    if not environment.exists():
        venv.EnvBuilder(with_pip=True).create(environment)
    interpreter = environment / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    if not interpreter.is_file():
        raise RuntimeError("Existing .venv is incomplete; repair it or select another runtime directory.")
    subprocess.run([str(interpreter), "-m", "pip", "install", "-r", str(package / "requirements.txt")], check=True)
    print(f"Ready. Runtime and configuration: {root}")
    print("Configure your chosen provider locally. Do not put API keys in the plugin archive.")
    print("The plugin launcher will automatically use this environment.")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Setup failed: {exc}", file=sys.stderr)
        sys.exit(1)
