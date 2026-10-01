"""Usage: python -m scientific install|list|read|audit."""
import argparse
import json
import subprocess

from .library import REVISION, SOURCE, ScientificLibrary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["install", "list", "read", "audit"])
    parser.add_argument("name", nargs="?", default="")
    parser.add_argument("--path", help="Repository checkout (or M1_SCIENTIFIC_SKILLS_PATH)")
    parser.add_argument("--resource", default="SKILL.md")
    parser.add_argument("--output", help="Write JSON to this file")
    args = parser.parse_args()
    library = ScientificLibrary(args.path)
    if args.command == "install":
        if library.root.exists():
            parser.error(f"Destination exists; use --path for a new checkout: {library.root}")
        library.root.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["git", "init", str(library.root)], check=True, timeout=60)
        git = ["git", "-C", str(library.root)]
        subprocess.run([*git, "remote", "add", "origin", SOURCE], check=True, timeout=60)
        # Avoid fetching hundreds of megabytes of promotional documentation images.
        subprocess.run([*git, "config", "remote.origin.promisor", "true"], check=True, timeout=60)
        subprocess.run([*git, "config", "remote.origin.partialclonefilter", "blob:none"], check=True, timeout=60)
        subprocess.run([*git, "sparse-checkout", "set", "skills"], check=True, timeout=60)
        subprocess.run([*git, "fetch", "--filter=blob:none", "--depth", "1", "origin", REVISION], check=True, timeout=600)
        subprocess.run([*git, "checkout", "--detach", "FETCH_HEAD"], check=True, timeout=600)
        (library.root / ".m1frame-source.json").write_text(
            json.dumps({"revision": REVISION, "method": "git sparse checkout"}), encoding="utf-8")
        result = {"installed": str(library.root), "revision": REVISION,
                  "skills": len(ScientificLibrary(library.root).skills)}
    elif args.command == "list":
        result = library.list(args.name, limit=len(library.skills))
    elif args.command == "read":
        result = library.read(args.name, args.resource)
    else:
        result = library.audit()
    output = json.dumps(result, indent=2, ensure_ascii=True)
    if args.output:
        from pathlib import Path
        Path(args.output).write_text(output + "\n", encoding="utf-8")
    else:
        print(output)


if __name__ == "__main__":
    main()
