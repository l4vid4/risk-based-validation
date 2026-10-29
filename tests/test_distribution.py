"""Exercise actual portable distribution, not README wording."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from tools.install_skill import install

ROOT = Path(__file__).resolve().parents[1]


class DistributionTests(unittest.TestCase):
    def test_portable_install_can_run_without_source_checkout(self):
        with tempfile.TemporaryDirectory(prefix='rbv-install-') as tmp:
            dest = install(tmp)
            p = subprocess.run([sys.executable, str(dest / 'scripts/validate.py'), '--version'],
                               cwd=tmp, capture_output=True, text=True)
            self.assertEqual(p.returncode, 0, p.stderr)
            self.assertEqual(p.stdout.strip(), '0.1.0')
            self.assertTrue((dest / 'scripts/rbv/planner.py').is_file())
            with self.assertRaises(FileExistsError):
                install(tmp)

    def test_bundled_configs_are_valid(self):
        sys.path.insert(0, str(ROOT / 'skills/risk-based-validation/scripts'))
        from rbv.config import load_config
        for name in ('.rbv.json', 'examples/python.json'):
            with self.subTest(name=name):
                self.assertTrue(load_config(ROOT / name)['tests'])
