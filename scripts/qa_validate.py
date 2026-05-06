#!/usr/bin/env python3
"""
m1frame — QA Validation Suite
35 tests across all 5 pillars + end-to-end pipeline.
No API key required (mock mode). Fast, deterministic, offline.

Usage:
  python scripts/qa_validate.py                # all tests
  python scripts/qa_validate.py --pillar bmad  # one pillar
  python scripts/qa_validate.py --live         # real LLM (needs ANTHROPIC_API_KEY)
"""
from __future__ import annotations
import sys, json, time, argparse, traceback, tempfile
from pathlib import Path
from dataclasses import dataclass, field
from typing import Callable, Optional

sys.path.insert(0, str(Path(__file__).parent.parent))


# ══════════════════════════════════════════════════════════════════════════════
# Mock LLM — deterministic, parser-valid, routes on system prompt only
# ══════════════════════════════════════════════════════════════════════════════
class MockLLMClient:
    backend = "mock"

    def chat(self, prompt: str = "", system: str = "", **kw) -> str:
        s = system.lower()  # route on system prompt only — avoids collision

        # BMAD blueprint
        if any(k in s for k in ["scrum master", "story backlog", "execution_order",
                                  "project_name", "mvp_scope", "bmad"]):
            return json.dumps({
                "project_name": "Mock Project",
                "goal_summary": "Build a mock system",
                "domain": "testing",
                "mvp_scope": "Core functionality",
                "constraints": ["offline"],
                "architecture_notes": "Simple layered arch.",
                "stories": [
                    {"id": 1, "title": "Requirements", "role": "analyst", "type": "research",
                     "complexity": "low", "depends_on": [],
                     "acceptance_criteria": ["requirements documented"], "description": "Gather requirements."},
                    {"id": 2, "title": "Implementation", "role": "dev", "type": "code",
                     "complexity": "medium", "depends_on": [1],
                     "acceptance_criteria": ["tests pass"], "description": "Write the code."},
                    {"id": 3, "title": "Validation", "role": "qa", "type": "test",
                     "complexity": "low", "depends_on": [2],
                     "acceptance_criteria": ["all green"], "description": "Validate output."},
                ],
                "execution_order": [1, 2, 3],
            })

        # Council brainstorm SYNTHESIS (unique: recommended_plan, consensus_points)
        if "recommended_plan" in s or "consensus_points" in s or \
           ("synthesiser" in s and "brainstorm" in s):
            return json.dumps({
                "consensus_points": ["Test early", "Iterate fast"],
                "key_disagreements": [],
                "recommended_plan": "Incremental delivery with continuous testing",
                "implementation_steps": ["Write tests", "Implement", "Review"],
                "risks_to_mitigate": ["Scope creep"],
                "confidence": "high",
            })

        # Council brainstorm PERSONA (unique: recommended_direction)
        if "recommended_direction" in s or \
           ("brainstorm" in s and "persona" in s) or \
           ("brainstorm" in s and "council member" in s):
            return json.dumps({
                "persona": "Mock Critic",
                "approach": "Systematic validation first",
                "key_considerations": ["test coverage", "edge cases"],
                "risks": ["scope creep"],
                "opportunities": ["early issue detection"],
                "recommended_direction": "Build tests alongside implementation",
            })

        # Council review SYNTHESIS (unique: consensus_score, approved_output)
        if "consensus_score" in s or "approved_output" in s or \
           ("synthesiser" in s and "review mode" in s):
            return json.dumps({
                "consensus_score": 8.5,
                "verdict": "pass",
                "summary": "Output meets all quality criteria.",
                "required_fixes": [],
                "approved_output": "Mock approved output — task completed successfully.",
            })

        # Council review PERSONA (unique: key_points in schema)
        if "council reviewer" in s or \
           ("verdict" in s and "key_points" in s and "score" in s):
            return json.dumps({
                "persona": "Mock Critic",
                "verdict": "pass",
                "score": 8,
                "key_points": ["Logically sound", "Well structured"],
                "recommendation": "No changes needed.",
            })

        # Wiki lint
        if "lint" in s or "health_score" in s or "orphan" in s:
            return json.dumps({
                "contradictions": [],
                "orphan_pages": [],
                "missing_pages": ["Getting Started"],
                "knowledge_gaps": ["deployment"],
                "health_score": 8,
                "recommendations": ["Add a Getting Started page"],
            })

        # Wiki overview
        if "overview" in s or "global summary" in s or "auto_generated" in s:
            return ("---\ntitle: Overview\nauto_generated: true\nupdated: 2026-05-06\n---\n\n"
                    "## Current State\nWiki is healthy.\n\n## Key Themes\n- Testing\n\n"
                    "## Synthesis\nSystem works as intended.")

        # Wiki analysis step 1
        if "analysis agent" in s or "key_entities" in s or "suggested_page_types" in s:
            return json.dumps({
                "key_entities": ["MockSystem"],
                "key_concepts": ["testing", "validation"],
                "main_arguments": ["Mock responses enable offline testing"],
                "connections_to_existing": [],
                "contradictions_with_existing": [],
                "suggested_page_types": ["concept"],
                "recommended_wiki_structure": "Single concept page",
                "confidence": "high",
            })

        # Wiki generation step 2 / refinement
        if "generation agent" in s or "wiki page" in s or \
           "frontmatter" in s or "page_type" in s or "wikilink" in s:
            return (
                "---\ntitle: Mock Wiki Page\ntags: [test, mock]\nrelated: []\n"
                "created: 2026-05-06\nsources: []\npage_type: concept\nconfidence: high\n---\n\n"
                "## Summary\nA mock page created during QA.\n\n"
                "## Key Concepts\n- Mock testing\n\n"
                "## Details\nSynthetic content for testing purposes.\n\n"
                "## Open Questions\nNone."
            )

        # Karpathy (must come after wiki checks)
        if "reasoning engine" in s or "chain-of-thought" in s or "thought block" in s:
            return ("<thought>\nStep 1: Understand the task.\n"
                    "Step 2: Plan the answer.\nStep 3: Execute.\n</thought>\n\n"
                    "Mock answer: Task completed with chain-of-thought reasoning.")

        # Wiki query
        if "wiki query" in s or "answer the question using" in s:
            return "Based on the wiki pages, the answer is: mock result."

        # Miras sub-agent / generic fallback
        return ("<thought>\nAnalysing story as Miras sub-agent.\n</thought>\n\n"
                "Mock sub-agent result: story completed successfully.")


# ══════════════════════════════════════════════════════════════════════════════
# Test runner
# ══════════════════════════════════════════════════════════════════════════════
@dataclass
class R:
    name: str; passed: bool; msg: str = ""; ms: float = 0.0; tb: str = ""

@dataclass
class Suite:
    results: list[R] = field(default_factory=list)

    def run(self, name: str, fn: Callable) -> R:
        t0 = time.perf_counter()
        try:
            fn()
            r = R(name=name, passed=True, msg="OK", ms=(time.perf_counter()-t0)*1000)
        except AssertionError as e:
            r = R(name=name, passed=False, msg=str(e), ms=(time.perf_counter()-t0)*1000)
        except Exception as e:
            r = R(name=name, passed=False, msg=str(e),
                  ms=(time.perf_counter()-t0)*1000, tb=traceback.format_exc()[-600:])
        self.results.append(r)
        icon = "✓" if r.passed else "✗"
        print(f"  {icon} {'PASS' if r.passed else 'FAIL'}  {name:<52} ({r.ms:.0f}ms)")
        if not r.passed:
            print(f"       → {r.msg}")
            if r.tb:
                print(r.tb)
        return r

    def summary(self) -> bool:
        ok = sum(1 for r in self.results if r.passed)
        n  = len(self.results)
        print(f"\n{'═'*65}")
        print(f"  m1frame QA:  {ok}/{n} passed")
        if ok == n:
            print("  🟢  ALL TESTS PASSED — release ready")
        else:
            print(f"  🔴  {n-ok} FAILED:")
            for r in self.results:
                if not r.passed:
                    print(f"     • {r.name}: {r.msg}")
        print(f"{'═'*65}\n")
        return ok == n


# ══════════════════════════════════════════════════════════════════════════════
# Tests
# ══════════════════════════════════════════════════════════════════════════════
def _wcfg(tmp):
    return {"directory": str(tmp/"wiki"), "index_file": str(tmp/"wiki"/"index.md"),
            "purpose_file": str(tmp/"purpose.md")}

# CONFIG
def t_config_keys():
    from llm_client import load_config
    cfg = load_config()
    for k in ["backend","claude","ollama","bmad","miras","karpathy","council","wiki"]:
        assert k in cfg, f"missing key: {k}"

def t_purpose_file():
    p = Path("purpose.md")
    assert p.exists() and len(p.read_text()) > 50

def t_claude_md():
    p = Path("CLAUDE.md")
    assert p.exists()
    c = p.read_text()
    assert "Page Types" in c and "WikiLink" in c

def t_imports():
    from agents import (BMADAgent, Blueprint, Story, BMAD_ROLES,
                        MirasOrchestrator, AgentState,
                        KarpathyEngine, KarpathyResult,
                        LLMCouncil, CouncilVerdict, BrainstormResult,
                        LLMWiki, WikiPage, LintReport)

def t_pyproject():
    assert Path("pyproject.toml").exists()

# BMAD
def t_bmad_plan(m):
    from agents.bmad import BMADAgent
    bp = BMADAgent(m).plan("Build a REST API")
    assert bp.project_name and bp.goal_summary
    assert len(bp.stories) >= 1
    assert len(bp.execution_order) >= 1

def t_bmad_roles(m):
    from agents.bmad import BMADAgent, BMAD_ROLES
    bp = BMADAgent(m).plan("Build something")
    for s in bp.stories:
        assert s.role in BMAD_ROLES, f"unknown role: {s.role}"
        assert isinstance(s.acceptance_criteria, list)

def t_bmad_validate(m):
    from agents.bmad import BMADAgent
    bp = BMADAgent(m).plan("Project")
    assert not BMADAgent(m).validate(bp)

def t_bmad_dep_order(m):
    from agents.bmad import BMADAgent
    bp = BMADAgent(m).plan("Deps")
    order = bp.execution_order
    for s in bp.stories:
        for dep in s.depends_on:
            assert order.index(dep) < order.index(s.id), f"dep order broken: {dep} must precede {s.id}"

def t_bmad_subtasks_alias(m):
    from agents.bmad import BMADAgent
    bp = BMADAgent(m).plan("Alias")
    assert bp.subtasks is bp.stories

# MIRAS
def t_miras_run(m):
    from agents.bmad import BMADAgent
    from agents.miras import MirasOrchestrator
    bp = BMADAgent(m).plan("Run")
    st = MirasOrchestrator(m).run(bp)
    assert st.outputs
    for sid in bp.execution_order:
        assert sid in st.outputs, f"story {sid} missing"

def t_miras_state(m):
    from agents.miras import AgentState
    st = AgentState(goal="t", blueprint_summary="b")
    st.add_result(1, "first"); st.add_result(2, "second")
    assert "Story 1" in st.final_output() and "Story 2" in st.final_output()

def t_miras_callbacks(m):
    from agents.bmad import BMADAgent
    from agents.miras import MirasOrchestrator
    started, done = [], []
    bp = BMADAgent(m).plan("CB")
    MirasOrchestrator(m,
        on_subtask_start=lambda s: started.append(s.id),
        on_subtask_done=lambda s,r: done.append(s.id)).run(bp)
    assert len(started) == len(done) == len(bp.stories)

def t_miras_route_single(m):
    from agents.miras import MirasOrchestrator
    r = MirasOrchestrator(m).route_single("Explain X", role="dev")
    assert r

# KARPATHY
def t_karpathy_thought(m):
    from agents.karpathy import KarpathyEngine
    r = KarpathyEngine(m).run("What is 2+2?")
    assert r.had_thought_tag and r.thought and r.answer

def t_karpathy_batch(m):
    from agents.karpathy import KarpathyEngine
    rs = KarpathyEngine(m).batch(["Q1","Q2","Q3"])
    assert len(rs) == 3 and all(r.raw for r in rs)

def t_karpathy_refine(m):
    from agents.karpathy import KarpathyEngine
    r = KarpathyEngine(m).run("Refine this", refine=True)
    assert r.raw

def t_karpathy_few_shot(m):
    from agents.karpathy import KarpathyEngine
    p = KarpathyEngine(m).build_prompt("3+3", [{"input":"2+2","thought":"math","output":"4"}])
    assert "2+2" in p and "3+3" in p

def t_karpathy_str(m):
    from agents.karpathy import KarpathyEngine
    r = KarpathyEngine(m).run("x")
    assert str(r) == r.answer

# COUNCIL
def t_council_brainstorm(m):
    from agents.council import LLMCouncil
    br = LLMCouncil(m).brainstorm("Build an API")
    assert br.recommended_plan and isinstance(br.implementation_steps, list)

def t_council_perspectives(m):
    from agents.council import LLMCouncil
    c = LLMCouncil(m)
    br = c.brainstorm("Design a schema")
    assert len(br.perspectives) == len(c.personas)

def t_council_review(m):
    from agents.council import LLMCouncil
    v = LLMCouncil(m).review("Sort a list", "def sort(a): return sorted(a)")
    assert v.consensus_score > 0
    assert v.verdict in ("pass","fail","conditional")
    assert v.approved_output

def t_council_pass_threshold(m):
    from agents.council import LLMCouncil
    v = LLMCouncil(m, config={"consensus_threshold":7,"personas":[
        {"name":"C","role":"Find flaws."}]}).review("t","o")
    assert v.passed, f"score={v.consensus_score}"

def t_council_report(m):
    from agents.council import LLMCouncil
    r = LLMCouncil(m).review("t","o").report()
    assert "Verdict" in r and "/10" in r

def t_council_quick_check(m):
    from agents.council import LLMCouncil
    assert isinstance(LLMCouncil(m).quick_check("t","o"), bool)

# WIKI
def t_wiki_dirs(m):
    from agents.wiki import LLMWiki
    tmp = Path(tempfile.mkdtemp())
    LLMWiki(m, config=_wcfg(tmp))
    for d in ["raw/sources","entities","concepts","sources","synthesis"]:
        assert (tmp/"wiki"/d).exists(), f"missing wiki/{d}"
    assert (tmp/"wiki"/"log.md").exists()

def t_wiki_ingest(m):
    from agents.wiki import LLMWiki
    tmp = Path(tempfile.mkdtemp())
    pg = LLMWiki(m, config=_wcfg(tmp)).ingest("Python is a language.", "python")
    assert pg.title and pg.filename
    pages = [f for f in (tmp/"wiki").rglob("*.md")
             if f.name not in ("index.md","log.md","overview.md")]
    assert len(pages) >= 1

def t_wiki_log(m):
    from agents.wiki import LLMWiki
    tmp = Path(tempfile.mkdtemp())
    LLMWiki(m, config=_wcfg(tmp)).ingest("Test", "t")
    assert "ingest" in (tmp/"wiki"/"log.md").read_text().lower()

def t_wiki_index(m):
    from agents.wiki import LLMWiki
    tmp = Path(tempfile.mkdtemp())
    LLMWiki(m, config=_wcfg(tmp)).ingest("Quantum computing.", "quantum")
    assert "[[" in (tmp/"wiki"/"index.md").read_text()

def t_wiki_search(m):
    from agents.wiki import LLMWiki
    tmp = Path(tempfile.mkdtemp())
    w = LLMWiki(m, config=_wcfg(tmp))
    w.ingest("ML basics", "ml")
    assert len(w.search("mock")) >= 1

def t_wiki_query(m):
    from agents.wiki import LLMWiki
    tmp = Path(tempfile.mkdtemp())
    w = LLMWiki(m, config=_wcfg(tmp))
    w.ingest("AI safety overview", "safety")
    assert w.query("What is AI safety?")

def t_wiki_lint(m):
    from agents.wiki import LLMWiki
    tmp = Path(tempfile.mkdtemp())
    w = LLMWiki(m, config=_wcfg(tmp))
    w.ingest("Deep learning", "dl")
    rpt = w.lint()
    assert 1 <= rpt.health_score <= 10
    assert "Health Score" in rpt.summary()

def t_wiki_overview(m):
    from agents.wiki import LLMWiki
    tmp = Path(tempfile.mkdtemp())
    LLMWiki(m, config=_wcfg(tmp)).ingest("Content", "c")
    assert (tmp/"wiki"/"overview.md").exists()

# E2E
def t_e2e(m):
    from agents.bmad import BMADAgent
    from agents.miras import MirasOrchestrator
    from agents.karpathy import KarpathyEngine
    from agents.council import LLMCouncil
    from agents.wiki import LLMWiki
    tmp = Path(tempfile.mkdtemp())
    goal = "Build a Python REST API with JWT auth"
    bp = BMADAgent(m).plan(goal);             assert bp.stories
    br = LLMCouncil(m).brainstorm(goal);      assert br.recommended_plan
    st = MirasOrchestrator(m).run(bp);        assert st.outputs
    rf = KarpathyEngine(m).run(f"Synthesise:\n{st.final_output()[:800]}", refine=True)
    assert rf.answer
    v  = LLMCouncil(m).review(goal, rf.answer); assert v.consensus_score > 0
    pg = LLMWiki(m, config=_wcfg(tmp)).ingest(v.approved_output, goal)
    assert pg.filename


# ══════════════════════════════════════════════════════════════════════════════
# Runner
# ══════════════════════════════════════════════════════════════════════════════
ALL: dict[str, list[tuple]] = {
    "config":  [("Config keys",            lambda m: t_config_keys()),
                ("purpose.md",             lambda m: t_purpose_file()),
                ("CLAUDE.md",              lambda m: t_claude_md()),
                ("All imports",            lambda m: t_imports()),
                ("pyproject.toml",         lambda m: t_pyproject())],
    "bmad":    [("Plan generation",        t_bmad_plan),
                ("Role assignment",        t_bmad_roles),
                ("Blueprint validation",   t_bmad_validate),
                ("Dependency ordering",    t_bmad_dep_order),
                ("subtasks alias",         t_bmad_subtasks_alias)],
    "miras":   [("Full run",               t_miras_run),
                ("State handoff",          t_miras_state),
                ("Callbacks",              t_miras_callbacks),
                ("route_single",           t_miras_route_single)],
    "karpathy":[("Thought extraction",     t_karpathy_thought),
                ("Batch processing",       t_karpathy_batch),
                ("Refine pass",            t_karpathy_refine),
                ("Few-shot builder",       t_karpathy_few_shot),
                ("__str__ == answer",      t_karpathy_str)],
    "council": [("Brainstorm",             t_council_brainstorm),
                ("Perspectives count",     t_council_perspectives),
                ("Review verdict",         t_council_review),
                ("Pass threshold",         t_council_pass_threshold),
                ("Report format",          t_council_report),
                ("quick_check",            t_council_quick_check)],
    "wiki":    [("Directory structure",    t_wiki_dirs),
                ("Two-step ingest",        t_wiki_ingest),
                ("Log append",             t_wiki_log),
                ("Index updated",          t_wiki_index),
                ("Search",                 t_wiki_search),
                ("Query",                  t_wiki_query),
                ("Lint report",            t_wiki_lint),
                ("Overview generated",     t_wiki_overview)],
    "e2e":     [("Full pipeline",          t_e2e)],
}

def run_all(pillar: Optional[str] = None) -> bool:
    m = MockLLMClient()
    suite = Suite()
    print(f"\n{'═'*65}")
    print("  m1frame — QA Validation Suite  (offline mock)")
    print(f"{'═'*65}\n")
    groups = {pillar: ALL[pillar]} if pillar else ALL
    for grp, tests in groups.items():
        print(f"[{grp.upper()}]")
        for name, fn in tests:
            suite.run(name, lambda fn=fn: fn(m))
        print()
    return suite.summary()

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--pillar", choices=list(ALL.keys()))
    p.add_argument("--live", action="store_true")
    args = p.parse_args()
    sys.exit(0 if run_all(pillar=args.pillar) else 1)

if __name__ == "__main__":
    main()
