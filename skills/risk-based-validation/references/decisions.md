# Decision examples and stopping rules

| Change/evidence | Proportionate action | Expand or stop |
|---|---|---|
| Non-runtime prose, reviewed exclusion, no repository doc check | Inspect rendered/content behavior only if relevant; no new test code needed | Explain why executable checks add no signal. A doc generator/template is runtime input. |
| Local fix with a reproducible regression | Run the failing reproduction against the fix and relevant boundaries; use existing tests where sufficient | Stop after the failure mode and affected consumers pass, unless wider obligations apply. |
| Shared utility refactor | Validate reverse transitive consumers and public contracts | Unknown dynamic consumers require broader checks. Diff size is not evidence of low risk. |
| Auth/tenant/permission logic | Fresh domain checks: allowed AND denied operations, cross-tenant access, error behavior | Missing domain coverage blocks completion; do not relabel an unrelated unit test as security coverage. |
| Schema, payment or persistence logic | Fresh domain checks for consistency, rollback/idempotence/recovery as applicable | Incompatible contracts require integration/consumer validation. A full unit suite alone may be insufficient. |
| Lock/build/shared fixture/config changes | Broaden to all relevant checks and environment validation | Dependency installation changes rotate cache context; cached source-only passes are insufficient. |
| Already passed the exact state | Reuse trustworthy results with equivalent inputs and context | Changed test, config, environment, ignored input or external service state means fresh evidence. |
| Initial check fails | Read logs, compare against expected behavior and known baseline; append unexecuted checks when useful | Fix or correct the harness based on evidence. No unchanged retry loop; a timeout is unresolved. |
| Budget runs out | Record completed and unresolved checks | Stop execution with `incomplete`, never silently drop a required gate. |

## Diagnosing failure

Check the exit status and log first. An assertion failure may indicate a product bug, stale expectation or incorrect test data; an import failure may indicate a missing dependency or product packaging defect. Diagnostic strings are hints, not root-cause findings.

Compare a known good baseline only when it helps classify the failure. Use an isolated checkout if needed; never reset the user's worktree. A pre-existing failure remains an explicit limitation. A later green result does not erase a prior failure; explain what changed, or treat intermittent behavior as unresolved. After a fix, rerun the affected checks on the new final input state. Earlier results can be reused only if their entire required identity remains valid.

## Review checklist before declaring completion

- Does the selected check assert the acceptance criterion and plausible regression modes?
- Are callers, contracts, dynamic loading and shared fixtures accounted for?
- Are repository/user-required checks included even if expensive?
- Do high-risk paths have meaningful negative and consistency assertions?
- Is any skipped check capable of detecting a distinct, still-plausible defect?
- Are cached passes tied to the actual final inputs and external context?
- Are failures, evidence gaps and unexecuted checks reported without overstating confidence?

These questions guide judgment, not a mandatory new test suite for every small change. Add tests when they capture meaningful behavior or a regression; avoid tests that merely restate implementation, file layout or generated wording.
