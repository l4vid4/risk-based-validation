"""Git evidence: final worktree plus staged changes, including deletions/untracked files."""
import hashlib
import json
import os
import stat
import subprocess
from pathlib import Path

from .config import ValidationError, matches


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=True, separators=(',', ':')).encode()).hexdigest()


def git(root, *args):
    env = dict(os.environ, GIT_OPTIONAL_LOCKS='0', GIT_NO_LAZY_FETCH='1')
    p = subprocess.run(['git', '-c', 'core.fsmonitor=false', '-C', str(root), *args],
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
    if p.returncode:
        raise ValidationError(p.stderr.decode('utf-8', 'replace').strip())
    return p.stdout


def names(data):
    return [os.fsdecode(p) for p in data.split(b'\0') if p]


def root_path(path):
    root = Path(os.fsdecode(git(path, 'rev-parse', '--show-toplevel')).strip()).resolve()
    if Path(path).resolve() != root:
        raise ValidationError(f'--repo must be the Git root: {root}')
    return root


def state_path(root):
    p = root / '.rbv'
    if p.is_symlink() or (p.exists() and not p.is_dir()) or p.resolve() != p:
        raise ValidationError('.rbv must be a real directory inside the repository')
    return p


def inventory(root, extra_inputs=()):
    paths = set(names(git(root, 'ls-files', '-z', '--cached', '--others', '--exclude-standard')))
    for pattern in extra_inputs:
        # Extra inputs can include ignored fixtures/config, but never outside the repo.
        for p in root.glob(pattern):
            if p.is_file() or p.is_symlink():
                paths.add(p.relative_to(root).as_posix())
    # Output state cannot overlap with tracked source.
    tracked_state = names(git(root, 'ls-files', '-z', '--', '.rbv'))
    if tracked_state:
        raise ValidationError('.rbv contains tracked files; move evidence out of source control')
    return sorted(p for p in paths if p != '.rbv' and not p.startswith('.rbv/'))


def snapshot(root, extra_inputs=()):
    items = []
    hazards = []
    for name in inventory(root, extra_inputs):
        p = root / name
        try:
            mode = p.lstat().st_mode
            if stat.S_ISLNK(mode):
                hazards.append(f'symlink input: {name}')
                value = ['symlink', os.readlink(p)]
            elif stat.S_ISREG(mode):
                h = hashlib.sha256()
                with p.open('rb') as f:
                    for block in iter(lambda: f.read(1024 * 1024), b''):
                        h.update(block)
                value = ['file', bool(mode & stat.S_IXUSR), h.hexdigest()]
            else:
                hazards.append(f'non-regular input (possibly submodule): {name}')
                value = ['special']
        except FileNotFoundError:
            value = ['deleted']
        items.append([name, value])
    return digest(items), hazards


def changes(root, base):
    # Explicit commit resolution avoids ambiguous revisions and path injection.
    resolved = git(root, 'rev-parse', '--verify', '--end-of-options', base + '^{commit}').decode().strip()
    args = ['--name-only', '-z', '--no-renames', '--no-ext-diff', '--no-textconv']
    changed = set(names(git(root, 'diff', *args, resolved, '--')))
    changed.update(names(git(root, 'diff', '--cached', *args, resolved, '--')))
    changed.update(names(git(root, 'ls-files', '-z', '--others', '--exclude-standard')))
    changed = sorted(p for p in changed if p != '.rbv' and not p.startswith('.rbv/'))
    return resolved, changed


def changed_text(root, base, paths):
    """Bounded hints only: unknown/binary/large changes widen selection, never prove safety."""
    text = []
    uncertain = []
    for name in paths:
        p = root / name
        if p.is_symlink() or p.is_dir():
            uncertain.append(name)
            continue
        if p.exists() and p.stat().st_size > 1_000_000:
            uncertain.append(name)
            continue
        # Both staged and worktree diffs matter; use added AND removed lines.
        chunks = [git(root, 'diff', '--no-ext-diff', '--no-textconv', '--unified=0', base, '--', name),
                  git(root, 'diff', '--cached', '--no-ext-diff', '--no-textconv', '--unified=0', base, '--', name)]
        if name in names(git(root, 'ls-files', '-z', '--others', '--exclude-standard', '--', name)):
            chunks.append(p.read_bytes() if p.exists() else b'')
        raw = b'\n'.join(chunks)
        if len(raw) > 2_000_000 or b'\0' in raw or b'Binary files ' in raw:
            uncertain.append(name)
            continue
        try:
            value = raw.decode('utf-8')
        except UnicodeDecodeError:
            uncertain.append(name)
            continue
        text.append((name, '\n'.join(line for line in value.splitlines() if line.startswith(('+', '-')) and not line.startswith(('+++', '---')))))
        # Untracked content does not have diff prefixes.
        if len(chunks) == 3:
            text.append((name, chunks[-1].decode('utf-8', 'replace')))
    return text, uncertain
