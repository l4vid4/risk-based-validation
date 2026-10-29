"""Run a real isolated demonstration without changing the caller's repository."""
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'skills/risk-based-validation/scripts'))
from benchmarks.fixture import create
from rbv.planner import make_plan
from rbv.runner import run


def main():
    with tempfile.TemporaryDirectory(prefix='rbv-demo-') as tmp:
        root = Path(tmp).resolve()
        create(root, cases=20)
        search = root / 'src/search.py'
        search.write_text(search.read_text() + '\n# A local refactor with unchanged behavior.\n')
        plan = make_plan(root, '.rbv.json')
        names = [t['id'] for t in plan['selected']]
        assert names == ['search'], names
        print('1. Local change: selected search (1 of 6 checks).')
        first = run(root, '.rbv.json', context='demo-stdlib-local-v1')
        assert first['status'] == 'passed', first
        print('   Executed search: passed.')
        second = run(root, '.rbv.json', context='demo-stdlib-local-v1')
        assert second['status'] == 'passed' and second['results'][0]['reused'], second
        print('2. Identical inputs and context: reused the verified search pass.')
        access = root / 'src/access.py'
        access.write_text(access.read_text().replace('actor["tenant"] == owner["tenant"] and ', ''))
        plan = make_plan(root, '.rbv.json')
        assert 'security' in plan['required_tags'] and len(plan['selected']) == 6, plan
        print('3. Tenant isolation change: security gate; selected all 6 checks fresh.')
        report = run(root, '.rbv.json', context='demo-stdlib-local-v1')
        assert report['status'] == 'failed', report
        assert any(r['id'] == 'security' and r['status'] == 'failed' for r in report['results']), report
        assert all(not r['reused'] for r in report['results']), report
        print('   Security defect detected: failed, as expected. No cached pass used.')
        print('Temporary fixture and logs are removed when this demo exits.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
