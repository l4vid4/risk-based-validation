# Research and technical decisions

Research date: 2026-10-29 (Asia/Shanghai). These are primary documentation/repository sources fetched during implementation. This review informed the design; it is not an empirical comparison against the listed projects.

| Source | Observed mechanism | Adopted lesson / boundary |
|---|---|---|
| [ISTQB/ASTQB risk management](https://astqb.org/5-2-risk-management/) and [Felderer & Schieferdecker, A taxonomy of risk-based testing](https://arxiv.org/abs/1912.11519) | Risk concerns likelihood and consequence; reassessment can guide selection, intensity and stopping throughout testing. | Use qualitative consequence/uncertainty tiers and adaptive broadening. No numerical probability is asserted without calibration data. |
| [Agent Skills specification](https://agentskills.io/specification) | A directory with `SKILL.md` frontmatter (`name`, `description`), optional scripts/references and progressive disclosure. | Ship a self-contained portable skill with short instructions and optional deterministic helpers. Avoid mandatory vendor APIs. |
| [Codex skills](https://learn.chatgpt.com/docs/build-skills) | Skills support local discovery under `.agents/skills` and explicit invocation, with metadata loaded before deeper instructions. | Keep detailed CLI/config information in linked references; distribute a folder that can be copied directly. |
| [Codex AGENTS.md](https://learn.chatgpt.com/docs/agent-configuration/agents-md) | Repository and user instructions compose by scope. | Respect required checks before optimizing. Do not treat a skill as authority to remove existing obligations. |
| [Codex approvals and security](https://learn.chatgpt.com/docs/agent-approvals-security) | Execution is governed by the harness's sandbox and permission policies. | Planning grants no execution permission; execution inherits the caller's sandbox. No auto-escalation or credential/network setup. |
| [pytest-testmon](https://www.testmon.org/) / [source](https://github.com/tarpas/pytest-testmon) | Runtime coverage-derived dependencies select affected Python tests; previous failures rerun. Its docs list static assets and external services as untracked dependencies. | Native dependency data is useful, but environment/asset omissions matter. Our general-purpose helper uses explicit maps and conservative fallbacks instead of assuming Python coverage generalizes to all languages. |
| [Nx affected](https://nx.dev/docs/features/ci-features/affected) / [source](https://github.com/nrwl/nx) | Git/task or project inputs determine affected work; lock changes conservatively affect all tasks by default. | Reverse reachability and explicit global inputs are understandable. Prefer Nx itself in established Nx projects. |
| [STARTS](https://github.com/TestingResearchIllinois/starts) | Static regression-test selection for Java, integrated into Maven. | Language-specific analysis can be stronger than coarse maps, but a generic skill should not duplicate compiler infrastructure. Leave a native-tool integration seam in the workflow. |
| [Bazel remote caching](https://bazel.build/remote/caching) | Actions declare inputs, outputs, command and environment; reproducibility is required for sound reuse. | Bind evidence to input identity and command/environment; do not reuse external-state-dependent results blindly. Local files here are not a remote trust protocol. |
| [StrykerJS incremental mode](https://stryker-mutator.io/docs/stryker-js/incremental/) / [source](https://github.com/stryker-mutator/stryker-js) | Reuses mutation results based on changed code/tests and documents limitations for other environment changes. | Evaluate actual defect detection with mutations, retain a negative control, and disclose what identity checks do not establish. |

## Chosen route

Use a reasoning Skill for semantic questions and a small Python standard-library CLI for repeatable mechanics. No learned risk model, test-covering set optimizer, language server, plugin server or remote cache is required. This keeps setup and trust boundaries small.

Risk is expressed as explainable tiers and mandatory constraints, not an uncalibrated numeric probability. An explicit graph makes transitive impact auditable. Unreviewed graphs, unknown paths and opaque changes broaden rather than disappear. High-risk hints and configurable domain gates provide a floor, while the agent must still identify sensitive semantics beyond keywords.

Cost estimates order checks only. Failure-driven broadening is finite and never repeats a completed check within a run. Whole-worktree fingerprints simplify reuse at the expense of cache hit rate. Context tokens cover identities the helper cannot independently discover, so reuse remains opt-in.

## Rejected/deferred alternatives

- A prompt-only skill cannot consistently collect Git edge cases or verify evidence identity. The optional CLI makes these operations inspectable and repeatable.
- Automatic cross-language import inference would imply coverage it cannot guarantee, especially with dynamic loading, assets and generated code. Native adapters are preferable future work.
- Coverage-based selection is a useful future adapter, not the default: it needs a trusted baseline and misses unobserved paths/external inputs without additional controls.
- Budget-based dropping or greedy “fewest tests” optimization could omit a distinct failure mode. Required checks remain constraints; budget exhaustion is incomplete.
- A runtime statistical model needs representative historical failures and calibration not available here. No invented probabilities or performance claims are used.
- Hooks/MCP/background services are unnecessary for the current scope. Explicit commands make effects and cost visible.

## Limits of this research

The implementation does not copy source code from these projects or claim equivalence with their dependency analyses. Comparative measurements use our executable fixture versus its direct full-suite baseline, not Nx/testmon/Bazel/STARTS/Stryker benchmarks. Later publication added hosted CI and public GitHub installation evidence in [validation.md](validation.md); production integrations and PyPI publication have not been exercised.
