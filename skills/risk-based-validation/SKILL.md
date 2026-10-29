---
name: risk-based-validation
description: Choose proportionate verification after a bug fix, feature, or refactor using the actual diff, reviewed impact evidence, regression risk, and test cost. Select checks, diagnose failures, reuse valid evidence, and stop when justified. Use for post-change validation; preserve explicit repository and user requirements.
license: MIT
---

# Risk-based validation

Match verification effort to the consequences of being wrong. A small diff can carry high risk. Test count alone is never the success metric.

The optional local helper requires Python 3.10+ and Git, with no third-party Python runtime packages.

1. Read applicable repository instructions and the task acceptance criteria. Identify required checks before optimizing. Inspect the final diff against the intended base, plus staged and untracked files. For a PR, resolve its merge base explicitly; `HEAD` only covers local edits. A missing base or incomplete evidence is unresolved, not low risk.
2. Identify changed behavior, callers, contracts, shared fixtures, generated assets, configuration, and external state. Inspect reverse dependencies and relevant regression tests. Prefer the project's native impact tools (Nx, Bazel, testmon, etc.) when their evidence is adequate. The bundled CLI uses reviewed explicit component maps; it does not infer imports or prove completeness.
3. Choose checks that can actually detect failure modes: regression assertions for fixes; normal and boundary/error paths for features; consumers/contracts for refactors. Permissions, tenant isolation, secrets, payments, persistence and migrations require domain checks, including denial/rollback/recovery paths where applicable. Do not weaken tests or mappings to obtain a cheaper plan.
4. Reuse valid results where possible. Record command, final input identity, environment, outcome, and log evidence. Reuse only successful, deterministic checks with equivalent inputs and context. External services, clocks, ignored dependencies, changed toolchains and random failures invalidate reuse unless explicitly accounted for. Fresh high-risk checks are mandatory in the CLI.
5. Run the cheapest useful checks first. Expand for unknown impact, unreviewed mappings, global inputs, high-risk changes or failures. Inspect failure logs and baseline; distinguish product/test defects from harness or infrastructure failures, then act on new evidence. Never retry an unchanged failure merely hoping for green. Do not hide a flaky failure behind a later pass.
6. Stop when required checks have valid passing evidence, relevant failure modes have been covered, and no unexplained failure or material risk remains. If cost limits prevent required checks, report incomplete validation. Additional full runs need a reason: new changes, new failure evidence, an explicit requirement, or a planned audit of selection quality.

## Optional deterministic helper

Use `<skill-dir>/scripts/validate.py` from the target repository. Read [configuration and CLI](references/configuration.md) before creating or changing `.rbv.json`. Register actual repository commands and review their meaning; a tag is a maintainer assertion, not proof of coverage.

```sh
python <skill-dir>/scripts/validate.py plan --repo . --base HEAD
python <skill-dir>/scripts/validate.py run --repo . --base HEAD --execute
```

Review the plan and command arrays before execution. `--execute` expresses execution intent; it grants no permissions and adds no sandbox. Proceed within already authorized scope; do not insert a new human approval step for normal permitted tests. Commands are repository code and inherit the caller's permissions. Never bypass a denied action or contact production services without authorization.

If no usable configuration exists, use the reasoning workflow and native tools directly, or create a small unreviewed inventory (`impact_reviewed: false`) that conservatively runs registered checks. Mark the map reviewed only after checking paths, reverse dependencies, shared fixtures, dynamic loading and documentation exclusions. Keep uncertainty visible.

## Report

State the changed behavior and risk, checks executed or reused with outcomes, deliberately skipped checks and reasons, unresolved failures, residual risks, and why verification stopped. Separate “no checks required”, “passed”, “failed”, and “incomplete”. A passing selection applies to the final worktree and reviewed scope, not every possible defect or a differing staged version. Use [decision and failure examples](references/decisions.md) when impact or stopping is unclear.
