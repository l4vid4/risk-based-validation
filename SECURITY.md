# Security model

The helper runs trusted repository-configured commands with the caller's permissions. It is not a sandbox, a source-code audit, a privilege boundary or a signed test-attestation service. Review configuration and run untrusted repositories in an appropriate existing sandbox. The Skill never authorizes bypassing a harness denial.

Planning uses Git subprocesses with fixed argv structure and external diff/textconv disabled; it does not execute configured tests. Running is explicit. Test commands may intentionally call interpreters or shells; arbitrary repository code remains arbitrary code. Platform batch-file semantics also matter: use explicit trusted interpreters and review arguments instead of assuming `shell=False` can make a malicious command safe.

Git calls disable fsmonitor hooks, optional index locks and lazy fetching. Git can still honor repository-configured content filters; use planning only in a trusted repository or existing sandbox. “Read-only plan” means no helper file writes or configured test execution, not a new isolation boundary around Git.

High-risk hints are conservative supplements. They cannot recognize every authorization, data or payment bug. Tags and impact maps must reflect actual coverage and repository requirements. A falsely reviewed map can omit a defect, as the benchmark negative control demonstrates.

Keep `.rbv/` private and ignored. Configured commands and logs may contain secrets or personal data. Environment/context values are stored as digests, but hashes do not make low-entropy secrets suitable public identifiers. Logs are stored on disk without a current size quota. Evidence can be edited by the local user and must not be trusted across untrusted workspaces. Do not point evidence directories at symlinks or share writable source trees during a run.

Ignored files, installed dependencies and external systems are not automatically tracked. Include file inputs explicitly or disable reuse. Context tokens must rotate with external state. Never cache flaky, time-dependent or mutable-service checks without a reliable equivalence model.

For a security issue, do not post credentials, private logs or exploit-sensitive details publicly. Use [GitHub private vulnerability reporting](https://github.com/l4vid4/risk-based-validation/security/advisories/new) to contact the maintainer privately. Include a minimal sanitized reproduction, affected version and the impact on check selection, execution or evidence reuse.
