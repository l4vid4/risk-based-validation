import json
import os
from pathlib import Path
import tempfile

from .support import RepoCase
from rbv.config import ValidationError


class BoundaryTests(RepoCase):
    def test_unmerged_index_cannot_certify_even_documentation(self):
        blob = self.git('hash-object', '-w', 'docs/guide.md')
        line = f'100644 {blob} 1\tdocs/guide.md\n100644 {blob} 2\tdocs/guide.md\n'
        import subprocess
        subprocess.run(['git', '-C', str(self.root), 'update-index', '--index-info'],
                       input=line.encode(), check=True, capture_output=True)
        r = self.run_checks()
        self.assertEqual(r['status'], 'incomplete')
        self.assertFalse(r['results'])

    def test_symlinked_evidence_is_rejected(self):
        with tempfile.TemporaryDirectory(prefix='rbv-link-') as other:
            try:
                os.symlink(other, self.root / '.rbv', target_is_directory=True)
            except OSError:
                self.skipTest('OS does not grant symlink creation')
            with self.assertRaises(ValidationError):
                self.plan()
            (self.root / '.rbv').unlink()

    def test_tracked_evidence_is_rejected(self):
        self.write('.rbv/unsafe.json', '{}')
        self.git('add', '-f', '.rbv/unsafe.json')
        with self.assertRaises(ValidationError):
            self.plan()

    def test_config_corrupted_by_check_reports_incomplete(self):
        self.cfg['tests'][1]['command'] = ['{python}', '-c', "from pathlib import Path; Path('.rbv.json').write_text('broken')"]
        self.save()
        self.commit()
        self.write('src/b.py', 'VALUE=2 # edit\n')
        r = self.run_checks(context='x')
        self.assertEqual(r['status'], 'incomplete')
        self.assertTrue(r['invalidated'])

    def test_fresh_failure_revokes_previous_success(self):
        self.cfg['tests'][1]['command'] = ['{python}', '-c', "from pathlib import Path; assert not Path('.rbv/fail-marker').exists()"]
        self.save()
        self.commit()
        self.write('src/b.py', 'VALUE=2 # edit\n')
        self.assertEqual(self.run_checks(context='x')['status'], 'passed')
        self.write('.rbv/fail-marker', '1')
        failed = self.run_checks(context='x', no_cache=True)
        self.assertEqual(failed['status'], 'failed')
        (self.root / '.rbv/fail-marker').unlink()
        r = self.run_checks(context='x')
        self.assertFalse(r['results'][0]['reused'])
