"""
tools/registry.py — a minimal, safe, extensible tool surface.

A `Tool` is a name + description + JSON-ish parameter schema + a Python callable.
`ToolRegistry` is what agents (and the API) call to discover and invoke tools.
This is the seam an MCP client plugs into (see tools/mcp_client.py), so external
MCP servers can register their tools alongside the built-ins.
"""
from __future__ import annotations

import builtins
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Tool:
    name: str
    description: str
    func: Callable[..., Any]
    schema: dict = field(default_factory=dict)   # {param: type-or-description}
    dangerous: bool = False                       # requires explicit approval to run

    def spec(self) -> dict:
        return {"name": self.name, "description": self.description,
                "schema": self.schema, "dangerous": self.dangerous}


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

    # `builtins.` is load-bearing: `list` is a method of this class (above), so a
    # bare `list[str]` here resolves to that method, not the builtin. Harmless at
    # runtime thanks to postponed annotations, but it breaks mypy and anything
    # calling `typing.get_type_hints()` on the class.
    def names(self) -> builtins.list[str]:
        return list(self._tools)

    def call(self, name: str, args: dict | None = None, approved: bool = False) -> Any:
        if name not in self._tools:
            raise KeyError(f"unknown tool '{name}'")
        tool = self._tools[name]
        if tool.dangerous and not approved:
            raise PermissionError(f"tool '{name}' is dangerous and requires approval")
        return tool.func(**(args or {}))

    def __contains__(self, name: str) -> bool:
        return name in self._tools

    def __len__(self) -> int:
        return len(self._tools)
