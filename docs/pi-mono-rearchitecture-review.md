# 基于 pi-mono 的重新架构审查

审查日期：2026-04-27

参考项目：`https://github.com/badlogic/pi-mono`

审查对象：`D:\liulanqixiazai\github-weekly-agent-rearchitecture-from-pi-mono.md`

## 1. 对 pi-mono 的学习结论

`badlogic/pi-mono` 是一个 AI Agent 工具链 monorepo。它的价值不在于某个单独脚本，而在于把 Agent 项目的核心能力拆成边界清晰的 package。

它的 README 显示，项目包含：

1. 统一多模型 LLM API。
2. Agent runtime。
3. coding agent CLI。
4. Slack bot。
5. TUI 和 Web UI 组件。
6. vLLM pods 管理工具。

`pi-coding-agent` 对本项目更有参考价值。它强调：

1. 核心保持小。
2. 默认能力够用。
3. 通过 prompts、skills、extensions 扩展。
4. 用项目上下文文件约束 Agent 行为。
5. 保存会话历史，方便复盘和延续。
6. 提交时只提交本次修改的文件，避免污染其他工作。

这些思想可以借鉴，但不应照搬 `pi-mono` 的 TypeScript monorepo 形态。本项目仍应保持 Python 自动化任务的简单结构。

## 2. 新版架构值得保留的改进

新版架构相比原架构有明显提升，建议保留以下内容。

### 2.1 增加 AGENTS.md

这是最值得采纳的改动。

`AGENTS.md` 应写清：

1. 项目目标。
2. 模块边界。
3. 密钥禁止硬编码。
4. 不删除历史报告。
5. 修改代码后必须说明改动。
6. 测试命令和验收标准。

这样后续 Codex 或其他 Agent 继续开发时，不需要每次重新解释项目规则。

### 2.2 Prompt 独立到 prompts/

建议第一阶段就创建：

```text
prompts/weekly_report.md
```

原因：

1. 提示词不应该散落在 Python 代码里。
2. 修改周报风格不需要改代码。
3. 后续可以增加日报、月报、简短 Telegram 摘要等模板。

### 2.3 data/ 用于历史记忆

保留 `data/` 是合理的，但建议拆成两类：

```text
data/runs/YYYY-MM-DD.json
data/state/sent_repos.json
```

`data/runs/` 保存不可变运行摘要，便于回溯。

`data/state/sent_repos.json` 保存去重状态，属于可变状态，后续如果增长较快，可以迁移到 SQLite。

### 2.4 保持核心流程简单

新版架构强调第一阶段只做 MVP，这是正确方向。

第一阶段只应实现：

1. GitHub 搜索。
2. 数据清洗和排序。
3. Kimi 周报生成。
4. Kimi 失败时的基础报告。
5. Telegram 分段推送。
6. Markdown 和运行摘要归档。
7. GitHub Actions 定时和手动触发。

不要在第一阶段加入 Web Dashboard、SQLite、完整 Skill 发布、复杂趋势图或 Telegram 交互式 Bot。

## 3. 建议收敛的部分

### 3.1 skills/ 不建议在 MVP 创建实体目录

新版架构提出：

```text
skills/github-weekly-agent/SKILL.md
```

这个方向可以作为未来扩展，但不建议在第一阶段创建空 Skill。原因：

1. 当前项目目标是可运行的自动化周报，不是发布 Codex Skill。
2. 空 Skill 会增加维护面。
3. 如果 Skill 内容只是重复 README 和 AGENTS.md，会造成文档重复。

建议：

1. 在 `docs/roadmap.md` 中记录未来 Skill 化计划。
2. 等项目稳定后再创建真正可用的 `skills/github-weekly-agent/SKILL.md`。

### 3.2 utils.py 不应变成杂物桶

新版架构把日期、日志、环境变量、文本截断和异常处理都放入 `utils.py`。这在早期可以接受，但要控制边界。

更简洁的做法：

```text
src/settings.py        读取配置和环境变量
src/utils.py           日期、文本分段等纯工具函数
src/logging_config.py  日志配置
```

如果第一阶段想更少文件，也可以只保留 `utils.py`，但不能把 GitHub、Kimi、Telegram 的业务逻辑塞进去。

### 3.3 history.json 应避免无限增长和提交冲突

如果所有运行摘要都追加进一个 `data/history.json`，长期会出现：

1. 文件越来越大。
2. GitHub Actions 并发运行时容易冲突。
3. 人工编辑和自动提交容易互相覆盖。

建议改为：

```text
data/runs/YYYY-MM-DD.json
```

如果需要总索引，再后续生成 `data/index.json`。

### 3.4 执行流程中应先归档再推送

新版流程里先 Telegram 推送，再 archive 保存。建议改为：

```text
生成报告
→ 先保存 reports/ 和 data/runs/
→ 再尝试 Telegram 推送
→ 更新运行摘要中的 telegram_sent 状态
```

这样即使 Telegram 失败，报告仍然保留。

## 4. 必须补充的工程要求

### 4.1 GitHub Actions 防循环

自动提交报告时必须防止重复触发：

1. 使用提交信息 `[skip ci]`。
2. 或在 workflow 中设置 `paths-ignore`。
3. 提交前检查是否有变更。
4. 增加 `concurrency`，避免多次手动触发互相覆盖。

### 4.2 Telegram 分段规则

Telegram 单条消息长度有限。第一阶段应定义清楚：

1. 每段控制在 3500 字符以内。
2. 优先按 Markdown 标题或空行切分。
3. 切不开时再硬切。
4. 推送失败不删除报告。

### 4.3 Kimi 降级输出

Kimi API 失败时不能让整个流程失败。

降级报告至少包含：

1. 本次搜索日期。
2. 搜索条件。
3. 项目名称。
4. Star、Fork、语言。
5. GitHub 链接。
6. 简介。

### 4.4 最小测试范围

为了保证代码简洁完整，第一阶段测试只覆盖关键纯逻辑：

1. `processor` 去重、过滤、排序。
2. `sender` 文本分段。
3. `reporter` fallback 报告。
4. `archive` 路径和文件命名。

不需要一开始就写复杂端到端测试。

## 5. 更新后的推荐 MVP 结构

第一阶段建议采用下面结构，比新版文档更收敛：

```text
github-weekly-agent/
├── AGENTS.md
├── README.md
├── requirements.txt
├── .env.example
├── .gitignore
├── main.py
├── prompts/
│   └── weekly_report.md
├── config/
│   └── interests.example.json
├── reports/
│   └── .gitkeep
├── data/
│   ├── runs/
│   │   └── .gitkeep
│   └── state/
│       └── sent_repos.example.json
├── docs/
│   ├── architecture.md
│   ├── setup.md
│   └── roadmap.md
├── src/
│   ├── __init__.py
│   ├── settings.py
│   ├── collector.py
│   ├── processor.py
│   ├── reporter.py
│   ├── sender.py
│   ├── archive.py
│   └── utils.py
└── .github/
    └── workflows/
        └── weekly.yml
```

暂不创建：

```text
skills/
web/
database/
dashboard/
```

这些等第一阶段稳定后再加。

## 6. 给后续开发的简洁性要求

写代码前必须遵守：

1. 每个模块只解决一个问题。
2. 不写重复封装。
3. 不提前抽象复杂插件系统。
4. 不为了“像 Agent 框架”而增加目录。
5. 只有当一个能力真实可用时，才创建对应文件。
6. Prompt 放在 `prompts/`，规则放在 `AGENTS.md`，运行结果放在 `reports/` 和 `data/`。
7. 外部 API 调用必须有 timeout 和清晰错误。
8. fallback 路径必须能独立工作。

## 7. 最终采纳建议

建议把新版架构作为原架构的升级版采纳，但做三点收敛：

1. 采纳 `AGENTS.md`、`prompts/`、`data/runs/`、`data/state/`。
2. 暂缓 `skills/` 实体目录，避免 MVP 过度设计。
3. 明确 GitHub Actions 防循环、Telegram 分段、Kimi fallback 和最小测试范围。

这样既吸收了 `pi-mono` 的 Agent 工程化思想，又能保持当前项目的代码简洁、完整、可落地。
