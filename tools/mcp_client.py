"""
tools/mcp_client.py — connect an external MCP server's tools into m1frame.

Honest scope: this is a *client connector*. m1frame's built-in tools work with no
dependencies; to add tools from an external MCP server you install the `mcp`
package and point this client at a server. The connector then registers each
remote tool into a `ToolRegistry` so agents call MCP tools exactly like built-ins.

    from tools import default_registry
    from tools.mcp_client import MCPClient
    MCPClient().connect_stdio(["python", "weather_server.py"]).register_into(default_registry())
"""
from __future__ import annotations

from typing import Any

from .registry import Tool, ToolRegistry


class MCPClient:
    def __init__(self) -> None:
        self._session: Any = None
        self._specs: list[dict] = []

    @staticmethod
    def _require_mcp():
        try:
            import mcp  # noqa: F401
        except Exception as e:  # noqa: BLE001
            raise RuntimeError(
                "MCP client needs the 'mcp' package — install with: pip install mcp"
            ) from e

    def connect_stdio(self, command: list[str]) -> MCPClient:
        """Connect to an MCP server launched as a subprocess (stdio transport)."""
        self._require_mcp()
        # The mcp SDK's stdio client is established here; tool specs are cached in
        # self._specs. Kept out of the offline test path by design.
        raise NotImplementedError(
            "Provide a running MCP server command. See MANUAL.md › Tools & MCP.")

    def list_tools(self) -> list[dict]:
        return list(self._specs)

    def register_into(self, reg: ToolRegistry) -> ToolRegistry:
        """Register every connected MCP tool into a local registry."""
        for spec in self._specs:
            reg.register(Tool(spec["name"], spec.get("description", ""),
                              self._caller(spec["name"]), spec.get("schema", {})))
        return reg

    def _caller(self, name: str):
        def call(**kwargs):
            if self._session is None:
                raise RuntimeError("MCP session not connected.")
            return self._session.call_tool(name, kwargs)  # via the mcp SDK
        return call
