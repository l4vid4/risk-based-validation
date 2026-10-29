"""Strict, deliberately small configuration contract."""
import fnmatch
import json
import math
from pathlib import Path, PurePosixPath


class ValidationError(Exception):
    """An actionable configuration, repository or execution boundary error."""


def matches(path, patterns):
    # fnmatch is explicitly case-sensitive on every OS; * can span directories.
    return any(fnmatch.fnmatchcase(path, p) for p in patterns)


def strings(value, label, nonempty=False):
    if not isinstance(value, list) or any(not isinstance(x, str) or not x for x in value):
        raise ValidationError(f"{label} must be an array of nonempty strings")
    if nonempty and not value:
        raise ValidationError(f"{label} cannot be empty")
    return value


def patterns(value, label):
    strings(value, label)
    for p in value:
        if p.startswith('/') or '\\' in p or ':' in p or '..' in PurePosixPath(p).parts:
            raise ValidationError(f"{label}: use repository-relative forward-slash patterns: {p}")
    return value


def keys(obj, allowed, label):
    if not isinstance(obj, dict) or set(obj) - set(allowed):
        raise ValidationError(f"{label}: expected object with keys {', '.join(allowed)}")


def positive(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
        raise ValidationError(f"{label} must be a positive finite number")


def load_config(path):
    try:
        cfg = json.loads(Path(path).read_text(encoding='utf-8-sig'))
    except (OSError, ValueError) as e:
        raise ValidationError(f"Cannot read config {path}: {e}") from e
    keys(cfg, ['version', 'impact_reviewed', 'components', 'tests', 'docs', 'global', 'protected', 'extra_inputs'], 'config')
    if type(cfg.get('version')) is not int or cfg['version'] != 1:
        raise ValidationError('config.version must be 1')
    if type(cfg.get('impact_reviewed', False)) is not bool:
        raise ValidationError('impact_reviewed must be boolean')
    cfg.setdefault('impact_reviewed', False)
    for k in ('docs', 'global', 'extra_inputs'):
        patterns(cfg.setdefault(k, []), k)
    components = cfg.setdefault('components', {})
    if not isinstance(components, dict):
        raise ValidationError('components must be an object')
    for name, c in components.items():
        if not name:
            raise ValidationError('component names cannot be empty')
        keys(c, ['paths', 'depends_on'], f'component {name}')
        patterns(c.setdefault('paths', []), f'{name}.paths')
        strings(c.setdefault('depends_on', []), f'{name}.depends_on')
        if set(c['depends_on']) - components.keys():
            raise ValidationError(f'{name}: unknown dependency')
    # Cycles are supported: reverse reachability uses a visited set.
    tests = cfg.get('tests')
    if not isinstance(tests, list) or not tests:
        raise ValidationError('tests must be a nonempty array; register the repository verification commands')
    seen = set()
    for t in tests:
        keys(t, ['id', 'command', 'components', 'inputs', 'tags', 'cost', 'timeout', 'cache'], 'test')
        name = t.get('id')
        if not isinstance(name, str) or not name or name in seen:
            raise ValidationError('test IDs must be nonempty and unique')
        seen.add(name)
        strings(t.get('command'), f'{name}.command', True)
        strings(t.setdefault('components', []), f'{name}.components')
        if set(t['components']) - components.keys():
            raise ValidationError(f'{name}: unknown component')
        patterns(t.setdefault('inputs', []), f'{name}.inputs')
        strings(t.setdefault('tags', []), f'{name}.tags')
        positive(t.setdefault('cost', 1), f'{name}.cost')
        positive(t.setdefault('timeout', 300), f'{name}.timeout')
        if type(t.setdefault('cache', False)) is not bool:
            raise ValidationError(f'{name}.cache must be boolean')
    protected = cfg.setdefault('protected', [])
    if not isinstance(protected, list):
        raise ValidationError('protected must be an array')
    for p in protected:
        keys(p, ['name', 'paths', 'required_tags'], 'protected rule')
        if not isinstance(p.get('name'), str) or not p['name']:
            raise ValidationError('protected.name must be nonempty')
        patterns(p.get('paths'), 'protected.paths')
        strings(p.get('required_tags'), 'protected.required_tags', True)
    return cfg
