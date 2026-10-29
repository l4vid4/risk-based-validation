# Contributing

Use Python 3.10+ and Git. There are no third-party runtime/test dependencies. Install optionally with `python -m pip install -e .`.

Keep the Skill and CLI contract aligned. Changes to selection, gates or reuse need behavioral regression coverage in a temporary repository. A cached pass must never mask changed inputs or a fresh failure. Costs may order checks but must not silently waive required checks. Do not add network calls, dependencies or background services without explaining their concrete benefit.

Run the tests relevant to your change first. Use `python -m unittest discover -s tests -t . -v` for broad cross-cutting changes. Re-run the benchmark when changing selection/execution/evidence mechanics or the fixture. Documentation-only edits usually need link/content review, not a new benchmark run.

Reproduce performance and defect-detection claims, retain raw outputs and describe environment/workload. Include end-to-end time, not only test count. Never remove negative controls to make results look better. Prefer native tool adapters with conservative fallback over unverified dependency inference.

No hosted repository URL or maintainer contact is configured in this source delivery. Once published, use that repository's contribution/issue channels and fill in its security contact before inviting private reports.
