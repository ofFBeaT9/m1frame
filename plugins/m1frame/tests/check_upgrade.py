"""Verify upgrades preserve credentials/config/history and back up changed code."""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from upgrade import upgrade_runtime


class UpgradeTests(unittest.TestCase):
    def test_code_backup_and_data_preservation(self):
        with tempfile.TemporaryDirectory() as folder:
            bundle, runtime = Path(folder, 'bundle'), Path(folder, 'runtime')
            for root in (bundle, runtime):
                (root / 'agents').mkdir(parents=True)
                (root / 'wiki').mkdir()
            for name in ('.env', 'config.yaml', 'wiki/history.md'):
                (bundle / name).write_text('bundled example')
                (runtime / name).write_text('user data')
            (bundle / 'agents/test.py').write_text('new code')
            (runtime / 'agents/test.py').write_text('old code')
            result = upgrade_runtime(bundle, runtime)
            self.assertEqual((runtime / 'agents/test.py').read_text(), 'new code')
            self.assertEqual((Path(result['backup']) / 'agents/test.py').read_text(), 'old code')
            for name in ('.env', 'config.yaml', 'wiki/history.md'):
                self.assertEqual((runtime / name).read_text(), 'user data')
            self.assertEqual(upgrade_runtime(bundle, runtime)['changed'], [])


if __name__ == '__main__':
    unittest.main()
