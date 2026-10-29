"""Local execution and conservative evidence reuse. Commands are never shell strings."""
import hashlib
import json
import math
import os
import platform
import shutil
import signal
import subprocess
import sys
import time
import uuid
from pathlib import Path

from . import __version__
from .config import ValidationError, load_config
from .planner import make_plan
from .repository import digest, git, snapshot, state_path


def file_hash(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda: f.read(1024 * 1024), b''):
            h.update(b)
    return h.hexdigest()


def safe_dir(path):
    if path.is_symlink() or (path.exists() and not path.is_dir()) or path.resolve() != path:
        raise ValidationError(f'Not a real evidence directory: {path}')
    path.mkdir(parents=True, exist_ok=True)
    return path


def atomic_json(path, value):
    if path.is_symlink():
        raise ValidationError(f'Refusing symlink output: {path}')
    temp = path.with_name(path.name + '.' + uuid.uuid4().hex + '.tmp')
    try:
        with temp.open('x', encoding='utf-8') as f:
            json.dump(value, f, ensure_ascii=True, indent=2, allow_nan=False)
            f.write('\n')
        os.replace(temp, path)
    finally:
        if temp.exists():
            temp.unlink()


def environment_key(context):
    # Only digests are persisted. Full env avoids omissions in hand-maintained allowlists.
    source = {p.name: file_hash(p) for p in Path(__file__).parent.glob('*.py')}
    return digest({'context': context, 'env': dict(os.environ), 'platform': platform.platform(),
                   'python': sys.version, 'executable': sys.executable, 'engine': source})


def command_args(test):
    return [sys.executable if a == '{python}' else a for a in test['command']]


def evidence_key(plan, test, context_key):
    args = command_args(test)
    executable = shutil.which(args[0])
    executable_hash = file_hash(executable) if executable and Path(executable).is_file() else None
    return digest({'snapshot': plan['snapshot'], 'base': plan['base'], 'root': plan['root'],
                   'config': plan['config_hash'], 'test': test, 'environment': context_key,
                   'executable': executable, 'executable_hash': executable_hash})


def read_cached(path, key, root, ttl):
    try:
        if path.is_symlink():
            return None
        record = json.loads(path.read_text(encoding='utf-8'))
        age = time.time() - record['finished_at']
        log = root / record['log']
        if not log.resolve().is_relative_to(state_path(root)) or log.is_symlink():
            return None
        if (record['key'] == key and record['status'] == 'passed' and record['returncode'] == 0
                and isinstance(record['duration_seconds'], (int, float)) and 0 <= age <= ttl
                and file_hash(log) == record['log_hash']):
            return record
    except (OSError, ValueError, TypeError, KeyError):
        pass
    return None


def stop_process(process):
    if os.name == 'nt':
        # Native argv, fixed switches, no shell. Include descendants on timeout/interruption.
        subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                       creationflags=subprocess.CREATE_NO_WINDOW)
    else:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    if process.poll() is None:
        process.kill()
    process.wait()


def execute(test, root, log, remaining):
    started = time.perf_counter()
    status = 'error'
    returncode = None
    timeout = min(test['timeout'], remaining) if remaining is not None else test['timeout']
    with log.open('xb') as output:
        try:
            options = {'creationflags': subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW} if os.name == 'nt' else {'start_new_session': True}
            process = subprocess.Popen(command_args(test), cwd=root, stdout=output, stderr=subprocess.STDOUT,
                                       stdin=subprocess.DEVNULL, shell=False, **options)
            try:
                returncode = process.wait(timeout=timeout)
                status = 'passed' if returncode == 0 else 'failed'
            except subprocess.TimeoutExpired:
                stop_process(process)
                status = 'timeout'
            except BaseException:
                stop_process(process)
                raise
        except OSError as e:
            output.write(str(e).encode('utf-8', 'replace'))
    diagnosis = None
    if status == 'timeout':
        diagnosis = 'timeout: unresolved; inspect deadlock, infrastructure, and budget before retrying'
    elif status == 'error':
        diagnosis = 'command startup error: inspect executable, environment, and configuration'
    elif status == 'failed':
        with log.open('rb') as f:
            f.seek(max(0, log.stat().st_size - 8192))
            tail = f.read().decode('utf-8', 'replace')
        if any(hint in tail for hint in ('ModuleNotFoundError', 'command not found', 'ConnectionRefusedError')):
            diagnosis = 'possible harness/infrastructure failure (heuristic); inspect log before classifying'
        else:
            diagnosis = 'nonzero exit: possible product or test defect; inspect assertions and baseline'
    return {'id': test['id'], 'status': status, 'returncode': returncode, 'diagnosis': diagnosis,
            'duration_seconds': time.perf_counter() - started,
            'log': log.relative_to(root).as_posix(), 'log_hash': file_hash(log),
            'finished_at': time.time(), 'reused': False}


def run(repo, config, base='HEAD', *, context=None, budget=None, no_cache=False, full=False, ttl=3600):
    if budget is not None and (budget <= 0 or not math.isfinite(budget)):
        raise ValidationError('budget must be positive and finite')
    if not 0 < ttl <= 86400:
        raise ValidationError('cache TTL must be between 0 and 86400 seconds')
    started = time.perf_counter()
    plan = make_plan(repo, config, base, full)
    root = Path(plan['root'])
    state = safe_dir(state_path(root))
    lock = state / 'lock'
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as e:
        raise ValidationError('Another run holds .rbv/lock; inspect its PID before removing a stale lock') from e
    with os.fdopen(fd, 'w') as f:
        f.write(str(os.getpid()))
    try:
        return _run_locked(root, state, plan, config, base, context, budget, no_cache, ttl, started)
    finally:
        lock.unlink()


def _run_locked(root, state, plan, config, base, context, budget, no_cache, ttl, started):
    run_id = uuid.uuid4().hex
    logs = safe_dir(safe_dir(state / 'logs') / run_id)
    cache = safe_dir(state / 'cache')
    reports = safe_dir(state / 'reports')
    context_key = environment_key(context)
    results = []
    pending = []
    escalated = False
    cache_allowed = bool(context) and not no_cache and not plan['required_tags'] and not plan['hazards']
    queue = list(plan['selected'])
    blockers = list(plan['blockers'])
    invalidated = False

    def stable():
        try:
            cfg_path = Path(config) if Path(config).is_absolute() else root / config
            current, _ = snapshot(root, plan['config']['extra_inputs'])
            current_base = git(root, 'rev-parse', '--verify', '--end-of-options', base + '^{commit}').decode().strip()
            return (current == plan['snapshot'] and current_base == plan['base']
                    and digest(load_config(cfg_path)) == plan['config_hash']
                    and environment_key(context) == context_key)
        except (ValidationError, OSError, ValueError):
            return False

    while queue and not blockers:
        test = queue.pop(0)
        remaining = budget - (time.perf_counter() - started) if budget is not None else None
        if remaining is not None and remaining <= 0:
            queue.insert(0, test)
            blockers.append('validation budget exhausted; required checks remain unresolved')
            break
        cache_path = cache / (digest(test['id']) + '.json')
        key = evidence_key(plan, test, context_key)
        previous = read_cached(cache_path, key, root, ttl) if cache_allowed and test['cache'] else None
        if previous:
            result = dict(previous, reused=True, duration_seconds=0, original_duration_seconds=previous['duration_seconds'])
        else:
            log = logs / (str(len(results)) + '.log')
            result = execute(test, root, log, remaining)
            result['key'] = key
            # A later failure MUST erase a prior success, even on a forced fresh run.
            if cache_path.exists() or cache_path.is_symlink():
                cache_path.unlink()
            if result['status'] == 'passed' and cache_allowed and test['cache']:
                pending.append((cache_path, result))
        results.append(result)
        if result['status'] != 'passed':
            escalated = True
            done = {r['id'] for r in results}
            queued = {t['id'] for t in queue}
            more = [dict(t, reasons=['expanded after failure; diagnose before any retry'])
                    for t in plan['config']['tests'] if t['id'] not in done | queued]
            queue.extend(sorted(more, key=lambda t: (t['cost'], t['id'])))
    if not stable():
        invalidated = True
        blockers.append('final state differs from validated state; results cannot certify current files')
    failed = any(r['status'] != 'passed' for r in results)
    if not invalidated:
        for path, record in pending:
            atomic_json(path, record)
    unresolved = [t['id'] for t in queue]
    status = 'incomplete' if blockers or unresolved else ('failed' if failed else 'passed')
    if not results and status == 'passed':
        status = 'no_checks_required'
    report = {'schema_version': 1, 'engine_version': __version__, 'run_id': run_id,
              'status': status, 'plan': {k: v for k, v in plan.items() if k != 'config'},
              'results': results, 'escalated': escalated, 'blockers': list(dict.fromkeys(blockers)),
              'unresolved': unresolved, 'invalidated': invalidated,
              'cache_enabled': cache_allowed, 'context_hash': digest(context) if context else None,
              'elapsed_seconds': time.perf_counter() - started,
              'executed_seconds': sum(r['duration_seconds'] for r in results if not r['reused']),
              'diagnosis': 'Inspect failure logs; distinguish product defects, harness/config errors, and infrastructure. Do not retry unchanged failures or treat a later pass as resolving flakiness.' if failed else None,
              'limitations': ['Selection depends on reviewed mappings and registered checks; it is not a proof of correctness.',
                              'Ignored files require extra_inputs; external state and toolchains require a caller-maintained context token.',
                              'Local evidence is not a trusted CI attestation.']}
    report_path = reports / (run_id + '.json')
    atomic_json(report_path, report)
    report['report_path'] = str(report_path)
    return report
