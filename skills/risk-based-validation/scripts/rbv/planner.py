"""Explainable selection. Gates are constraints; estimated cost only orders commands."""
import re
from pathlib import Path

from .config import load_config, matches
from .repository import changes, changed_text, digest, git, names, root_path, snapshot, state_path

GLOBAL = ['**/package.json', 'package.json', '*.lock', '**/*.lock', 'package-lock.json',
          '**/package-lock.json', 'npm-shrinkwrap.json', '**/npm-shrinkwrap.json',
          'pnpm-lock.yaml', '**/pnpm-lock.yaml', 'go.sum', '**/go.sum', 'pyproject.toml',
          '**/pyproject.toml', '*requirements*.txt', '**/*requirements*.txt', 'setup.cfg',
          'setup.py', 'conftest.py', '**/conftest.py', 'pytest.ini', 'tox.ini',
          '.github/*', '.gitignore', '.gitmodules', 'Dockerfile*', '**/Dockerfile*',
          'Makefile', '**/Makefile', 'tsconfig*.json', '**/tsconfig*.json',
          'Cargo.toml', '**/Cargo.toml', 'go.mod', '**/go.mod', '*rbv*.json',
          'AGENTS.md', '**/AGENTS.md', 'AGENTS.override.md', '**/AGENTS.override.md']
SECURITY_PATH = re.compile(r'(^|[/_.-])(auth\w*|secur\w*|permission\w*|acl|rbac|crypto\w*|secret\w*|token\w*)([/_.-]|$)', re.I)
DATA_PATH = re.compile(r'(^|[/_.-])(migrat\w*|schema\w*|transaction\w*|payment\w*|ledger\w*|persist\w*)([/_.-]|$)|\.sql$', re.I)
SECURITY_TEXT = re.compile(r'\b(authoriz\w*|authenticat\w*|permission\w*|password\w*|verify_token|check_access|jwt|csrf|encrypt\w*|decrypt\w*)\b', re.I)
DATA_TEXT = re.compile(r'\b(BEGIN TRANSACTION|COMMIT|ROLLBACK|ALTER TABLE|DROP TABLE|DELETE FROM|transaction\w*|idempotenc\w*)\b', re.I)


def make_plan(repo, config, base='HEAD', force_full=False):
    root = root_path(repo)
    state_path(root)
    cfg_path = Path(config)
    if not cfg_path.is_absolute():
        cfg_path = root / cfg_path
    cfg = load_config(cfg_path)
    resolved, changed = changes(root, base)
    snap, hazards = snapshot(root, cfg['extra_inputs'])
    texts, uncertain = changed_text(root, resolved, changed)
    all_tests = {t['id']: t for t in cfg['tests']}
    selected = {}
    reasons = []
    blockers = []
    conflicts = names(git(root, 'ls-files', '-z', '--unmerged'))
    if conflicts:
        blockers.append('unresolved merge conflicts; resolve the index before validation')
    gates = set()
    affected = set()
    unknown = []
    docs = []
    full = force_full or not cfg['impact_reviewed']
    if force_full:
        reasons.append('full inventory explicitly requested')
    if not cfg['impact_reviewed']:
        reasons.append('impact mapping has not been reviewed')
    if cfg['extra_inputs']:
        full = True
        reasons.append('extra inputs have no reliable Git change baseline; select full inventory')
    if hazards or uncertain:
        full = True
        reasons.extend(hazards)
        if uncertain:
            reasons.append('opaque/large/non-UTF8 changes: ' + ', '.join(uncertain))

    def select(test_id, why):
        selected.setdefault(test_id, []).append(why)

    for path in changed:
        owned = {name for name, c in cfg['components'].items() if matches(path, c['paths'])}
        affected.update(owned)
        input_tests = [t for t in cfg['tests'] if matches(path, t['inputs'])]
        for t in input_tests:
            select(t['id'], f'declared input changed: {path}')
        sensitive = False
        if SECURITY_PATH.search(path):
            gates.add('security')
            sensitive = True
        if DATA_PATH.search(path):
            gates.add('data')
            sensitive = True
        for rule in cfg['protected']:
            if matches(path, rule['paths']):
                gates.update(rule['required_tags'])
                sensitive = True
                reasons.append(f"protected rule: {rule['name']} ({path})")
        is_config = cfg_path.is_relative_to(root) and path == cfg_path.relative_to(root).as_posix()
        if matches(path, GLOBAL + cfg['global']) or is_config:
            full = True
            reasons.append(f'global/build/policy input: {path}')
        elif not owned and not input_tests and not sensitive:
            if matches(path, cfg['docs']):
                docs.append(path)
            else:
                unknown.append(path)
    for path, value in texts:
        # Explicit documentation paths suppress content hints only when unowned.
        if path in docs:
            continue
        if SECURITY_TEXT.search(value):
            gates.add('security')
            reasons.append(f'security content hint: {path}')
        if DATA_TEXT.search(value):
            gates.add('data')
            reasons.append(f'data consistency content hint: {path}')
    if unknown:
        full = True
        reasons.append('unmapped changes: ' + ', '.join(unknown))
    # Reverse transitive closure: consumers of a changed component are affected.
    while True:
        more = {name for name, c in cfg['components'].items() if set(c['depends_on']) & affected}
        new = more - affected
        if not new:
            break
        affected.update(new)
    for t in cfg['tests']:
        overlap = set(t['components']) & affected
        if overlap:
            select(t['id'], 'affected components: ' + ', '.join(sorted(overlap)))
        if 'always' in t['tags']:
            select(t['id'], 'repository always-run check')
    for component in sorted(affected):
        if not any(component in t['components'] for t in cfg['tests']):
            blockers.append(f'no registered validation for affected component: {component}')
            full = True
    if gates:
        full = True
        reasons.append('high-risk gates require fresh full inventory')
        for tag in sorted(gates):
            if not any(tag in t['tags'] for t in cfg['tests']):
                blockers.append(f'missing required validation tag: {tag}')
    if full:
        for tid in all_tests:
            select(tid, 'conservative full inventory')
    order = sorted(selected, key=lambda tid: (0 if gates & set(all_tests[tid]['tags']) else 1, all_tests[tid]['cost'], tid))
    return {
        'schema_version': 1, 'root': str(root), 'base': resolved, 'snapshot': snap,
        'config_hash': digest(cfg), 'risk': 'high' if gates else ('conservative' if full else ('targeted' if affected or selected else 'minimal')),
        'changed': changed, 'affected_components': sorted(affected), 'required_tags': sorted(gates),
        'reasons': reasons, 'blockers': blockers, 'hazards': hazards, 'docs_only_paths': docs,
        'selected': [dict(all_tests[tid], reasons=selected[tid]) for tid in order],
        'skipped': [{'id': tid, 'reason': 'outside reviewed impact map; no changed declared inputs'} for tid in all_tests if tid not in selected],
        'estimated_cost': sum(all_tests[tid]['cost'] for tid in selected),
        'full_cost': sum(t['cost'] for t in cfg['tests']),
        'config': cfg,
    }
