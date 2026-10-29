"""Compare actual commands against raw full-suite execution. Writes reproducible raw evidence."""
import argparse
import json
import platform
from pathlib import Path
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'skills/risk-based-validation/scripts'))
from rbv.runner import run, command_args, file_hash
from rbv.repository import digest
from benchmarks.fixture import create, git

SCENARIOS = [
    ('docs_only', 'docs/guide.md', None, '# Improved guide\n', False),
    ('local_refactor', 'src/search.py', 'query.casefold()', '(query.casefold())', False),
    ('local_bug', 'src/search.py', 'query.casefold()', 'query.lower()', True),
    ('pricing_bug', 'src/pricing.py', '* 9 // 10', '* 10 // 10', True),
    ('shared_dependency_bug', 'src/shared.py', 'sum(values)', 'sum(values) + 7', True),
    ('tenant_isolation_bug', 'src/access.py', 'actor["tenant"] == owner["tenant"] and ', '', True),
    ('atomicity_bug', 'src/storage.py', 'with db:', 'if True:', True),
    ('unmapped_loader_bug', 'src/loader.py', 'json.loads(raw)["enabled"] is True', 'bool(json.loads(raw)["enabled"])', True),
    ('dependency_lock_change', 'requirements.lock', None, '# dependency update\n', False),
    ('deleted_component', 'src/search.py', None, None, True),
    ('unreviewed_mapping', 'src/search.py', 'query.casefold()', 'query.lower()', True),
    ('repeat_identical_state', 'src/search.py', 'query.casefold()', '(query.casefold())', False),
]


def full_run(root, cfg):
    start = time.perf_counter()
    results = []
    for test in cfg['tests']:
        t0 = time.perf_counter()
        p = subprocess.run(command_args(test), cwd=root, capture_output=True, text=True, timeout=test.get('timeout', 300))
        results.append({'id': test['id'], 'returncode': p.returncode,
                        'duration_seconds': time.perf_counter() - t0,
                        'stdout': p.stdout.replace(str(root), '<fixture>'),
                        'stderr': p.stderr.replace(str(root), '<fixture>')})
    return {'elapsed_seconds': time.perf_counter() - start, 'results': results,
            'detected_defect': any(r['returncode'] for r in results)}


def evaluate(cases=1000, repetitions=1, scenario_names=None):
    rows = []
    for repetition in range(repetitions):
        for name, path, old, new, defect in SCENARIOS:
            if scenario_names and name not in scenario_names:
                continue
            with tempfile.TemporaryDirectory(prefix='rbv-eval-') as tmp:
                root = Path(tmp).resolve()
                cfg = create(root, cases)
                # Verify the baseline fixture once per case: no pre-existing failures.
                baseline = full_run(root, cfg)
                if baseline['detected_defect']:
                    raise RuntimeError(f'Invalid baseline: {name}: {baseline}')
                if name == 'unreviewed_mapping':
                    cfg['impact_reviewed'] = False
                    (root / '.rbv.json').write_text(json.dumps(cfg))
                    git(root, 'add', '.')
                    git(root, '-c', 'user.name=RBV Benchmark', '-c', 'user.email=benchmark@example.invalid',
                        '-c', 'core.hooksPath=', 'commit', '-qm', 'unreviewed map')
                target = root / path
                if new is None:
                    target.unlink()
                elif old is None:
                    target.write_text(new, encoding='utf-8')
                else:
                    content = target.read_text(encoding='utf-8')
                    if old not in content:
                        raise RuntimeError(f'Mutation did not apply: {name}')
                    target.write_text(content.replace(old, new), encoding='utf-8')
                args = {'context': 'fixture-python-stdlib-local-v1'} if name == 'repeat_identical_state' else {'no_cache': True}
                warmup = None
                if name == 'repeat_identical_state':
                    warmup = run(root, '.rbv.json', **args)
                # Alternate order to reduce systematic warm-start bias.
                if repetition % 2:
                    selective = run(root, '.rbv.json', **args)
                    full = full_run(root, cfg)
                else:
                    full = full_run(root, cfg)
                    selective = run(root, '.rbv.json', **args)
                detected = any(r['status'] == 'failed' for r in selective['results'])
                # Preserve evidence semantics while removing local usernames/temp paths.
                for item in (selective, warmup):
                    if item:
                        item['plan']['root'] = '<fixture>'
                        item['report_path'] = '<fixture>/' + Path(item['report_path']).name
                row = {'scenario': name, 'repetition': repetition, 'known_defect': defect,
                       'baseline_clean': not baseline['detected_defect'], 'full': full,
                       'selective': selective, 'detected_defect': detected,
                       'missed_known_defect': defect and not detected,
                       'false_alarm': not defect and selective['status'] not in ('passed', 'no_checks_required'),
                       'warmup': warmup}
                rows.append(row)
                print(f'{name}: full={len(full["results"])} risk={sum(not r["reused"] for r in selective["results"])} status={selective["status"]}', file=sys.stderr, flush=True)
    # Negative control: explicitly lying about a component path can hide a defect.
    with tempfile.TemporaryDirectory(prefix='rbv-negative-') as tmp:
        root = Path(tmp).resolve()
        cfg = create(root, cases)
        cfg['docs'].append('src/search.py')
        cfg['components']['search']['paths'] = ['obsolete/search.py']
        (root / '.rbv.json').write_text(json.dumps(cfg))
        git(root, 'add', '.')
        git(root, '-c', 'user.name=RBV Benchmark', '-c', 'user.email=benchmark@example.invalid',
            '-c', 'core.hooksPath=', 'commit', '-qm', 'intentionally false reviewed mapping')
        p = root / 'src/search.py'
        p.write_text(p.read_text().replace('query.casefold()', 'query.lower()'))
        control_full = full_run(root, cfg)
        control_risk = run(root, '.rbv.json', no_cache=True)
        negative = {'description': 'Intentionally incorrect reviewed map labels runtime source as documentation.',
                    'full_detected': control_full['detected_defect'],
                    'selective_detected': any(r['status'] == 'failed' for r in control_risk['results']),
                    'selective_status': control_risk['status'],
                    'conclusion': 'Reviewed mappings are a trust boundary; file heuristics cannot prove safe omission.'}
    counts = lambda f: sum(f(r) for r in rows)
    full_seconds = counts(lambda r: r['full']['elapsed_seconds'])
    risk_seconds = counts(lambda r: r['selective']['elapsed_seconds'])
    full_commands = counts(lambda r: len(r['full']['results']))
    executed_commands = counts(lambda r: sum(not x['reused'] for x in r['selective']['results']))
    full_command_seconds = counts(lambda r: sum(x['duration_seconds'] for x in r['full']['results']))
    risk_command_seconds = counts(lambda r: r['selective']['executed_seconds'])
    source = {str(p.relative_to(ROOT)): file_hash(p) for p in [Path(__file__), ROOT / 'benchmarks/fixture.py', *sorted((ROOT / 'skills/risk-based-validation/scripts/rbv').glob('*.py'))]}
    return {'schema_version': 1, 'environment': {'python': sys.version, 'platform': platform.platform(),
            'git': subprocess.run(['git', '--version'], capture_output=True, text=True).stdout.strip()},
            'method': {'cases_per_group': cases, 'repetitions': repetitions, 'scenario_filter': scenario_names, 'source_hashes': source,
                       'timing': 'perf_counter; sequential actual subprocesses; raw full suite has no planner overhead; baseline prechecks and cache warmup excluded and disclosed',
                       'synthetic_fixture': True, 'network': False, 'artificial_sleeps': False},
            'summary': {'scenarios': len(rows), 'known_defects': counts(lambda r: r['known_defect']),
                        'full_detected': counts(lambda r: r['known_defect'] and r['full']['detected_defect']),
                        'selective_detected': counts(lambda r: r['known_defect'] and r['detected_defect']),
                        'missed_known_defects': counts(lambda r: r['missed_known_defect']),
                        'false_alarms': counts(lambda r: r['false_alarm']),
                        'full_commands': full_commands, 'executed_commands': executed_commands,
                        'command_reduction_fraction': 1 - executed_commands / full_commands,
                        'full_command_seconds': full_command_seconds, 'selective_command_seconds': risk_command_seconds,
                        'command_time_reduction_fraction': 1 - risk_command_seconds / full_command_seconds,
                        'full_wall_seconds': full_seconds, 'selective_wall_seconds': risk_seconds,
                        'wall_time_reduction_fraction': 1 - risk_seconds / full_seconds,
                        'excluded_warmup_seconds': counts(lambda r: r['warmup']['elapsed_seconds'] if r['warmup'] else 0)},
            'negative_control': negative, 'rows': rows}


def markdown(result):
    s = result['summary']
    lines = ['# Measured evaluation', '',
             'Synthetic executable fixture; these numbers are local observations, not production guarantees.', '',
             '| Scenario | Known defect | Full commands | Executed / reused | Defect detected (full / risk) | Full wall s | Risk wall s |',
             '|---|---:|---:|---:|---|---:|---:|']
    for row in result['rows']:
        r = row['selective']
        executed = sum(not x['reused'] for x in r['results'])
        reused = len(r['results']) - executed
        lines.append(f'| {row["scenario"]} #{row["repetition"] + 1} | {row["known_defect"]} | {len(row["full"]["results"])} | {executed} / {reused} | {row["full"]["detected_defect"]} / {row["detected_defect"]} | {row["full"]["elapsed_seconds"]:.3f} | {r["elapsed_seconds"]:.3f} |')
    lines.extend(['', f'Known defects detected: full {s["full_detected"]}/{s["known_defects"]}; risk {s["selective_detected"]}/{s["known_defects"]}. Misses: {s["missed_known_defects"]}; false alarms: {s["false_alarms"]}.', '',
                  f'Commands: {s["full_commands"]} → {s["executed_commands"]} ({s["command_reduction_fraction"]:.1%} reduction).',
                  f'Actual command time: {s["full_command_seconds"]:.3f}s → {s["selective_command_seconds"]:.3f}s ({s["command_time_reduction_fraction"]:.1%} reduction).',
                  f'End-to-end measured wall time: {s["full_wall_seconds"]:.3f}s → {s["selective_wall_seconds"]:.3f}s ({s["wall_time_reduction_fraction"]:.1%} reduction; negative means slower).', '',
                  f'Repeated-state warmup cost excluded from comparison: {s["excluded_warmup_seconds"]:.3f}s; raw warmup is retained in JSON. Baseline cleanliness prechecks are also excluded.', '',
                  'The negative control intentionally corrupts a reviewed mapping and labels runtime source as docs. The full suite detects its defect; selection misses it. This demonstrates the mapping trust boundary and is not included in the headline scenario counts.', '',
                  'No confidence interval is claimed. Small subprocess tests can be cheaper than Git analysis and snapshot hashing; inspect end-to-end time before adopting. Compare against real project workloads and periodically audit skips with a full run.', '',
                  f'Cases per group: {result["method"]["cases_per_group"]}; repetitions: {result["method"]["repetitions"]}; scenario filter: {result["method"]["scenario_filter"]}.', '',
                  'Reproduce with `python -m benchmarks.evaluate --cases N --repetitions R --output path.json`; optionally repeat `--scenario NAME` to restrict cases. Raw JSON contains environment, source hashes, exact commands, return codes, logs metadata, baseline identities and wall timings. Fixture paths are normalized for privacy. Temporary per-command logs are deleted with the fixture; full-suite stdout/stderr is embedded.'])
    return '\n'.join(lines) + '\n'


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--cases', type=int, default=1000)
    p.add_argument('--repetitions', type=int, default=1)
    p.add_argument('--output', type=Path, default=ROOT / 'benchmarks/results/local.json')
    p.add_argument('--scenario', action='append', choices=[s[0] for s in SCENARIOS])
    args = p.parse_args()
    if args.cases <= 0 or args.repetitions <= 0:
        p.error('cases and repetitions must be positive')
    result = evaluate(args.cases, args.repetitions, args.scenario)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    args.output.with_suffix('.md').write_text(markdown(result), encoding='utf-8')
    print(json.dumps(result['summary'], indent=2))
    return 1 if result['summary']['missed_known_defects'] or result['summary']['false_alarms'] else 0


if __name__ == '__main__':
    raise SystemExit(main())
