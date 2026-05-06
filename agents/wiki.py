"""
agents/wiki.py — LLM Wiki Pattern (The Memory Layer)
Based on: Karpathy's LLM Wiki gist + nashsu/llm_wiki implementation.

Three-layer architecture (Karpathy):
  Raw Sources  → wiki/raw/sources/   (immutable — LLM reads, never writes)
  Wiki         → wiki/               (LLM-owned: entities, concepts, sources, synthesis)
  Schema       → CLAUDE.md           (rules & conventions — co-evolved by human + LLM)

Three operations:
  Ingest  — two-step: Analysis → Generation
  Query   — index.md first, then drill into pages
  Lint    — health-check: contradictions, orphans, stale claims

Key files:
  wiki/index.md    — content catalog (LLM updates on every ingest)
  wiki/log.md      — chronological append-only operation record
  wiki/overview.md — global summary (auto-regenerated on ingest)
  purpose.md       — goals, research scope, evolving thesis (the wiki's soul)
  CLAUDE.md        — schema: page types, conventions, workflows
"""

from __future__ import annotations
import re
import yaml
import datetime
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional


# ── Prompts ───────────────────────────────────────────────────────────────────

ANALYSIS_SYSTEM = """You are a Wiki Analysis Agent (Step 1 of two-step ingest).
Read the source and produce a structured analysis. Do NOT write wiki pages yet.

Respond in this JSON format:
{
  "key_entities": ["entity1", "entity2"],
  "key_concepts": ["concept1", "concept2"],
  "main_arguments": ["..."],
  "connections_to_existing": ["..."],
  "contradictions_with_existing": ["..."],
  "suggested_page_types": ["entity|concept|source|synthesis"],
  "recommended_wiki_structure": "...",
  "confidence": "high|medium|low"
}
No preamble. Pure JSON only.
"""

GENERATION_SYSTEM = """You are a Wiki Generation Agent (Step 2 of two-step ingest).
Using the analysis, generate wiki pages in Markdown with YAML frontmatter.

Rules:
- Start each page with --- YAML frontmatter
- Include: title, tags, related (as [[WikiLinks]]), created (ISO date), sources (list), page_type
- Use [[WikiLinks]] to link to other pages
- Write ## Summary, ## Key Concepts, ## Details, ## Related, ## Open Questions sections
- Keep factual, concise, no filler
- Source pages go in sources/, entity pages in entities/, concepts in concepts/

Generate a source summary page for this ingestion. No code fences. Start with ---
"""

LINT_SYSTEM = """You are a Wiki Lint Agent.
Health-check the wiki. Look for:
1. Contradictions between pages
2. Orphan pages with no inbound links
3. Missing [[WikiLinks]] for mentioned concepts
4. Stale claims that newer content may have superseded
5. Important concepts mentioned but lacking their own page
6. Knowledge gaps that could be filled

Respond in this JSON format:
{
  "contradictions": ["..."],
  "orphan_pages": ["..."],
  "missing_pages": ["..."],
  "knowledge_gaps": ["..."],
  "health_score": <integer 1-10>,
  "recommendations": ["..."]
}
No preamble. Pure JSON only.
"""

OVERVIEW_SYSTEM = """You are a Wiki Overview Agent.
Given the wiki index and recent changes, write a fresh overview.md — a global summary
of everything in the wiki: key themes, major entities, open questions, evolving synthesis.

Start with YAML frontmatter (title: Overview, auto_generated: true, updated: <date>).
Then write ## Current State, ## Key Themes, ## Major Entities, ## Open Questions, ## Synthesis.
No code fences. Start with ---
"""


# ── Data structures ───────────────────────────────────────────────────────────

@dataclass
class WikiPage:
    title: str
    tags: list[str]
    related: list[str]
    created: str
    sources: list[str]
    page_type: str      # entity | concept | source | synthesis | query
    content: str
    filename: str = ""

    @classmethod
    def from_markdown(cls, text: str, filename: str = "") -> "WikiPage":
        fm, _ = _split_frontmatter(text)
        return cls(
            title=fm.get("title", "Untitled"),
            tags=fm.get("tags") or [],
            related=fm.get("related") or [],
            created=str(fm.get("created", "")),
            sources=fm.get("sources") or [],
            page_type=fm.get("page_type", "concept"),
            content=text,
            filename=filename,
        )

    def excerpt(self, chars: int = 300) -> str:
        body = re.sub(r"^---.*?---\n", "", self.content, flags=re.DOTALL).strip()
        return body[:chars] + ("..." if len(body) > chars else "")


@dataclass
class LintReport:
    contradictions: list[str]
    orphan_pages: list[str]
    missing_pages: list[str]
    knowledge_gaps: list[str]
    health_score: int
    recommendations: list[str]

    def summary(self) -> str:
        lines = [f"Wiki Health Score: {self.health_score}/10"]
        if self.contradictions:
            lines.append(f"Contradictions: {len(self.contradictions)}")
        if self.orphan_pages:
            lines.append(f"Orphan pages: {', '.join(self.orphan_pages)}")
        if self.missing_pages:
            lines.append(f"Missing pages needed: {', '.join(self.missing_pages)}")
        if self.recommendations:
            lines.append("Recommendations:")
            for r in self.recommendations:
                lines.append(f"  • {r}")
        return "\n".join(lines)


# ── Main class ────────────────────────────────────────────────────────────────

class LLMWiki:
    """
    Portable LLM Wiki implementing Karpathy's three-layer pattern.

    Three-layer structure:
      wiki/raw/sources/   — immutable source documents
      wiki/               — LLM-maintained knowledge pages
      CLAUDE.md           — schema (rules & conventions)

    Two-step ingest: Analysis → Generation (per nashsu implementation)
    Operations: ingest | query | lint
    """

    def __init__(self, llm_client, config: Optional[dict] = None):
        self.llm = llm_client
        self.cfg = config or {}
        self.wiki_dir = Path(self.cfg.get("directory", "wiki"))
        self.index_file = Path(self.cfg.get("index_file", "wiki/index.md"))
        self.purpose_file = Path(self.cfg.get("purpose_file", "purpose.md"))
        self._init_structure()

    # ── Three Operations ──────────────────────────────────────────────────────

    def ingest(self, raw_text: str, topic_hint: str = "", source_name: str = "") -> WikiPage:
        """
        Two-step ingest (Karpathy + nashsu pattern):
          Step 1 — Analysis: understand the source, find connections & contradictions
          Step 2 — Generation: write wiki pages based on analysis
        """
        # Save raw source
        if source_name:
            raw_path = self.wiki_dir / "raw" / "sources" / f"{_slugify(source_name)}.md"
            raw_path.write_text(raw_text)

        # Step 1: Analysis
        index_snapshot = self._read_index_snapshot()
        purpose = self.read_purpose()
        analysis = self._analyse(raw_text, topic_hint, index_snapshot, purpose)

        # Step 2: Generation
        page_text = self._generate(raw_text, topic_hint, analysis, index_snapshot)
        page = WikiPage.from_markdown(page_text)

        # Save to sources/ subdirectory
        subdir = self._subdir_for_type(page.page_type)
        filename = self._save_page(page, page_text, subdir=subdir)
        page.filename = filename

        # Update index, log, overview
        self._update_index(page)
        self._append_log("ingest", topic_hint or page.title)
        self._update_overview()

        return page

    def query(self, question: str, max_pages: int = 5) -> str:
        """
        Query the wiki: read index first, find relevant pages, synthesise answer.
        Follows Karpathy's query pattern — index.md as navigation entry point.
        """
        relevant = self.search(question, max_results=max_pages)
        context_parts = [f"Question: {question}\n\nWiki pages retrieved:"]
        for page in relevant:
            context_parts.append(f"\n### {page.title}\n{page.excerpt(600)}")

        index = self.index_file.read_text() if self.index_file.exists() else ""
        prompt = "\n".join(context_parts)
        system = (
            "You are a Wiki Query Agent. Answer the question using only the wiki pages provided. "
            "Cite pages by [[title]]. If the answer requires pages not shown, say so.\n\n"
            f"Wiki index (for navigation):\n{index[:1500]}"
        )
        answer = self.llm.chat(prompt=prompt, system=system, temperature=0.2)
        self._append_log("query", question[:100])
        return answer

    def lint(self) -> LintReport:
        """
        Health-check the wiki: find contradictions, orphans, gaps, stale claims.
        """
        import json
        pages = self._load_all_pages()
        page_summaries = "\n".join(
            f"- [[{p.title}]] (type={p.page_type}, tags={p.tags}): {p.excerpt(150)}"
            for p in pages[:30]   # limit to avoid token overflow
        )
        index = self.index_file.read_text() if self.index_file.exists() else ""
        prompt = (
            f"Wiki index:\n{index[:1000]}\n\n"
            f"Page summaries:\n{page_summaries}"
        )
        raw = self.llm.chat(prompt=prompt, system=LINT_SYSTEM, temperature=0.1)
        try:
            clean = re.sub(r"```(?:json)?", "", raw).strip()
            data = json.loads(clean)
            report = LintReport(
                contradictions=data.get("contradictions", []),
                orphan_pages=data.get("orphan_pages", []),
                missing_pages=data.get("missing_pages", []),
                knowledge_gaps=data.get("knowledge_gaps", []),
                health_score=int(data.get("health_score", 5)),
                recommendations=data.get("recommendations", []),
            )
        except (json.JSONDecodeError, ValueError):
            report = LintReport([], [], [], [], 5, ["Lint parse error — re-run."])
        self._append_log("lint", f"score={report.health_score}")
        return report

    # ── Search & Read ─────────────────────────────────────────────────────────

    def search(self, query: str, max_results: int = 5) -> list[WikiPage]:
        """Keyword search across all wiki subdirectories."""
        q = query.lower()
        results = []
        for md_file in sorted(self.wiki_dir.rglob("*.md")):
            if md_file.name in ("index.md", "log.md", "overview.md"):
                continue
            if "raw" in md_file.parts:
                continue
            text = md_file.read_text()
            if q in text.lower():
                results.append(WikiPage.from_markdown(text, filename=str(md_file.relative_to(self.wiki_dir))))
            if len(results) >= max_results:
                break
        return results

    def get_page(self, title: str) -> Optional[WikiPage]:
        slug = _slugify(title)
        for md_file in self.wiki_dir.rglob(f"{slug}*.md"):
            return WikiPage.from_markdown(md_file.read_text(), filename=md_file.name)
        return None

    def list_pages(self) -> list[str]:
        return [
            f.stem for f in sorted(self.wiki_dir.rglob("*.md"))
            if f.name not in ("index.md", "log.md", "overview.md")
            and "raw" not in f.parts
        ]

    def read_purpose(self) -> str:
        return self.purpose_file.read_text() if self.purpose_file.exists() else ""

    # ── Private ───────────────────────────────────────────────────────────────

    def _analyse(self, raw_text: str, hint: str, index: str, purpose: str) -> str:
        prompt = (
            f"Topic hint: {hint}\n\n"
            f"Existing wiki index:\n{index[:1500]}\n\n"
            f"Purpose context:\n{purpose[:500]}\n\n"
            f"Source to analyse:\n{raw_text[:3000]}"
        )
        return self.llm.chat(prompt=prompt, system=ANALYSIS_SYSTEM, temperature=0.1)

    def _generate(self, raw_text: str, hint: str, analysis: str, index: str) -> str:
        prompt = (
            f"Topic: {hint}\n\n"
            f"Analysis from Step 1:\n{analysis}\n\n"
            f"Existing wiki index:\n{index[:1000]}\n\n"
            f"Source text:\n{raw_text[:2000]}"
        )
        return self.llm.chat(prompt=prompt, system=GENERATION_SYSTEM, temperature=0.2)

    # BETA: overview regeneration heuristic — output quality varies by model
    def _update_overview(self):
        index = self.index_file.read_text() if self.index_file.exists() else ""
        prompt = f"Current wiki index:\n{index[:3000]}\n\nDate: {datetime.date.today().isoformat()}"
        overview_text = self.llm.chat(prompt=prompt, system=OVERVIEW_SYSTEM, temperature=0.3)
        overview_path = self.wiki_dir / "overview.md"
        overview_path.write_text(overview_text)

    def _save_page(self, page: WikiPage, content: str, subdir: str = "", suffix: str = "") -> str:
        slug = _slugify(page.title)
        target_dir = self.wiki_dir / subdir if subdir else self.wiki_dir
        target_dir.mkdir(parents=True, exist_ok=True)
        filename = f"{slug}{suffix}.md"
        path = target_dir / filename
        if path.exists():
            ts = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
            filename = f"{slug}_{ts}{suffix}.md"
            path = target_dir / filename
        path.write_text(content)
        return f"{subdir}/{filename}" if subdir else filename

    def _update_index(self, page: WikiPage):
        existing = self.index_file.read_text() if self.index_file.exists() else "# Wiki Index\n\n"
        entry = (
            f"- [[{page.title}]] ({page.page_type}) — {page.excerpt(120)}"
            f" *(tags: {', '.join(page.tags)})*\n"
        )
        self.index_file.write_text(existing + entry)

    def _append_log(self, operation: str, detail: str):
        """Append-only chronological log (Karpathy pattern)."""
        log_path = self.wiki_dir / "log.md"
        ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        entry = f"## [{ts}] {operation} | {detail}\n\n"
        existing = log_path.read_text() if log_path.exists() else "# Wiki Log\n\n"
        log_path.write_text(existing + entry)

    def _read_index_snapshot(self) -> str:
        return self.index_file.read_text() if self.index_file.exists() else "Empty index."

    def _load_all_pages(self) -> list[WikiPage]:
        pages = []
        for f in sorted(self.wiki_dir.rglob("*.md")):
            if f.name in ("index.md", "log.md", "overview.md") or "raw" in f.parts:
                continue
            pages.append(WikiPage.from_markdown(f.read_text(), filename=f.name))
        return pages

    def _init_structure(self):
        """Create the Karpathy three-layer directory structure."""
        for subdir in ["", "raw/sources", "entities", "concepts", "sources", "synthesis", "queries"]:
            (self.wiki_dir / subdir).mkdir(parents=True, exist_ok=True)
        if not self.index_file.exists():
            self.index_file.write_text(
                "# Wiki Index\n\n"
                "> Content catalog. Updated on every ingest. LLM reads this first when querying.\n\n"
            )
        log_path = self.wiki_dir / "log.md"
        if not log_path.exists():
            log_path.write_text("# Wiki Log\n\n> Append-only chronological record of operations.\n\n")

    @staticmethod
    def _subdir_for_type(page_type: str) -> str:
        return {"entity": "entities", "concept": "concepts", "source": "sources",
                "synthesis": "synthesis", "query": "queries"}.get(page_type, "concepts")


# ── Utilities ─────────────────────────────────────────────────────────────────

def _slugify(text: str) -> str:
    text = str(text).lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "_", text)
    return text[:80]


def _split_frontmatter(text: str) -> tuple[dict, str]:
    if text.startswith("---"):
        end = text.find("---", 3)
        if end != -1:
            try:
                fm = yaml.safe_load(text[3:end])
                return fm or {}, text[end + 3:].strip()
            except yaml.YAMLError:
                pass
    return {}, text
