"""Scientific skills on the shared CLI/API/MCP tool registry."""
from .library import configured_library


def register_scientific_tools(reg):
    from tools.registry import Tool

    reg.register(Tool("scientific_list", "Discover scientific workflow skills by keyword.",
                      lambda query="", limit=200: configured_library().list(query, limit),
                      {"query": "string (optional)", "limit": "int (optional)"}))
    reg.register(Tool("scientific_read", "Read scientific instructions or supporting text, with pagination.",
                      lambda name, resource="SKILL.md", offset=0, limit=100000:
                      configured_library().read(name, resource, offset, limit),
                      {"name": "string", "resource": "string (optional)",
                       "offset": "int (optional)", "limit": "int (optional)"}))
    reg.register(Tool("scientific_resources", "List all supporting files for a scientific skill.",
                      lambda name: configured_library().resources(name), {"name": "string"}))
    reg.register(Tool("scientific_audit", "Audit scientific skill loading and static dependency hints.",
                      lambda: configured_library().audit(), {}))
    return reg
