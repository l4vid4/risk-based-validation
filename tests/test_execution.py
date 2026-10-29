import json
import os
import sys
from unittest.mock import patch

from .support import RepoCase
from rbv.config import ValidationError
from rbv.repository import digest


class ExecutionTests(RepoCase):
    def change(self):
        self.write('src/b.py', 'VALUE = 2 # refactor\n')

    def test_exact_state_reuse_and_log_tamper(self):
        self.change()
        first = self.run_checks(context='deps-v1')
        second = self.run_checks(context='deps-v1')
        self.assertEqual(first['status'], 'passed')
        self.assertFalse(first['results'][0]['reused'])
        self.assertTrue(second['results'][0]['reused'])
        (self.root / first['results'][0]['log']).write_text('tampered')
        self.assertFalse(self.run_checks(context='deps-v1')['results'][0]['reused'])

    def test_content_environment_context_config_and_extra_input_invalidate(self):
        self.cfg['extra_inputs'] = ['ignored/*.txt']
        self.save()
        self.commit()
        self.change()
        self.run_checks(context='v1')
        self.assertTrue(self.run_checks(context='v1')['results'][0]['reused'])
        self.write('ignored/data.txt', 'new state')
        self.assertFalse(self.run_checks(context='v1')['results'][0]['reused'])
        with patch.dict(os.environ, {'RBV_TEST_VARIANT': 'other'}):
            self.assertFalse(self.run_checks(context='v1')['results'][0]['reused'])
        self.assertFalse(self.run_checks(context='v2')['results'][0]['reused'])
        self.write('src/b.py', 'VALUE=2 # different\n')
        self.assertFalse(self.run_checks(context='v2')['results'][0]['reused'])
        self.cfg['tests'][1]['timeout'] = 50
        self.save()
        self.assertFalse(any(r['reused'] for r in self.run_checks(context='v2')['results']))

    def test_no_context_default_and_no_cache_force_fresh(self):
        self.change()
        for kwargs in ({}, {}, {'context': 'x'}, {'context': 'x', 'no_cache': True}):
            self.assertFalse(self.run_checks(**kwargs)['results'][0]['reused'])

    def test_expired_and_corrupt_evidence_reexecute(self):
        self.change()
        self.run_checks(context='x')
        path = self.root / '.rbv/cache' / (digest('b') + '.json')
        record = json.loads(path.read_text())
        record['finished_at'] = 0
        path.write_text(json.dumps(record))
        self.assertFalse(self.run_checks(context='x')['results'][0]['reused'])
        path.write_text('not json')
        self.assertFalse(self.run_checks(context='x')['results'][0]['reused'])

    def test_failure_expands_once_without_repeating(self):
        self.write('src/b.py', 'VALUE = 3\n')
        report = self.run_checks(context='x')
        self.assertEqual(report['status'], 'failed')
        self.assertTrue(report['escalated'])
        ids = [r['id'] for r in report['results']]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(set(ids), {'a', 'b', 'other'})
        self.assertFalse(self.run_checks(context='x')['results'][0]['reused'])

    def test_high_risk_checks_are_never_reused(self):
        self.cfg['tests'][0]['tags'] = ['security']
        self.save()
        self.commit()
        self.write('src/a.py', 'VALUE=1\npassword="example"\n')
        self.run_checks(context='x')
        r = self.run_checks(context='x')
        self.assertEqual(r['status'], 'passed')
        self.assertFalse(any(x['reused'] for x in r['results']))

    def test_timeout_and_budget_cannot_pass(self):
        self.cfg['tests'][1]['command'] = ['{python}', '-c', 'import time; time.sleep(10)']
        self.cfg['tests'][1]['timeout'] = 0.1
        self.save()
        self.commit()
        self.change()
        r = self.run_checks()
        self.assertIn(r['status'], ['failed', 'incomplete'])
        self.assertEqual(r['results'][0]['status'], 'timeout')
        r = self.run_checks(budget=0.00001)
        self.assertEqual(r['status'], 'incomplete')
        self.assertTrue(r['unresolved'])

    def test_source_mutation_invalidates_entire_run(self):
        self.cfg['tests'][1]['command'] = ['{python}', '-c', "from pathlib import Path; Path('src/a.py').write_text('VALUE=99')"]
        self.save()
        self.commit()
        self.change()
        r = self.run_checks(context='x')
        self.assertEqual(r['status'], 'incomplete')
        self.assertTrue(r['invalidated'])
        self.assertFalse(list((self.root / '.rbv/cache').glob('*.json')))

    def test_missing_executable_is_error_and_escalates(self):
        self.cfg['tests'][1]['command'] = ['rbv-missing-executable-67e00']
        self.save()
        self.commit()
        self.change()
        r = self.run_checks()
        self.assertEqual(r['status'], 'failed')
        self.assertEqual(r['results'][0]['status'], 'error')
        self.assertTrue(r['diagnosis'])

    def test_exclusive_lock_and_no_shell_injection(self):
        self.change()
        (self.root / '.rbv').mkdir()
        (self.root / '.rbv/lock').write_text('123')
        with self.assertRaises(ValidationError):
            self.run_checks()
        (self.root / '.rbv/lock').unlink()
        self.cfg['tests'][1]['command'] = ['{python}', '-c', 'import sys; print(sys.argv[1])', '; touch injected']
        self.save()
        r = self.run_checks()
        self.assertEqual(r['status'], 'passed')
        self.assertFalse((self.root / 'injected').exists())

    def test_report_contains_evidence_and_no_environment_values(self):
        self.change()
        with patch.dict(os.environ, {'RBV_PRIVATE_KEY': 'should-never-appear-in-report'}):
            r = self.run_checks(context='secret-context-token')
        from pathlib import Path
        raw = Path(r['report_path']).read_text(encoding='utf-8')
        self.assertNotIn('should-never-appear-in-report', raw)
        self.assertNotIn('secret-context-token', raw)
        self.assertTrue(r['results'][0]['log_hash'])
