"""Offline integration checks: python -m unittest scripts.test_scientific."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from agents.bmad import Blueprint, Story
from agents.miras import MirasOrchestrator
from scientific import ScientificLibrary
from scientific.tools import register_scientific_tools
from tools.registry import ToolRegistry


class ScientificTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.directory = self.root / "skills" / "genomics"
        self.directory.mkdir(parents=True)
        (self.directory / "SKILL.md").write_text(
            "---\nname: genomics\ndescription: |\n  DNA sequence analysis and genomics.\n---\n"
            "Use biological controls.\n", encoding="utf-8")
        (self.directory / "scripts").mkdir()
        (self.directory / "scripts" / "analyze.py").write_text(
            "import nonexistent_science_dependency\nimport os\n"
            "raise RuntimeError('must never execute during audit')\n"
            "key = os.environ['EXAMPLE_API_KEY']\n", encoding="utf-8")
        self.library = ScientificLibrary(self.root)

    def test_discovery_search_and_missing_checkout(self):
        self.assertEqual(self.library.list("DNA")[0]["name"], "genomics")
        self.assertEqual(self.library.list("unrelated"), [])
        self.assertEqual(self.library.list("build using"), [])
        self.assertFalse(ScientificLibrary(self.root / "missing").audit()["available"])

    def test_bad_frontmatter_and_duplicate_are_reported(self):
        for folder, text in [("bad", "not frontmatter"), ("duplicate", (self.directory / "SKILL.md").read_text())]:
            path = self.root / "skills" / folder
            path.mkdir()
            (path / "SKILL.md").write_text(text, encoding="utf-8")
        library = ScientificLibrary(self.root)
        self.assertEqual(len(library.skills), 1)
        self.assertEqual(len(library.errors), 2)

    def test_resource_traversal_and_pagination(self):
        self.assertIn("scripts/analyze.py", self.library.resources("genomics"))
        with self.assertRaises(ValueError):
            self.library.read("genomics", "../../outside.txt")
        with self.assertRaises(KeyError):
            self.library.read("../genomics")
        first = self.library.read("genomics", limit=11)
        rest = self.library.read("genomics", offset=first["next_offset"])
        self.assertEqual(first["text"] + rest["text"], self.library.read("genomics")["text"])

    def test_static_audit_never_executes_or_exposes_keys(self):
        with patch.dict("os.environ", {"EXAMPLE_API_KEY": "private-value"}):
            result = self.library.audit()
        entry = result["skills"][0]
        self.assertFalse(entry["import_probes"]["nonexistent_science_dependency"])
        self.assertTrue(entry["credential_hints"]["EXAMPLE_API_KEY"])
        self.assertNotIn("private-value", json.dumps(result))
        self.assertFalse(entry["execution_verified"])

    def test_complete_context_and_explicit_selection(self):
        context, names = self.library.context("DNA")
        self.assertEqual(names, ["genomics"])
        self.assertIn("Use biological controls.", context)
        self.assertEqual(self.library.context("DNA", max_chars=5), ("", []))
        self.assertEqual(self.library.context("DNA", names=[]), ("", []))
        self.assertEqual(self.library.context("unrelated", names=["genomics"])[1], names)

    def test_tool_registry_and_configured_checkout(self):
        with patch("llm_client.load_config", return_value={"scientific": {"path": str(self.root)}}):
            registry = register_scientific_tools(ToolRegistry())
            self.assertEqual(len(registry), 4)
            self.assertEqual(registry.call("scientific_list")[0]["name"], "genomics")
            self.assertIn("Use biological controls", registry.call("scientific_read", {"name": "genomics"})["text"])
        with patch("llm_client.load_config", return_value={"scientific": {"path": str(self.root), "enabled": False}}):
            self.assertEqual(registry.call("scientific_list"), [])

    def test_agents_receive_instructions_in_both_modes(self):
        class Client:
            def chat(inner, **kwargs):
                self.assertIn("Use biological controls.", kwargs["system"])
                return "instructions received"

        agent = MirasOrchestrator(Client(), scientific_library=self.library)
        self.assertEqual(agent.route_single("DNA sequence"), "instructions received")
        for parallel in (False, True):
            story = Story(id=1, title="DNA analysis", description="Analyze sequences", role="research",
                          type="research", complexity="low", depends_on=[], acceptance_criteria=[])
            blueprint = Blueprint(project_name="Science", goal_summary="DNA genomics",
                                  domain="science", mvp_scope="analysis", constraints=[],
                                  architecture_notes="", stories=[story], execution_order=[1])
            state = agent.run_parallel(blueprint) if parallel else agent.run(blueprint)
            self.assertEqual(state.outputs[1], "instructions received")

    def test_pipeline_selects_skills_for_planner_and_agents(self):
        from scripts import run_workflow as workflow
        from scripts.qa_validate import MockLLMClient

        calls = []

        class Client(MockLLMClient):
            def chat(inner, prompt="", system="", **kwargs):
                calls.append((prompt, system))
                return super().chat(prompt=prompt, system=system, **kwargs)

        cfg = {"backend": "mock", "scientific": {"path": str(self.root), "skills": ["genomics"]}}
        with patch.object(workflow, "load_config", return_value=cfg), \
                patch.object(workflow, "LLMClient", return_value=Client()), \
                patch.object(workflow, "PillarLogger", return_value=MagicMock()):
            result = workflow.run_workflow("Analyze DNA", verbose=False, skip_council=True,
                                           skip_wiki=True, skip_openplanter=True, learn_skills=False)
        self.assertEqual(result["scientific"]["selected"], ["genomics"])
        self.assertIn("Use biological controls.", calls[0][0])
        agent_calls = [system for _, system in calls if "Your assigned role:" in system]
        self.assertEqual(len(agent_calls), 3)
        self.assertTrue(all("Use biological controls." in system for system in agent_calls))


if __name__ == "__main__":
    unittest.main()
