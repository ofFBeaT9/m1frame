"""
tools/registry.py — a minimal, safe, extensible tool surface.

A `Tool` is a name + description + JSON-ish parameter schema + a Python callable.
`ToolRegistry` is what agents (and the API) call to discover and invoke tools.
This is the seam an MCP client plugs into (see tools/mcp_client.py), so external
MCP servers can register their tools alongside the built-ins.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class Tool:
    name: str
    description: str
    func: Callable[..., Any]
    schema: dict = field(default_factory=dict)   # {param: type-or-description}

    def spec(self) -> dict:
        return {"name": self.name, "description": self.description, "schema": self.schema}


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> Tool:
        self._tools[tool.name] = tool
        return tool

    def tool(self, name: str, description: str, schema: dict | None = None):
        """Decorator: @registry.tool('name', 'desc', {...})."""
        def deco(fn: Callable[..., Any]) -> Callable[..., Any]:
            self.register(Tool(name, description, fn, schema or {}))
            return fn
        return deco

    def list(self) -> list[dict]:
        return [t.spec() for t in self._tools.values()]

    def names(self) -> list[str]:
        return list(self._tools)

    def call(self, name: str, args: dict | None = None) -> Any:
        if name not in self._tools:
            raise KeyError(f"unknown tool '{name}'")
        return self._tools[name].func(**(args or {}))

    def __contains__(self, name: str) -> bool:
        return name in self._tools

    def __len__(self) -> int:
        return len(self._tools)
