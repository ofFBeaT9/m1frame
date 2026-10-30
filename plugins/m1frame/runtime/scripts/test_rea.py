"""REA adapter: registration, path jail and response handling offline; live Ghidra when installed."""
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools import ToolRegistry, default_registry, rea

_ROOT = Path(__file__).resolve().parent.parent


class ReaOfflineTests(unittest.TestCase):
    def test_registered_on_default_surface(self):
        names = default_registry().names()
        self.assertIn("rea_available", names)
        self.assertIn("rea_investigate", names)
        self.assertFalse(any(t["dangerous"] for t in rea.register_rea_tools(ToolRegistry()).list()))

    def test_target_jail(self):
        cfg = rea.rea_config()
        with self.assertRaisesRegex(ValueError, "outside workspace"):
            rea._safe_target("/etc/passwd", cfg)
        with self.assertRaisesRegex(ValueError, "outside workspace"):
            rea._safe_target("../../etc/passwd", cfg)
        with self.assertRaises(ValueError):
            rea._safe_target("a\x00b", cfg)
        with self.assertRaises(FileNotFoundError):
            rea._safe_target("no-such-binary", cfg)
        self.assertEqual(rea._safe_target("config.yaml", cfg), _ROOT / "config.yaml")
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder, "bin")
            target.write_bytes(b"\x7fELF")
            allowed = {**cfg, "allowed_roots": [folder]}
            self.assertEqual(rea._safe_target(str(target), allowed), target.resolve())

    def test_error_response_raises_code(self):
        response = {"isError": True, "content": [{"type": "text", "text":
                    '{"error":{"code":"provider_unavailable","message":"no engine"}}'}]}
        with self.assertRaisesRegex(RuntimeError, "provider_unavailable: no engine"):
            rea._evidence(response)
        self.assertEqual(rea._evidence({"structuredContent": {"evidence_id": "ev_1"}}),
                         {"evidence_id": "ev_1"})

    def test_missing_binary_is_structured(self):
        with patch.object(rea, "_command", return_value=None):
            result = rea.rea_investigate("config.yaml")
        self.assertFalse(result["ok"])
        self.assertFalse(result["available"])

    def test_ghidra_env_is_passed_explicitly(self):
        env = rea._env({"ghidra_install_dir": "/x/ghidra", "java_home": "/x/jdk"})
        self.assertEqual((env["GHIDRA_INSTALL_DIR"], env["JAVA_HOME"]), ("/x/ghidra", "/x/jdk"))


@unittest.skipUnless(rea.rea_available()["available"] and rea.rea_available()["ghidra_present"]
                     and shutil.which("gcc"), "REA, Ghidra and gcc required for live analysis")
class ReaLiveTests(unittest.TestCase):
    def test_decompiles_symbolized_function(self):
        with tempfile.TemporaryDirectory(dir=_ROOT) as folder:
            source = Path(folder, "demo.c")
            source.write_text("int check(int k){return (k*7)^0x5a;}\nint main(int c,char**v){return check(c);}\n")
            subprocess.run(["gcc", "-O0", "-o", os.path.join(folder, "demo"), str(source)], check=True)
            result = rea.rea_investigate(str(Path(folder, "demo")), procedures=["check"])
        self.assertTrue(result["ok"])
        self.assertTrue(result["untrusted_content"])
        self.assertTrue(result["functions"][0]["ok"])
        self.assertIn("0x5a", result["functions"][0]["pseudocode"])
        self.assertTrue(result["evidence_ids"])


if __name__ == "__main__":
    unittest.main()
