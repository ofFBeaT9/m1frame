"""Create an isolated Python environment for the local plugin, without API keys."""
import argparse
import os
import shutil
import subprocess
import sys
import venv
from pathlib import Path

from launch import runtime_path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--upgrade-runtime', action='store_true', help='Back up and replace runtime code; preserve data and settings')
    parser.add_argument('--scientific', action='store_true', help='Download the pinned scientific skill catalog')
    parser.add_argument('--headroom', action='store_true', help='Install optional Headroom compression')
    parser.add_argument('--skillopt', action='store_true', help='Install optional SkillOpt edit engine')
    args = parser.parse_args()
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
    if args.upgrade_runtime:
        subprocess.run([str(interpreter), str(package / 'scripts/upgrade.py'), str(root)], check=True)
    extras = []
    if args.headroom:
        extras.append('headroom-ai==0.39.1')
    if args.skillopt:
        extras.append('skillopt==0.2.0')
    if extras:
        subprocess.run([str(interpreter), '-m', 'pip', 'install', *extras], check=True)
    if args.scientific and not (root / '.external/scientific-skills').exists():
        subprocess.run([str(interpreter), '-m', 'scientific', 'install'], cwd=root, check=True)
    print(f"Ready. Runtime and configuration: {root}")
    print("Configure your chosen provider locally. Do not put API keys in the plugin archive.")
    print("The plugin launcher will automatically use this environment.")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Setup failed: {exc}", file=sys.stderr)
        sys.exit(1)
