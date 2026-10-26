"""Offline tests for Phase 1: independent council, run journal + Studio, evaluation harness."""
import json
import os
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock


class FakeClient:
    def __init__(self, backend, reply):
        self.backend, self.reply, self.calls = backend, reply, []
        self.cfg = {backend: {"model": f"{backend}-default"}}

    def chat(self, prompt="", system="", temperature=None, model=None, **_):
        self.calls.append({"system": system[:40], "model": model})
        return self.reply(system) if callable(self.reply) else self.reply


def council_reply(system):
    if "red" in system.lower() and "team" in system.lower():
        return json.dumps({"verdict": "pass", "score": 8, "key_points": [], "recommendation": ""})
    if "synthes" in system.lower() or "aggregate" in system.lower():
        return json.dumps({"consensus_score": 8, "verdict": "pass", "summary": "ok",
                           "required_fixes": [], "consensus_points": [], "recommended_plan": "plan"})
    return json.dumps({"verdict": "pass", "score": 8, "key_points": ["fine"], "recommendation": "",
                       "approach": "a", "key_considerations": [], "risks": [], "opportunities": [],
                       "recommended_direction": "d"})


class IndependentCouncilTests(unittest.TestCase):
    def build(self, factory_ok=True, **cfg):
        from agents.council import LLMCouncil
        default = FakeClient("claude", council_reply)
        others = {}

        def factory(backend):
            if not factory_ok:
                raise RuntimeError("Missing OPENAI_API_KEY")
            others[backend] = FakeClient(backend, council_reply)
            return others[backend]
        personas = [{"name": "Critic", "role": "r", "backend": "openai", "model": "gpt-x"},
                    {"name": "Advocate", "role": "r"},
                    {"name": "Domain Expert", "role": "r", "backend": "openrouter"}]
        council = LLMCouncil(default, {"personas": personas, **cfg}, client_factory=factory)
        return council, default, others

    def test_personas_use_their_own_providers(self):
        council, default, others = self.build(red_team_backend="openrouter", red_team_model="rt-model")
        council.review("task", "output")
        self.assertEqual(others["openai"].calls[0]["model"], "gpt-x")
        self.assertTrue(others["openrouter"].calls)
        status = council.model_status()
        self.assertEqual(status["distinct_providers"], 3)
        self.assertEqual(status["members"]["Red-Team"], {"backend": "openrouter", "model": "rt-model",
                                                         "requested_backend": "openrouter", "fell_back": False})
        self.assertEqual(status["scope"], "independent providers")

    def test_missing_provider_falls_back_and_says_so(self):
        council, default, _ = self.build(factory_ok=False)
        council.brainstorm("task")
        status = council.model_status()
        self.assertTrue(status["members"]["Critic"]["fell_back"])
        self.assertEqual(status["members"]["Critic"]["backend"], "claude")
        self.assertIn("openai", status["provider_fallbacks"])
        # The other provider's model id must not be sent to the fallback client.
        self.assertTrue(all(c["model"] is None for c in default.calls))

    def test_default_council_unchanged(self):
        from agents.council import LLMCouncil
        default = FakeClient("claude", council_reply)
        verdict = LLMCouncil(default, {}).review("task", "output")
        self.assertTrue(verdict.passed)
        self.assertEqual(LLMCouncil(default, {}).model_status()["distinct_providers"], 1)


class JournalTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        patcher = mock.patch.dict(os.environ, {"M1FRAME_RUNS_DIR": self.tmp.name})
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_live_then_final(self):
        from agents import journal
        j = journal.RunJournal("abcdef1234", "plan a thing", source="test")
        j.emit("pillar_start", pillar="bmad")
        self.assertIn("abcdef12", journal.list_live())
        events, offset = journal.read_events("abcdef12")
        self.assertEqual((events[0]["type"], events[0]["pillar"]), ("pillar_start", "bmad"))
        j.emit("final", output="answer", score=8.5, passed=True)
        more, _ = journal.read_events("abcdef12", offset)
        self.assertEqual(more[0]["type"], "final")
        j.finish({"output": "answer", "approved": True})
        self.assertEqual(journal.list_live(), [])
        final = journal.read_final("abcdef12")
        self.assertEqual((final["status"], final["output"], final["source"]), ("complete", "answer", "test"))
        self.assertEqual(final["events"][-1]["type"], "done")

    def test_partial_line_waits(self):
        from agents import journal
        j = journal.RunJournal("feedface99", "g")
        with j.events_path.open("a", encoding="utf-8") as f:
            f.write('{"type": "half"')
        self.assertEqual(journal.read_events("feedface")[0], [])

    def test_bad_ids_rejected(self):
        from agents import journal
        self.assertIsNone(journal.read_final("../etc"))
        self.assertIsNone(journal.read_live("../x"))

    def test_record_run_journals_only_external_runs(self):
        from modules.receipts import record_run

        @record_run
        def fake_workflow(goal, emit=None):
            emit("pillar_start", pillar="bmad")
            emit("final", output="done", score=9, passed=True)
            emit("done")
            return {"output": "done", "approved": True}

        cwd = os.getcwd()
        os.chdir(self.tmp.name)                    # receipts write under ./runs
        try:
            result = fake_workflow(goal="external goal")
            sid = result["studio_run_id"]
            final = json.loads((Path(self.tmp.name) / f"{sid}.json").read_text())
            self.assertEqual(final["goal"], "external goal")
            seen = []
            studio = fake_workflow(goal="studio goal", emit=lambda e, **d: seen.append(e))
            self.assertNotIn("studio_run_id", studio)
            self.assertIn("final", seen)
        finally:
            os.chdir(cwd)

    def test_journal_can_be_disabled(self):
        from agents import journal
        with mock.patch.dict(os.environ, {"M1FRAME_JOURNAL": "0"}):
            self.assertFalse(journal.enabled())


class StudioExternalRunTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        patcher = mock.patch.dict(os.environ, {"M1FRAME_RUNS_DIR": self.tmp.name})
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_studio_lists_and_streams_a_run_started_elsewhere(self):
        from fastapi.testclient import TestClient

        from agents import journal
        from api import server
        server._RUNS.clear()
        j = journal.RunJournal("0123456789", "goal from Claude", source="mcp")
        j.emit("pillar_start", pillar="bmad")
        with TestClient(server.create_app()) as client:
            runs = {r["run_id"]: r for r in client.get("/runs").json()}
            self.assertEqual(runs["01234567"]["status"], "running")
            self.assertEqual(runs["01234567"]["source"], "mcp")

            def finish():
                j.emit("final", output="the answer", score=8, passed=True)
                j.emit("done")
                j.finish({"output": "the answer", "approved": True})
            threading.Timer(0.8, finish).start()
            stream = client.get("/run/01234567/events").text
            self.assertIn("pillar_start", stream)
            self.assertIn("the answer", stream)
            self.assertIn('"done"', stream)
            self.assertEqual(client.get("/run/01234567").json()["status"], "complete")
        server._RUNS.clear()

    def test_configured_public_origin_allowed(self):
        from api.server import _allowed_origin
        self.assertTrue(_allowed_origin("http://127.0.0.1:8080", "http://127.0.0.1:8080/"))
        self.assertFalse(_allowed_origin("https://evil.example", "http://127.0.0.1:8080/"))
        with mock.patch.dict(os.environ, {"M1FRAME_ALLOWED_ORIGINS": "https://pi.tail.ts.net:8443"}):
            self.assertTrue(_allowed_origin("https://pi.tail.ts.net:8443", "http://127.0.0.1:8080/"))


class ScriptedLLM:
    def __init__(self, backend, fn):
        self.backend, self.fn = backend, fn
        self.cfg = {backend: {"model": f"{backend}-m"}}

    def chat(self, prompt="", system="", temperature=None, **_):
        return self.fn(prompt, system)


def longer_wins_judge(prompt, system):
    a = prompt.split("Answer A:\n", 1)[1].split("\n\nAnswer B:\n", 1)[0]
    b = prompt.split("\n\nAnswer B:\n", 1)[1]
    hi, lo = {c: 8 for c in ("correctness", "completeness", "reasoning", "actionability", "risk_awareness")}, \
        {c: 5 for c in ("correctness", "completeness", "reasoning", "actionability", "risk_awareness")}
    win = "A" if len(a) > len(b) else "B"
    return json.dumps({"A": hi if win == "A" else lo, "B": lo if win == "A" else hi,
                       "winner": win, "rationale": "more complete"})


class EvalHarnessTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def problems(self):
        from evals.harness import Problem
        return [Problem("p1", "decide X"), Problem("p2", "decide Y", domain="ops")]

    def test_consistent_preference_counts_as_win(self):
        from evals.harness import SystemAnswer, run_eval
        out, summary = run_eval(self.problems(), baseline_llm=ScriptedLLM("claude", lambda p, s: "short"),
                                judge_llm=ScriptedLLM("openai", longer_wins_judge), out_root=self.tmp.name,
                                m1frame_fn=lambda p: SystemAnswer("a much longer, checked answer", 30.0, 17, True, 8.5))
        self.assertEqual((summary["m1frame_wins"], summary["judged"]), (2, 2))
        self.assertEqual(summary["mean_model_requests"], {"m1frame": 17.0, "baseline": 1.0})
        for name in ("results.json", "report.md", "blind_sheet.csv", "key.json"):
            self.assertTrue((out / name).is_file(), name)
        report = (out / "report.md").read_text()
        self.assertIn("m1frame won 2 of 2", report)
        self.assertNotIn("Warning: the judge", report)

    def test_position_bias_becomes_tie(self):
        from evals.harness import SystemAnswer, run_eval
        always_a = lambda p, s: json.dumps({"A": {c: 7 for c in ("correctness", "completeness", "reasoning",  # noqa: E731
                                                                   "actionability", "risk_awareness")},
                                            "B": {c: 6 for c in ("correctness", "completeness", "reasoning",
                                                                   "actionability", "risk_awareness")},
                                            "winner": "A", "rationale": "first"})
        _, summary = run_eval(self.problems()[:1], baseline_llm=ScriptedLLM("claude", lambda p, s: "b"),
                              judge_llm=ScriptedLLM("openai", always_a), out_root=self.tmp.name,
                              m1frame_fn=lambda p: SystemAnswer("m", 1.0))
        self.assertEqual((summary["ties"], summary["consistent_judgements"]), (1, 0))

    def test_same_judge_is_flagged_and_failures_not_judged(self):
        from evals.harness import SystemAnswer, run_eval
        out, summary = run_eval(self.problems()[:1], baseline_llm=ScriptedLLM("claude", lambda p, s: "b"),
                                judge_llm=ScriptedLLM("claude", longer_wins_judge), out_root=self.tmp.name,
                                m1frame_fn=lambda p: SystemAnswer("", 1.0, error="provider down"))
        self.assertEqual((summary["judged"], summary["errors"]), (0, 1))
        self.assertIn("Warning: the judge", (out / "report.md").read_text())

    def test_blind_sheet_key_matches(self):
        import csv

        from evals.harness import SystemAnswer, run_eval
        out, _ = run_eval(self.problems(), baseline_llm=ScriptedLLM("claude", lambda p, s: "BASE"),
                          judge_llm=ScriptedLLM("openai", longer_wins_judge), out_root=self.tmp.name,
                          m1frame_fn=lambda p: SystemAnswer("FULL PIPELINE", 1.0))
        key = json.loads((out / "key.json").read_text())
        with (out / "blind_sheet.csv").open(encoding="utf-8") as f:
            for row in csv.DictReader(f):
                expected = "FULL PIPELINE" if key[row["problem_id"]]["X"] == "m1frame" else "BASE"
                self.assertEqual(row["answer_X"], expected)

    def test_starter_problems_load(self):
        from evals.harness import load_problems
        problems = load_problems(Path(__file__).resolve().parent.parent / "evals/problems/starter.yaml")
        self.assertEqual(len(problems), 12)


class EnvOverrideTests(unittest.TestCase):
    def test_controller_and_vector_switches(self):
        from llm_client import load_config
        root = Path(__file__).resolve().parent.parent
        with mock.patch.dict(os.environ, {"M1FRAME_CONTROLLER": "on",
                                          "M1FRAME_VECTOR_MODEL": "sentence-transformers/all-MiniLM-L6-v2"}):
            cfg = load_config(str(root / "config.yaml"))
        self.assertTrue(cfg["controller"]["enabled"])
        self.assertEqual(cfg["wiki"]["vector_store"], "lancedb")


if __name__ == "__main__":
    unittest.main()
