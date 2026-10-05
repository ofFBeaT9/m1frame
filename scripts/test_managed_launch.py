"""Regression coverage for selecting the persistent runtime and missing auth."""
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from llm_client import LLMClient
from scripts.launch_managed import runtime_command


class ManagedLaunchTests(unittest.TestCase):
    def test_relative_runtime_rejected(self):
        with patch.dict(os.environ, {"M1FRAME_HOME": "relative"}):
            with self.assertRaisesRegex(RuntimeError, "absolute"):
                runtime_command()

    def test_incomplete_runtime_fails_without_fallback(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch.dict(os.environ, {"M1FRAME_HOME": folder}):
                with self.assertRaisesRegex(RuntimeError, "incomplete"):
                    runtime_command()

    def test_runtime_uses_its_own_interpreter_and_server(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            python = root / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
            python.parent.mkdir(parents=True)
            for file in (python, root / "mcp_server.py", root / "config.yaml"):
                file.touch()
            with patch.dict(os.environ, {"M1FRAME_HOME": folder}):
                cwd, command = runtime_command()
            self.assertEqual(cwd, root)
            self.assertEqual(command, [str(python), str(root / "mcp_server.py")])

    def test_missing_claude_credential_fails_before_request(self):
        client = object.__new__(LLMClient)
        client.backend = "claude"
        client.cfg = {"claude": {"api_key_env": "M1_TEST_MISSING_KEY"}}
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(RuntimeError, "Missing M1_TEST_MISSING_KEY"):
                client._build_client()


if __name__ == "__main__":
    unittest.main()
