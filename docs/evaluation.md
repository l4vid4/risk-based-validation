# Evaluation protocol and interpretation

The generated [local table](../benchmarks/results/local.md) and [raw JSON](../benchmarks/results/local.json) are the measured record. Do not treat projected or illustrative numbers as results. The raw file includes environment and hashes of the engine and benchmark sources used; compare hashes after local edits.

## Observed results on this machine

| Experiment | Known defects (full / selected) | Command execution time | End-to-end wall time | Interpretation |
|---|---|---|---|---|
| Primary 12 scenarios, 1,000 cases/group | 8/8 and 8/8; no primary miss or false alarm | 16.300s → 12.213s (25.1% lower) | 16.300s → 22.757s (39.6% higher) | Analysis costs dominate small checks, especially the deliberately failure-heavy workload. Commands 72 → 55. |
| Two successful scenarios, 10,000 cases/group | No injected defects in these two scenarios | 13.537s → 0.161s | 13.537s → 1.837s (86.4% lower) | Avoiding unrelated SQLite batch checks has measurable value. This is a restricted successful workload, not another defect-detection claim. |

The [larger workload record](../benchmarks/results/scale.json) and [table](../benchmarks/results/scale.md) use exactly `local_refactor` and `repeat_identical_state`. Their excluded cache warmup is 0.804s; including it makes selected total wall cost 2.640s rather than 1.837s. Primary warmup excluded is 1.010s. No confidence interval or universal speedup is claimed from single repetitions. The additional intentionally false-map negative control misses a known defect, as described below.

## Correctness checks

The standard-library unittest suite exercises temporary Git repositories and real commands: reverse transitive selection, additive ownership, docs exclusions, changed tests, unknown/binary files, locks, staged/PR/rename/deletion evidence, cyclic dependencies, sensitive path/content gates, missing checks, strict configuration, CLI exit codes and read-only planning.

Execution checks cover successful exact-state reuse, context/environment/config/content/ignored-input invalidation, expiry/corruption/tampered logs, fresh high-risk execution, failure expansion without repeats, missing executables, timeouts, budgets, changed-source invalidation, exclusive locks, argv handling and report privacy. Tests assert observable decisions and execution outcomes, not generated prose.

Implementation validation itself follows risk: run an initial complete small suite, then focused regressions for changes/failures. Repeating the complete suite is justified only when cross-cutting engine changes make prior results insufficient. Document actual run evidence in [validation.md](validation.md), without claiming unexecuted remote CI results.

## Full-suite comparison

`benchmarks.fixture` creates an executable multi-component Python application with pricing/cart consumers, shared helpers, tenant access, SQLite atomic transfers, Unicode search and a JSON loader. Six commands run real assertions over a configurable deterministic batch. There are no artificial sleeps. Every scenario verifies its clean baseline before applying a mutation. The full strategy directly executes all six commands without our planner.

The default twelve scenarios include correct local/doc changes, eight known defects, global dependency input, deletion, unreviewed mapping and repeated exact state. Compare both strategies on identical file contents. Failing selective checks broaden to the rest, so failing cases often offer no command savings; that is intentional. Alternating strategy order across repetitions reduces systematic warm-start bias, but does not establish a statistically powered performance study.

Measure:

- Detection of known defects, misses, and false alarms on the primary scenarios.
- Actual command execution seconds and command counts; these are separate metrics.
- End-to-end wall seconds, including Git analysis, hashing and final evidence checks. The direct full baseline does not include planner overhead.
- Reuse warmup cost separately, retained in raw JSON. A warm cache is not free; repeated-state rows explicitly exclude the recorded first validation from their comparison.

Baseline-cleanliness prechecks are experiment preparation and excluded from compared strategy timings. Source hashes, Python/platform/Git versions, commands, statuses, return codes, log hashes, elapsed time and full-suite stdout/stderr are retained. Temporary fixtures/log files are removed after each case; the raw record is not a permanent log archive or a signed attestation. Paths may be normalized to `<fixture>` for public sharing.

## Negative control and limitations

An additional negative control intentionally removes runtime-source ownership, labels that source as docs, and falsely marks the map reviewed. It records that the full suite detects a real Unicode defect while selection does not. This is outside the headline twelve scenarios and must always be disclosed alongside them. It demonstrates that human/agent map review is a quality boundary, not a guaranteed inference by this tool.

The experiment does not claim zero production defects, zero false negatives for arbitrary projects, speedup on every workload, superiority to native affected-test tools, or behavior of other LLM agents under this Skill. Successful deterministic CLI outcomes do not validate the model's semantic review behavior. A future model/harness evaluation and historical defect replay would test those dimensions independently.

## Reproduce

```sh
python -m unittest discover -s tests -t . -v
python -m benchmarks.evaluate --cases 1000 --repetitions 1 --output benchmarks/results/local.json
python -m benchmarks.evaluate --cases 10000 --repetitions 1 --scenario local_refactor --scenario repeat_identical_state --output benchmarks/results/scale.json
```

Use additional repetitions and a real repository workload before making operational decisions. Keep collection and test execution costs separate. A narrow successful expensive suite may benefit substantially; tiny suites or high failure rates can make full validation cheaper. Choose the simpler route when measured net value is absent.
