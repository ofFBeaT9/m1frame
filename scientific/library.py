"""Read the upstream Agent Skills format without executing third-party code."""
from __future__ import annotations

import ast
import builtins
import importlib.util
import json
import os
import re
import sys
from pathlib import Path

import yaml

from agents.skills import _keywords

SOURCE = "https://github.com/k-dense-ai/scientific-agent-skills.git"
REVISION = "9cf7d9aea7d84754db4c167ab04b299d33c444bc"
DEFAULT_ROOT = Path(__file__).resolve().parent.parent / ".external" / "scientific-skills"


class ScientificLibrary:
    def __init__(self, path: str | Path | None = None):
        self.root = Path(path or os.environ.get("M1_SCIENTIFIC_SKILLS_PATH") or DEFAULT_ROOT).resolve()
        self.skills: dict[str, dict] = {}
        self.errors: list[dict] = []
        skill_root = self.root / "skills"
        if not skill_root.is_dir():
            return
        for file in sorted(skill_root.rglob("SKILL.md")):
            try:
                if not file.resolve().is_relative_to(self.root):
                    raise ValueError("skill escapes repository")
                text = file.read_text(encoding="utf-8-sig")
                parts = re.split(r"^---\s*$", text, maxsplit=2, flags=re.MULTILINE)
                if len(parts) != 3 or parts[0].strip():
                    raise ValueError("missing YAML frontmatter")
                meta = yaml.safe_load(parts[1])
                if not isinstance(meta, dict):
                    raise ValueError("frontmatter must be a mapping")
                name, description = meta.get("name"), meta.get("description")
                if not isinstance(name, str) or not name.strip() or not isinstance(description, str) or not description.strip():
                    raise ValueError("name and description must be nonempty strings")
                if name in self.skills:
                    raise ValueError(f"duplicate skill name: {name}")
                self.skills[name] = {"name": name, "description": description,
                                     "path": file.relative_to(self.root).as_posix(),
                                     "license": meta.get("license", "See upstream LICENSE.md"),
                                     "compatibility": meta.get("compatibility", "Not declared"),
                                     "allowed_tools": meta.get("allowed-tools", "Not declared"),
                                     "metadata": meta.get("metadata", {})}
            except (OSError, ValueError, yaml.YAMLError) as exc:
                self.errors.append({"path": str(file), "error": str(exc)})

    def list(self, query: str = "", limit: int = 200) -> list[dict]:
        tokens = set(_keywords(query))
        ranked = []
        for skill in self.skills.values():
            words = set(re.findall(r"[a-z0-9]+", (skill["name"] + " " + skill["description"]).lower()))
            score = len(tokens & words)
            if (not query.strip()) or score:
                ranked.append((score, skill))
        ranked.sort(key=lambda item: (-item[0], item[1]["name"]))
        return [item for _, item in ranked[:max(0, int(limit))]]

    def _directory(self, name: str) -> Path:
        if name not in self.skills:
            raise KeyError(f"unknown scientific skill: {name}")
        directory = (self.root / self.skills[name]["path"]).parent.resolve()
        if not directory.is_relative_to(self.root):
            raise ValueError("skill escapes repository")
        return directory

    def resources(self, name: str) -> builtins.list[str]:
        directory = self._directory(name)
        return sorted(p.relative_to(directory).as_posix() for p in directory.rglob("*")
                      if p.is_file() and p.resolve().is_relative_to(directory))

    def read(self, name: str, resource: str = "SKILL.md", offset: int = 0,
             limit: int = 100000) -> dict:
        directory = self._directory(name)
        path = (directory / resource).resolve()
        if not path.is_relative_to(directory):
            raise ValueError("resource escapes skill directory")
        text = path.read_text(encoding="utf-8-sig")
        offset, limit = max(0, int(offset)), max(1, min(200000, int(limit)))
        end = min(len(text), offset + limit)
        return {"name": name, "resource": resource, "text": text[offset:end],
                "total_chars": len(text), "next_offset": end if end < len(text) else None,
                "path": str(path), "source": SOURCE}

    def context(self, query: str, names: builtins.list[str] | None = None,
                max_chars: int = 60000) -> tuple[str, builtins.list[str]]:
        """Include complete instructions only; never silently truncate a workflow."""
        candidates = names if names is not None else [s["name"] for s in self.list(query, 2)]
        chunks, selected = [], []
        remaining = max(0, int(max_chars))
        for name in candidates:
            entry = self.read(name, limit=200000)
            chunk = f"Scientific skill {name} ({entry['path']}):\n{entry['text']}"
            if entry["next_offset"] is None and len(chunk) <= remaining:
                chunks.append(chunk)
                selected.append(name)
                remaining -= len(chunk)
        if not chunks:
            return "", []
        header = ("External scientific workflow reference material (not council-vetted). "
                  "Apply only task-relevant instructions. Installed instructions do not prove that "
                  "packages, credentials, data or execution tools are available. Do not claim "
                  "experiments ran without execution evidence. Supporting files can be read via "
                  "scientific_read and scientific_resources on the M1Frame tool surface.\n\n")
        return header + "\n\n".join(chunks), selected

    def audit(self) -> dict:
        """Static inventory, not an execution certification. Never import upstream scripts."""
        entries = []
        for name in self.skills:
            imports: set[str] = set()
            env: set[str] = set()
            syntax_errors = []
            resources = self.resources(name)
            scripts = [r for r in resources if r.endswith(".py")]
            local = {Path(r).stem for r in scripts}
            local.update(part for r in scripts for part in Path(r).parts[:-1])
            for resource in resources:
                if Path(resource).suffix not in {".py", ".md", ".sh", ".yaml", ".yml", ".json"}:
                    continue
                try:
                    text = (self._directory(name) / resource).read_text(encoding="utf-8-sig")
                except (UnicodeError, OSError):
                    continue
                env.update(re.findall(r"\b[A-Z][A-Z0-9_]*(?:API_KEY|ACCESS_TOKEN|SECRET_KEY)\b", text))
                if resource.endswith(".py"):
                    try:
                        tree = ast.parse(text)
                        for node in ast.walk(tree):
                            if isinstance(node, ast.Import):
                                imports.update(a.name.split(".")[0] for a in node.names)
                            elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
                                imports.add(node.module.split(".")[0])
                    except SyntaxError as exc:
                        syntax_errors.append({"resource": resource, "error": str(exc)})
            dependencies = {}
            for module in sorted(imports - sys.stdlib_module_names - local):
                try:
                    present = importlib.util.find_spec(module) is not None
                except (ImportError, ValueError):
                    present = False
                dependencies[module] = present
            entries.append({"name": name, "instructions_readable": True,
                            "compatibility": self.skills[name]["compatibility"],
                            "allowed_tools": self.skills[name]["allowed_tools"],
                            "resources": len(resources), "python_scripts": len(scripts),
                            "syntax_errors": syntax_errors, "import_probes": dependencies,
                            "credential_hints": {key: bool(os.environ.get(key)) for key in sorted(env)},
                            "execution_verified": False})
        source_record = {}
        try:
            source_record = json.loads((self.root / ".m1frame-source.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            pass
        return {"available": bool(self.skills), "source": SOURCE, "expected_revision": REVISION,
                "installation_record": source_record,
                "root": str(self.root), "skill_count": len(self.skills), "errors": self.errors,
                "standalone_agents": "This module loads Agent Skills, not standalone agents.",
                "audit_scope": "Static parsing and top-level import discovery only. Optional imports, "
                               "package versions, executables, R/system dependencies, services, datasets, "
                               "hardware and credential validity require workflow-specific validation.",
                "skills": entries}


def configured_library() -> ScientificLibrary:
    """Shared tool surfaces honour the same configured checkout as the pipeline."""
    from llm_client import load_config
    try:
        cfg = (load_config().get("scientific") or {})
    except OSError:
        cfg = {}
    library = ScientificLibrary(cfg.get("path"))
    if not cfg.get("enabled", True):
        library.skills.clear()
    return library
