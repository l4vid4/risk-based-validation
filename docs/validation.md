# Local validation record

Date: 2026-10-29, Asia/Shanghai. Exercised locally on Windows, Python 3.13.9, Git 2.49.0.windows.1. No remote CI run or other-platform pass is claimed.

## Automated behavior

The final tree discovers **36 unittest cases**. Relevant batches collectively exercised all final cases: **35 passed, 1 skipped**. The skipped case requires creating a Windows symlink, which this machine does not permit. Tracked-evidence rejection is a separate case and did pass.

Actual recorded runs:

| Command | Observed outcome | Purpose |
|---|---|---|
| `python -m unittest discover -s tests -t . -v` | 30 cases passed, 52.930s at that stage | Broad selection/execution/cache/CLI/distribution validation before final boundary additions. |
| `python -m unittest tests.test_boundaries tests.test_selection tests.test_cli tests.test_distribution -v` | 23 cases, one skipped, otherwise passed, 30.771s | Git policy changes, unresolved index, corrupt-config boundary, selection and portable install. |
| `python -m unittest tests.test_execution tests.test_boundaries -v` | 16 cases, one skipped, otherwise passed, 40.447s | Final execution/cache behavior and separated tracked/symlink evidence checks. |
| `python -m unittest tests.test_selection.SelectionTests.test_clock_named_source_is_not_a_dependency_lock tests.test_selection.SelectionTests.test_unreviewed_map_and_global_lock_force_full -v` | 2 passed, 2.642s | Narrow regression after refining lock-file patterns to avoid treating `clock.py` as a lock. |
| `python -X utf8 <skill-creator>/scripts/quick_validate.py skills/risk-based-validation` | `Skill is valid!` | Local Skill frontmatter/name/scaffold validation. |
| `python -m pip wheel --no-deps --no-build-isolation --wheel-dir .rbv/packages .` | Built `risk_based_validation-0.1.0-py3-none-any.whl` successfully | Validate actual source packaging without downloading runtime dependencies. |

The final wheel was then installed with `pip --no-index --no-deps --target .rbv/installed`. Its Python modules were compared byte-for-byte with the final source. With only that installed package on `PYTHONPATH`, an isolated temporary fixture successfully executed both `python -m rbv.cli plan` (selecting only the changed search check) and `run --execute` (passed). No global installation was changed.

The batches overlap; their counts must not be summed as independent coverage. Timing is observed wall time, not a performance guarantee. Added symlink and Git/index checks are not inferred to pass on platforms where they were skipped or never run.

## Why validation stopped

Tests cover observable decision and execution boundaries, including high-risk gates, cache identity, failure retention, budget/timeout outcomes and final-state invalidation. Subsequent lock-pattern edits received targeted tests rather than another identical full run. Documentation changes received content/link review. Benchmark reruns were justified by cross-cutting evidence-collection changes, and retain final source hashes.

The benchmark [raw data](../benchmarks/results/local.json) and [generated table](../benchmarks/results/local.md) record both direct full execution and risk-based execution. The additional [larger successful-workload comparison](../benchmarks/results/scale.md) separates a case where expensive unrelated checks dominate from the primary small-suite experiment. Interpret each workload separately; no universal speedup is asserted.

Open limitations remain explicit: one unexercised symlink case locally, unexecuted remote CI matrix, synthetic benchmark rather than production history, and no model/harness behavioral eval. These are reported confidence limits, not reasons to repeat unrelated tests.
