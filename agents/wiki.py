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

New in v1.1:
  decay_confidence()  — age-based confidence decay on stale pages
  detect_contradictions() — writes wiki/contradictions.md
  Semantic search via LanceDB (optional, vector_store: lancedb in config)
"""

from __future__ import annotations

import datetime
import functools
import json
import re
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from agents.skills import _keywords
from agents.wiki_contract import inspect_pages, normalize_page, render_page, split_page


def _read_text(path: Path) -> str:
    """Read wiki markdown as UTF-8, tolerating legacy mixed-encoding files.

    Earlier versions called `read_text()` with no encoding, so on Windows they
    wrote cp1252 bytes (an em-dash became 0x97) into files that were otherwise
    UTF-8. Reading such a file strictly would now raise where the old code
    silently produced mojibake — turning a cosmetic bug into a crash on an
    existing workspace. Invalid bytes are therefore decoded as cp1252, which is
    where they actually came from, and the file heals on its next write.
    """
    raw = path.read_bytes()
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        out, i = [], 0
        while i < len(raw):
            try:
                out.append(raw[i:].decode("utf-8"))
                break
            except UnicodeDecodeError as e:
                out.append(raw[i:i + e.start].decode("utf-8"))
                out.append(raw[i + e.start:i + e.end].decode("cp1252", errors="replace"))
                i += e.end
        return "".join(out)


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
- For valid quoting, write the frontmatter as one JSON object (JSON is valid YAML),
  bounded by --- lines. All keys and string values must use double quotes.
  Never emit bare [[WikiLinks]] as YAML values. Related links are strings in an array.
- Include: title, tags, related (as [[WikiLinks]]), created (ISO date), sources (list), page_type, confidence (high|medium|low)
- Use [[WikiLinks]] to link to other pages
- Write ## Summary, ## Key Concepts, ## Details, ## Related, ## Open Questions sections
- Keep factual, concise, no filler
- Source pages go in sources/, entity pages in entities/, concepts in concepts/

Generate one page using the requested page type and project tag from the topic instructions. Default to a source summary when none is specified. No code fences. Start with ---
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

CONTRADICTION_SYSTEM = """You are a Contradiction Detection Agent.
Given a list of wiki page excerpts, identify any factual contradictions:
- Two pages asserting conflicting facts about the same entity
- Pages with incompatible dates, numbers, or claims
- Logical inconsistencies between related concepts

Respond in JSON:
{
  "contradictions": [
    {
      "page_a": "...",
      "page_b": "...",
      "conflict": "...",
      "severity": "high|medium|low",
      "recommendation": "..."
    }
  ],
  "clean": true|false
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
    def from_markdown(cls, text: str, filename: str = "") -> WikiPage:
        fm, _ = _split_frontmatter(text)
        heading = re.search(r"^#\s+(.+)$", text, re.MULTILINE)
        return cls(
            title=fm.get("title") or (heading.group(1).strip() if heading else Path(filename).stem or "Untitled"),
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

    @property
    def confidence(self) -> str:
        fm, _ = _split_frontmatter(self.content)
        return fm.get("confidence", "high")

    @property
    def created_date(self) -> datetime.date | None:
        try:
            return datetime.date.fromisoformat(str(self.created))
        except (ValueError, TypeError):
            return None

    @property
    def age_days(self) -> int:
        d = self.created_date
        if d is None:
            return 0
        return (datetime.date.today() - d).days


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


@dataclass
class ContradictionReport:
    contradictions: list[dict]   # {page_a, page_b, conflict, severity, recommendation}
    clean: bool

    def summary(self) -> str:
        if self.clean:
            return "No contradictions detected."
        lines = [f"Contradictions found: {len(self.contradictions)}"]
        for c in self.contradictions:
            lines.append(f"  [{c.get('severity','?').upper()}] {c.get('page_a')} ↔ {c.get('page_b')}: {c.get('conflict','')}")
        return "\n".join(lines)


# ── Main class ────────────────────────────────────────────────────────────────

def _locked_ingest(fn):
    @functools.wraps(fn)
    def wrapped(self, *args, **kwargs):
        from filelock import FileLock
        with FileLock(str(self.wiki_dir / '.ingest.lock'), timeout=30):
            return fn(self, *args, **kwargs)
    return wrapped


class LLMWiki:
    """
    Portable LLM Wiki implementing Karpathy's three-layer pattern.

    Three-layer structure:
      wiki/raw/sources/   — immutable source documents
      wiki/               — LLM-maintained knowledge pages
      CLAUDE.md           — schema (rules & conventions)

    Two-step ingest: Analysis → Generation (per nashsu implementation)
    Operations: ingest | query | lint | decay_confidence | detect_contradictions
    """

    def __init__(self, llm_client, config: dict | None = None):
        self.llm = llm_client
        self.cfg = config or {}
        self.wiki_dir = Path(self.cfg.get("directory", "wiki"))
        self.index_file = Path(self.cfg.get("index_file", str(self.wiki_dir / "index.md")))
        self.purpose_file = Path(self.cfg.get("purpose_file", "purpose.md"))
        self._vector_store = self.cfg.get("vector_store", "file")
        self._lancedb_table = None
        self._embedding_model: Any = None
        self._init_structure()

    # ── Three Operations ──────────────────────────────────────────────────────

    @_locked_ingest
    def ingest(self, raw_text: str, topic_hint: str = "", source_name: str = "",
               page_type: str | None = None, project: str = "",
               _analysis: str | None = None) -> WikiPage:
        """
        Two-step ingest (Karpathy + nashsu pattern):
          Step 1 — Analysis: understand the source, find connections & contradictions
          Step 2 — Generation: write wiki pages based on analysis
        """
        # Every ingest has immutable source evidence, including unnamed input.
        source_slug = _slugify(source_name) or f"source_{uuid.uuid4().hex}"
        raw_path = self.wiki_dir / "raw" / "sources" / f"{source_slug}.md"
        if raw_path.exists():
            raw_path = raw_path.with_name(raw_path.stem + "_" + uuid.uuid4().hex + ".md")
        with raw_path.open("x", encoding="utf-8", newline="") as handle:
            handle.write(raw_text)

        # Step 1: Analysis
        index_snapshot = self._read_index_snapshot()
        purpose = self.read_purpose()
        if page_type:
            topic_hint += f"\nRequired page_type: {page_type}. Project tag: {project}"
        analysis = _analysis if _analysis is not None else self._analyse(raw_text, topic_hint, index_snapshot, purpose)

        # Step 2: Generation
        page_text = self._generate(raw_text, topic_hint, analysis, index_snapshot)
        known = {p.title for p in self._load_all_pages()}
        fm, _ = split_page(page_text)
        # Creation is runtime metadata, never a date invented by the model.
        fm['created'] = datetime.date.today().isoformat()
        _, generated_body = split_page(page_text)
        page_text = render_page(fm, generated_body)
        kind = page_type or fm.get('page_type', 'source')
        source_id = raw_path.stem
        if kind != 'source':
            # An evidence pointer is deterministic bookkeeping, not a third LLM pass.
            evidence_title = f"Source Evidence {source_id}"
            evidence_fm = {'title': evidence_title, 'tags': [project] if project else [],
                           'related': [], 'created': datetime.date.today().isoformat(),
                           'page_type': 'source', 'confidence': 'medium',
                           'raw_source': str(raw_path.relative_to(self.wiki_dir)).replace('\\', '/')}
            evidence_text = render_page(evidence_fm, f"Immutable source record: [raw input](../raw/sources/{raw_path.name}).")
            evidence = WikiPage.from_markdown(evidence_text)
            evidence.filename = self._save_page(evidence, evidence_text, subdir='sources')
            self._update_index(evidence)
            known.add(evidence_title)
            source_id = Path(evidence.filename).stem
            page_text += f"\n\n## Source evidence\n[[{evidence_title}]]\n"
        if fm['title'] in known:
            fm['title'] += ' ' + uuid.uuid4().hex[:8]
            _, body = split_page(page_text)
            page_text = render_page(fm, body)
        page_text = normalize_page(page_text, known, page_type=kind,
                                   sources=[source_id] if kind != 'source' else [], project=project,
                                   raw_source=str(raw_path.relative_to(self.wiki_dir)).replace('\\', '/'))
        page = WikiPage.from_markdown(page_text)
        page.filename = self._save_page(page, page_text, subdir=self._subdir_for_type(page.page_type))

        # Update index, log, overview
        self._update_index(page)
        self._append_log("ingest", topic_hint or page.title)

        # Index into LanceDB if configured
        if self._vector_store == "lancedb":
            self._lancedb_upsert(page)

        self._update_overview()
        count = sum(1 for line in _read_text(self.wiki_dir / 'log.md').splitlines()
                    if '] ingest |' in line)
        if count and count % 5 == 0:
            self.decay_confidence()
            self.lint()
        return page

    def query(self, question: str, max_pages: int = 5) -> str:
        """
        Query the wiki: read index first, find relevant pages, synthesise answer.
        Follows Karpathy's query pattern — index.md as navigation entry point.
        Uses LanceDB semantic search when available, keyword search otherwise.
        """
        index = self._read_index_snapshot()
        purpose = self.read_purpose()
        if self._vector_store == "lancedb":
            relevant = self._lancedb_search(question, max_pages)
        else:
            relevant = self.search(question, max_results=max_pages)

        context_parts = [f"Question: {question}\n\nWiki pages retrieved:"]
        for page in relevant:
            context_parts.append(f"\n### {page.title}\n{page.excerpt(600)}")

        index = _read_text(self.index_file) if self.index_file.exists() else ""
        prompt = "\n".join(context_parts)
        system = (
            "You are a Wiki Query Agent. Answer the question using only the wiki pages provided. "
            "Cite pages by [[title]]. If the answer requires pages not shown, say so.\n\n"
            f"Purpose: {purpose[:1500]}\nWiki index (for navigation):\n{index[:1500]}"
        )
        answer = self.llm.chat(prompt=prompt, system=system, temperature=0.2)
        self._append_log("query", question[:100])
        return answer

    def lint(self) -> LintReport:
        """
        Health-check the wiki: find contradictions, orphans, gaps, stale claims.
        """
        self.read_purpose()
        index = self._read_index_snapshot()
        pages = self._load_all_pages()
        missing, orphans, issues = inspect_pages(pages, index)
        affected = {page.title for page in pages
                    if page.title in orphans
                    or any(item.startswith(page.title + ' ->') for item in missing)
                    or any(item.startswith(page.title + ':') or item.startswith(page.filename + ':')
                           for item in issues)}
        report = LintReport([], orphans, missing, [],
                            round(10 * (1 - len(affected) / max(1, len(pages)))), issues)
        self._append_log("lint", f"score={report.health_score}; pages={len(pages)}; semantic contradictions not assessed")
        return report

    # ── New v1.1 Operations ───────────────────────────────────────────────────

    def decay_confidence(
        self,
        medium_after_days: int = 30,
        low_after_days: int = 90,
    ) -> int:
        """
        Age-based confidence decay: pages older than the thresholds are
        downgraded if no newer sources have confirmed their claims.

          high  → medium  after `medium_after_days` days
          medium → low    after `low_after_days` days

        Returns the number of pages whose confidence was updated.
        """
        self.read_purpose()
        self._read_index_snapshot()
        updated = 0
        for md_file in self.wiki_dir.rglob("*.md"):
            if md_file.name in ("index.md", "log.md", "overview.md", "contradictions.md", "purpose.md"):
                continue
            if "raw" in md_file.parts:
                continue
            content = _read_text(md_file)
            page = WikiPage.from_markdown(content, filename=md_file.name)
            current = page.confidence
            age = page.age_days
            fm, _ = _split_frontmatter(content)
            # A confirmed date must accompany explicit confirming source references.
            if fm.get('confirming_sources') and fm.get('last_confirmed'):
                try:
                    confirmed = datetime.date.fromisoformat(str(fm['last_confirmed']))
                    source_stems = {Path(p.filename).stem for p in self._load_all_pages() if p.page_type == 'source'}
                    if all(ref in source_stems for ref in fm['confirming_sources']):
                        age = min(age, (datetime.date.today() - confirmed).days)
                except ValueError:
                    pass

            new_confidence = current
            if current == "high" and age >= medium_after_days:
                new_confidence = "medium"
            elif current == "medium" and age >= low_after_days:
                new_confidence = "low"

            if new_confidence != current:
                updated_content = re.sub(
                    r"(confidence:\s*)\S+",
                    f"\\g<1>{new_confidence}",
                    content,
                    count=1,
                )
                md_file.write_text(updated_content, encoding="utf-8")
                updated += 1

        if updated:
            self._append_log("decay", f"updated={updated} pages")
        return updated

    def detect_contradictions(self) -> ContradictionReport:
        """
        Run an LLM contradiction-detection pass across all wiki pages.
        Writes a summary to wiki/contradictions.md.
        Returns a ContradictionReport.
        """
        if hasattr(self, "purpose_file"):
            self.read_purpose()
            self._read_index_snapshot()
        pages = self._load_all_pages()
        if len(pages) < 2:
            report = ContradictionReport(contradictions=[], clean=True)
            self._write_contradictions(report)
            return report

        excerpts = "\n\n".join(
            f"=== [[{p.title}]] (type={p.page_type}) ===\n{p.excerpt(400)}"
            for p in pages
        )
        if len(excerpts) > int(getattr(self, 'cfg', {}).get('contradiction_max_chars', 100000)):
            raise ValueError('Contradiction corpus exceeds configured limit; no clean verdict recorded')
        raw = self.llm.chat(
            prompt=f"Analyse these wiki pages for contradictions:\n\n{excerpts}",
            system=CONTRADICTION_SYSTEM,
            temperature=0.1,
        )
        try:
            clean = re.sub(r"```(?:json)?", "", raw).strip()
            data = json.loads(clean)
            if (not isinstance(data, dict) or not isinstance(data.get("contradictions"), list)
                    or not isinstance(data.get("clean"), bool)):
                raise ValueError("Expected contradictions list and clean boolean")
            report = ContradictionReport(
                contradictions=data["contradictions"],
                clean=data["clean"] and not data["contradictions"],
            )
        except (json.JSONDecodeError, ValueError) as exc:
            raise ValueError("Contradiction check failed: invalid model response; no clean verdict recorded") from exc

        # Persist to wiki/contradictions.md
        self._write_contradictions(report)
        if report.contradictions:
            # Detection supplied the Analysis pass; Generation is the second call.
            self.ingest(excerpts, topic_hint="Document the detected source contradictions and evidence limits",
                        page_type="synthesis", project="wiki-contradictions", _analysis=raw)
        self._append_log("contradictions", f"found={len(report.contradictions)}")
        return report

    # ── Search & Read ─────────────────────────────────────────────────────────

    def search(self, query: str, max_results: int = 5) -> list[WikiPage]:
        """Rank meaningful query terms instead of requiring a whole-sentence match."""
        self.read_purpose()
        self._read_index_snapshot()
        terms = set(_keywords(query))
        if not terms or max_results <= 0:
            return []
        ranked = []
        for md_file in sorted(self.wiki_dir.rglob("*.md")):
            if md_file.name in ("index.md", "log.md", "overview.md"):
                continue
            if "raw" in md_file.relative_to(self.wiki_dir).parts:
                continue
            text = _read_text(md_file)
            page = WikiPage.from_markdown(text, filename=str(md_file.relative_to(self.wiki_dir)))
            matches = terms & set(_keywords(page.title + " " + page.content))
            if matches:
                score = len(matches) + 2 * len(terms & set(_keywords(page.title)))
                ranked.append((score, page))
        ranked.sort(key=lambda item: item[0], reverse=True)
        return [page for _, page in ranked[:max_results]]

    def get_page(self, title: str) -> WikiPage | None:
        self.read_purpose()
        self._read_index_snapshot()
        slug = _slugify(title)
        pages = self._load_all_pages()
        for page in pages:
            if page.title.casefold() == title.casefold():
                return page
        for page in pages:
            if _slugify(Path(page.filename).stem.replace("-", " ")) == slug:
                return page
        return None

    def list_pages(self) -> list[str]:
        self.read_purpose()
        self._read_index_snapshot()
        return [
            f.stem for f in sorted(self.wiki_dir.rglob("*.md"))
            if f.name not in ("index.md", "log.md", "overview.md", "contradictions.md", "purpose.md")
            and "raw" not in f.parts
        ]

    def read_purpose(self) -> str:
        return _read_text(self.purpose_file) if self.purpose_file.exists() else ""

    # ── LanceDB semantic search ───────────────────────────────────────────────

    def _lancedb_upsert(self, page: WikiPage) -> None:
        try:
            import lancedb
            db = lancedb.connect(str(self.wiki_dir / ".lancedb"))
            embed = self._embed(page.excerpt(800))
            if embed is None:
                return
            data = [{"id": page.title, "text": page.excerpt(800), "vector": embed}]
            if "pages" not in db.table_names():
                tbl = db.create_table("pages", data=data)
            else:
                tbl = db.open_table("pages")
                tbl.merge_insert("id").when_matched_update_all().when_not_matched_insert_all().execute(data)
        except Exception:
            pass  # LanceDB not available — degrade to keyword search

    def _lancedb_search(self, query: str, max_results: int = 5) -> list[WikiPage]:
        try:
            import lancedb
            db = lancedb.connect(str(self.wiki_dir / ".lancedb"))
            if "pages" not in db.table_names():
                return self.search(query, max_results)
            embed = self._embed(query)
            if embed is None:
                return self.search(query, max_results)
            tbl = db.open_table("pages")
            hits = tbl.search(embed).limit(max_results).to_list()
            pages = []
            for h in hits:
                p = self.get_page(h["id"])
                if p:
                    pages.append(p)
            return pages or self.search(query, max_results)
        except Exception:
            return self.search(query, max_results)

    def _embed(self, text: str) -> list[float] | None:
        """Return a vector embedding for text. Returns None if no embed model."""
        embed_model = self.cfg.get("embed_model")
        if not embed_model:
            return None
        try:
            from sentence_transformers import SentenceTransformer
            if self._embedding_model is None:
                self._embedding_model = SentenceTransformer(
                    embed_model, local_files_only=bool(self.cfg.get("embed_local_only", False)))
            return self._embedding_model.encode(text).tolist()
        except Exception:
            return None

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

    def _update_overview(self):
        """Refresh navigation without a third generation pass or invented claims."""
        index = _read_text(self.index_file) if self.index_file.exists() else ""
        overview_text = "# Wiki Overview\n\nGenerated from the current index.\n\n" + index
        overview_path = self.wiki_dir / "overview.md"
        overview_path.write_text(overview_text, encoding="utf-8")

    def _write_contradictions(self, report: ContradictionReport) -> None:
        path = self.wiki_dir / "contradictions.md"
        lines = [
            "# Contradiction Report",
            f"\nGenerated: {datetime.datetime.utcnow().isoformat()}Z\n",
        ]
        if report.clean:
            lines.append("✓ No contradictions detected.\n")
        else:
            for i, c in enumerate(report.contradictions, 1):
                lines.append(f"## Contradiction {i} [{c.get('severity','?').upper()}]")
                lines.append(f"**Pages:** [[{c.get('page_a','')}]] ↔ [[{c.get('page_b','')}]]")
                lines.append(f"**Conflict:** {c.get('conflict','')}")
                lines.append(f"**Recommendation:** {c.get('recommendation','')}\n")
        path.write_text("\n".join(lines), encoding="utf-8")

    def _save_page(self, page: WikiPage, content: str, subdir: str = "", suffix: str = "") -> str:
        slug = _slugify(page.title)
        target_dir = self.wiki_dir / subdir if subdir else self.wiki_dir
        target_dir.mkdir(parents=True, exist_ok=True)
        filename = f"{slug}{suffix}.md"
        path = target_dir / filename
        if path.exists():
            ts = uuid.uuid4().hex
            filename = f"{slug}_{ts}{suffix}.md"
            path = target_dir / filename
        with path.open("x", encoding="utf-8") as handle:
            handle.write(content)
        return f"{subdir}/{filename}" if subdir else filename

    def _update_index(self, page: WikiPage):
        entry = (
            f"- [[{page.title}]] ({page.page_type}) — {page.excerpt(120)}"
            f" *(tags: {', '.join(page.tags)})*\n"
        )
        with self.index_file.open("a", encoding="utf-8") as handle:
            handle.write(entry)

    def _append_log(self, operation: str, detail: str):
        """Append-only chronological log (Karpathy pattern)."""
        log_path = self.wiki_dir / "log.md"
        ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        entry = f"## [{ts}] {operation} | {detail}\n\n"
        with log_path.open("a", encoding="utf-8") as handle:
            handle.write(entry)

    def _read_index_snapshot(self) -> str:
        return _read_text(self.index_file) if self.index_file.exists() else "Empty index."

    def _load_all_pages(self) -> list[WikiPage]:
        pages = []
        for f in sorted(self.wiki_dir.rglob("*.md")):
            if f.name in ("index.md", "log.md", "overview.md", "contradictions.md", "purpose.md") or "raw" in f.parts:
                continue
            pages.append(WikiPage.from_markdown(_read_text(f), filename=str(f.relative_to(self.wiki_dir)).replace("\\", "/")))
        return pages

    def _init_structure(self):
        """Create the Karpathy three-layer directory structure."""
        for subdir in ["", "raw/sources", "entities", "concepts", "sources", "synthesis", "queries"]:
            (self.wiki_dir / subdir).mkdir(parents=True, exist_ok=True)
        if not self.index_file.exists():
            self.index_file.write_text(
                "# Wiki Index\n\n"
                "> Content catalog. Updated on every ingest. LLM reads this first when querying.\n\n",
                encoding="utf-8",
            )
        log_path = self.wiki_dir / "log.md"
        if not log_path.exists():
            log_path.write_text("# Wiki Log\n\n> Append-only chronological record of operations.\n\n", encoding="utf-8")

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
                return fm if isinstance(fm, dict) else {}, text[end + 3:].strip()
            except yaml.YAMLError:
                pass
    return {}, text
