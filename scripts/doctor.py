"""Reproducible module probes. No provider calls unless --live is supplied."""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from llm_client import LLMClient, load_config
from modules.status import module_status


def audit(config: str = "config.yaml", live: bool = False) -> dict:
    cfg = load_config(config)
    root = Path(config).resolve().parent
    cfg.setdefault("scientific", {})
    if not cfg["scientific"].get("path"):
        cfg["scientific"]["path"] = str(root / ".external/scientific-skills")
    results = []

    def probe(name, fn):
        started = time.monotonic()
        try:
            details = fn()
            results.append({"module": name, "status": "verified", "evidence": details,
                            "seconds": round(time.monotonic() - started, 3)})
        except Exception as exc:
            results.append({"module": name, "status": "failed",
                            "evidence": f"{type(exc).__name__}: {str(exc)[:300]}",
                            "seconds": round(time.monotonic() - started, 3)})

    def unavailable(name, why):
        results.append({"module": name, "status": "needs_setup", "evidence": why})

    def headroom():
        from modules.headroom import HeadroomAdapter
        adapter = HeadroomAdapter({**cfg.get("headroom", {}), "enabled": True,
                                   "protect_recent": 1, "min_tokens_to_compress": 20})
        messages = [{"role": "system", "content": "Keep this instruction unchanged."},
                    {"role": "assistant", "content": json.dumps([
                        {"status": "ok", "value": 42} for _ in range(200)])},
                    {"role": "user", "content": "Summarize the status records."}]
        result = adapter.compress_messages(messages, model="gpt-4o")
        if result.error or not result.available or not result.applied:
            raise RuntimeError(result.error or "Compression did not run on the fixture")
        assert result.messages[0] == messages[0] and result.messages[-1] == messages[-1]
        assert result.tokens_after < result.tokens_before
        return result.status()

    def semantic():
        from agents.wiki import LLMWiki, WikiPage
        wiki_cfg = cfg.get("wiki", {})
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)
            (path / "purpose.md").write_text("Isolated semantic retrieval test.", encoding="utf-8")
            wiki = LLMWiki(None, {**wiki_cfg, "directory": folder,
                                  "index_file": str(path / "index.md"),
                                  "purpose_file": str(path / "purpose.md"),
                                  "embed_local_only": True})
            text = ("---\ntitle: Semantic Fixture\npage_type: concept\ntags: [qa]\n"
                    "related: []\ncreated: 2026-10-04\nsources: [fixture]\nconfidence: high\n---\n"
                    "Cars are vehicles used for transportation on roads.")
            (path / "concepts/semantic-fixture.md").write_text(text, encoding="utf-8")
            page = WikiPage.from_markdown(text)
            assert wiki._embed("automobiles") is not None, "Embedding model unavailable locally"
            wiki._lancedb_upsert(page)
            wiki._lancedb_upsert(page)
            import lancedb
            table = lancedb.connect(str(path / ".lancedb")).open_table("pages")
            assert table.count_rows() == 1, "Duplicate index entries"
            # A semantic-only synonym avoids mistaking keyword fallback for success.
            hits = wiki._lancedb_search("automobiles", 1)
            assert hits and hits[0].title == "Semantic Fixture", "Semantic retrieval failed"
            return {"embedding": wiki_cfg.get("embed_model"), "rows_after_two_upserts": 1,
                    "retrieved": hits[0].title}

    def scientific():
        from scientific import ScientificLibrary
        library = ScientificLibrary((cfg.get("scientific") or {}).get("path") or
                                    root / ".external/scientific-skills")
        assert library.skills, "Scientific catalog is not installed"
        assert not library.errors, library.errors
        return {"count": len(library.skills), "catalog_errors": library.errors,
                "scope": "Catalog parse; scientific experiments are not executed"}

    def optimizer():
        from optimizers.tools import skill_optimize
        out = skill_optimize("Check the result.", ["quasar"], rounds=50, seed=7, prefer="skillopt")
        assert out.get("improved"), "Optimizer did not improve the fixture objective"
        return {key: out.get(key) for key in ("tier", "improved", "before_score", "after_score")}

    def sensor():
        from sensors.tools import client
        result = client(timeout=45).scan("agents")
        assert result.available and result.quality_signal is not None, result.error
        return {"quality_signal": result.quality_signal, "scope": "agents directory"}

    inventory = module_status(cfg)
    probe("Headroom compression", headroom)
    probe("Scientific catalog", scientific)
    if inventory["semantic_wiki"]["model_configured"]:
        probe("Semantic wiki", semantic)
    else:
        unavailable("Semantic wiki", "Configure wiki.embed_model and install vector dependencies")
    probe("SkillOpt", optimizer)
    probe("Sentrux", sensor)
    for name, key in (("Exa", "exa"), ("Voyage", "voyage")):
        status = inventory[key]
        if not status["key_configured"]:
            unavailable(name, "SDK installed" if status["package_installed"] else "SDK missing")
            results[-1]["evidence"] += "; provider credential is not configured"
        else:
            results.append({"module": name, "status": "configured",
                            "evidence": "Credential present; provider call not performed by doctor"})
    if inventory["shieldgemma"]["enabled"] and live:
        def classifier():
            from agents.guardrails import GuardrailEngine
            guard = GuardrailEngine(cfg.get("guardrails"))
            assert not guard._shieldgemma_verdict("The sky is blue."), "Benign fixture rejected"
            return "Configured classifier returned a valid No response to a benign fixture"
        probe("ShieldGemma", classifier)
    else:
        unavailable("ShieldGemma", "Requires an explicitly enabled, running classifier endpoint; use --live to probe")
    if live:
        def provider():
            client = LLMClient(config)
            response = client.chat("Reply with exactly M1FRAME_OK.", max_tokens=32)
            assert "M1FRAME_OK" in response, "Provider did not return the fixture marker"
            return {"backend": client.backend, "reply": response}
        probe("Model provider", provider)
    return {"config": str(Path(config).resolve()), "inventory": inventory, "checks": results}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="config.yaml")
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = audit(args.config, args.live)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    for check in result["checks"]:
        print(f"{check['status']:12} {check['module']}: {check['evidence']}")
    return int(any(check["status"] == "failed" for check in result["checks"]))


if __name__ == "__main__":
    sys.exit(main())
