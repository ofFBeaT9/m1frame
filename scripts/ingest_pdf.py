#!/usr/bin/env python3
"""
scripts/ingest_pdf.py — Feed one or more PDFs into the m1frame wiki pipeline.

Extracts text page-by-page, then calls wiki.ingest() with a two-step
Analysis → Generation pass. Each PDF becomes a `source` wiki page.

Usage:
    python scripts/ingest_pdf.py report.pdf "topic hint"
    python scripts/ingest_pdf.py *.pdf                          # glob
    python scripts/ingest_pdf.py report.pdf --dry-run           # preview text only
    python scripts/ingest_pdf.py report.pdf --chunk 4000        # chunk size (chars)
    python scripts/ingest_pdf.py report.pdf --backend ollama    # override LLM backend

Dependencies:
    pip install pypdf                   # PDF text extraction (pure Python)
    # Optional: pip install pdfplumber  # richer table/layout extraction (fallback)

Environment:
    ANTHROPIC_API_KEY  (or OPENAI_API_KEY / none for Ollama)
"""
from __future__ import annotations

import argparse
import sys
import textwrap
from pathlib import Path

# ── project root on path ──────────────────────────────────────────────────────
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))


def _extract_pypdf(pdf_path: Path) -> str:
    try:
        from pypdf import PdfReader
        reader = PdfReader(str(pdf_path))
        pages = []
        for i, page in enumerate(reader.pages):
            text = page.extract_text() or ""
            if text.strip():
                pages.append(f"[Page {i+1}]\n{text.strip()}")
        return "\n\n".join(pages)
    except ImportError:
        raise SystemExit(
            "pypdf not installed. Run: pip install pypdf\n"
            "Or for richer table extraction: pip install pdfplumber"
        )


def _extract_pdfplumber(pdf_path: Path) -> str:
    import pdfplumber
    pages = []
    with pdfplumber.open(str(pdf_path)) as pdf:
        for i, page in enumerate(pdf.pages):
            text = page.extract_text() or ""
            if text.strip():
                pages.append(f"[Page {i+1}]\n{text.strip()}")
    return "\n\n".join(pages)


def extract_text(pdf_path: Path) -> str:
    """Try pypdf first, fall back to pdfplumber if installed."""
    try:
        return _extract_pypdf(pdf_path)
    except SystemExit:
        pass
    try:
        return _extract_pdfplumber(pdf_path)
    except ImportError:
        raise SystemExit(
            "No PDF extraction library found.\n"
            "Install one of:\n"
            "  pip install pypdf          (recommended, pure Python)\n"
            "  pip install pdfplumber     (better for tables)"
        )


def chunk_text(text: str, chunk_size: int) -> list[str]:
    """Split text into overlapping chunks so context is preserved at boundaries."""
    if len(text) <= chunk_size:
        return [text]
    chunks = []
    step = int(chunk_size * 0.9)          # 10% overlap
    for start in range(0, len(text), step):
        chunk = text[start: start + chunk_size]
        if chunk.strip():
            chunks.append(chunk)
    return chunks


def ingest_pdf(
    pdf_path: Path,
    topic_hint: str = "",
    chunk_size: int = 6000,
    backend: str | None = None,
    dry_run: bool = False,
    verbose: bool = False,
) -> None:
    print(f"\n[PDF] {pdf_path.name}")

    # ── Extract ───────────────────────────────────────────────────────────────
    text = extract_text(pdf_path)
    char_count = len(text)
    word_count = len(text.split())
    print(f"      Extracted {char_count:,} chars · {word_count:,} words · "
          f"{len(chunk_text(text, chunk_size))} chunk(s)")

    if dry_run:
        print("\n── DRY RUN preview (first 600 chars) ──")
        print(textwrap.indent(text[:600], "  "))
        print("──────────────────────────────────────")
        return

    # ── Load LLM + Wiki ───────────────────────────────────────────────────────
    from llm_client import LLMClient, load_config
    from agents.wiki import LLMWiki

    cfg = load_config(ROOT / "config.yaml")
    if backend:
        cfg["backend"] = backend
    llm = LLMClient(cfg)
    wiki = LLMWiki(llm, wiki_dir=str(ROOT / "wiki"), purpose_file=str(ROOT / "purpose.md"))

    hint = topic_hint or pdf_path.stem.replace("_", " ").replace("-", " ")
    chunks = chunk_text(text, chunk_size)

    # ── Ingest each chunk ─────────────────────────────────────────────────────
    for i, chunk in enumerate(chunks):
        label = f"{hint} (part {i+1})" if len(chunks) > 1 else hint
        print(f"      Ingesting chunk {i+1}/{len(chunks)}: {label!r} ...", end="", flush=True)
        try:
            page = wiki.ingest(chunk, topic_hint=label)
            print(f" -> {page.page_type}: {page.title!r}")
            if verbose:
                print(f"         saved: {page.file_path}")
        except Exception as exc:
            print(f" ERROR: {exc}")

    print(f"[OK]  {pdf_path.name} ingested into wiki.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Ingest PDF files into the m1frame wiki pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""\
            Examples:
              python scripts/ingest_pdf.py report.pdf
              python scripts/ingest_pdf.py report.pdf "quarterly earnings"
              python scripts/ingest_pdf.py report.pdf --dry-run
              python scripts/ingest_pdf.py *.pdf --chunk 8000
              python scripts/ingest_pdf.py report.pdf --backend ollama
        """),
    )
    parser.add_argument("pdfs", nargs="+", help="One or more PDF file paths")
    parser.add_argument("topic", nargs="?", default="", help="Topic hint for wiki page (optional)")
    parser.add_argument("--chunk", type=int, default=6000, metavar="N",
                        help="Max chars per ingest chunk (default: 6000)")
    parser.add_argument("--backend", default=None, choices=["claude","openai","ollama","vllm","lmstudio"],
                        help="Override LLM backend from config.yaml")
    parser.add_argument("--dry-run", action="store_true",
                        help="Extract text and preview; skip LLM ingest")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Print saved file paths")
    args = parser.parse_args()

    pdf_paths = []
    for p in args.pdfs:
        path = Path(p)
        if not path.exists():
            print(f"WARNING: {p} not found, skipping")
            continue
        if path.suffix.lower() != ".pdf":
            print(f"WARNING: {p} is not a .pdf, skipping")
            continue
        pdf_paths.append(path)

    if not pdf_paths:
        print("No valid PDF files found.")
        sys.exit(1)

    print(f"\nm1frame PDF Ingest — {len(pdf_paths)} file(s)")
    print("=" * 50)

    for pdf in pdf_paths:
        ingest_pdf(
            pdf,
            topic_hint=args.topic,
            chunk_size=args.chunk,
            backend=args.backend,
            dry_run=args.dry_run,
            verbose=args.verbose,
        )

    print("\nDone. Run wiki.lint() or check wiki/index.md to verify.")


if __name__ == "__main__":
    main()
