"""Real stdio integration test, no model credentials or network required."""
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

from tools import ToolRegistry
from tools.mcp_client import MCPClient


class MCPConnectorTests(unittest.TestCase):
    def test_paginated_discovery_and_repeated_cursor(self):
        import asyncio
        session = SimpleNamespace(list_tools=AsyncMock())
        def tool(name):
            return SimpleNamespace(name=name, description='', inputSchema={})
        session.list_tools.side_effect = [
            SimpleNamespace(tools=[tool('first')], nextCursor='next'),
            SimpleNamespace(tools=[tool('second')], nextCursor=None)]
        result = asyncio.run(MCPClient._discover_tools(session))
        self.assertEqual([spec['name'] for spec in result], ['first', 'second'])
        session.list_tools.assert_awaited_with(cursor='next')
        session.list_tools.side_effect = [SimpleNamespace(tools=[], nextCursor='same')] * 2
        with self.assertRaisesRegex(RuntimeError, 'repeated'):
            asyncio.run(MCPClient._discover_tools(session))

    def test_unresponsive_server_times_out_and_closes(self):
        import time
        started = time.monotonic()
        client = MCPClient(timeout=1)
        with self.assertRaisesRegex(TimeoutError, 'connection timed out'):
            client.connect_stdio([sys.executable, '-c', 'import time; time.sleep(60)'])
        self.assertLess(time.monotonic() - started, 9)
        self.assertIsNone(client._thread)
        self.assertIsNone(client._session)

    def test_real_server_roundtrip_and_approval(self):
        with tempfile.TemporaryDirectory() as folder:
            server = Path(folder, 'server.py')
            server.write_text('from mcp.server.fastmcp import FastMCP\n'
                              'm=FastMCP("fixture")\n@m.tool()\n'
                              'def add(a:int,b:int)->int: return a+b\nm.run()\n')
            with MCPClient(timeout=10).connect_stdio([sys.executable, str(server)]) as client:
                self.assertEqual(client.list_tools()[0]['name'], 'add')
                result = client.call_tool('add', {'a': 19, 'b': 23})
                self.assertFalse(result.get('isError', False))
                self.assertIn('42', str(result))
                registry = client.register_into(ToolRegistry())
                with self.assertRaises(PermissionError):
                    registry.call('add', {'a': 1, 'b': 2})
                self.assertIn('3', str(registry.call('add', {'a': 1, 'b': 2}, approved=True)))
            with self.assertRaisesRegex(RuntimeError, 'not connected'):
                client.call_tool('add')


if __name__ == '__main__':
    unittest.main()
