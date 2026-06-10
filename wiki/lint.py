#!/usr/bin/env python3
"""wiki.lint() — health check for the knowledge graph (per CLAUDE.md Quality Rules).

Checks: (1) every [[WikiLink]] resolves to an existing page title; (2) no orphans
(every typed page has >=1 inbound link); (3) typed pages have YAML frontmatter.
Run: python wiki/lint.py
"""
import re
import sys
from pathlib import Path

WIKI = Path(__file__).parent
LINK = re.compile(r"\[\[([^\]]+)\]\]")
STRUCTURAL = {"index", "log", "overview", "purpose"}  # not link targets-by-title

def title_of(p: Path, text: str):
    m = re.search(r"^title:\s*(.+)$", text, re.M)
    return m.group(1).strip() if m else None

def main() -> int:
    # raw/ is Layer 1 (immutable source text, no frontmatter by design) — not lintable pages.
    pages = [p for p in WIKI.rglob("*.md") if "raw" not in p.relative_to(WIKI).parts]
    title2file, inbound, errors, warnings = {}, {}, [], []
    page_links = {}
    for p in pages:
        text = p.read_text(encoding="utf-8")
        t = title_of(p, text)
        links = [ln.split("|")[0].strip() for ln in LINK.findall(text)]
        page_links[p] = links
        if p.stem in STRUCTURAL:
            continue
        if t is None:
            errors.append(f"FRONTMATTER: {p.relative_to(WIKI)} has no title:")
            continue
        if "page_type:" not in text:
            warnings.append(f"no page_type: {p.relative_to(WIKI)}")
        title2file[t] = p
        inbound.setdefault(t, 0)

    for p, links in page_links.items():
        for ln in links:
            if ln in inbound:
                inbound[ln] += 1
            elif ln not in title2file:
                errors.append(f"BROKEN LINK: {p.relative_to(WIKI)} -> [[{ln}]]")

    orphans = [t for t, n in inbound.items() if n == 0]
    for t in orphans:
        errors.append(f"ORPHAN: '{t}' has no inbound links")

    print("# LintReport")
    print(f"pages: {len(pages)} | titled: {len(title2file)} | "
          f"links: {sum(len(v) for v in page_links.values())}")
    print(f"errors: {len(errors)} | warnings: {len(warnings)}")
    for e in errors:
        print("  ERROR  ", e)
    for w in warnings:
        print("  warn   ", w)
    print("OK — graph is consistent." if not errors else "FAIL — fix errors above.")
    return 1 if errors else 0

if __name__ == "__main__":
    sys.exit(main())
