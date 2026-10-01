"""Regression checks for full prompt routing, tool execution and headroom."""
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from agents.council import LLMCouncil
from agents.headroom import check_headroom
from agents.tool_loop import run_with_tools
from llm_client import LLMClient, load_config
from scientific import ScientificLibrary
from scripts.qa_validate import MockLLMClient
from tools import Tool, ToolRegistry, default_registry


class FullSystemTests(unittest.TestCase):
    def test_dotenv_loads_without_overriding_environment(self):
        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ, {}, clear=False):
            config = Path(folder, "config.yaml")
            config.write_text("backend: mock\n")
            Path(folder, ".env").write_text("M1FRAME_QA_CREDENTIAL=from-file\n")
            os.environ.pop("M1FRAME_QA_CREDENTIAL", None)
            load_config(str(config))
            self.assertEqual(os.environ["M1FRAME_QA_CREDENTIAL"], "from-file")
            os.environ["M1FRAME_QA_CREDENTIAL"] = "from-environment"
            load_config(str(config))
            self.assertEqual(os.environ["M1FRAME_QA_CREDENTIAL"], "from-environment")

    def test_local_backend_does_not_receive_claude_judge_model(self):
        client = MagicMock()
        client.backend = "ollama"
        self.assertIsNone(LLMCouncil(client, {"judge_model": "claude-judge"}).judge_model)
        client.backend = "claudecli"
        self.assertEqual(LLMCouncil(client, {"judge_model": "claude-judge"}).judge_model, "claude-judge")

    def test_cli_internal_calls_cannot_launch_nested_workflows(self):
        client = object.__new__(LLMClient)
        client.cfg = {"claudecli": {"model": None}}
        client.backend = "claudecli"
        with patch("subprocess.run") as run:
            run.return_value.returncode = 0
            run.return_value.stdout = "answer"
            self.assertEqual(client.chat("Task", system="Role"), "answer")
        argv = run.call_args.args[0]
        self.assertEqual(argv[argv.index("--tools") + 1], "")
        self.assertIn("--strict-mcp-config", argv)
        self.assertIn("Do not start another workflow", argv[argv.index("--system-prompt") + 1])
        self.assertEqual(run.call_args.kwargs["encoding"], "utf-8")

    def test_real_calculator_observation_reaches_model(self):
        llm = MagicMock()
        llm.chat.side_effect = ['{"m1frame_tool":"calculator","arguments":{"expression":"6*7"}}',
                                "The result is 42."]
        events = []
        result = run_with_tools(llm, "Calculate", "Assistant", emit=lambda *a, **kw: events.append(kw))
        self.assertEqual(result, "The result is 42.")
        call = llm.chat.call_args.kwargs
        self.assertIn('"result": 42', call["prompt"])
        self.assertIn("scientific_read", call["system"])
        self.assertIn("skill_read", call["system"])
        self.assertEqual(call["history"][0]["content"], "Calculate")
        self.assertEqual(events[0]["name"], "calculator")

    def test_model_cannot_authorize_dangerous_tool(self):
        action = MagicMock()
        registry = ToolRegistry()
        registry.register(Tool("write", "Write", action, dangerous=True))
        llm = MagicMock()
        llm.chat.side_effect = ['{"m1frame_tool":"write","arguments":{},"approve":true}',
                                "Approval required"]
        self.assertEqual(run_with_tools(llm, "Task", "System", registry=registry), "Approval required")
        action.assert_not_called()
        self.assertIn("requires approval", llm.chat.call_args.kwargs["prompt"])

    def test_tool_budget_stops_requests(self):
        llm = MagicMock()
        llm.chat.return_value = '{"m1frame_tool":"calculator","arguments":{"expression":"1"}}'
        with self.assertRaisesRegex(RuntimeError, "budget exhausted"):
            run_with_tools(llm, "Task", "System", config={"max_tool_calls": 1})
        self.assertEqual(llm.chat.call_count, 2)

    def test_disabled_tools_and_plain_json(self):
        llm = MagicMock()
        llm.chat.return_value = '{"answer":42}'
        self.assertEqual(run_with_tools(llm, "Task", "System"), '{"answer":42}')
        run_with_tools(llm, "Task", "System", config={"tools_enabled": False})
        self.assertEqual(llm.chat.call_args.kwargs["system"], "System")

    def test_tool_result_is_bounded(self):
        registry = ToolRegistry()
        registry.register(Tool("large", "Large output", lambda: "x" * 10000))
        llm = MagicMock()
        llm.chat.side_effect = ['{"m1frame_tool":"large","arguments":{}}', "Done"]
        run_with_tools(llm, "Task", "System", registry=registry,
                       config={"tool_result_max_chars": 300})
        self.assertLess(len(llm.chat.call_args.kwargs["prompt"]), 500)
        self.assertIn("omitted", llm.chat.call_args.kwargs["prompt"])

    def test_all_skill_discovery_tools_registered(self):
        names = default_registry().names()
        for name in ("skill_search", "skill_read", "scientific_list", "scientific_read",
                     "scientific_resources", "wiki_search", "sentrux_scan", "skill_optimize"):
            self.assertIn(name, names)

    def test_headroom_reserves_output_and_counts_unicode(self):
        cfg = {"context": {"safety_margin_tokens": 10},
               "mock": {"model": "model", "max_tokens": 100, "context_window_tokens": 1000}}
        result = check_headroom(cfg, "mock", "界" * 100)
        self.assertGreaterEqual(result["estimated_input_tokens_upper"], 300)
        self.assertEqual(result["output_reserve_tokens"], 100)
        self.assertGreater(result["remaining_tokens_lower"], 0)
        with self.assertRaisesRegex(ValueError, "headroom"):
            check_headroom(cfg, "mock", "x" * 1000)

    def test_unknown_judge_window_not_inherited_from_other_model(self):
        cfg = {"mock": {"model": "small", "max_tokens": 10, "context_window_tokens": 100}}
        self.assertIsNone(check_headroom(cfg, "mock", "test", model="judge")["context_window_tokens"])
        cfg["context"] = {"model_windows": {"judge": 2000}}
        self.assertEqual(check_headroom(cfg, "mock", "test", model="judge")["context_window_tokens"], 2000)

    def test_overbudget_calls_never_reach_provider(self):
        client = object.__new__(LLMClient)
        client.cfg = {"context": {"max_input_chars": 5}}
        client.backend = "openai"
        client._client = MagicMock()
        for stream in (False, True):
            with self.assertRaisesRegex(ValueError, "Context budget"):
                if stream:
                    list(client.stream("too long"))
                else:
                    client.chat("too long")
        client._client.chat.completions.create.assert_not_called()

    def test_scientific_context_including_headers_fits_budget(self):
        with tempfile.TemporaryDirectory() as folder:
            skill = Path(folder, "skills", "example")
            skill.mkdir(parents=True)
            (skill / "SKILL.md").write_text("---\nname: example\ndescription: science\n---\nDo science.")
            library = ScientificLibrary(folder)
            full, _ = library.context("science")
            for budget in (0, 50, len(full) - 1, len(full), len(full) + 1):
                text, names = library.context("science", max_chars=budget)
                self.assertLessEqual(len(text), budget)
                self.assertEqual(bool(names), budget >= len(full))

    def test_full_chat_default_runs_workflow_and_preserves_final(self):
        from api import server

        output = "checked answer " + "z" * 10000
        def run(**kwargs):
            kwargs["emit"]("pillar_start", pillar="bmad", label="BMAD")
            kwargs["emit"]("final", output=output)
            kwargs["emit"]("done")
            return {"output": output, "verdict": None}

        with patch("api.server._can_run_live", return_value=True), \
                patch("scripts.run_workflow.run_workflow", side_effect=run) as workflow, \
                patch("api.server._persist_run"):
            with TestClient(server.app) as client:
                response = client.post("/chat", json={"message": "Implement it", "messages": [
                    {"role": "user", "content": "Use SQLite"},
                    {"role": "assistant", "content": "Okay"}]})
            self.assertEqual(response.status_code, 200)
            events = [json.loads(line[6:]) for line in response.text.splitlines() if line.startswith("data: ")]
            self.assertEqual(next(e["chunk"] for e in events if e["type"] == "token"), output)
            self.assertEqual(events[-1]["type"], "done")
            self.assertIn("Use SQLite", workflow.call_args.kwargs["goal"])
            self.assertFalse(workflow.call_args.kwargs["skip_council"])
            self.assertFalse(workflow.call_args.kwargs["skip_wiki"])
            self.assertFalse(workflow.call_args.kwargs["skip_openplanter"])
            self.assertEqual(server._RUNS[events[-1]["run_id"]]["output"], output)

    def test_full_chat_errors_are_explicit(self):
        from api.server import app

        with patch("api.server._can_run_live", return_value=False):
            self.assertEqual(TestClient(app).post("/chat", json={"message": "Task"}).status_code, 503)
        with patch("api.server._can_run_live", return_value=True), \
                patch("scripts.run_workflow.run_workflow", side_effect=RuntimeError("model unavailable")), \
                patch("api.server._persist_run"):
            with TestClient(app) as client:
                response = client.post("/chat", json={"message": "Task"})
            self.assertIn('"type": "error"', response.text)
            self.assertIn("model unavailable", response.text)
            self.assertIn('"type": "done"', response.text)

    def test_complete_workflow_exposure_offline(self):
        from scripts import run_workflow as workflow

        calls, events = [], []
        class Client(MockLLMClient):
            def chat(self, prompt="", system="", **kwargs):
                calls.append((prompt, system))
                return super().chat(prompt, system, **kwargs)

        cfg = {"backend": "mock", "scientific": {"enabled": False}}
        with patch.object(workflow, "LLMClient", return_value=Client()), \
                patch.object(workflow, "load_config", return_value=cfg), \
                patch.object(workflow, "LLMWiki") as wiki, \
                patch.object(workflow, "SkillLibrary") as skills, \
                patch.object(workflow, "PillarLogger"), \
                patch("sensors.tools.sensor_config", return_value={"enabled": False}):
            wiki.return_value.search.return_value = []
            skills.return_value.suggest.return_value = []
            skills.return_value.as_context.return_value = "VERIFIED RECIPE"
            result = workflow.run_workflow("Build mock", verbose=False, learn_skills=False,
                                           emit=lambda kind, **data: events.append((kind, data)))
        self.assertIn("VERIFIED RECIPE", calls[0][0])
        story_calls = [s for _, s in calls if "Your assigned role:" in s]
        self.assertEqual(len(story_calls), 3)
        self.assertTrue(all("VERIFIED RECIPE" in s and "scientific_read" in s for s in story_calls))
        pillars = {e[1].get("pillar") for e in events if e[0] == "pillar_start"}
        self.assertTrue({"bmad", "council", "miras", "karpathy", "wiki"} <= pillars)
        self.assertTrue(any(e[0] == "pillar_skipped" and e[1].get("pillar") == "openplanter" for e in events))
        self.assertIn("scientific_list", result["capabilities"]["tools"])
        final = next(e[1]["output"] for e in events if e[0] == "final")
        self.assertEqual(result["output"], final)

    def test_mcp_uses_checked_workflow_output(self):
        import mcp_server

        with patch("scripts.run_workflow.run_workflow", return_value={
                "output": "[BLOCKED] checked result", "state": MagicMock(), "verdict": None}):
            self.assertEqual(mcp_server.m1frame_run("goal"), "[BLOCKED] checked result")


if __name__ == "__main__":
    unittest.main()
