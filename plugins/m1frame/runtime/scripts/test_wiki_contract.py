"""Verify the two-pass ingest and immutable input contract."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock

from agents.wiki import LLMWiki
from scripts.qa_validate import MockLLMClient


class WikiContractTests(unittest.TestCase):
    def test_unnamed_source_is_saved_unchanged_in_two_passes(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            llm = MagicMock(wraps=MockLLMClient())
            wiki = LLMWiki(llm, {"directory": folder, "index_file": str(root / "index.md")})
            raw = "First line\r\nSecond line\nUnicode: λ"
            wiki.ingest(raw, "fixture")
            sources = list((root / "raw/sources").glob("*.md"))
            self.assertEqual(len(sources), 1)
            self.assertEqual(sources[0].read_bytes(), raw.encode("utf-8"))
            self.assertEqual(llm.chat.call_count, 2)

    def test_repeated_source_name_never_overwrites_original(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            wiki = LLMWiki(MockLLMClient(), {"directory": folder,
                                           "index_file": str(root / "index.md")})
            wiki.ingest("first", source_name="shared")
            wiki.ingest("second", source_name="shared")
            self.assertEqual((root / "raw/sources/shared.md").read_text(), "first")
            self.assertEqual(len(list((root / "raw/sources").glob("*.md"))), 2)


if __name__ == "__main__":
    unittest.main()
