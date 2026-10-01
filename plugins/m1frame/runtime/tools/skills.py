"""Read-only discovery of all locally learned recipes."""
from dataclasses import asdict

from agents.skills import SkillLibrary
from tools.registry import Tool


def skill_search(query: str = "", limit: int = 20) -> list[dict]:
    library = SkillLibrary()
    limit = max(0, min(int(limit), 200))
    skills = library.suggest(query, k=limit, min_overlap=0.01) if query.strip() else library.all()[:limit]
    return [{"id": s.id, "title": s.title, "score": s.score} for s in skills]


def skill_read(skill_id: str) -> dict:
    for skill in SkillLibrary().all():
        if skill.id == skill_id:
            return asdict(skill)
    raise KeyError(f"Unknown learned skill: {skill_id}")


def register_skill_tools(reg):
    reg.register(Tool("skill_search", "Find council-vetted recipes; empty query lists all.",
                      skill_search, {"query": "string (optional)", "limit": "int (optional)"}))
    reg.register(Tool("skill_read", "Read a complete council-vetted recipe by ID.",
                      skill_read, {"skill_id": "string"}))
    return reg
