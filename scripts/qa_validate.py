#!/usr/bin/env python3
"""
m1frame — QA Validation Suite  (38 tests, zero API key required)
Usage:
  python scripts/qa_validate.py
  python scripts/qa_validate.py --pillar openplanter
  python scripts/qa_validate.py --pillar e2e
"""
from __future__ import annotations
import sys, json, time, argparse, traceback, tempfile
from pathlib import Path
from dataclasses import dataclass, field
from typing import Callable, Optional

sys.path.insert(0, str(Path(__file__).parent.parent))


# ══ Mock LLM — routes on system prompt only ════════════════════════════════════
class MockLLMClient:
    backend = "mock"
    def chat(self, prompt: str = "", system: str = "", **kw) -> str:
        s = system.lower()

        # BMAD
        if any(k in s for k in ["scrum master","story backlog","execution_order","project_name","bmad"]):
            return json.dumps({
                "project_name":"Mock","goal_summary":"Build mock","domain":"testing",
                "mvp_scope":"Core","constraints":["offline"],"architecture_notes":"Layered.",
                "stories":[
                    {"id":1,"title":"Requirements","role":"analyst","type":"research",
                     "complexity":"low","depends_on":[],"acceptance_criteria":["documented"],
                     "description":"Gather requirements."},
                    {"id":2,"title":"Implementation","role":"dev","type":"code",
                     "complexity":"medium","depends_on":[1],"acceptance_criteria":["tests pass"],
                     "description":"Write code."},
                    {"id":3,"title":"Validation","role":"qa","type":"test",
                     "complexity":"low","depends_on":[2],"acceptance_criteria":["green"],
                     "description":"Validate."},
                ],
                "execution_order":[1,2,3],
            })

        # Council brainstorm synthesis
        if "recommended_plan" in s or "consensus_points" in s or ("synthesiser" in s and "brainstorm" in s):
            return json.dumps({
                "consensus_points":["Test early"],"key_disagreements":[],
                "recommended_plan":"Incremental delivery","implementation_steps":["Write","Implement","Review"],
                "risks_to_mitigate":["Scope creep"],"confidence":"high",
            })

        # Council brainstorm persona
        if "recommended_direction" in s or ("brainstorm" in s and "council member" in s):
            return json.dumps({
                "persona":"Mock Critic","approach":"Systematic validation",
                "key_considerations":["coverage"],"risks":["scope creep"],
                "opportunities":["early detection"],"recommended_direction":"Test alongside implementation",
            })

        # Council review synthesis
        if "consensus_score" in s or "approved_output" in s or ("synthesiser" in s and "review mode" in s):
            return json.dumps({
                "consensus_score":8.5,"verdict":"pass",
                "summary":"Output meets quality criteria.","required_fixes":[],
                "approved_output":"Mock approved output — task completed successfully.",
            })

        # Council review persona
        if "council reviewer" in s or ("verdict" in s and "key_points" in s and "score" in s):
            return json.dumps({
                "persona":"Mock Critic","verdict":"pass","score":8,
                "key_points":["Logical","Structured"],"recommendation":"No changes.",
            })

        # OpenPlanter entity resolution
        if "entity resolution" in s or "canonical_name" in s or "aliases" in s:
            return json.dumps({
                "entities":[{"canonical_name":"AcmeCorp","aliases":["Acme","ACME Inc"],
                              "entity_type":"org","confidence":"high","sources":["dataset_a"]}],
                "unresolved":[],"conflicts":[],
            })

        # OpenPlanter cross-reference
        if "cross-reference" in s or "direct_matches" in s or "indirect_connections" in s:
            return json.dumps({
                "direct_matches":[{"entity":"AcmeCorp","datasets":["a","b"],"significance":"high"}],
                "indirect_connections":[{"path":["AcmeCorp","via","LobbyFirm"],"significance":"lobbying link"}],
                "flags":[{"type":"pattern","description":"Same director across both datasets","severity":"high"}],
                "summary":"Overlap detected between vendor payments and lobbying.",
            })

        # OpenPlanter investigation
        if "openplanter" in s or "investigation agent" in s or "entity map" in s or "evidence chain" in s:
            return ("<thought>\nIdentify datasets. Resolve entities. Cross-reference.\n</thought>\n\n"
                    "## Investigation Summary\nMock investigation complete.\n\n"
                    "## Entity Map\n- AcmeCorp [org]\n\n"
                    "## Key Connections\n- AcmeCorp ↔ LobbyFirm\n\n"
                    "## Evidence Chain\nVendor payment records matched lobbying disclosures.\n\n"
                    "## Recommended Follow-up\nRequest financial records.")

        # Wiki lint
        if "lint" in s or "health_score" in s or "orphan" in s:
            return json.dumps({
                "contradictions":[],"orphan_pages":[],"missing_pages":["Getting Started"],
                "knowledge_gaps":["deployment"],"health_score":8,"recommendations":["Add Getting Started"],
            })

        # Wiki overview
        if "overview" in s or "global summary" in s or "auto_generated" in s:
            return ("---\ntitle: Overview\nauto_generated: true\nupdated: 2026-05-06\n---\n\n"
                    "## Current State\nWiki healthy.\n\n## Key Themes\n- Testing")

        # Wiki analysis step 1
        if "analysis agent" in s or "key_entities" in s or "suggested_page_types" in s:
            return json.dumps({
                "key_entities":["MockSystem"],"key_concepts":["testing"],
                "main_arguments":["Mock enables offline testing"],"connections_to_existing":[],
                "contradictions_with_existing":[],"suggested_page_types":["concept"],
                "recommended_wiki_structure":"Single concept page","confidence":"high",
            })

        # Wiki generation
        if "generation agent" in s or "wiki page" in s or "frontmatter" in s or "page_type" in s:
            return ("---\ntitle: Mock Wiki Page\ntags: [test,mock]\nrelated: []\n"
                    "created: 2026-05-06\nsources: []\npage_type: concept\nconfidence: high\n---\n\n"
                    "## Summary\nMock QA page.\n\n## Key Concepts\n- Testing\n\n"
                    "## Details\nSynthetic content.\n\n## Open Questions\nNone.")

        # Karpathy
        if "reasoning engine" in s or "chain-of-thought" in s or "thought block" in s:
            return ("<thought>\nStep 1: Understand.\nStep 2: Plan.\nStep 3: Execute.\n</thought>\n\n"
                    "Mock answer: Task completed with chain-of-thought reasoning.")

        # Wiki query
        if "wiki query" in s or "answer the question using" in s:
            return "Based on wiki pages: mock result."

        # Miras / fallback
        return ("<thought>\nProcessing story as Miras sub-agent.\n</thought>\n\n"
                "Mock sub-agent result: story completed successfully.")


# ══ Runner ════════════════════════════════════════════════════════════════════
@dataclass
class R:
    name: str; passed: bool; msg: str=""; ms: float=0.; tb: str=""

@dataclass
class Suite:
    results: list[R] = field(default_factory=list)
    def run(self, name: str, fn: Callable) -> R:
        t0 = time.perf_counter()
        try:
            fn(); r = R(name=name,passed=True,msg="OK",ms=(time.perf_counter()-t0)*1000)
        except AssertionError as e:
            r = R(name=name,passed=False,msg=str(e),ms=(time.perf_counter()-t0)*1000)
        except Exception as e:
            r = R(name=name,passed=False,msg=str(e),ms=(time.perf_counter()-t0)*1000,
                  tb=traceback.format_exc()[-800:])
        self.results.append(r)
        print(f"  {'✓' if r.passed else '✗'} {'PASS' if r.passed else 'FAIL'}  {name:<52} ({r.ms:.0f}ms)")
        if not r.passed:
            print(f"       → {r.msg}")
            if r.tb: print(r.tb)
        return r
    def summary(self) -> bool:
        ok=sum(1 for r in self.results if r.passed); n=len(self.results)
        print(f"\n{'═'*65}\n  m1frame QA: {ok}/{n} passed")
        if ok==n: print("  🟢  ALL TESTS PASSED — release ready")
        else:
            print(f"  🔴  {n-ok} FAILED:")
            [print(f"     • {r.name}: {r.msg}") for r in self.results if not r.passed]
        print(f"{'═'*65}\n")
        return ok==n


# ══ Tests — CONFIG ════════════════════════════════════════════════════════════
def t_config(m):
    from llm_client import load_config
    cfg = load_config()
    for k in ["backend","claude","ollama","bmad","miras","karpathy","council","wiki","openplanter"]:
        assert k in cfg, f"missing: {k}"

def t_purpose(m):
    p=Path("purpose.md"); assert p.exists() and len(p.read_text())>50

def t_claude_md(m):
    p=Path("CLAUDE.md"); assert p.exists()
    c=p.read_text(); assert "Page Types" in c and "WikiLink" in c

def t_imports(m):
    from agents import (BMADAgent,Blueprint,Story,BMAD_ROLES,
                        MirasOrchestrator,AgentState,KarpathyEngine,KarpathyResult,
                        LLMCouncil,CouncilVerdict,BrainstormResult,
                        LLMWiki,WikiPage,LintReport,
                        OpenPlanterAgent,InvestigationResult)

def t_pyproject(m): assert Path("pyproject.toml").exists()
def t_license(m):   assert Path("LICENSE").exists()
def t_contrib(m):   assert Path("CONTRIBUTING.md").exists()
def t_security(m):  assert Path("SECURITY.md").exists()
def t_makefile(m):  assert Path("Makefile").exists()
def t_ci(m):        assert Path(".github/workflows/ci.yml").exists()
def t_issue_tpl(m): assert Path(".github/ISSUE_TEMPLATE/bug_report.md").exists()
def t_pr_tpl(m):    assert Path(".github/pull_request_template.md").exists()


# ══ Tests — BMAD ═════════════════════════════════════════════════════════════
def t_bmad_plan(m):
    from agents.bmad import BMADAgent
    bp=BMADAgent(m).plan("Build REST API")
    assert bp.project_name and bp.goal_summary and bp.stories and bp.execution_order

def t_bmad_roles(m):
    from agents.bmad import BMADAgent, BMAD_ROLES
    assert "investigator" in BMAD_ROLES
    bp=BMADAgent(m).plan("x")
    for s in bp.stories: assert s.role in BMAD_ROLES

def t_bmad_validate(m):
    from agents.bmad import BMADAgent
    assert not BMADAgent(m).validate(BMADAgent(m).plan("x"))

def t_bmad_deps(m):
    from agents.bmad import BMADAgent
    bp=BMADAgent(m).plan("x")
    for s in bp.stories:
        for d in s.depends_on: assert bp.execution_order.index(d)<bp.execution_order.index(s.id)

def t_bmad_alias(m):
    from agents.bmad import BMADAgent
    bp=BMADAgent(m).plan("x"); assert bp.subtasks is bp.stories


# ══ Tests — MIRAS ════════════════════════════════════════════════════════════
def t_miras_run(m):
    from agents.bmad import BMADAgent; from agents.miras import MirasOrchestrator
    bp=BMADAgent(m).plan("x"); st=MirasOrchestrator(m).run(bp)
    assert st.outputs
    for sid in bp.execution_order: assert sid in st.outputs

def t_miras_state(m):
    from agents.miras import AgentState
    st=AgentState(goal="t",blueprint_summary="b")
    st.add_result(1,"first"); st.add_result(2,"second")
    assert "Story 1" in st.final_output() and "Story 2" in st.final_output()

def t_miras_callbacks(m):
    from agents.bmad import BMADAgent; from agents.miras import MirasOrchestrator
    s,d=[],[]
    MirasOrchestrator(m,on_subtask_start=lambda x:s.append(x.id),
                      on_subtask_done=lambda x,r:d.append(x.id)).run(BMADAgent(m).plan("x"))
    assert len(s)==len(d)

def t_miras_investigator_role(m):
    from agents.miras import ROLE_MAP
    assert "investigator" in ROLE_MAP


# ══ Tests — KARPATHY ═════════════════════════════════════════════════════════
def t_karpathy_thought(m):
    from agents.karpathy import KarpathyEngine
    r=KarpathyEngine(m).run("2+2?"); assert r.had_thought_tag and r.thought and r.answer

def t_karpathy_batch(m):
    from agents.karpathy import KarpathyEngine
    rs=KarpathyEngine(m).batch(["Q1","Q2"]); assert len(rs)==2

def t_karpathy_str(m):
    from agents.karpathy import KarpathyEngine
    r=KarpathyEngine(m).run("x"); assert str(r)==r.answer


# ══ Tests — COUNCIL ══════════════════════════════════════════════════════════
def t_council_brainstorm(m):
    from agents.council import LLMCouncil
    br=LLMCouncil(m).brainstorm("Build API")
    assert br.recommended_plan and isinstance(br.implementation_steps,list)

def t_council_perspectives(m):
    from agents.council import LLMCouncil
    c=LLMCouncil(m); br=c.brainstorm("x")
    assert len(br.perspectives)==len(c.personas)

def t_council_review(m):
    from agents.council import LLMCouncil
    v=LLMCouncil(m).review("Sort","def s(a):return sorted(a)")
    assert v.consensus_score>0 and v.verdict in ("pass","fail","conditional") and v.approved_output

def t_council_pass(m):
    from agents.council import LLMCouncil
    v=LLMCouncil(m,config={"consensus_threshold":7,"personas":[{"name":"C","role":"Find flaws."}]}).review("t","o")
    assert v.passed

def t_council_report(m):
    from agents.council import LLMCouncil
    r=LLMCouncil(m).review("t","o").report(); assert "Verdict" in r and "/10" in r


# ══ Tests — WIKI ══════════════════════════════════════════════════════════════
def _wc(tmp): return {"directory":str(tmp/"wiki"),"index_file":str(tmp/"wiki"/"index.md"),"purpose_file":str(tmp/"purpose.md")}

def t_wiki_dirs(m):
    from agents.wiki import LLMWiki
    tmp=Path(tempfile.mkdtemp()); LLMWiki(m,config=_wc(tmp))
    for d in ["raw/sources","entities","concepts","sources","synthesis"]:
        assert (tmp/"wiki"/d).exists()
    assert (tmp/"wiki"/"log.md").exists()

def t_wiki_ingest(m):
    from agents.wiki import LLMWiki
    tmp=Path(tempfile.mkdtemp())
    pg=LLMWiki(m,config=_wc(tmp)).ingest("Python is a language.","python")
    assert pg.title and pg.filename
    pages=[f for f in (tmp/"wiki").rglob("*.md") if f.name not in ("index.md","log.md","overview.md")]
    assert len(pages)>=1

def t_wiki_log(m):
    from agents.wiki import LLMWiki
    tmp=Path(tempfile.mkdtemp()); LLMWiki(m,config=_wc(tmp)).ingest("Test","t")
    assert "ingest" in (tmp/"wiki"/"log.md").read_text().lower()

def t_wiki_index(m):
    from agents.wiki import LLMWiki
    tmp=Path(tempfile.mkdtemp()); LLMWiki(m,config=_wc(tmp)).ingest("Quantum","q")
    assert "[[" in (tmp/"wiki"/"index.md").read_text()

def t_wiki_search(m):
    from agents.wiki import LLMWiki
    tmp=Path(tempfile.mkdtemp()); w=LLMWiki(m,config=_wc(tmp))
    w.ingest("ML basics","ml"); assert len(w.search("mock"))>=1

def t_wiki_lint(m):
    from agents.wiki import LLMWiki
    tmp=Path(tempfile.mkdtemp()); w=LLMWiki(m,config=_wc(tmp))
    w.ingest("DL","dl"); rpt=w.lint()
    assert 1<=rpt.health_score<=10 and "Health Score" in rpt.summary()

def t_wiki_overview(m):
    from agents.wiki import LLMWiki
    tmp=Path(tempfile.mkdtemp()); LLMWiki(m,config=_wc(tmp)).ingest("Content","c")
    assert (tmp/"wiki"/"overview.md").exists()


# ══ Tests — OPENPLANTER ═══════════════════════════════════════════════════════
def t_op_investigate(m):
    from agents.openplanter import OpenPlanterAgent
    tmp=Path(tempfile.mkdtemp())
    op=OpenPlanterAgent(m,workspace=str(tmp))
    r=op.investigate("Cross-reference vendor payments vs lobbying")
    assert r.task and r.summary and r.raw_analysis

def t_op_workspace_file(m):
    from agents.openplanter import OpenPlanterAgent
    tmp=Path(tempfile.mkdtemp())
    r=OpenPlanterAgent(m,workspace=str(tmp)).investigate("Find connections in dataset")
    assert len(r.workspace_files)>=1
    assert Path(r.workspace_files[0]).exists()

def t_op_entity_resolution(m):
    from agents.openplanter import OpenPlanterAgent
    tmp=Path(tempfile.mkdtemp())
    entities=OpenPlanterAgent(m,workspace=str(tmp)).resolve_entities("Acme Corp paid ACME Inc $500k")
    assert len(entities)>=1
    assert entities[0].canonical_name

def t_op_cross_reference(m):
    from agents.openplanter import OpenPlanterAgent
    tmp=Path(tempfile.mkdtemp())
    r=OpenPlanterAgent(m,workspace=str(tmp)).cross_reference(
        "Vendor: AcmeCorp $1M contract","Lobbyist: AcmeCorp filed 2025-Q1"
    )
    assert r.summary

def t_op_miras_handler(m):
    from agents.openplanter import OpenPlanterAgent
    tmp=Path(tempfile.mkdtemp())
    result=OpenPlanterAgent(m,workspace=str(tmp)).miras_handler("Investigate dataset overlaps")
    assert result and isinstance(result,str)

def t_op_mode(m):
    from agents.openplanter import OpenPlanterAgent
    tmp=Path(tempfile.mkdtemp())
    op=OpenPlanterAgent(m,workspace=str(tmp))
    assert op.mode in ("full","llm-only")


# ══ E2E ═══════════════════════════════════════════════════════════════════════
def t_e2e(m):
    from agents.bmad import BMADAgent; from agents.miras import MirasOrchestrator
    from agents.karpathy import KarpathyEngine; from agents.council import LLMCouncil
    from agents.wiki import LLMWiki; from agents.openplanter import OpenPlanterAgent
    tmp=Path(tempfile.mkdtemp()); goal="Build a Python REST API with JWT auth"
    bp=BMADAgent(m).plan(goal);               assert bp.stories
    br=LLMCouncil(m).brainstorm(goal);        assert br.recommended_plan
    st=MirasOrchestrator(m).run(bp);          assert st.outputs
    rf=KarpathyEngine(m).run(f"Synthesise:\n{st.final_output()[:600]}",refine=True)
    assert rf.answer
    v=LLMCouncil(m).review(goal,rf.answer);   assert v.consensus_score>0
    pg=LLMWiki(m,config=_wc(tmp)).ingest(v.approved_output,goal); assert pg.filename
    inv=OpenPlanterAgent(m,workspace=str(tmp)).investigate("Validate data sources for: "+goal)
    assert inv.summary


# ══ Registry ══════════════════════════════════════════════════════════════════
ALL: dict[str,list] = {
    "config":   [("Config keys",              t_config),
                 ("purpose.md",               t_purpose),
                 ("CLAUDE.md schema",         t_claude_md),
                 ("All imports",              t_imports),
                 ("pyproject.toml",           t_pyproject),
                 ("LICENSE",                  t_license),
                 ("CONTRIBUTING.md",          t_contrib),
                 ("SECURITY.md",              t_security),
                 ("Makefile",                 t_makefile),
                 ("CI workflow",              t_ci),
                 ("Issue templates",          t_issue_tpl),
                 ("PR template",              t_pr_tpl)],
    "bmad":     [("Plan generation",          t_bmad_plan),
                 ("Roles incl investigator",  t_bmad_roles),
                 ("Blueprint validation",     t_bmad_validate),
                 ("Dependency order",         t_bmad_deps),
                 ("subtasks alias",           t_bmad_alias)],
    "miras":    [("Full run",                 t_miras_run),
                 ("State handoff",            t_miras_state),
                 ("Callbacks",                t_miras_callbacks),
                 ("Investigator in ROLE_MAP", t_miras_investigator_role)],
    "karpathy": [("Thought extraction",       t_karpathy_thought),
                 ("Batch",                    t_karpathy_batch),
                 ("__str__ == answer",        t_karpathy_str)],
    "council":  [("Brainstorm",               t_council_brainstorm),
                 ("Perspectives count",       t_council_perspectives),
                 ("Review verdict",           t_council_review),
                 ("Pass threshold",           t_council_pass),
                 ("Report format",            t_council_report)],
    "wiki":     [("Directory structure",      t_wiki_dirs),
                 ("Two-step ingest",          t_wiki_ingest),
                 ("Log append",               t_wiki_log),
                 ("Index updated",            t_wiki_index),
                 ("Search",                   t_wiki_search),
                 ("Lint report",              t_wiki_lint),
                 ("Overview generated",       t_wiki_overview)],
    "openplanter":[("investigate()",          t_op_investigate),
                   ("Workspace file saved",   t_op_workspace_file),
                   ("Entity resolution",      t_op_entity_resolution),
                   ("Cross-reference",        t_op_cross_reference),
                   ("miras_handler()",        t_op_miras_handler),
                   ("Mode detection",         t_op_mode)],
    "e2e":      [("Full 7-pillar pipeline",   t_e2e)],
}

def run_all(pillar: Optional[str]=None) -> bool:
    m=MockLLMClient(); suite=Suite()
    print(f"\n{'═'*65}\n  m1frame — QA Validation Suite  (offline mock)\n{'═'*65}\n")
    groups={pillar:ALL[pillar]} if pillar else ALL
    for grp,tests in groups.items():
        print(f"[{grp.upper()}]")
        for name,fn in tests: suite.run(name, lambda fn=fn: fn(m))
        print()
    return suite.summary()

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--pillar",choices=list(ALL.keys()))
    args=p.parse_args()
    sys.exit(0 if run_all(pillar=args.pillar) else 1)

if __name__=="__main__": main()
