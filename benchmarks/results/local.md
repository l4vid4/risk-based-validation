# Measured evaluation

Synthetic executable fixture; these numbers are local observations, not production guarantees.

| Scenario | Known defect | Full commands | Executed / reused | Defect detected (full / risk) | Full wall s | Risk wall s |
|---|---:|---:|---:|---|---:|---:|
| docs_only #1 | False | 6 | 0 / 0 | False / False | 1.122 | 1.070 |
| local_refactor #1 | False | 6 | 1 / 0 | False / False | 1.543 | 1.142 |
| local_bug #1 | True | 6 | 6 / 0 | True / True | 1.693 | 2.761 |
| pricing_bug #1 | True | 6 | 6 / 0 | True / True | 2.611 | 3.239 |
| shared_dependency_bug #1 | True | 6 | 6 / 0 | True / True | 1.485 | 2.283 |
| tenant_isolation_bug #1 | True | 6 | 6 / 0 | True / True | 1.397 | 2.051 |
| atomicity_bug #1 | True | 6 | 6 / 0 | True / True | 0.658 | 1.523 |
| unmapped_loader_bug #1 | True | 6 | 6 / 0 | True / True | 1.284 | 1.997 |
| dependency_lock_change #1 | False | 6 | 6 / 0 | False / False | 1.142 | 2.028 |
| deleted_component #1 | True | 6 | 6 / 0 | True / True | 0.652 | 1.662 |
| unreviewed_mapping #1 | True | 6 | 6 / 0 | True / True | 1.143 | 2.189 |
| repeat_identical_state #1 | False | 6 | 0 / 1 | False / False | 1.571 | 0.812 |

Known defects detected: full 8/8; risk 8/8. Misses: 0; false alarms: 0.

Commands: 72 → 55 (23.6% reduction).
Actual command time: 16.300s → 12.213s (25.1% reduction).
End-to-end measured wall time: 16.300s → 22.757s (-39.6% reduction; negative means slower).

Repeated-state warmup cost excluded from comparison: 1.010s; raw warmup is retained in JSON. Baseline cleanliness prechecks are also excluded.

The negative control intentionally corrupts a reviewed mapping and labels runtime source as docs. The full suite detects its defect; selection misses it. This demonstrates the mapping trust boundary and is not included in the headline scenario counts.

No confidence interval is claimed. Small subprocess tests can be cheaper than Git analysis and snapshot hashing; inspect end-to-end time before adopting. Compare against real project workloads and periodically audit skips with a full run.

Cases per group: 1000; repetitions: 1; scenario filter: None.

Reproduce with `python -m benchmarks.evaluate --cases N --repetitions R --output path.json`; optionally repeat `--scenario NAME` to restrict cases. Raw JSON contains environment, source hashes, exact commands, return codes, logs metadata, baseline identities and wall timings. Fixture paths are normalized for privacy. Temporary per-command logs are deleted with the fixture; full-suite stdout/stderr is embedded.
