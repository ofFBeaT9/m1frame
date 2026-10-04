"""Explicit synchronous MCP connector backed by a managed async stdio session.

Use as a context manager. Remote tools require caller approval by default.
No host connections or credentials are discovered or forwarded automatically.
"""
from __future__ import annotations

import asyncio
import concurrent.futures
import threading
from typing import Any

from .registry import Tool, ToolRegistry


class MCPClient:
    def __init__(self, timeout: float = 30):
        self.timeout = max(1, min(float(timeout), 600))
        self._session: Any = None
        self._specs: list[dict] = []
        self._loop: Any = None
        self._stop: Any = None
        self._thread: Any = None

    def connect_stdio(self, command: list[str], cwd: str | None = None,
                      env: dict[str, str] | None = None) -> MCPClient:
        if self._thread is not None:
            raise RuntimeError('MCP client already connected; close it before reconnecting')
        if not command or not all(isinstance(a, str) and a for a in command):
            raise ValueError('A nonempty server command is required')
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client
        ready: concurrent.futures.Future = concurrent.futures.Future()

        async def serve():
            self._loop = asyncio.get_running_loop()
            self._stop = asyncio.Event()
            try:
                params = StdioServerParameters(command=command[0], args=command[1:], cwd=cwd, env=env)
                async with stdio_client(params) as (read, write), ClientSession(read, write) as session:
                    self._session = session
                    await session.initialize()
                    self._specs = await self._discover_tools(session)
                    ready.set_result(True)
                    await self._stop.wait()
            except BaseException as exc:
                if not ready.done():
                    ready.set_exception(RuntimeError(f'MCP connection failed: {exc}'))
            finally:
                self._session = None

        self._thread = threading.Thread(target=lambda: asyncio.run(serve()), daemon=True)
        self._thread.start()
        try:
            ready.result(timeout=self.timeout)
        except concurrent.futures.TimeoutError:
            self.close()
            raise TimeoutError(f'MCP connection timed out after {self.timeout}s') from None
        except BaseException:
            self.close()
            raise
        return self

    @staticmethod
    async def _discover_tools(session) -> list[dict]:
        specs: list[dict] = []
        seen: set[str] = set()
        cursor = None
        for _ in range(100):
            result = await session.list_tools(cursor=cursor) if cursor else await session.list_tools()
            specs.extend({'name': t.name, 'description': t.description or '',
                          'schema': t.inputSchema} for t in result.tools)
            cursor = result.nextCursor
            if not cursor:
                return specs
            if cursor in seen:
                raise RuntimeError('MCP server repeated its tool pagination cursor')
            seen.add(cursor)
        raise RuntimeError('MCP tool discovery exceeded 100 pages')

    def list_tools(self) -> list[dict]:
        return list(self._specs)

    def call_tool(self, name: str, args: dict | None = None) -> dict:
        if self._session is None or self._loop is None:
            raise RuntimeError('MCP session not connected')
        future = asyncio.run_coroutine_threadsafe(self._session.call_tool(name, args or {}), self._loop)
        try:
            return future.result(timeout=self.timeout).model_dump(mode='json', exclude_none=True)
        except concurrent.futures.TimeoutError:
            future.cancel()
            raise TimeoutError(f'MCP tool {name} timed out after {self.timeout}s') from None

    def register_into(self, reg: ToolRegistry) -> ToolRegistry:
        for spec in self._specs:
            reg.register(Tool(spec['name'], spec['description'], self._caller(spec['name']),
                              spec['schema'], dangerous=True))
        return reg

    def _caller(self, name: str):
        def call(**kwargs):
            return self.call_tool(name, kwargs)
        return call

    def close(self):
        if self._loop is not None and self._stop is not None and not self._loop.is_closed():
            self._loop.call_soon_threadsafe(self._stop.set)
        if self._thread is not None:
            self._thread.join(timeout=self.timeout)
            if self._thread.is_alive():
                # Startup can be hung before the stop event is reached. Cancel
                # the session task so the SDK closes its subprocess transports.
                if self._loop is not None and not self._loop.is_closed():
                    self._loop.call_soon_threadsafe(self._cancel_tasks)
                self._thread.join(timeout=5)
        self._thread = self._loop = self._stop = self._session = None
        self._specs = []

    def _cancel_tasks(self):
        for task in asyncio.all_tasks(self._loop):
            task.cancel()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()
