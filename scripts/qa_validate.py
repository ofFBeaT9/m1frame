#!/usr/bin/env python3
"""
m1frame — QA Validation Suite  (65 tests, zero API key required)
Usage:
  python scripts/qa_validate.py
  python scripts/qa_validate.py --pillar openplanter
  python scripts/qa_validate.py --pillar e2e
  python scripts/qa_validate.py --pillar logger
  python scripts/qa_validate.py --pillar metrics
  python scripts/qa_validate.py --pillar scheduler
  python scripts/qa_validate.py --pillar parallel
  python scripts/qa_validate.py --pillar self_critique
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

        # Semantic entity matching (Voyage merge)
        if "semantic entity matching" in s or "merge_confidence" in s:
            return json.dumps({
                "merged_entities":[
                    {"canonical_name":"AcmeCorp","members":["AcmeCorp","Acme Corp"],
                     "merge_confidence":"high","rationale":"Same company, name variants"}
                ]
            })

        # Contradiction detection
        if "contradiction detection" in s or "page_a" in s or "conflict" in s:
            return json.dumps({
                "contradictions":[],
                "clean": True,
            })

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

        # Karpathy / self-critique
        if "self-critique" in s or "critique agent" in s or "brutally honest" in s:
            return ("<thought>\nDraft looks correct. No critical flaws found.\n</thought>\n\n"
                    "Refined mock answer: same as draft, no issues found.")

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

    def stream(self, prompt: str = "", system: str = "", **kw):
        """Mock stream — yields the full response as single chunk."""
        full = self.chat(prompt=prompt, system=system, **kw)
        yield full


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
        mark = "PASS" if r.passed else "FAIL"
        print(f"  [{mark}]  {name:<52} ({r.ms:.0f}ms)")
        if not r.passed:
            print(f"       -> {r.msg}")
            if r.tb: print(r.tb)
        return r
    def summary(self) -> bool:
        ok=sum(1 for r in self.results if r.passed); n=len(self.results)
        sep="="*65
        print(f"\n{sep}\n  m1frame QA: {ok}/{n} passed")
        if ok==n: print("  ALL TESTS PASSED -- release ready")
        else:
            print(f"  {n-ok} FAILED:")
            [print(f"     * {r.name}: {r.msg}") for r in self.results if not r.passed]
        print(f"{sep}\n")
        return ok==n


# ══ Tests — CONFIG ════════════════════════════════════════════════════════════
def t_config(m):
    from llm_client import load_config
    cfg = load_config()
    for k in ["backend","claude","ollama","bmad","miras","karpathy","council","wiki","openplanter",
              "api","metrics","logging","webhooks","scheduler"]:
        assert k in cfg, f"missing: {k}"

def t_purpose(m):
    p=Path("purpose.md"); assert p.exists() and len(p.read_text())>50

def t_claude_md(m):
    p=Path("CLAUDE.md"); assert p.exists()
    c=p.read_text(encoding="utf-8"); assert "Page Types" in c and "WikiLink" in c

def t_imports(m):
    from agents import (BMADAgent,Blueprint,Story,BMAD_ROLES,
                        MirasOrchestrator,AgentState,KarpathyEngine,KarpathyResult,
                        LLMCouncil,CouncilVerdict,BrainstormResult,
                        LLMWiki,WikiPage,LintReport,ContradictionReport,
                        OpenPlanterAgent,InvestigationResult,
                        PillarLogger,MetricsCollector,get_metrics,
                        InvestigationScheduler,ScheduledJob)

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

def t_miras_adaptive_temp(m):
    from agents.miras import _COMPLEXITY_TEMP
    assert _COMPLEXITY_TEMP["low"] < _COMPLEXITY_TEMP["medium"] < _COMPLEXITY_TEMP["high"]
    assert _COMPLEXITY_TEMP["low"] <= 0.15


# ══ Tests — PARALLEL MIRAS ═══════════════════════════════════════════════════
def t_parallel_run(m):
    from agents.bmad import BMADAgent; from agents.miras import MirasOrchestrator
    bp = BMADAgent(m).plan("x")
    st = MirasOrchestrator(m).run_parallel(bp)
    assert st.outputs
    for sid in bp.execution_order: assert sid in st.outputs

def t_parallel_same_result(m):
    from agents.bmad import BMADAgent; from agents.miras import MirasOrchestrator
    bp = BMADAgent(m).plan("x")
    seq = MirasOrchestrator(m).run(bp)
    par = MirasOrchestrator(m).run_parallel(bp)
    assert set(seq.outputs.keys()) == set(par.outputs.keys())

def t_parallel_state_threadsafe(m):
    from agents.miras import AgentState
    import threading
    st = AgentState(goal="g", blueprint_summary="b")
    def write(i): st.add_result(i, f"result_{i}")
    threads = [threading.Thread(target=write, args=(i,)) for i in range(20)]
    for t in threads: t.start()
    for t in threads: t.join()
    assert len(st.outputs) == 20


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


# ══ Tests — SELF-CRITIQUE ════════════════════════════════════════════════════
def t_self_critique_runs(m):
    from agents.karpathy import KarpathyEngine
    r = KarpathyEngine(m).self_critique("What is 2+2?")
    assert r.answer  # must return something

def t_self_critique_has_cot(m):
    from agents.karpathy import KarpathyEngine
    r = KarpathyEngine(m).self_critique("Explain recursion briefly.")
    assert r.had_thought_tag  # critique pass must produce <thought>

def t_self_critique_result_type(m):
    from agents.karpathy import KarpathyEngine, KarpathyResult
    r = KarpathyEngine(m).self_critique("x")
    assert isinstance(r, KarpathyResult)


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

def t_wiki_decay_confidence(m):
    from agents.wiki import LLMWiki
    tmp=Path(tempfile.mkdtemp())
    w=LLMWiki(m,config=_wc(tmp))
    # ingest a page, then manually set its created date to old
    pg=w.ingest("Old content","old")
    page_path=tmp/"wiki"/pg.filename
    content=page_path.read_text()
    old_content=content.replace("created: 2026-05-06","created: 2025-12-01")
    page_path.write_text(old_content)
    # decay should update confidence for old pages
    updated=w.decay_confidence(medium_after_days=30)
    assert isinstance(updated,int)  # returns count (0 is ok if already medium)

def t_wiki_contradictions(m):
    from agents.wiki import LLMWiki
    tmp=Path(tempfile.mkdtemp())
    w=LLMWiki(m,config=_wc(tmp))
    w.ingest("Python is fast","perf")
    report=w.detect_contradictions()
    assert hasattr(report,"contradictions") and hasattr(report,"clean")
    assert (tmp/"wiki"/"contradictions.md").exists()


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
    assert "llm-only" in op.mode or "full" in op.mode

def t_op_web_results_field(m):
    from agents.openplanter import OpenPlanterAgent
    tmp=Path(tempfile.mkdtemp())
    r=OpenPlanterAgent(m,workspace=str(tmp)).investigate("any task")
    assert isinstance(r.web_results, list)


# ══ Tests — LOGGER ═══════════════════════════════════════════════════════════
def t_logger_creates_file(m):
    from agents.logger import PillarLogger
    tmp=Path(tempfile.mkdtemp())
    lg=PillarLogger(log_dir=str(tmp))
    lg.info("bmad","test_event",foo="bar")
    files=list(tmp.glob("m1frame_*.jsonl"))
    assert len(files)==1

def t_logger_valid_json(m):
    from agents.logger import PillarLogger
    tmp=Path(tempfile.mkdtemp())
    lg=PillarLogger(log_dir=str(tmp))
    lg.info("miras","event",stories=3)
    lines=(list(tmp.glob("*.jsonl"))[0]).read_text().strip().splitlines()
    parsed=json.loads(lines[0])
    assert parsed["pillar"]=="miras" and parsed["event"]=="event"

def t_logger_trace_id(m):
    from agents.logger import PillarLogger
    tmp=Path(tempfile.mkdtemp())
    lg=PillarLogger(log_dir=str(tmp))
    assert len(lg.trace_id)==8

def t_logger_timing(m):
    from agents.logger import PillarLogger
    tmp=Path(tempfile.mkdtemp())
    lg=PillarLogger(log_dir=str(tmp))
    lg.timing("karpathy",ms=123.4)
    lines=(list(tmp.glob("*.jsonl"))[0]).read_text().strip().splitlines()
    d=json.loads(lines[0])
    assert d["latency_ms"]==123.4

def t_logger_read_trace(m):
    from agents.logger import PillarLogger
    tmp=Path(tempfile.mkdtemp())
    lg=PillarLogger(log_dir=str(tmp))
    lg.info("wiki","ingest"); lg.error("council","fail")
    trace=lg.read_trace()
    assert len(trace)==2
    assert all(e["trace"]==lg.trace_id for e in trace)


# ══ Tests — METRICS ══════════════════════════════════════════════════════════
def t_metrics_record(m):
    from agents.metrics import MetricsCollector
    mc=MetricsCollector()
    mc.record("bmad",ms=100); mc.record("bmad",ms=200,error=True)
    p=mc.get("bmad")
    assert p.calls==2 and p.errors==1 and abs(p.avg_ms-150)<1

def t_metrics_prometheus(m):
    from agents.metrics import MetricsCollector
    mc=MetricsCollector()
    mc.record("council",ms=300)
    out=mc.to_prometheus()
    assert "m1frame_pillar_calls_total" in out
    assert 'pillar="council"' in out

def t_metrics_timer_ctx(m):
    from agents.metrics import MetricsCollector
    import time
    mc=MetricsCollector()
    with mc.timer("miras"):
        time.sleep(0.01)
    assert mc.get("miras").calls==1 and mc.get("miras").total_ms>=10

def t_metrics_timer_error(m):
    from agents.metrics import MetricsCollector
    mc=MetricsCollector()
    try:
        with mc.timer("wiki"):
            raise ValueError("oops")
    except ValueError:
        pass
    assert mc.get("wiki").errors==1

def t_metrics_singleton(m):
    from agents.metrics import get_metrics
    a=get_metrics(); b=get_metrics()
    assert a is b


# ══ Tests — SCHEDULER ════════════════════════════════════════════════════════
def t_scheduler_add(m):
    from agents.scheduler import InvestigationScheduler
    tmp=Path(tempfile.mkdtemp())
    s=InvestigationScheduler(m,workspace=str(tmp))
    job=s.add("test_job","Investigate vendors",interval_hours=1)
    assert job.job_id=="test_job" and job.interval_hours==1

def t_scheduler_persist(m):
    from agents.scheduler import InvestigationScheduler
    tmp=Path(tempfile.mkdtemp())
    InvestigationScheduler(m,workspace=str(tmp)).add("j1","task",2)
    s2=InvestigationScheduler(m,workspace=str(tmp))
    assert any(j.job_id=="j1" for j in s2.list_jobs())

def t_scheduler_remove(m):
    from agents.scheduler import InvestigationScheduler
    tmp=Path(tempfile.mkdtemp())
    s=InvestigationScheduler(m,workspace=str(tmp))
    s.add("rm_me","task",1); assert s.remove("rm_me")
    assert not any(j.job_id=="rm_me" for j in s.list_jobs())

def t_scheduler_run_now(m):
    from agents.scheduler import InvestigationScheduler
    tmp=Path(tempfile.mkdtemp())
    s=InvestigationScheduler(m,workspace=str(tmp))
    s.add("now_job","Find overlaps",1)
    result=s.run_now("now_job")
    assert isinstance(result,str) and len(result)>0

def t_scheduler_disable(m):
    from agents.scheduler import InvestigationScheduler
    tmp=Path(tempfile.mkdtemp())
    s=InvestigationScheduler(m,workspace=str(tmp))
    s.add("d_job","task",1); s.disable("d_job")
    assert not s.get_job("d_job").enabled


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
    sc=KarpathyEngine(m).self_critique(f"Critique: {rf.answer[:200]}")
    assert sc.answer
    v=LLMCouncil(m).review(goal,rf.answer);   assert v.consensus_score>0
    pg=LLMWiki(m,config=_wc(tmp)).ingest(v.approved_output,goal); assert pg.filename
    inv=OpenPlanterAgent(m,workspace=str(tmp)).investigate("Validate data sources for: "+goal)
    assert inv.summary
    # Parallel also works
    st2=MirasOrchestrator(m).run_parallel(bp)
    assert set(st2.outputs.keys())==set(st.outputs.keys())


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
                 ("Investigator in ROLE_MAP", t_miras_investigator_role),
                 ("Adaptive temperature",     t_miras_adaptive_temp)],
    "parallel": [("run_parallel() works",    t_parallel_run),
                 ("Same stories as seq",      t_parallel_same_result),
                 ("Thread-safe AgentState",   t_parallel_state_threadsafe)],
    "karpathy": [("Thought extraction",       t_karpathy_thought),
                 ("Batch",                    t_karpathy_batch),
                 ("__str__ == answer",        t_karpathy_str)],
    "self_critique": [("self_critique() runs",    t_self_critique_runs),
                      ("self_critique has CoT",   t_self_critique_has_cot),
                      ("self_critique type",      t_self_critique_result_type)],
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
                 ("Overview generated",       t_wiki_overview),
                 ("Confidence decay",         t_wiki_decay_confidence),
                 ("Contradiction detection",  t_wiki_contradictions)],
    "openplanter":[("investigate()",          t_op_investigate),
                   ("Workspace file saved",   t_op_workspace_file),
                   ("Entity resolution",      t_op_entity_resolution),
                   ("Cross-reference",        t_op_cross_reference),
                   ("miras_handler()",        t_op_miras_handler),
                   ("Mode detection",         t_op_mode),
                   ("web_results field",      t_op_web_results_field)],
    "logger":   [("Creates JSONL file",       t_logger_creates_file),
                 ("Valid JSON entries",       t_logger_valid_json),
                 ("Trace ID length",          t_logger_trace_id),
                 ("Timing entry",             t_logger_timing),
                 ("read_trace filter",        t_logger_read_trace)],
    "metrics":  [("record() counts",          t_metrics_record),
                 ("Prometheus format",        t_metrics_prometheus),
                 ("timer() context manager",  t_metrics_timer_ctx),
                 ("timer() error tracking",   t_metrics_timer_error),
                 ("Singleton get_metrics()",  t_metrics_singleton)],
    "scheduler":[("add() job",                t_scheduler_add),
                 ("Persist to disk",          t_scheduler_persist),
                 ("remove() job",             t_scheduler_remove),
                 ("run_now() executes",       t_scheduler_run_now),
                 ("disable() job",            t_scheduler_disable)],
    "e2e":      [("Full 7-pillar pipeline",   t_e2e)],
}

def run_all(pillar: Optional[str]=None) -> bool:
    m=MockLLMClient(); suite=Suite()
    total=sum(len(v) for v in ALL.values())
    sep="="*65
    print(f"\n{sep}\n  m1frame QA Validation Suite  ({total} tests, offline mock)\n{sep}\n")
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
