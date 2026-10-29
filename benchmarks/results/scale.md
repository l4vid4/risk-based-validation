# Measured evaluation

Synthetic executable fixture; these numbers are local observations, not production guarantees.

| Scenario | Known defect | Full commands | Executed / reused | Defect detected (full / risk) | Full wall s | Risk wall s |
|---|---:|---:|---:|---|---:|---:|
| local_refactor #1 | False | 6 | 1 / 0 | False / False | 7.207 | 1.117 |
| repeat_identical_state #1 | False | 6 | 0 / 1 | False / False | 6.330 | 0.720 |

Known defects detected: full 0/0; risk 0/0. Misses: 0; false alarms: 0.

Commands: 12 → 1 (91.7% reduction).
Actual command time: 13.537s → 0.161s (98.8% reduction).
End-to-end measured wall time: 13.537s → 1.837s (86.4% reduction; negative means slower).

Repeated-state warmup cost excluded from comparison: 0.804s; raw warmup is retained in JSON. Baseline cleanliness prechecks are also excluded.

The negative control intentionally corrupts a reviewed mapping and labels runtime source as docs. The full suite detects its defect; selection misses it. This demonstrates the mapping trust boundary and is not included in the headline scenario counts.

No confidence interval is claimed. Small subprocess tests can be cheaper than Git analysis and snapshot hashing; inspect end-to-end time before adopting. Compare against real project workloads and periodically audit skips with a full run.

Cases per group: 10000; repetitions: 1; scenario filter: ['local_refactor', 'repeat_identical_state'].

Reproduce with `python -m benchmarks.evaluate --cases N --repetitions R --output path.json`; optionally repeat `--scenario NAME` to restrict cases. Raw JSON contains environment, source hashes, exact commands, return codes, logs metadata, baseline identities and wall timings. Fixture paths are normalized for privacy. Temporary per-command logs are deleted with the fixture; full-suite stdout/stderr is embedded.
