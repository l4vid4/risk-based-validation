import json
import subprocess
import sys

from .support import RepoCase, SCRIPTS


class CLITests(RepoCase):
    def cli(self, *args):
        return subprocess.run([sys.executable, str(SCRIPTS / 'validate.py'), *args,
                               '--repo', str(self.root)], capture_output=True, text=True)

    def test_plan_is_read_only_and_execute_is_explicit(self):
        p = self.cli('plan')
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertFalse((self.root / '.rbv').exists())
        p = self.cli('run')
        self.assertEqual(p.returncode, 2)
        self.assertIn('--execute', p.stderr)

    def test_exit_codes(self):
        self.write('src/b.py', 'VALUE=3\n')
        p = self.cli('run', '--execute')
        self.assertEqual(p.returncode, 1, p.stderr)
        self.assertEqual(json.loads(p.stdout)['status'], 'failed')
        p = self.cli('run', '--execute', '--budget', '0.000001')
        self.assertEqual(p.returncode, 2, p.stderr)

    def test_clean_repo_still_obeys_always_checks(self):
        self.cfg['tests'][2]['tags'] = ['always']
        self.save()
        self.commit()
        self.assertEqual([t['id'] for t in self.plan()['selected']], ['other'])
