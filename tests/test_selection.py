from .support import RepoCase, load_config
from rbv.config import ValidationError


class SelectionTests(RepoCase):
    def test_clock_named_source_is_not_a_dependency_lock(self):
        self.cfg['components']['b']['paths'].append('src/clock.py')
        self.save()
        self.commit()
        self.write('src/clock.py', 'VALUE=1\n')
        self.assertEqual([t['id'] for t in self.plan()['selected']], ['b'])

    def test_transitive_impact_and_cost_order(self):
        self.write('src/a.py', 'VALUE = 1 # refactor\n')
        p = self.plan()
        self.assertEqual(p['affected_components'], ['a', 'b'])
        self.assertEqual([t['id'] for t in p['selected']], ['a', 'b'])
        self.assertEqual([t['id'] for t in p['skipped']], ['other'])

    def test_docs_only_can_require_no_commands(self):
        self.write('docs/guide.md', '# Better guide\n')
        p = self.plan()
        self.assertFalse(p['selected'])
        self.assertEqual(self.run_checks()['status'], 'no_checks_required')

    def test_owned_document_is_not_blindly_skipped(self):
        self.cfg['components']['a']['paths'].append('docs/*.md')
        self.save()
        self.commit()
        self.write('docs/guide.md', 'runtime template\n')
        self.assertEqual(self.plan()['affected_components'], ['a', 'b'])

    def test_unknown_untracked_and_binary_widen(self):
        for name, value in [('plugin.py', 'x=1'), ('new.bin', b'\x00\x01')]:
            with self.subTest(name=name):
                self.write(name, value)
                self.assertEqual(len(self.plan()['selected']), 3)
                (self.root / name).unlink()

    def test_unreviewed_map_and_global_lock_force_full(self):
        self.cfg['impact_reviewed'] = False
        self.save()
        self.assertEqual(len(self.plan()['selected']), 3)
        self.cfg['impact_reviewed'] = True
        self.save()
        self.write('src/b.py', 'VALUE=2 # edit\n')
        self.write('package-lock.json', '{}')
        self.assertEqual(len(self.plan()['selected']), 3)

    def test_new_tests_select_via_inputs(self):
        self.write('tests/a/new.py', 'assert True\n')
        self.assertEqual([t['id'] for t in self.plan()['selected']], ['a'])

    def test_rename_delete_staged_and_pr_base(self):
        base = self.git('rev-parse', 'HEAD')
        self.git('mv', 'src/b.py', 'src/renamed.py')
        p = self.plan()
        self.assertIn('src/b.py', p['changed'])
        self.assertIn('src/renamed.py', p['changed'])
        self.assertEqual(len(p['selected']), 3)
        self.commit()
        self.assertEqual(self.plan()['changed'], [])
        self.assertIn('src/b.py', self.plan(base=base)['changed'])

    def test_staged_content_cannot_disappear_from_analysis(self):
        self.write('src/a.py', 'password = "new"\nVALUE=1\n')
        self.git('add', 'src/a.py')
        self.write('src/a.py', 'VALUE = 1\n')
        self.assertIn('security', self.plan()['required_tags'])

    def test_sensitive_content_enforces_gate_even_at_neutral_path(self):
        self.write('src/a.py', 'def check_access(): return True\nVALUE=1\n')
        p = self.plan()
        self.assertEqual(p['risk'], 'high')
        self.assertIn('missing required validation tag: security', p['blockers'])
        self.assertEqual(self.run_checks()['status'], 'incomplete')

    def test_sensitive_data_and_custom_gate_cannot_be_removed(self):
        self.cfg['protected'] = [{'name': 'checkout', 'paths': ['src/b.py'], 'required_tags': ['contract']}]
        self.save()
        self.commit()
        self.write('src/b.py', 'transaction = False\nVALUE=2\n')
        p = self.plan()
        self.assertEqual(p['required_tags'], ['contract', 'data'])
        self.assertEqual(len(p['selected']), 3)

    def test_component_without_test_is_incomplete(self):
        self.cfg['components']['c'] = {'paths': ['src/c.py']}
        self.save()
        self.commit()
        self.write('src/c.py', 'X=1')
        self.assertTrue(self.plan()['blockers'])

    def test_cycles_terminate(self):
        self.cfg['components']['a']['depends_on'] = ['b']
        self.save()
        self.commit()
        self.write('src/a.py', 'VALUE=1\n')
        self.assertEqual(self.plan()['affected_components'], ['a', 'b'])

    def test_configuration_typos_fail_closed(self):
        cases = [lambda c: c.update(impact_reviwed=True),
                 lambda c: c['tests'][0].update(command='echo pass'),
                 lambda c: c['components']['a'].update(depends_on=['missing']),
                 lambda c: c['tests'][0].update(cost=float('nan')),
                 lambda c: c['tests'][0].update(cache='yes'),
                 lambda c: c.update(docs=['../*'])]
        import copy
        original = copy.deepcopy(self.cfg)
        for mutate in cases:
            self.cfg = copy.deepcopy(original)
            mutate(self.cfg)
            self.save()
            with self.assertRaises(ValidationError):
                load_config(self.root / '.rbv.json')

    def test_no_base_is_an_error(self):
        with self.assertRaises(ValidationError):
            self.plan(base='missing-ref')
