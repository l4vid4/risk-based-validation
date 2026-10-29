import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPTS = Path(__file__).resolve().parents[1] / 'skills' / 'risk-based-validation' / 'scripts'
sys.path.insert(0, str(SCRIPTS))
from rbv.config import load_config
from rbv.planner import make_plan
from rbv.runner import run


class RepoCase(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='rbv-test-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.write('.gitignore', '.rbv/\n__pycache__/\n*.pyc\nignored/\n')
        self.write('src/a.py', 'VALUE = 1\n')
        self.write('src/b.py', 'VALUE = 2\n')
        self.write('docs/guide.md', '# Guide\n')
        self.cfg = {
            'version': 1, 'impact_reviewed': True,
            'components': {'a': {'paths': ['src/a.py']}, 'b': {'paths': ['src/b.py'], 'depends_on': ['a']}},
            'docs': ['docs/*.md'],
            'tests': [
                {'id': 'a', 'command': ['{python}', '-c', "import runpy; assert runpy.run_path('src/a.py')['VALUE'] == 1"], 'components': ['a'], 'inputs': ['tests/a/*'], 'cost': 1, 'cache': True},
                {'id': 'b', 'command': ['{python}', '-c', "import runpy; assert runpy.run_path('src/b.py')['VALUE'] == 2"], 'components': ['b'], 'inputs': ['tests/b/*'], 'cost': 2, 'cache': True},
                {'id': 'other', 'command': ['{python}', '-c', 'print(42)'], 'components': [], 'cost': 3, 'cache': True},
            ]}
        self.save()
        self.git('init', '-q')
        self.commit()

    def write(self, path, value):
        p = self.root / path
        p.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(value, bytes):
            p.write_bytes(value)
        else:
            p.write_text(value, encoding='utf-8')

    def save(self):
        self.write('.rbv.json', json.dumps(self.cfg))

    def git(self, *args):
        p = subprocess.run(['git', '-C', str(self.root), '-c', 'core.autocrlf=false', *args], capture_output=True, check=True)
        return p.stdout.decode().strip()

    def commit(self):
        self.git('add', '.')
        self.git('-c', 'user.name=RBV Tests', '-c', 'user.email=tests@example.invalid', '-c', 'core.hooksPath=', 'commit', '-qm', 'fixture')

    def plan(self, **kwargs):
        return make_plan(self.root, '.rbv.json', **kwargs)

    def run_checks(self, **kwargs):
        return run(self.root, '.rbv.json', **kwargs)
