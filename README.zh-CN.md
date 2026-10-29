# risk-based-validation

面向 Codex 和其他编程 Agent 的风险驱动验证 Skill：让验证力度与实际风险相匹配，减少重复执行，同时保留关键质量底线。

这是可运行的 Skill、Python CLI、配置约定和验收场景组成的项目。运行时仅依赖 Python 标准库与 Git；不用模型 API、数据库或服务端。项目没有自动发布到 GitHub、PyPI，也没有修改你的全局 Agent 设置。

## 安装与运行

需要 Python 3.10+、Git。将整个 `skills/risk-based-validation` 目录放入 Agent 的技能目录。Codex 项目级安装示例（从本项目运行，替换目标路径）：

```sh
python tools/install_skill.py --target /path/to/project/.agents/skills
```

安装器遇到已有同名目录会停止，不覆盖旧文件。Codex 用户级路径也可使用 `~/.agents/skills`。其他 Agent 按各自的技能发现机制加载。Python CLI 不必 pip 安装；如需短命令，可在项目目录执行 `python -m pip install .`，随后使用 `rbv plan` / `rbv run --execute`。

在 Codex 中调用 `$risk-based-validation`。Agent 会先查看任务验收标准、仓库要求、实际变更和消费者。可以只使用 Skill 工作流及仓库原生工具，也可以配置 `.rbv.json` 来使用确定性辅助工具。

```sh
python .agents/skills/risk-based-validation/scripts/validate.py plan --repo . --base HEAD
python .agents/skills/risk-based-validation/scripts/validate.py run --repo . --base HEAD --execute
```

`plan` 只采集与分析，不执行仓库测试、不生成状态文件；`run --execute` 执行配置中已审阅的命令，不赋予额外权限。已有授权范围内的常规验证不需要新增人工确认。

`HEAD` 只涵盖本地改动。验证 PR 已提交的变更时，先核实 `git merge-base <目标分支> HEAD`，再将该提交传给 `--base`。工具不自动联网获取分支。仓库必须已有基线提交。

先以 `impact_reviewed: false` 建立真实检查清单，默认执行全部已注册检查。确认组件路径、反向依赖、共享 fixture、动态加载和文档排除规则后，才启用选择性跳过。模板见 [examples/python.json](examples/python.json)，字段定义见 [配置与 CLI 合同](skills/risk-based-validation/references/configuration.md)。模板中的检查名称必须替换为实际存在的命令。

## 核心行为

1. **变更与影响**：读取基线以来的变更、暂存区、工作区、删除、重命名和未跟踪文件，以组件依赖的反向传递闭包选择消费者检查。测试文件和 fixture 通过 `inputs` 显式关联。
2. **风险底线**：未知文件、未审核映射、依赖锁、构建/CI/策略输入及不透明变更扩大至完整检查清单。安全和数据一致性规则要求相应领域检查，缺失则不能宣称完成。仅凭文件名或关键词不能证明风险已被识别，Agent 仍需阅读实际行为。
3. **自适应执行**：成本估计用于排序，不能豁免必需检查。失败后仅补充尚未执行的检查，保留失败、输出诊断线索，不进行无依据重试。
4. **保守复用**：默认不复用。需要检查配置 `cache: true`，以及调用者提供依赖、工具链和外部状态标识 `--context`。复用键绑定整个可见工作区内容、配置、命令、环境、日志和有效期；高风险始终重新执行。
5. **明确停止**：必需检查有有效通过证据且不存在未解释失败时停止。`--budget 60` 耗尽、必需领域检查缺失、验证期间最终内容变化，都报告 `incomplete`。文档无需检查时单独报告 `no_checks_required`。

将 `.rbv/` 加入 `.gitignore`；报告与原始日志保存在其中。环境变量值及 context 只保存摘要，命令和日志仍可能含敏感内容，公开前应检查。缓存只是本地证据，不是可信 CI 签名；工具不替代仓库强制 CI。

退出码：`0` 表示检查通过或经判断无需检查，`1` 表示检查失败，`2` 表示验证未完成或配置/仓库错误。不要将 `no_checks_required` 写成“全部测试通过”。

## 独立验收

```sh
python -m unittest discover -s tests -t . -v
python -m benchmarks.evaluate --cases 1000 --repetitions 1 --output benchmarks/results/local.json
```

验收运行真实临时 Git 仓库、子进程和断言，对照策略直接运行完整场景套件。场景涵盖局部修改、共享依赖、租户隔离、SQLite 事务原子性、未知文件、锁文件、删除与完全相同状态的重复验证。先确认基线干净，再注入已知缺陷。原始命令、退出码、耗时和结果均有记录，没有用 sleep 模拟收益。

结果见 [实测表格](benchmarks/results/local.md)、[原始数据](benchmarks/results/local.json) 和 [验收说明](docs/evaluation.md)。需要同时看缺陷检出率、误报、实际命令时间与总耗时。小测试场景中分析开销可能抵消节省，不能将减少命令数量直接解释成整体提速。

本机主实验：12 个场景、8 个已知缺陷均检出，72 次命令降为 55 次，命令执行时间减少 25.1%，但总耗时增加 39.6%。两个更高成本的成功变更场景总耗时从 13.537 秒降至 1.837 秒，另有 0.804 秒缓存预热成本；这是明确限定的场景收益，见 [较大工作负载记录](benchmarks/results/scale.md)。最终 36 个自动化用例中，35 个通过、1 个因本机符号链接权限跳过；完整说明见 [本地验收记录](docs/validation.md)。

特别保留一个负对照：故意将运行时代码错误标记为文档并谎称映射已审核，此时选择器会漏检，而全量能够检出。它明确展示了配置可信边界；工具没有声称任意错误配置都安全。

## 限制与后续方向

当前依赖图为人工/Agent 审核的显式映射，不自动解析所有语言的 import 或动态调用。完整检查清单也需要维护者保证真实、充分。`security` / `data` 标签必须对应实际的拒绝路径、隔离、回滚等断言，标签本身不是覆盖证据。

复用绑定整个工作区，宁可失去部分命中率，也不依赖未经证明的局部输入集合。被 Git 忽略的输入需配置 `extra_inputs`（会保守扩大范围）；外部服务与未受跟踪的工具链需更新 context，否则关闭复用。运行期间应保持源文件单写入者；首尾快照不是持续文件监控。不同于工作区的暂存版本需要单独验证。

接下来优先考虑接入 Nx/Bazel/testmon 等原生影响与证据工具、增加真实开源仓库的历史缺陷回放、验证映射漂移、优化大仓库采集开销，而不是增加固定数量的测试或引入复杂服务。

本地实际验收平台为 Windows / Python 3.13。仓库提供 Windows/Linux 的 Python 3.10/3.13 CI 定义，但未将其描述为已在远程通过。项目采用 MIT 许可证；贡献方式见 [CONTRIBUTING.md](CONTRIBUTING.md)。
