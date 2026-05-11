#!/usr/bin/env python3
"""
scripts/reset_workspace.py — Clean-slate reset for m1frame.

What it clears:
  - workspace/       investigation outputs + schedule.json
  - logs/            JSONL structured logs
  - wiki/sources/    ingested source pages
  - wiki/entities/   entity pages
  - wiki/concepts/   concept pages
  - wiki/synthesis/  synthesis pages
  - wiki/queries/    saved queries
  - wiki/raw/        raw source text
  - wiki/contradictions.md

What it KEEPS (structural skeletons):
  - wiki/index.md    (reset to blank template)
  - wiki/overview.md (reset to blank template)
  - wiki/log.md      (reset to blank template)
  - purpose.md       (user must re-fill for new project)
  - config.yaml      (LLM config unchanged)
  - .env             (API keys unchanged)

Usage:
    python scripts/reset_workspace.py           # interactive confirm
    python scripts/reset_workspace.py --yes     # skip confirm (CI / scripted)
    python scripts/reset_workspace.py --dry-run # show what would be deleted
"""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent

DIRS_TO_WIPE = [
    "workspace",
    "logs",
    "wiki/sources",
    "wiki/entities",
    "wiki/concepts",
    "wiki/synthesis",
    "wiki/queries",
    "wiki/raw",
]

FILES_TO_DELETE = [
    "wiki/contradictions.md",
    "wiki/overview.md",
]

WIKI_INDEX_TEMPLATE = """\
# m1frame Wiki Index

> Auto-generated. Updated after every ingest. Do not edit manually.

## Sources
*(none yet)*

## Entities
*(none yet)*

## Concepts
*(none yet)*

## Synthesis
*(none yet)*

## Queries
*(none yet)*
"""

WIKI_LOG_TEMPLATE = """\
# Wiki Log

> Append-only chronological record of all ingest operations.
"""

PURPOSE_TEMPLATE = """\
# Purpose — Central Guide for the LLM Wiki

**System Name:** m1frame
**Author:** *(your name)*
**Project:** *(project name)*
**Date:** {date}

---

## Mission Statement

*(Describe what you are researching or building.)*

---

## Research Questions

1. *(What is the primary question you want answered?)*
2. *(What are secondary questions?)*

---

## Domain

*(What field / domain are you working in?)*

---

## Evolving Thesis

*(Update this as understanding grows.)*

---

## Sources in Scope

*(List key documents, papers, datasets you will feed in.)*
"""


def _count_items(root: Path, dirs: list[str]) -> int:
    total = 0
    for d in dirs:
        p = root / d
        if p.exists():
            total += sum(1 for _ in p.rglob("*") if _.is_file())
    return total


def reset(root: Path, dry_run: bool = False) -> None:
    from datetime import date

    print(f"\nm1frame Workspace Reset {'(DRY RUN)' if dry_run else ''}")
    print("=" * 50)

    file_count = _count_items(root, DIRS_TO_WIPE)
    print(f"  Will delete ~{file_count} files across {len(DIRS_TO_WIPE)} directories")

    if dry_run:
        print("\nDirectories that would be wiped:")
        for d in DIRS_TO_WIPE:
            p = root / d
            n = sum(1 for _ in p.rglob("*") if _.is_file()) if p.exists() else 0
            print(f"  {'[EXISTS]' if p.exists() else '[missing]'} {d}/ ({n} files)")
        print("\nFiles that would be deleted:")
        for f in FILES_TO_DELETE:
            p = root / f
            print(f"  {'[EXISTS]' if p.exists() else '[missing]'} {f}")
        print("\n(no changes made — dry run)")
        return

    # ── Wipe directories ──────────────────────────────────────────────────────
    for d in DIRS_TO_WIPE:
        p = root / d
        if p.exists():
            shutil.rmtree(p)
            print(f"  cleared: {d}/")
        p.mkdir(parents=True, exist_ok=True)
        print(f"  created: {d}/")

    # ── Delete loose files ────────────────────────────────────────────────────
    for f in FILES_TO_DELETE:
        p = root / f
        if p.exists():
            p.unlink()
            print(f"  deleted: {f}")

    # ── Restore skeleton files ────────────────────────────────────────────────
    wiki = root / "wiki"
    (wiki / "index.md").write_text(WIKI_INDEX_TEMPLATE, encoding="utf-8")
    print("  reset: wiki/index.md")

    (wiki / "log.md").write_text(WIKI_LOG_TEMPLATE, encoding="utf-8")
    print("  reset: wiki/log.md")

    purpose = root / "purpose.md"
    purpose.write_text(
        PURPOSE_TEMPLATE.format(date=date.today().isoformat()),
        encoding="utf-8",
    )
    print("  reset: purpose.md  <-- EDIT THIS for your new project")

    # ── .gitkeep files so git tracks empty dirs ───────────────────────────────
    for d in DIRS_TO_WIPE:
        (root / d / ".gitkeep").write_text("", encoding="utf-8")

    print("\nReset complete.")
    print("\nNext steps:")
    print("  1. Edit purpose.md — describe your project and research questions")
    print("  2. Feed your first document:")
    print("       python scripts/ingest_pdf.py your_doc.pdf 'topic hint'")
    print("  3. Run the first workflow:")
    print("       python -m m1frame --goal 'Your research goal here'")


def main() -> None:
    parser = argparse.ArgumentParser(description="Reset m1frame workspace to a clean slate")
    parser.add_argument("--yes", "-y", action="store_true", help="Skip confirmation prompt")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be deleted without deleting")
    args = parser.parse_args()

    if args.dry_run:
        reset(ROOT, dry_run=True)
        return

    if not args.yes:
        print("\n WARNING: This will delete all wiki pages, logs, and workspace outputs.")
        print("  config.yaml and .env (API keys) are NOT affected.")
        answer = input("\n  Type 'reset' to confirm: ").strip().lower()
        if answer != "reset":
            print("Aborted.")
            sys.exit(0)

    reset(ROOT)


if __name__ == "__main__":
    main()
