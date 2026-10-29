# Launch materials and adoption plan

Repository: https://github.com/l4vid4/risk-based-validation

Published GitHub announcement and feedback thread: https://github.com/l4vid4/risk-based-validation/discussions/1. The repository is public, with topics, a release, install instructions, a runnable demo and the CI matrix. External-platform drafts below remain unsent.

These are ready-to-adapt external announcement drafts. They are not claims that posts have already been sent or that any directory has accepted the project. Do not post the same content repeatedly or solicit reciprocal/paid stars. Evaluate adoption by useful installs, reproducible feedback, retained use and fixes as well as genuine stars.

## English short post

> Coding agents can spend more time re-running tests than fixing the bug. I open-sourced risk-based-validation: an Agent Skill + local Python CLI that selects checks from reviewed change impact, preserves security/data gates, reuses equivalent passing evidence, and explains when to stop.
>
> The benchmarks include the awkward part too: tiny checks can be cheaper than analysis. All raw results and an incorrect-map negative control are public.
>
> Try the temporary-repo demo: `python -m examples.demo`
>
> https://github.com/l4vid4/risk-based-validation
>
> Looking for real workload feedback, especially missed dependencies and cases where full validation is cheaper. If useful, a star helps discovery.

## 中文短帖

> 修完一个小 Bug，编程 Agent 却反复跑全量测试？我开源了 risk-based-validation：一个 Skill + 轻量 Python CLI，根据变更影响选择验证、保留权限和数据一致性的必需检查、复用有效结果，并解释为什么可以停止。
>
> 不只报“少跑了几个测试”：公开了原始耗时、8 个已知缺陷的检出结果、小测试反而变慢的场景，以及错误映射会漏检的负对照。
>
> 仓库：https://github.com/l4vid4/risk-based-validation
>
> 欢迎试用临时仓库演示 `python -m examples.demo`，尤其希望看到真实项目的失败案例与成本对照。有帮助的话，欢迎 Star。

## Longer Show HN / developer-community draft

Title: **Show HN: Risk-based validation for coding agents, with honest cost benchmarks**

I built a small Agent Skill and a standard-library Python helper to address a recurring agent workflow problem: after a narrow fix, the agent runs broad checks, repeats them unchanged, and still does not explain which regressions the checks cover.

The Skill handles semantic review; the helper collects Git changes, computes reverse component impact from an explicit reviewed map, enforces high-risk tags, orders useful checks, and records evidence. Unknown impact widens the selection. Failed checks expand to unexecuted checks once; there is no retry-until-green loop. Reuse is opt-in and bound to the final inputs and context.

It is an alpha with important limits. The map is not an automatic cross-language dependency proof, a tag is not coverage evidence, and small suites can be faster to run in full. The synthetic experiment detected the 8 known defects with both strategies, while the small mixed workload was slower overall. A deliberately bad reviewed map also demonstrates a miss. The raw data is in the repo.

I would especially appreciate feedback from maintainers with dynamic loading, monorepos or expensive integration suites: where would the mapping drift, and what evidence would make a skipped check defensible?

## Channels and timing

| Channel | Suitable next action | Boundary |
|---|---|---|
| GitHub repository | Public README, topics, release, demo and adoption-report template. | Current metadata and CI should be verifiable. |
| skills.sh / Vercel skills CLI | Publish a working standard-layout repository and provide the install command. | [FAQ](https://www.skills.sh/docs/faq) says listing follows real user installs; availability is not guaranteed by a successful discovery check. Keep test telemetry disabled to avoid manufacturing installs. |
| Developer communities / personal social accounts | Share one relevant announcement adapted to the audience, then answer concrete feedback. | Check each community's current self-promotion rules; publish from the owner's chosen account. The drafts above have not been sent. |
| VoltAgent/awesome-agent-skills | Wait for genuine users and practical evidence, then submit one targeted entry. | [Contribution rules](https://github.com/VoltAgent/awesome-agent-skills/blob/main/CONTRIBUTING.md) currently reject brand-new skills without real adoption. Do not open an ineligible PR. |

## First feedback cycle

1. Collect real project type, selected/full commands, full end-to-end times, known failures and skipped-check concerns through the adoption template.
2. Reproduce and fix a concrete mapping or execution issue; retain the negative result and regression evidence.
3. Publish a short follow-up showing what changed and the measured workload, without extrapolating a universal speedup.
4. Submit to relevant directories once their quality/adoption criteria are met. Star count is an observation, not a promised outcome.
