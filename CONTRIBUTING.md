# Contributing to m1frame

Thank you for helping improve m1frame. This guide gets you from zero to first PR in minutes.

---

## Quick setup

```bash
git clone https://github.com/mahdadshakiba/m1frame.git
cd m1frame
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
pip install ruff mypy pytest          # dev tools

# Verify everything works (no API key needed)
python scripts/qa_validate.py
```

---

## Before you code

- Open an issue first for anything non-trivial so we can align before you invest time.
- Check existing issues and PRs to avoid duplicate work.
- Read `CLAUDE.md` before touching the Wiki pillar.
- Read `purpose.md` to understand the system's intent.

---

## Making changes

### Branch naming
```
feat/add-lancedb-backend
fix/council-review-recursion
docs/update-wiki-readme
```

### Commit style (conventional commits — required for changelog automation)
```
feat(council): add Domain Expert persona to brainstorm
fix(miras): guard against missing story role attr
docs(readme): add offline Ollama quickstart
test(wiki): add lint report health_score bounds check
```

### Pillar ownership
| Pillar | File | Key class |
|---|---|---|
| BMAD | `agents/bmad.py` | `BMADAgent`, `Blueprint`, `Story` |
| Council | `agents/council.py` | `LLMCouncil`, `BrainstormResult`, `CouncilVerdict` |
| Miras | `agents/miras.py` | `MirasOrchestrator`, `AgentState` |
| Karpathy | `agents/karpathy.py` | `KarpathyEngine`, `KarpathyResult` |
| Wiki | `agents/wiki.py` | `LLMWiki`, `WikiPage`, `LintReport` |
| Client | `llm_client.py` | `LLMClient` |

---

## QA requirements

All PRs **must** pass the full QA suite:

```bash
python scripts/qa_validate.py          # 34 tests, no key needed
```

If you add a feature, add a test for it in `scripts/qa_validate.py` under the correct pillar group.

---

## Code style

```bash
ruff check .       # linting
mypy agents/ llm_client.py   # type checking
```

Rules: `ruff` enforces PEP 8, isort, and pyupgrade. All public functions need type hints and a one-line docstring.

---

## Beta API policy

New features that may change before v2.0 must be marked:

```python
# BETA: API subject to change before v2.0
def experimental_feature() -> str:
    ...
```

---

## Release process (maintainers only)

1. Update `CHANGELOG.md` under `## Unreleased`
2. Bump version in `pyproject.toml`
3. Commit: `chore: release v1.x.x`
4. Tag: `git tag v1.x.x && git push --tags`
5. GitHub Actions auto-publishes to PyPI on tag push.

---

## Getting help

Open a [Discussion](https://github.com/mahdadshakiba/m1frame/discussions) for questions.  
Use [Issues](https://github.com/mahdadshakiba/m1frame/issues) for bugs and feature requests only.
