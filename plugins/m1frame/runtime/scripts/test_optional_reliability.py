"""Optional integrations must preserve evidence and fail visibly."""
import json
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from agents.guardrails import GuardedLLMClient, GuardrailEngine
from agents.openplanter import Entity, OpenPlanterAgent
from modules.headroom import HeadroomAdapter


class OptionalReliabilityTests(unittest.TestCase):
    def test_classifier_ambiguous_response_fails_closed(self):
        guard = GuardrailEngine({"shieldgemma": {"enabled": True}})
        guard._sg_client = MagicMock()
        for answer in ("", "maybe", "No idea", "Yes and No"):
            guard._sg_client.chat.completions.create.return_value.choices[0].message.content = answer
            with self.subTest(answer=answer):
                self.assertTrue(guard._shieldgemma_blocks("input", "ordinary text"))
        for answer, expected in (("No.", False), ("Yes", True)):
            guard._sg_client.chat.completions.create.return_value.choices[0].message.content = answer
            self.assertEqual(guard._shieldgemma_blocks("input", "ordinary text"), expected)

    def test_guarded_stream_checks_combined_output(self):
        inner, guard = MagicMock(), MagicMock()
        guard.check_input.return_value = types.SimpleNamespace(allowed=True, text="prompt")
        guard.check_output.return_value = types.SimpleNamespace(allowed=False)
        guard.refusal_text.return_value = "blocked"
        inner.stream.return_value = iter(["sen", "sitive"])
        self.assertEqual(list(GuardedLLMClient(inner, guard).stream("prompt")), ["blocked"])
        guard.check_output.assert_called_once_with("sensitive")

    def test_compression_defaults_avoid_download_and_preserve_system(self):
        adapter = HeadroomAdapter()
        adapter.enabled = True
        messages = [{"role": "system", "content": "rules"}, {"role": "user", "content": "task"}]
        adapter._compress = MagicMock(return_value=types.SimpleNamespace(messages=messages))
        adapter.compress_messages(messages, "example")
        self.assertEqual(adapter._compress.call_args.kwargs["kompress_model"], "disabled")
        self.assertFalse(adapter._compress.call_args.kwargs["compress_system_messages"])

    def test_compression_explicit_model_is_honored(self):
        adapter = HeadroomAdapter({"kompress_model": "chosen-model"})
        adapter.enabled = True
        messages = [{"role": "user", "content": "task"}]
        adapter._compress = MagicMock(return_value=types.SimpleNamespace(messages=messages))
        adapter.compress_messages(messages)
        self.assertEqual(adapter._compress.call_args.kwargs["kompress_model"], "chosen-model")

    def test_voyage_merge_preserves_all_evidence(self):
        agent = object.__new__(OpenPlanterAgent)
        agent._voyage_key = "fixture"
        agent.llm = MagicMock()
        agent.llm.chat.return_value = json.dumps({"merged_entities": [{
            "canonical_name": "Acme", "members": ["ACME", "Acme Inc"], "merge_confidence": "high"}]})
        fake = types.ModuleType("voyageai")
        fake.Client = MagicMock()
        fake.Client.return_value.embed.return_value.embeddings = [[1, 0], [1, 0]]
        entities = [Entity("ACME", ["A"], "org", "high", ["source-one"]),
                    Entity("Acme Inc", ["B"], "org", "medium", ["source-two"])]
        with patch.dict("sys.modules", {"voyageai": fake}):
            merged = agent._voyage_merge_entities(entities)
        self.assertEqual(len(merged), 1)
        self.assertEqual(set(merged[0].sources), {"source-one", "source-two"})
        self.assertEqual(set(merged[0].aliases), {"ACME", "Acme Inc", "A", "B"})
        self.assertEqual(merged[0].confidence, "medium")

    def test_investigation_workspace_and_results_do_not_collide(self):
        with tempfile.TemporaryDirectory() as folder:
            llm = MagicMock()
            llm.chat.return_value = "Observed fixture result"
            agent = OpenPlanterAgent(llm, {"workspace": folder})
            with patch.dict("os.environ", {}, clear=True):
                agent._exa_key = ""
                first = agent.investigate("first")
                second = agent.investigate("second")
            self.assertNotEqual(first.workspace_files, second.workspace_files)
            self.assertEqual(Path(first.workspace_files[0]).parent, Path(folder))
            self.assertIn("first", Path(first.workspace_files[0]).read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
