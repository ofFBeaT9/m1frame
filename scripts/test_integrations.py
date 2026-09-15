"""Offline tests for the optional ADHD and Headroom integrations."""
from __future__ import annotations

import sys
import types
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.adhd import ADHDFormatter
from modules.headroom import HeadroomAdapter


class IntegrationTests(unittest.TestCase):
    def test_adhd_formatter_is_opt_in_and_conservative(self):
        prose = "Great question! Run the command.\n\nHope this helps!"
        self.assertEqual(ADHDFormatter().format(prose), prose)
        self.assertEqual(ADHDFormatter(True).format(prose), "Run the command.")
        structured = "---\ntitle: Example\n---\n\nHope this helps!"
        self.assertEqual(ADHDFormatter(True).format(structured), structured)
        self.assertIn("next action", ADHDFormatter(True).system_guidance().lower())

    def test_headroom_disabled_is_passthrough(self):
        messages = [{"role": "user", "content": "hello"}]
        result = HeadroomAdapter({"enabled": False}).compress_messages(messages)
        self.assertEqual(result.messages, messages)
        self.assertFalse(result.applied)

    def test_headroom_missing_dependency_is_passthrough(self):
        messages = [{"role": "user", "content": "hello"}]
        adapter = HeadroomAdapter({"enabled": True})
        if "headroom" in sys.modules:
            self.skipTest("headroom is installed in this environment")
        result = adapter.compress_messages(messages)
        self.assertEqual(result.messages, messages)
        self.assertFalse(result.available)
        self.assertTrue(result.error)

    def test_headroom_result_metrics_are_adapted(self):
        fake = types.ModuleType("headroom")

        class FakeResult:
            messages = [{"role": "user", "content": "short"}]
            tokens_before = 10
            tokens_after = 5
            tokens_saved = 5
            compression_ratio = 0.5
            transforms_applied = ["fake"]

        fake.compress = lambda messages, **kwargs: FakeResult()
        old = sys.modules.get("headroom")
        sys.modules["headroom"] = fake
        try:
            result = HeadroomAdapter({"enabled": True}).compress_messages(
                [{"role": "user", "content": "long"}], model="test"
            )
        finally:
            if old is None:
                sys.modules.pop("headroom", None)
            else:
                sys.modules["headroom"] = old
        self.assertTrue(result.available)
        self.assertTrue(result.applied)
        self.assertEqual(result.tokens_saved, 5)
        self.assertEqual(result.transforms_applied, ["fake"])


if __name__ == "__main__":
    unittest.main()
