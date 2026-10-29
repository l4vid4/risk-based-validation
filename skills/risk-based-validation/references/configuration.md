# Configuration and CLI contract (v1)

Python 3.10+ and Git are required for the helper. Copy the whole skill, including `scripts/rbv`. No package installation, network access, hooks or model API is needed. From the Git root:

```sh
python /path/to/risk-based-validation/scripts/validate.py plan --repo . --config .rbv.json --base HEAD
python /path/to/risk-based-validation/scripts/validate.py run --repo . --execute
```

`--repo` must name the Git root. `HEAD` covers local staged/worktree/untracked changes only. For a pull request, compute `git merge-base <target-ref> HEAD`, inspect it, and pass that commit as `--base`. No fetch happens automatically. Initial repositories need a baseline commit. An invalid base/config fails closed.

## Minimal example

Replace commands and paths with actual repository checks. Do not copy invented commands into a plan.

```json
{
  "version": 1,
  "impact_reviewed": false,
  "docs": ["docs/*.md", "README.md"],
  "global": ["tools/*"],
  "components": {
    "core": {"paths": ["src/core/*"]},
    "api": {"paths": ["src/api/*"], "depends_on": ["core"]}
  },
  "protected": [
    {"name": "tenant boundaries", "paths": ["src/api/access.py"], "required_tags": ["security"]}
  ],
  "tests": [
    {"id": "core", "command": ["{python}", "-m", "unittest", "tests.test_core"], "components": ["core"], "inputs": ["tests/test_core.py"], "cost": 2},
    {"id": "api", "command": ["{python}", "-m", "unittest", "tests.test_api"], "components": ["api"], "inputs": ["tests/test_api.py"], "tags": ["security"], "cost": 5, "timeout": 60}
  ]
}
```

## Fields

Unknown keys, duplicate IDs, unknown components, invalid booleans, nonpositive/nonfinite costs, malformed patterns and commands are errors. Config is strict JSON, UTF-8 (BOM accepted). Top-level version must be integer `1`.

| Field | Default | Meaning |
|---|---|---|
| `impact_reviewed` | `false` | `false` forces all registered checks; `true` asserts complete, reviewed impact evidence. |
| `components` | `{}` | Each component has `paths` patterns and optional `depends_on` component IDs. Reverse transitive reachability selects consumers. Cycles terminate safely. |
| `tests` | required, nonempty | Inventory of meaningful verification commands, including relevant CI/repository obligations. Full means this inventory, not undiscovered tests. |
| `tests[].id` | required | Unique nonempty name; arbitrary names are hashed for output filenames. |
| `tests[].command` | required | Nonempty argv array. Exact argument `{python}` resolves to the current interpreter. No shell interpolation by the helper. |
| `tests[].components` | `[]` | Components this check validates. Include shared components if checked directly. |
| `tests[].inputs` | `[]` | Changed test files, fixtures or other inputs that select this check. Shared fixtures should select all consumers. |
| `tests[].tags` | `[]` | `always` runs regardless of impact. `security`/`data` satisfy built-in gates; custom gate tags are supported. |
| `tests[].cost` | `1` | Positive estimated relative execution cost. Orders checks; never removes required checks. Use seconds if estimates are available. |
| `tests[].timeout` | `300` | Maximum seconds per command. A timeout is unresolved failure, not a pass. |
| `tests[].cache` | `false` | Opt in only for deterministic, repeatable checks. Does not itself enable reuse. |
| `docs` | `[]` | Explicit non-runtime docs; never overrides owned paths, declared test inputs, global inputs or sensitive path rules. Avoid broad `*.md` exclusions for templates/spec-generated behavior. |
| `global` | `[]` | Additional full-inventory triggers; built-in lock/build/CI/policy rules remain active. |
| `protected` | `[]` | `{name, paths, required_tags}`. A match forces all checks fresh and requires a check tagged for every requested domain. |
| `extra_inputs` | `[]` | Patterns for ignored file inputs. Their contents enter snapshots. Because Git has no reliable change baseline for them, configuring these forces full selection. External tools/services still need a context identity. |

Patterns use Python `fnmatchcase`, case-sensitive on all platforms: `*` can span `/`; `**` has no special recursive meaning. `src/*` matches nested source paths, while `docs/*.md` does not match `README.md`. Use repository-relative paths and `/`, without `..`, drive letters or backslashes. This deliberately is not gitignore/pathspec syntax. Pattern ownership is additive, never first-match-wins.

## Decision behavior

Git evidence includes committed changes since base, staged changes since base, final worktree changes, untracked nonignored paths, renames as deletion+addition and deletions. Binary, non-UTF8, large or special inputs cause conservative selection. Symlinks/submodules disable reuse and force full selection; their external targets are not certified. Built-in path/content hints widen security/data validation but are not semantic analysis and cannot detect every sensitive change. The agent must inspect the diff and add domain checks when needed.

Unmapped non-documentation files, unreviewed maps, build/lock/CI/policy changes, and `--full` select the full inventory. A changed component without registered validation, or a required domain tag without a check, blocks execution and reports `incomplete`. A registered tag must correspond to real checks (e.g. cross-tenant denial and rollback invariants), not a placeholder command.

On any command failure/startup error/timeout, append all unexecuted inventory checks once. Checks already executed are not rerun. A passing later check cannot clear a failure. This gives bounded diagnosis at potentially higher cost on failing runs; use `--budget` when a hard wall limit is needed. No automatic retry, automatic repair, baseline checkout, network fetch or deployment occurs.

## Evidence and reuse

Add `.rbv/` to `.gitignore`. The helper excludes its own output even without that rule, and rejects tracked `.rbv` files and symlinked evidence directories. It holds an exclusive lock; after interruption inspect the recorded PID before manually removing a stale lock. Each run writes a JSON report and combined stdout/stderr logs below `.rbv/`.

Reuse requires both `cache: true` and a nonempty `--context` supplied by the caller. The context must identify dependency installation, toolchain/container, test data and any external state not represented by repository files. Rotate it whenever these change. Do not put secrets in commands or context tokens. Without a reliable identity, leave reuse off; prefer native hermetic build caches when available.

The key covers the entire tracked/nonignored worktree (not only guessed dependencies), config, base commit, root, engine source, Python/platform, hashed ambient environment, command and resolved executable content. It is conservative: even an unrelated README edit invalidates reuse. Passes only are reusable, logs must still exist and match their digest, TTL defaults to one hour and is capped at one day. High-risk or special-file plans always execute fresh. `--no-cache` forces fresh checks. A fresh failure revokes a previous pass.

A final content/config/base/environment check invalidates the whole run if state changed. Cache writes happen only after this check. Keep a single writer to the source tree during a run: endpoint hashing is not a sandbox or a continuous filesystem monitor and cannot detect transient changes that are reverted before the final snapshot. Snapshot cost is proportional to input bytes; very large repositories should use native input tracking. Git-ignored files outside `extra_inputs` and external state remain a caller responsibility. Results apply to the final worktree; a differing index version needs its own validation before commit.

`--budget SECONDS` includes planning and execution in the reported budget. It is an execution bound with subprocess timeouts, not an OS resource quota; planning/hashing and cleanup may overrun it. Exhaustion leaves required checks unresolved. Timeout cleanup targets the process group on POSIX and process tree on Windows; tests must not leave background services running after normal exit. Output logs go to disk and currently have no size quota. In the absence of a user budget, the per-command timeout and finite inventory bound the run.

## Output and exit status

`plan` prints JSON, runs no repository command, and writes no state. It exits `2` for blockers, `0` otherwise. A plan selects checks; it does not certify them.

`run --execute` regenerates the plan instead of trusting saved executable instructions. The JSON report includes inputs, risk/reasons, selected/skipped checks, actual durations, return codes, log digests, reuse flags, escalation, blockers and unresolved checks. Failed commands get diagnostic hints; classification is heuristic, so inspect original logs. Environment/context values are hashed, but commands and logs may contain sensitive material; do not commit evidence without review.

| Status | Exit | Meaning |
|---|---:|---|
| `passed` | 0 | All required selected/escalated checks passed on the recorded scope. |
| `no_checks_required` | 0 | Reviewed scope requires no commands; not a test pass. |
| `failed` | 1 | At least one executed check failed/errored/timed out; no budget/state blocker superseded it. |
| `incomplete` | 2 | Missing gate, budget exhaustion, state mutation or unresolved checks. Inspect results too: they may contain known failures. |
| `error` | 2 | Configuration/Git/execution-boundary error. Written to stderr as JSON. |

`--full --no-cache` provides a deliberate audit against the registered inventory. Schedule it through existing CI when appropriate; the helper does not replace mandated CI checks. Local evidence is editable by the repository owner and must not be treated as a signed CI attestation or shared between untrusted workspaces.
