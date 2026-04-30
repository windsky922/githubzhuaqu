# 操作日志

本文件记录 Codex 对本仓库执行的文档审查和项目规划操作。

## 2026-04-27

### 1. 读取原始文档

输入文件：

```text
D:\liulanqixiazai\github-weekly-agent-architecture.md
```

处理结果：

1. 首次读取时终端中文显示为乱码。
2. 使用显式 UTF-8 重新读取后，确认文档内容完整可读。
3. 已完成对项目目标、用户需求、模块设计、技术选型、MVP 和验收标准的审查。

### 2. 审查架构

结论：

1. 原架构总体清晰，不需要推翻重建。
2. 需要补强热点定义、GitHub Actions 自提交、防循环、Telegram 分段、运行摘要和模块边界。
3. 推荐采用“原始架构 + 工程化增强”的架构。

输出文件：

```text
docs/architecture-review.md
```

### 3. 生成优化后的项目文档

新增完整架构文档，覆盖：

1. 项目定位。
2. 推荐架构。
3. 数据流。
4. MVP 范围。
5. 推荐目录结构。
6. 模块职责。
7. 搜索策略。
8. 推荐评分。
9. 周报格式。
10. Telegram 推送策略。
11. 运行归档。
12. GitHub Actions 要求。
13. 安全要求。
14. 迭代路线。

输出文件：

```text
docs/project-architecture.md
```

### 4. 建立仓库入口文档

新增 `README.md`，用于说明当前仓库状态、文档索引、项目目标、技术路线和第一阶段范围。

### 5. 当前阶段未执行的事项

按照用户要求，本阶段暂不开发项目代码，因此没有创建 Python 源码、GitHub Actions workflow、依赖文件或运行脚本。

后续如果进入开发阶段，再按 `docs/project-architecture.md` 中的开发顺序实施。

---

## 2026-04-27 追加：基于 pi-mono 的重新架构审查

### 1. 学习参考项目

参考链接：

```text
https://github.com/badlogic/pi-mono
```

重点学习内容：

1. `pi-mono` 是围绕 AI Agent 构建的 monorepo，包含统一 LLM API、Agent runtime、coding agent、TUI、Web UI、Slack bot 和 vLLM pods 管理工具。
2. `pi-coding-agent` 的核心思想是最小核心、工具扩展、Prompt Templates、Skills、AGENTS.md、Sessions 和 Extensions。
3. 对本项目最有价值的是项目级 Agent 规则、提示词模板外置、运行历史记录、可扩展但不过度复杂的模块边界。

### 2. 审查新版架构文档

输入文件：

```text
D:\liulanqixiazai\github-weekly-agent-rearchitecture-from-pi-mono.md
```

结论：

1. 新版架构方向正确，适合作为原架构的升级版。
2. `AGENTS.md` 和 `prompts/weekly_report.md` 应纳入第一阶段。
3. `data/` 历史记录设计应保留，但要区分不可变运行摘要和可变去重状态。
4. `skills/` 目录只应作为后续预留说明，MVP 阶段不建议创建空 Skill 文件，避免增加无实际用途的维护面。
5. GitHub Actions 自动提交必须加入防循环、并发控制和变更检测。

### 3. 本次新增文档

输出文件：

```text
docs/pi-mono-rearchitecture-review.md
```

该文档记录：

1. 从 `pi-mono` 学到的可采纳设计。
2. 新版架构中建议保留的部分。
3. 需要收敛或延后的部分。
4. 面向“代码简洁完整”的最终开发建议。

---

## 2026-04-27 追加：第一阶段 MVP 开发

### 1. 开发范围

严格按照收敛后的 MVP 架构开发，未创建暂缓的 `skills/`、Web Dashboard、SQLite 或复杂插件系统。

本次实现内容：

1. `AGENTS.md` 项目级 Agent 开发规则。
2. `prompts/weekly_report.md` 独立周报提示词。
3. `main.py` 主流程编排。
4. `src/collector.py` GitHub Search API 采集。
5. `src/processor.py` 去重、过滤、评分和排序。
6. `src/reporter.py` Kimi 生成和 fallback 基础报告。
7. `src/sender.py` Telegram 分段推送。
8. `src/archive.py` Markdown、原始数据和运行摘要归档。
9. `src/settings.py` 环境变量和兴趣配置读取。
10. `src/utils.py` 日期、分段和通用辅助函数。
11. `.github/workflows/weekly.yml` 定时和手动触发工作流。
12. `tests/` 最小单元测试。

### 2. 简洁性处理

1. 暂不增加外部依赖，`requirements.txt` 保持标准库实现。
2. 暂不拆分 HTTP clients，避免 MVP 过度抽象。
3. 暂不创建 Skill 目录，等工作流稳定后再产品化。
4. 每个模块只负责一个主要职责。

### 3. 本地验证

已执行：

```text
py -m unittest discover -v
py -m compileall main.py src tests
py main.py
```

验证结果：

1. 3 个单元测试通过。
2. Python 编译检查通过。
3. 端到端运行成功生成报告。
4. 本地未配置 Telegram，程序按设计输出 `Telegram is not configured`，未阻断归档流程。

本地验证生成的临时报告和运行数据不作为源码提交。

---

## 2026-04-27 追加：文档中文化

### 1. 用户要求

用户要求项目中所有文档使用中文书写，将英文写成的部分重新用中文表达。

### 2. 本次处理范围

本次已将以下文档性文件中的英文说明改写为中文：

1. `AGENTS.md`
2. `docs/architecture.md`
3. `docs/setup.md`
4. `docs/roadmap.md`
5. `prompts/weekly_report.md`
6. `.env.example`
7. `requirements.txt`
8. `.github/workflows/weekly.yml` 中面向用户显示的工作流名称和步骤名称

### 3. 保留内容

以下内容属于技术名词、命令、路径、环境变量名或 GitHub Actions 语法，保持原样：

1. `GitHub Weekly Agent`
2. `GitHub Actions`
3. `Telegram`
4. `Kimi API`
5. `python main.py`
6. `GH_SEARCH_TOKEN` 等环境变量名
7. `.github/workflows/weekly.yml` 中的工作流关键字

---

## 2026-04-27 追加：GitHub Secrets 配置测试

### 1. 测试方式

新增检查工作流：

```text
.github/workflows/secrets-check.yml
```

该工作流通过 GitHub Actions 读取仓库 Secrets，并验证：

1. `GH_SEARCH_TOKEN` 是否存在并可访问 GitHub API。
2. `KIMI_API_KEY`、`KIMI_BASE_URL`、`KIMI_MODEL` 是否存在并可调用 Kimi API。
3. `TELEGRAM_BOT_TOKEN`、`TELEGRAM_CHAT_ID` 是否存在并可发送 Telegram 测试消息。

### 2. 初始测试结果

运行结论：失败。

已确认：

1. 所有必要 Secrets 都能被 GitHub Actions 读取到。
2. `GH_SEARCH_TOKEN` 验证通过，GitHub API 剩余额度正常。

失败点：

```text
Kimi API 返回 HTTP 400。
```

### 3. 失败原因

GitHub Actions 日志显示：

```text
invalid temperature: only 1 is allowed for this model
```

说明当前配置的 Kimi 模型只允许 `temperature=1`。

### 4. 修复动作

已将以下位置的 `temperature` 改为 `1`：

1. `src/reporter.py`
2. `.github/workflows/secrets-check.yml`

### 5. 最终测试结果

最终运行结果：成功。

已确认：

1. `GH_SEARCH_TOKEN` 已配置，并通过 GitHub API 验证。
2. `KIMI_API_KEY` 已配置。
3. `KIMI_BASE_URL` 已配置。
4. `KIMI_MODEL` 已配置。
5. Kimi API 可以连通并返回 `choices`。
6. `TELEGRAM_BOT_TOKEN` 已配置。
7. `TELEGRAM_CHAT_ID` 已配置。
8. Telegram 测试消息发送成功。

GitHub Actions 成功运行链接：

```text
https://github.com/windsky922/githubzhuaqu/actions/runs/24992511910
```

说明：本次 Kimi 轻量测试请求返回内容为空，但 HTTP 调用成功并返回了有效 `choices` 字段，因此判断为 API 配置可用。正式周报生成流程会使用完整提示词和项目数据调用 Kimi。

---

## 2026-04-28 追加：完整周报工作流验证

### 1. 验证目的

在用户完成 GitHub Secrets 配置后，对完整自动化链路进行验证，确认从 GitHub Actions 到周报归档、Kimi 生成和 Telegram 推送的流程可以正常运行。

验证链路：

```text
GitHub Actions
-> python -m unittest
-> python main.py
-> GitHub 项目采集
-> Kimi 中文周报生成
-> reports/ 与 data/ 归档
-> Telegram 推送
-> Actions 自动提交归档文件
```

### 2. 临时触发方式

为避免等待每周定时任务，临时给 `.github/workflows/weekly.yml` 增加了仅用于测试的 `push` 触发器。

测试完成后已移除该临时触发器，正式工作流保留：

1. `workflow_dispatch` 手动触发。
2. 每周一 UTC 00:00 的定时触发。

### 3. 第一次完整流程测试

运行链接：

```text
https://github.com/windsky922/githubzhuaqu/actions/runs/25031865017
```

运行结论：成功。

归档结果：

1. `reports/2026-04-28.md`
2. `data/raw/2026-04-28.json`
3. `data/runs/2026-04-28.json`

本次结果显示 Telegram 推送成功，但 Kimi 周报生成使用了降级报告。为便于后续定位，随后在运行摘要中增加了 `report_error` 字段，并增强了 Kimi 响应内容提取逻辑。

### 4. 第二次完整流程测试

运行链接：

```text
https://github.com/windsky922/githubzhuaqu/actions/runs/25031996992
```

运行结论：成功。

关键结果：

1. `collected_count`: 165
2. `selected_count`: 10
3. `kimi_used`: true
4. `fallback_used`: false
5. `telegram_sent`: true
6. `report_path`: `reports/2026-04-28.md`
7. `run_summary_path`: `data/runs/2026-04-28.json`

说明：第二次完整流程已经确认 Kimi 正常生成中文周报，Telegram 正常推送，Actions 自动归档提交正常执行。

### 5. 本次代码与文档调整

1. `src/models.py`：为运行摘要增加 `report_error` 字段。
2. `src/reporter.py`：让 Kimi 生成失败时返回明确错误原因，并兼容更多响应内容结构。
3. `main.py`：写入 `report_error`，便于从 `data/runs/` 追踪模型生成问题。
4. `tests/test_reporter.py`：增加 Kimi 响应内容提取测试。
5. `.github/workflows/weekly.yml`：移除测试用 `push` 触发器。
6. `docs/operation-log.md`：记录完整工作流验证过程和结果。

### 6. 当前结论

Secrets 配置已经通过完整链路验证。当前项目已具备按周自动抓取 GitHub 热点项目、生成中文周报、推送到 Telegram、归档运行结果并自动提交到 GitHub 的基础能力。

---

## 2026-04-28 追加：第二阶段已推送仓库状态记录

### 1. 开发目的

进入第二阶段数据质量增强后，优先实现最小且必要的历史状态能力，避免同一仓库在后续周报中被重复推送。

### 2. 本次实现

新增模块：

```text
src/state.py
```

该模块负责：

1. 读取 `data/state/sent_repos.json`。
2. 过滤已经成功推送过的仓库。
3. Telegram 推送成功后写入新的已推送仓库。
4. 兼容旧的字符串数组格式和新的对象数组格式。

### 3. 主流程变化

新的处理顺序：

```text
collect_repositories
-> load_sent_repository_names
-> filter_unsent_repositories
-> process_repositories
-> generate_report
-> send_report
-> write_sent_repositories
```

状态写入条件：

1. Telegram 推送成功。
2. 本次筛选出的新仓库列表不为空。

如果 Kimi 不可用，仍可使用降级版周报；如果 Telegram 不可用或发送失败，则不会写入已推送状态，避免遗漏后续真实推送。

### 4. 运行摘要变化

`data/runs/YYYY-MM-DD.json` 新增字段：

1. `skipped_sent_count`：本次采集结果中被历史推送状态跳过的仓库数。
2. `state_path`：本次成功写入的状态文件路径。

### 5. 工作流变化

`.github/workflows/weekly.yml` 的自动提交范围增加：

```text
data/state
```

这样 GitHub Actions 生成的已推送状态会和周报、原始数据、运行摘要一起提交回仓库。

### 6. 本地验证

已执行：

```text
py -m unittest
py -m compileall main.py src tests
```

验证结果：通过。

### 7. 初始状态写入

由于 `2026-04-28` 的完整工作流已经确认 Telegram 推送成功，本次同步创建：

```text
data/state/sent_repos.json
```

该文件使用 `data/raw/2026-04-28.json` 中的 10 个已推送仓库初始化，避免下一次运行重复推送同一批项目。

---

## 2026-04-28 追加：第二阶段 README 摘要抓取

### 1. 开发目的

提升周报内容质量。仅依赖仓库名称和简介时，Kimi 对项目定位容易过于粗略；加入 README 摘要后，可以让周报更准确地说明项目用途、特性和学习价值。

### 2. 实现范围

本次实现保持简洁，不增加新依赖，不引入复杂缓存或数据库。

新增能力：

1. 对最终入选周报的仓库抓取 README。
2. 清洗 README 中的多余空白。
3. 每个仓库只保留前 2000 个字符作为摘要。
4. 单个 README 获取失败时跳过，不影响整体运行。
5. Kimi 提示词要求优先参考 README 摘要。
6. 降级版周报也会展示 README 摘要。

### 3. 主流程变化

新的处理顺序：

```text
collect_repositories
-> load_sent_repository_names
-> filter_unsent_repositories
-> process_repositories
-> enrich_repositories_with_readmes
-> generate_report
-> send_report
-> write_sent_repositories
```

### 4. 运行摘要变化

`data/runs/YYYY-MM-DD.json` 新增字段：

```text
readme_fetched_count
```

该字段记录本次成功获取 README 摘要的入选仓库数量。

### 5. 本地验证

已执行：

```text
py -m unittest
py -m compileall main.py src tests
```

验证结果：通过。

---

## 2026-04-28 追加：第二阶段 Star 增量评分

### 1. 开发目的

补齐第二阶段数据质量增强中的历史热度能力。单纯按总 Star 排序容易长期偏向大型老项目；加入 Star 增量后，可以更好发现近期增长明显的项目。

### 2. 本次实现

新增状态文件：

```text
data/state/star_history.json
```

该文件记录：

1. 仓库完整名称。
2. 仓库链接。
3. 最近一次采集到的 Star 数。
4. 最近一次采集日期。

### 3. 评分变化

`Repository` 新增字段：

```text
star_growth
```

计算方式：

```text
star_growth = 当前 Star - 历史 Star
```

如果没有历史记录，则增长值为 0。

当前评分权重：

1. 总 Star：35%
2. Fork：15%
3. 兴趣主题匹配：25%
4. Star 增量：15%
5. 创建时间新鲜度：10%

### 4. 主流程变化

主流程会在处理仓库前读取 Star 历史，在完成本次归档时写入最新 Star 历史。

运行摘要新增字段：

1. `star_history_updated_count`
2. `star_history_path`

### 5. 初始状态写入

由于 `2026-04-28` 已经有一次成功完整运行，本次使用 `data/raw/2026-04-28.json` 初始化 `data/state/star_history.json`，为下一次运行提供增量基线。

### 6. 本地验证

已执行：

```text
py -m unittest
py -m compileall main.py src tests
```

验证结果：通过。

---

## 2026-04-28 追加：第三阶段 GitHub Pages 周报归档页面

### 1. 开发目的

进入第三阶段产品化输出后，优先实现轻量的周报归档页面，让生成的周报可以通过 GitHub Pages 直接浏览。

### 2. 本次实现

新增脚本：

```text
scripts/build_pages.py
```

该脚本负责：

1. 读取 `reports/` 下的周报。
2. 读取 `data/runs/` 下的运行摘要。
3. 生成 `docs/index.md` 周报归档首页。
4. 将周报同步到 `docs/weekly/YYYY-MM-DD.md`。

### 3. 工作流变化

`.github/workflows/weekly.yml` 新增步骤：

```text
python scripts/build_pages.py
```

自动提交范围新增：

```text
docs/index.md
docs/weekly
```

### 4. 本次生成文件

```text
docs/index.md
docs/weekly/2026-04-28.md
```

### 5. GitHub Pages 启用方式

在 GitHub 仓库中进入：

```text
Settings -> Pages
```

设置：

```text
Source: Deploy from a branch
Branch: main
Folder: /docs
```

### 6. 本地验证

已执行：

```text
py scripts/build_pages.py
py -m unittest
py -m compileall main.py src tests scripts
```

验证结果：通过。

---

## 2026-04-28 追加：周报页面内容与链接格式修正

### 1. 用户反馈

用户反馈 GitHub Pages 中生成的周报页面存在以下问题：

1. 需要确保页面内容属于本周范围。
2. “主要语言”中不能出现“蟒蛇”这类中文直译，应保留 `Python` 等技术语言英文名称。
3. 热门项目总览中的 GitHub 链接应为可点击超链接。
4. 修改后需要检查代码是否存在冗余或明显问题。

### 2. 本次修正

采集范围修正：

1. 移除 `pushed:>=...` 查询，避免历史老项目仅因本周更新而进入“本周创建项目”周报。
2. 在处理阶段增加 `created_at >= since_date` 二次校验，即使 GitHub Search 查询变化，也不会让非本周创建项目进入周报。

报告格式修正：

1. Kimi 输出和降级报告都会经过 `normalize_report_markdown` 清洗。
2. 将“蟒蛇”统一替换为 `Python`。
3. 将 GitHub 原始 URL 转为 Markdown 超链接。
4. 已经是 Markdown 格式的链接不会重复包装。
5. 降级版周报中的 README 摘要截断展示，避免页面过长影响阅读。

提示词修正：

1. 要求技术语言名称保留官方英文名称。
2. 要求只分析用户数据提供的本周创建项目。
3. 要求热点项目总览中的链接列使用 Markdown 超链接格式。

### 3. 当前页面重新生成

已重新执行：

```text
py main.py
py scripts/build_pages.py
```

说明：本地环境没有 Kimi 和 Telegram 密钥，因此本次重新生成的 `2026-04-28` 页面为降级版周报，且不会写入已推送状态。GitHub Actions 后续正式运行时仍会读取仓库 Secrets 并使用 Kimi 与 Telegram。

### 4. 校验结果

已确认：

1. `reports/2026-04-28.md` 和 `docs/weekly/2026-04-28.md` 中没有“蟒蛇”。
2. 热门项目总览中的 GitHub 链接已为 `[GitHub](...)` Markdown 超链接。
3. `data/raw/2026-04-28.json` 中所有入选项目的 `created_at` 都不早于 `2026-04-21`。

### 5. 本地验证

已执行：

```text
py -m unittest
py -m compileall main.py src tests scripts
```

验证结果：通过。

---

## 2026-04-28 追加：修正“本周最火爆”定义与 Kimi 降级原因

### 1. 用户纠正

用户指出：项目应当是一周内最火爆的项目，而不是生成时间或创建时间在一周之内的项目。

这是正确的。本项目的采集逻辑应以“最近一周活跃且热度高”为主，不能只看 `created_at`。

### 2. 采集逻辑修正

已将主查询从 `created:>=...` 改为 `pushed:>=...`：

```text
pushed:>=YYYY-MM-DD stars:>N
topic:ai pushed:>=YYYY-MM-DD stars:>N
topic:agent pushed:>=YYYY-MM-DD stars:>10
topic:llm pushed:>=YYYY-MM-DD stars:>10
topic:automation pushed:>=YYYY-MM-DD stars:>10
language:Python pushed:>=YYYY-MM-DD stars:>N
language:TypeScript pushed:>=YYYY-MM-DD stars:>N
created:>=YYYY-MM-DD stars:>10
```

其中 `created` 查询只作为补充，用于捕捉本周新出现且增长较快的项目。

### 3. 过滤逻辑修正

`Repository` 新增字段：

```text
pushed_at
```

处理阶段不再要求 `created_at >= since_date`，改为要求：

```text
pushed_at 或 updated_at >= since_date
```

这样老项目只要本周仍然活跃且热度高，也可以进入周报。

### 4. Kimi 降级原因判断

本次页面显示“ Kimi API 未启用或调用失败”的直接原因是：为了修正页面，我在本地执行了：

```text
py main.py
```

当前本地环境没有配置：

```text
KIMI_API_KEY
KIMI_MODEL
```

因此程序按设计生成降级版 Markdown 周报，并在 `data/runs/2026-04-28.json` 中记录：

```text
"kimi_used": false
"fallback_used": true
"report_error": "Kimi API 未配置"
```

这不是 GitHub Actions Secrets 失效。之前 GitHub Actions 自动归档提交 `3767552` 中的运行摘要显示：

```text
"kimi_used": true
"fallback_used": false
"telegram_sent": true
```

说明在 GitHub Actions 环境中，Kimi Secrets 曾经正常生效。

### 5. 当前页面重新生成

已重新执行：

```text
py main.py
py scripts/build_pages.py
```

当前 `2026-04-28` 页面已经按最近一周活跃项目重新生成。由于本地未配置 Kimi 和 Telegram，本次页面为降级版，且不会写入已推送状态。

### 6. 校验结果

已确认：

1. `data/raw/2026-04-28.json` 中所有入选项目的 `pushed_at` 或 `updated_at` 都不早于 `2026-04-21`。
2. 报告中没有“蟒蛇”。
3. 热门项目总览中的 GitHub 链接为 Markdown 超链接。

### 7. 本地验证

已执行：

```text
py -m unittest
py -m compileall main.py src tests scripts
```

验证结果：通过。

---

## 2026-04-28 追加：提高新增 Star 权重与完整链接显示

### 1. 用户要求

用户要求：

1. 将新增 Star 作为重要筛选依据。
2. 链接部分应显示完整链接，而不是只显示 `GitHub`。

### 2. 评分调整

已将综合评分权重调整为：

1. Star 增量：40%
2. 总 Star：25%
3. 兴趣主题匹配：20%
4. 活跃时间新鲜度：10%
5. Fork：5%

同时排序时增加明确的兜底顺序：

```text
score -> star_growth -> stargazers_count
```

这样新增 Star 会成为判断“本周最火爆”的主要依据。

### 3. 链接显示调整

周报中的 GitHub 链接统一显示为完整 URL，并保持可点击：

```text
[https://github.com/owner/repo](https://github.com/owner/repo)
```

报告清洗逻辑也会把模型生成的短文本链接：

```text
[GitHub](https://github.com/owner/repo)
```

转换为完整 URL 文本链接。

### 4. 本地验证

已补充测试，覆盖：

1. 新增 Star 对排序的优先影响。
2. 原始 GitHub URL 转换为完整 URL 文本链接。
3. `[GitHub](...)` 链接转换为完整 URL 文本链接。

已执行：

```text
py -m unittest
py -m compileall main.py src tests scripts
```

验证结果：通过。

### 5. 当前页面重新生成

已重新执行：

```text
py main.py
py scripts/build_pages.py
```

当前 `2026-04-28` 周报已按新增 Star 高权重重新排序，前两项为：

1. `NousResearch/hermes-agent`，新增 Star 25。
2. `affaan-m/everything-claude-code`，新增 Star 10。

报告和 Pages 页面中的链接均显示完整 URL。

---

## 2026-04-28 追加：第三阶段趋势总结

### 1. 开发目的

继续第三阶段产品化输出，增加数据驱动的趋势总结，减少周报趋势部分依赖模型自由发挥。

### 2. 本次实现

新增模块：

```text
src/trends.py
```

该模块根据本期入选仓库生成：

1. 入选项目总数。
2. 累计新增 Star。
3. 主要语言分布。
4. 项目方向分布。
5. 新增 Star 最高的项目列表。
6. 可直接写入周报的趋势要点。

### 3. 归档文件

新增归档路径：

```text
data/trends/YYYY-MM-DD.json
```

运行摘要新增字段：

```text
trend_summary_path
```

### 4. 报告生成变化

Kimi 生成周报时会收到 `trend_summary`。如果本地未配置 Kimi，降级版周报也会在“本周趋势”部分展示趋势要点。

### 5. 工作流变化

`.github/workflows/weekly.yml` 自动提交范围增加：

```text
data/trends
```

### 6. 本地验证

已补充测试：

1. `tests/test_trends.py`
2. `tests/test_reporter.py` 中的趋势要点展示断言

---

## 2026-04-29 追加：阶段性代码审查记录

### 1. 审查目的

在趋势总结功能提交后，对当前代码进行阶段性审查，确认已经实现的能力、仍存在的风险点，以及下一步开发优先级。

本次审查范围包括：

1. `main.py`
2. `src/collector.py`
3. `src/processor.py`
4. `src/reporter.py`
5. `src/settings.py`
6. `src/state.py`
7. `src/trends.py`
8. `.github/workflows/weekly.yml`
9. 现有测试文件

### 2. 已确认实现的能力

当前项目已经实现：

1. GitHub 近期活跃仓库采集。
2. 仓库去重、过滤、评分和排序。
3. 新增 Star 历史记录与评分加权。
4. README 摘要抓取。
5. Kimi 中文周报生成。
6. Kimi 不可用时生成降级版 Markdown 周报。
7. Telegram 手机推送。
8. Telegram 不可用时保留归档。
9. 周报、原始数据、运行摘要和趋势总结归档。
10. GitHub Actions 定时运行、手动触发和自动提交归档。
11. GitHub Pages 周报归档页面。
12. 单元测试覆盖核心采集、处理、报告、状态和趋势逻辑。

本地验证结果：

```text
py -m unittest
```

结果：20 个测试全部通过。

### 3. 本次审查发现

#### 问题 1：仍保留 `created` 查询，可能继续偏向“新建项目”

位置：

```text
src/collector.py:27
```

说明：

用户已经明确要求关注“一周内最火爆的项目”，而不是“这一周新创建的项目”。当前仍保留：

```text
created:>=... stars:>10
```

该查询会额外引入新建项目。虽然后续会经过活跃时间过滤，但它仍可能影响候选池来源。

建议：

1. 下一步移除该查询；或
2. 将其作为低权重补充来源，并在运行摘要中标明。

#### 问题 2：部分 GitHub 查询失败不会进入运行摘要

位置：

```text
src/collector.py:83-90
```

说明：

当前逻辑只有在所有查询都失败时才抛出错误。如果部分查询失败、部分成功，错误会被内部收集但不会写入 `data/runs/YYYY-MM-DD.json`。

影响：

1. 周报可能正常生成，但采集结果不完整。
2. 后续无法从运行摘要中判断是否发生 GitHub API 限流、网络异常或查询语法问题。

建议：

将部分查询失败记录写入 `RunSummary`，例如新增：

```text
collector_errors
```

#### 问题 3：只读取 example 配置，不利于自定义兴趣配置

位置：

```text
src/settings.py:49
```

说明：

当前 `load_settings` 固定读取：

```text
config/interests.example.json
```

这会让示例配置承担真实配置职责，不利于用户长期维护自己的兴趣偏好。

建议：

优先读取：

```text
config/interests.json
```

如果不存在，再回退到：

```text
config/interests.example.json
```

#### 问题 4：`data/raw` 实际写入的是筛选后项目

位置：

```text
main.py:41
```

说明：

当前调用：

```text
write_raw_repositories(selected, settings)
```

写入的是最终入选项目，而不是原始采集结果。`raw` 命名容易误导后续调试。

建议：

二选一处理：

1. 如果要保留真正原始采集结果，应写入 `collected`。
2. 如果只想保留入选项目，应将函数或目录命名调整为 `selected`。

### 4. 下一步建议

下一步优先处理：

1. 修正采集查询，移除或弱化 `created` 查询。
2. 增强运行摘要，记录部分采集失败。
3. 增加 `config/interests.json` 用户配置优先级。
4. 明确 `data/raw` 与入选项目归档的命名和职责。

这些改动属于数据质量和可观测性增强，不需要推翻现有架构。

---

## 2026-04-29 追加：代码审查问题修复

### 1. 修复范围

根据阶段性代码审查的下一步建议，本次继续处理数据质量和可观测性问题。

### 2. 采集查询修正

已从 `src/collector.py` 中移除：

```text
created:>=... stars:>10
```

当前采集查询只围绕最近一周 `pushed` 活跃项目展开，避免候选池继续偏向“本周新创建项目”。

### 3. 部分采集失败记录

`collect_repositories` 现在会返回：

```text
repositories
queries
errors
```

如果部分 GitHub 查询失败但仍有其他查询成功，程序会继续生成周报，同时把错误写入运行摘要：

```text
collector_errors
```

这样后续可以从 `data/runs/YYYY-MM-DD.json` 判断采集是否完整。

### 4. 自定义兴趣配置

`src/settings.py` 新增用户配置优先级：

1. 优先读取 `config/interests.json`。
2. 如果不存在，再读取 `config/interests.example.json`。

这样用户可以维护自己的兴趣配置，不需要直接修改示例文件。

### 5. 归档职责明确

本次将原始候选数据和最终入选数据拆开：

1. `data/raw/YYYY-MM-DD.json`：保存本次 GitHub API 采集到的原始候选仓库。
2. `data/selected/YYYY-MM-DD.json`：保存最终入选周报的仓库。

`.github/workflows/weekly.yml` 的自动提交范围也已加入：

```text
data/selected
```

### 6. 测试补充

新增和更新测试：

1. 采集查询不再包含 `created` 条件。
2. 部分采集失败会返回错误列表。
3. `config/interests.json` 优先于示例配置。
4. `data/raw` 和 `data/selected` 写入不同路径。

---

## 2026-04-29 追加：配置说明补充

### 1. 补充原因

代码已经支持优先读取 `config/interests.json`，但配置文档中还没有说明该文件的用途和提交方式。

### 2. 本次更新

已更新：

```text
docs/setup.md
```

新增内容：

1. `config/interests.json` 的读取优先级。
2. `preferred_topics`、`preferred_languages`、`exclude_keywords`、`max_projects`、`min_stars` 的用途。
3. 如果希望 GitHub Actions 使用自定义兴趣配置，需要将 `config/interests.json` 提交到仓库。
4. `config/interests.json` 不应包含任何 API Key、Token 或 Chat ID。

### 3. 处理结论

本次不把 `config/interests.json` 加入 `.gitignore`。原因是该文件不是密钥文件，并且 GitHub Actions 需要从仓库读取它才能使用自定义偏好。

---

## 2026-04-29 追加：GitHub Actions 真实运行复测

### 1. 复测结果

已通过 GitHub CLI 手动触发每周周报工作流：

```text
https://github.com/windsky922/githubzhuaqu/actions/runs/25087537033
```

运行结论：成功。

关键结果：

1. `collected_count`: 210
2. `selected_count`: 10
3. `collector_errors`: []
4. `readme_fetched_count`: 10
5. `telegram_sent`: true
6. `raw_repositories_path`: `data/raw/2026-04-29.json`
7. `selected_repositories_path`: `data/selected/2026-04-29.json`
8. `trend_summary_path`: `data/trends/2026-04-29.json`

### 2. 发现的问题

本次 Kimi 调用超时，运行摘要记录：

```text
"report_error": "The read operation timed out"
```

因此本次周报使用降级模板生成，但主流程、Telegram 推送和归档均成功。

### 3. 修复动作

已将 Kimi 请求超时时间从固定 60 秒调整为可配置项：

```text
KIMI_TIMEOUT_SECONDS
```

默认值为：

```text
120
```

同时更新 `.env.example` 和 `docs/setup.md`。

---

## 2026-04-29 追加：GitHub Actions Node 24 兼容更新

### 1. 触发原因

GitHub Actions 运行时提示 `actions/checkout@v4` 和 `actions/setup-python@v5` 仍运行在 Node.js 20。GitHub 已提示 Node.js 20 actions 将被弃用。

### 2. 官方版本确认

已确认官方 action 新版本：

1. `actions/checkout@v6`：支持 Node 24。
2. `actions/setup-python@v6`：支持 Node 24。

### 3. 本次调整

已更新：

```text
.github/workflows/weekly.yml
```

调整内容：

```text
actions/checkout@v4 -> actions/checkout@v6
actions/setup-python@v5 -> actions/setup-python@v6
```

### 4. 预期效果

后续每周周报工作流不再触发 Node.js 20 action 弃用警告。

---

## 2026-04-29 追加：Kimi 内容过滤降级修复

### 1. 问题现象

用户在 GitHub 网页手动触发工作流后，工作流本身运行成功，但生成的是降级版周报。

运行摘要显示：

```text
"kimi_used": false
"fallback_used": true
"report_error": "Kimi API error 400: ... high risk ... content_filter"
```

### 2. 原因判断

这次不是超时，也不是 Secrets 未配置。Kimi API 返回了内容过滤错误，说明请求中的提示词或项目数据被判定为高风险。

最可能的触发源是某个入选仓库的 README 摘要包含模型安全策略不接受的原文内容。

### 3. 修复动作

已在 `src/reporter.py` 中增加安全重试：

1. 第一次仍使用完整项目数据，包括 README 摘要。
2. 如果 Kimi 返回 `content_filter` 或 `high risk`，自动重试一次。
3. 重试时移除 `readme_excerpt`，只保留仓库名称、简介、语言、Star、Fork、链接、分类、趋势摘要等结构化信息。
4. 如果重试成功，则不再生成降级版周报。
5. 如果重试仍失败，才保留原有降级逻辑，避免整个工作流中断。

### 4. 说明

外部模型 API 仍可能因为服务不可用、限流或更严格的安全策略失败，因此无法绝对保证永远不出现降级版。但本次修复已经针对当前真实失败原因做了兜底，能显著降低因 README 原文触发内容过滤而降级的概率。

### 5. 测试补充

已增加测试：当第一次 Kimi 调用返回 `content_filter high risk` 时，程序会自动以不包含 README 摘要的 payload 重试，并在重试成功时返回 Kimi 周报。

---

## 2026-04-29 追加：Codex 技能封装

### 1. 开发目的

路线图第三阶段最后一项是“在项目流程稳定后，再封装真正可用的 Codex 技能”。当前采集、筛选、Kimi 周报、Telegram 推送、归档和 GitHub Actions 已完成多次真实运行验证，因此开始封装技能。

### 2. 本次实现

新增技能目录：

```text
skills/github-weekly-agent/
```

核心文件：

```text
skills/github-weekly-agent/SKILL.md
```

技能内容覆盖：

1. 项目维护约束。
2. 主流程。
3. 目录职责。
4. 采集与排序修改规范。
5. 周报生成修改规范。
6. 归档和 GitHub Pages 修改规范。
7. GitHub Actions 修改规范。
8. 本地验证和真实链路验证方式。

### 3. 简洁性处理

本次只创建必要的技能说明，不增加脚本、模板或资产，避免重复维护已有项目代码。

### 4. 路线图更新

`docs/roadmap.md` 中第三阶段 Codex 技能封装标记为已完成。

---

## 2026-04-29 追加：未来更新规划

### 1. 规划目的

当前前三阶段已经完成，项目具备稳定的采集、筛选、Kimi 周报、Telegram 推送、归档、GitHub Pages 和 Codex 技能能力。

为了避免后续开发直接堆到主流程中，本次补充长期更新路线和架构边界。

### 2. 新增文档

新增：

```text
docs/future-plan.md
```

该文档规划：

1. 数据质量增强。
2. 多数据源采集。
3. 报告质量增强。
4. 推送渠道扩展。
5. 展示页面增强。
6. 长期状态和 SQLite 评估。
7. 短期、中期、长期优先级。
8. 暂不建议做的事项。

### 3. 同步更新

已更新：

1. `docs/roadmap.md`：增加第四阶段和第五阶段。
2. `docs/architecture.md`：增加后续扩展边界。
3. `docs/index.md`：增加未来更新规划入口。

### 4. 设计结论

后续不应提前重构为复杂框架。当前主流程保持稳定，只有当某类能力开始包含多个实现或明显变复杂时，再拆出 `sources`、`quality`、`report_checks`、`channels`、`storage` 等模块。

---

## 2026-04-29 追加：安全检查基础版本

### 1. 用户要求

用户要求在未来规划中加入安全性检查功能，用于检查项目是否存在安全风险，同时对当前工作方式做安全保护。

### 2. 当前安全状态检查

已检查：

1. GitHub CLI 当前未登录，本机没有继续保留 CLI 登录态。
2. 当前进程环境中未发现 `TOKEN`、`KEY`、`SECRET`、`CHAT_ID` 等密钥类环境变量名。
3. 本次操作不读取、不输出任何真实密钥值。

### 3. 本次实现

新增：

```text
scripts/security_check.py
tests/test_security_check.py
```

能力：

1. 扫描源码、配置、workflow、文档和提示词中的疑似硬编码密钥。
2. 检测 GitHub token、Telegram Bot Token、通用 key/token/secret/password/chat_id 赋值。
3. 允许 GitHub Actions Secrets 引用和 `os.getenv` 这类安全读取方式。
4. 排除 `data/` 和 `reports/`，避免把第三方 README 或生成报告误判为项目自身密钥。

### 4. 工作流接入

`.github/workflows/weekly.yml` 新增步骤：

```text
python scripts/security_check.py
```

该步骤在单元测试前运行。如果发现疑似硬编码密钥，工作流会失败，阻止继续生成和提交归档。

### 5. 未来规划更新

`docs/future-plan.md` 新增“安全风险检查”阶段，后续会扩展到入选仓库风险提示，例如可疑关键词、异常 Star 增长、许可证缺失和维护风险。

---

## 2026-04-29 追加：入选仓库安全风险提示

### 1. 开发目的

在项目自身密钥扫描之后，继续增加入选仓库的安全风险提示能力。该能力用于提醒用户关注潜在风险，不对第三方项目做安全背书。

### 2. 本次实现

新增：

```text
src/security.py
tests/test_security.py
```

`Repository` 新增字段：

```text
security_flags
```

主流程在抓取 README 后，对最终入选仓库执行：

```text
apply_security_flags(selected)
```

### 3. 当前检查范围

当前只做元数据级检查：

1. 缺少许可证。
2. 仓库已归档。
3. 仓库是 fork。
4. 名称、简介、主题或 README 摘要中包含明显风险关键词，例如空投、赠送、破解、窃取、恶意软件、钓鱼。

### 4. 报告变化

降级版周报的重点项目分析中新增：

```text
风险提示
```

Kimi 周报生成也会收到 `security_flags` 字段，可用于生成更谨慎的项目说明。

### 5. 安全边界

本功能不会执行第三方仓库代码，不会下载或运行项目依赖，也不会把项目判定为安全。风险提示只作为人工复核线索。

---

## 2026-04-29 追加：入选原因记录

### 1. 开发目的

继续第四阶段质量与可观测性增强，增加每个入选项目的解释字段，让用户知道项目为什么进入周报。

### 2. 本次实现

`Repository` 新增字段：

```text
selection_reasons
```

`src/processor.py` 会根据以下信号生成入选原因：

1. 新增 Star。
2. 当前累计 Star。
3. 主题、语言或名称与关注方向匹配。
4. 最近一周仍有更新或维护活动。

### 3. 报告变化

降级版周报在重点项目分析中新增：

```text
入选原因
```

Kimi 提示词也已更新，要求优先使用 `selection_reasons` 解释项目为什么值得关注，并结合 `security_flags` 保持谨慎表述。

### 4. 归档变化

`data/selected/YYYY-MM-DD.json` 会保存每个项目的 `selection_reasons` 字段，为后续报告质量检查和页面展示提供基础数据。

---

## 2026-04-29 追加：报告质量检查

### 1. 开发目的

继续第四阶段质量与可观测性增强，降低 Kimi 输出缺项、链接格式错误或语言翻译不当的概率。

### 2. 本次实现

新增：

```text
src/report_checks.py
tests/test_report_checks.py
```

当前检查范围：

1. 报告中不能出现“蟒蛇”这类不合适的技术语言翻译。
2. 每个入选项目的完整仓库名必须出现在报告中。
3. 每个入选项目的 GitHub 链接必须以完整 URL 的 Markdown 链接形式出现。

### 3. 主流程变化

Kimi 输出会先经过：

```text
normalize_report_markdown
check_report_quality
```

如果质量检查失败，程序会记录 `report_error`，并回退到规则周报，避免把结构不完整的模型输出推送给用户。

### 4. 后续空间

后续可以继续增强：

1. 检查报告是否包含非入选项目。
2. 对结构问题增加 Kimi 自动重试，而不是直接回退。
3. 检查每个项目是否包含入选原因和风险提示。

---

## 2026-04-29 追加：采集分项统计

### 1. 开发目的

继续第四阶段质量与可观测性增强。此前运行摘要只记录 `collector_errors`，无法清楚看到每条 GitHub Search 查询的成功、失败和返回数量。

### 2. 本次实现

`collect_repositories` 现在返回：

```text
repositories
queries
errors
stats
```

运行摘要新增字段：

```text
collector_stats
```

每条统计包含：

1. `query`：查询条件。
2. `status`：`success` 或 `failed`。
3. `count`：返回仓库数量。
4. `error`：失败原因。

### 3. 价值

后续可以从 `data/runs/YYYY-MM-DD.json` 直接判断：

1. 哪些查询成功。
2. 哪些查询失败。
3. 每条查询贡献了多少候选仓库。
4. 是否存在 GitHub API 限流、网络异常或查询语法问题。

该结构也为后续 GitHub Trending、GraphQL API 等多数据源扩展预留了统计入口。

---

## 2026-04-29 追加：GitHub Pages 首页摘要增强

### 1. 开发目的

继续第四阶段质量与可观测性增强，让 GitHub Pages 首页不只显示周报列表，也能快速看到最新运行状态和趋势要点。

### 2. 本次实现

更新：

```text
scripts/build_pages.py
tests/test_build_pages.py
```

首页新增：

1. 最新运行摘要。
2. 入选项目数。
3. 采集候选数。
4. 生成方式。
5. Telegram 推送状态。
6. 采集错误数量。
7. 最新趋势要点。

### 3. 数据来源

首页读取：

```text
data/runs/YYYY-MM-DD.json
data/trends/YYYY-MM-DD.json
```

### 4. 设计边界

本次仍保持 GitHub Pages 为轻量 Markdown，不引入前端框架。后续当历史周报数量增加后，再考虑筛选、项目卡片和趋势可视化。

---

## 2026-04-29 追加：历史周报趋势摘要

### 1. 开发目的

继续增强 GitHub Pages 的浏览效率，让“全部周报”列表不仅显示日期和推送状态，也能快速看出每期的主要语言、主要方向和新增 Star。

### 2. 本次实现

更新：

```text
scripts/build_pages.py
tests/test_build_pages.py
```

`docs/index.md` 的每条历史周报记录会在存在趋势数据时追加：

1. 主语言。
2. 主方向。
3. 累计新增 Star。

### 3. 数据来源

该信息来自：

```text
data/trends/YYYY-MM-DD.json
```

如果历史周报没有趋势数据，则保持原有简洁格式。

---

## 2026-04-29 追加：历史项目索引

### 1. 开发目的

继续增强 GitHub Pages 浏览能力，让用户不只按周报日期回看，也能在一个页面中查看历次入选项目。

### 2. 本次实现

`scripts/build_pages.py` 新增生成：

```text
docs/projects.md
```

该页面从以下目录读取数据：

```text
data/selected/
```

并生成历史项目表格，包含：

1. 日期。
2. 项目名称。
3. 方向。
4. 语言。
5. Star。
6. 新增 Star。
7. 风险提示数量。
8. 完整 GitHub 链接。

### 3. 首页入口

`docs/index.md` 的项目文档区域新增：

```text
历史项目索引
```

### 4. 设计边界

本次仍保持 Markdown 页面，不引入前端框架。后续如果历史项目明显增多，再考虑按语言、方向、日期生成更细的分组页面。

---

## 2026-04-29 追加：GitHub Trending 第一优先级采集

### 1. 用户要求

用户明确希望以 GitHub Trending 作为热点考核的第一指标，其余信号作为辅助，同时保留垂直方向配置，方便后续做个性化调整。

### 2. 架构判断

本次没有提前拆出新的 `src/sources/` 目录，而是在现有 `src/collector.py` 中接入 Trending。原因是当前只有两个来源：GitHub Trending 和 GitHub Search API，直接在采集层扩展更简洁；等后续接入 GraphQL、自定义仓库列表或更多来源时，再拆分来源模块。

当前数据源定位：

1. GitHub Trending 周榜：第一优先级候选来源。
2. GitHub Search API：辅助候选来源，主要用于补充垂直方向和 Trending 遗漏项目。
3. 后续预留：GraphQL 细粒度热度、用户自定义关注仓库。

### 3. 本次实现

更新：

```text
src/models.py
src/collector.py
src/processor.py
config/interests.example.json
tests/test_collector.py
tests/test_processor.py
docs/architecture.md
docs/future-plan.md
docs/setup.md
```

新增仓库字段：

1. `sources`：记录项目来自 `github_trending`、`github_search` 或多个来源。
2. `trending_rank`：记录项目在 GitHub Trending 周榜中的排名。
3. `trending_period`：当前为 `weekly`。
4. `source_priority`：用于保留来源优先级，Trending 高于 Search。

采集流程调整为：

```text
GitHub Trending weekly
-> GitHub Search API 辅助查询
-> 去重并合并来源信号
-> 过滤最近一周活跃项目
-> 综合评分排序
```

### 4. 评分调整

当前默认评分权重：

1. `trending`：45%。
2. `star_growth`：25%。
3. `topic`：15%。
4. `freshness`：10%。
5. `community`：5%。

其中 `community` 由总 Star 和 Fork 共同构成。该设计把 Trending 作为第一指标，同时保留新增 Star、垂直方向匹配、近期活跃和社区基础信号。

### 5. 个性化预留

`config/interests.example.json` 新增：

1. `enable_github_trending`：是否启用 Trending。
2. `trending_languages`：额外采集指定语言的 Trending 榜。
3. `trending_max_repositories`：限制每个 Trending 榜补齐详情的项目数。
4. `search_topics`：Search API 的 topic 补充方向。
5. `search_languages`：Search API 的语言补充方向。
6. `score_weights`：综合评分权重。

后续用户可以通过 `config/interests.json` 调整这些字段，不需要改主流程代码。

---

## 2026-04-29 追加：Trending 信号展示增强

### 1. 开发目的

上一轮已经把 GitHub Trending 周榜作为第一优先级候选来源。本轮继续补齐可见性：让周报、趋势摘要和 GitHub Pages 历史项目索引都能直接看到项目来源与 Trending 排名，方便判断排序是否符合“Trending 优先”的设计。

### 2. 本次实现

更新：

```text
prompts/weekly_report.md
src/reporter.py
src/trends.py
scripts/build_pages.py
tests/test_reporter.py
tests/test_trends.py
tests/test_build_pages.py
```

具体变化：

1. Kimi 提示词要求优先解释 `trending_rank`，并说明 `sources` 来源。
2. 降级周报的项目总览新增“来源”和“Trending 排名”。
3. 重点项目分析新增“热度来源”。
4. 趋势摘要新增 `trending_project_count` 和 `top_trending`。
5. GitHub Pages 历史项目索引新增“来源”和“Trending 排名”列。

### 3. 设计边界

本次只增强展示与摘要，不改变采集排序逻辑。排序逻辑仍由上一轮的 `score_weights` 控制，后续可以通过 `config/interests.json` 调整权重。

---

## 2026-04-29 追加：Trending 页面非仓库链接过滤

### 1. 问题来源

检查 GitHub Actions 自动归档回来的 `data/runs/2026-04-29.json` 后发现，GitHub Trending 采集已经生效，但页面解析器把部分非仓库链接也当成仓库，例如：

```text
sponsors/explore
apps/dependabot
apps/github-actions
```

这些路径不是普通仓库，调用 GitHub 仓库详情 API 时会返回 404，导致运行摘要中出现不必要的 `collector_errors`。

### 2. 本次修复

更新：

```text
src/collector.py
tests/test_collector.py
```

修复方式：

1. 在 Trending 链接解析阶段过滤 `sponsors`、`apps`、`users`、`settings` 等非仓库路径前缀。
2. 保留真实仓库路径解析逻辑，不改变 Trending 优先级和评分逻辑。
3. 增加单元测试，确保 `sponsors/explore` 和 `apps/dependabot` 不会进入 Trending 仓库候选列表。

### 3. 预期效果

下一次 GitHub Actions 运行时，Trending 来源的 404 噪声应明显减少。若 GitHub 页面结构继续变化，后续再考虑把解析规则收紧到 Trending 项目卡片区域。

---

## 2026-04-29 追加：Trending 标题区域解析收紧

### 1. 开发目的

上一轮通过过滤非仓库路径减少了 Trending 采集噪声。本轮继续收紧解析边界，避免未来 GitHub Trending 页面新增其他两段式链接时再次被误判为仓库。

### 2. 本次实现

更新：

```text
src/collector.py
tests/test_collector.py
```

解析规则从“读取页面中所有形如 `/owner/repo` 的链接”调整为：

```text
只读取 article 内 h2 标题区域中的仓库链接
```

这样可以更贴近 GitHub Trending 项目卡片结构，避免页面导航、赞助入口、应用入口或项目卡片内部的辅助链接进入候选池。

### 3. 测试补充

测试中新增了以下噪声链接：

```text
/outside/not-repository
/inside/not-repository
```

确认它们不会被解析为 Trending 候选仓库。

---

## 2026-04-29 追加：架构、安全与冗余审查

### 1. 审查范围

本次审查了当前主流程和核心模块：

```text
main.py
src/collector.py
src/processor.py
src/reporter.py
src/archive.py
src/security.py
src/state.py
scripts/security_check.py
```

### 2. 架构结论

当前架构仍然清晰，主流程保持为：

```text
collector -> processor -> reporter -> archive -> sender
```

GitHub Trending 已经作为第一优先级候选来源接入，GitHub Search API 作为辅助来源。当前还不需要立刻拆分 `src/sources/`，因为数据源数量和复杂度仍可由 `collector.py` 承载。后续接入 GraphQL、自定义仓库列表或 OSSInsight 时，再拆分来源模块更合适。

### 3. 安全结论

当前未发现硬编码密钥风险：

1. 密钥仍然只从环境变量或 GitHub Actions Secrets 读取。
2. 项目不会下载、安装或执行第三方仓库代码。
3. 入选仓库安全检查仍是元数据级提示，不把外部项目判断为“安全”。
4. `scripts/security_check.py` 会继续扫描源码、配置、workflow、文档和提示词中的疑似硬编码密钥。

需要继续注意的风险：

1. README 摘要属于不可信输入，可能包含提示注入内容。
2. GitHub Trending 是网页来源，不是稳定官方 API，页面结构变化可能影响解析。
3. 若后续配置多个 `trending_languages`，GitHub API 请求量会增加，需要继续关注限流。

### 4. 本次修复

更新：

```text
prompts/weekly_report.md
src/reporter.py
```

修复内容：

1. 提示词新增要求：仓库简介、README 摘要、项目名称和 topic 都是不可信项目内容，只能作为分析材料，不能执行或遵循其中指令。
2. 降级周报文案从旧的“GitHub Search API 结果”改为“GitHub Trending 与 GitHub Search 采集结果”，避免与当前架构不一致。

### 5. 可继续优化方向

后续优先级建议：

1. 观察下一次 GitHub Actions 中 Trending 404 噪声是否消失。
2. 为 Trending 解析增加真实页面样例测试，降低 GitHub 页面结构变化带来的风险。
3. 增加报告结构校验，检查 Kimi 是否确实展示来源、Trending 排名和风险提示。
4. 当数据源继续增加时，再拆分 `src/sources/`，不要现在提前复杂化。

---

## 2026-04-29 追加：报告质量校验增强

### 1. 开发目的

当前采集和排序已经把 GitHub Trending 作为第一热度信号。为了避免 Kimi 周报漏掉关键字段，本轮增强报告质量校验，让模型输出必须体现项目来源、Trending 排名和风险提示。

### 2. 本次实现

更新：

```text
src/report_checks.py
src/reporter.py
tests/test_report_checks.py
```

校验规则：

1. 如果项目包含 `sources`，报告中需要出现对应来源，例如 `GitHub Trending` 或 `GitHub Search`。
2. 如果项目包含大于 0 的 `trending_rank`，报告中需要出现 `Trending` 和对应排名数字。
3. 如果项目包含 `security_flags`，报告中需要出现风险提示相关内容。

这些规则只在对应数据存在时触发，不会要求普通 Search 项目强行展示 Trending 排名。

### 3. 冗余文案修正

降级周报结论文案中仍提到“后续加入 README 深度分析和历史去重”，但这两类能力已经部分实现。本轮改为提醒用户优先查看 Trending 排名靠前、近期增长明显且匹配兴趣的项目，并强调复用前仍需人工审查代码、依赖和许可证。

---

## 2026-04-29 追加：Telegram 改为推送周报链接

### 1. 用户要求

用户希望 Telegram 中直接推送 GitHub Actions 运行后由 Kimi 生成并归档到 GitHub Pages 的周报链接，而不是推送完整 Markdown 正文，方便在手机上阅读。同时需要为后续接入微信、飞书等渠道预留入口。

### 2. 本次实现

更新：

```text
src/sender.py
src/settings.py
tests/test_sender.py
.env.example
docs/setup.md
docs/future-plan.md
```

具体变化：

1. `send_report` 不再把完整 Markdown 拆分发送到 Telegram。
2. 新增 `build_report_message`，统一构建短版推送消息。
3. 新增 `report_url`，用于生成周报公开访问链接。
4. 新增 `REPORT_BASE_URL` 配置，适配自定义域名、自定义 Pages 路径或未来其他展示入口。
5. 如果未配置 `REPORT_BASE_URL`，GitHub Actions 中会根据 `GITHUB_REPOSITORY` 自动推导 GitHub Pages 链接。

默认链接格式：

```text
https://<owner>.github.io/<repo>/weekly/YYYY-MM-DD.md
```

### 3. 后续渠道预留

当前仍保持 Telegram 单渠道，不提前创建复杂的 `channels` 框架。后续接入微信、飞书时，可以复用 `build_report_message` 和 `report_url`，只新增对应渠道的发送函数即可。

---

## 2026-04-29 追加：Trending 入选保底与 Telegram 超链接修复

### 1. 问题现象

用户反馈真实运行后仍然没有把 GitHub Trending 放在足够重要的位置，希望 Trending 周榜前 10 的项目至少有 7 个进入热点项目周报。同时 Telegram 推送中的周报地址不能直接点击，需要以超链接形式发送。

### 2. 原因判断

仅依赖评分权重仍可能让高 Star、高增长的 Search API 项目挤掉 Trending Top 10 项目。另一个隐藏原因是历史去重会在排序前过滤已推送项目，如果某个 Trending Top 10 项目之前发过，它会被挡在周报外。

Telegram 侧的问题是当前消息只发送纯文本地址，而且默认生成的是 `.md` 地址；GitHub Pages 更适合使用 `.html` 页面地址。

### 3. 本次实现

更新：

```text
src/processor.py
src/state.py
src/sender.py
config/interests.example.json
tests/test_processor.py
tests/test_state.py
tests/test_sender.py
docs/setup.md
docs/future-plan.md
```

具体变化：

1. `process_repositories` 新增 Trending Top 10 保底选择逻辑。
2. 默认 `min_trending_top10_projects` 为 `7`，即 Trending 前 10 中至少 7 个进入周报；如果可用项目不足 7 个，则保留实际可用数量。
3. `filter_unsent_repositories` 对 Trending Top 10 项目放行，避免历史去重挡掉本周真正热门项目。
4. Telegram 消息改为 HTML 超链接：`打开本周周报`。
5. 周报链接从 GitHub Pages 的 `.md` 地址改为 `.html` 地址，更适合浏览器直接打开。

### 4. 设计边界

该规则只保护 Trending 周榜前 10，不取消其他 Search API 辅助项目。周报剩余名额仍按综合评分补齐，继续保留垂直方向和个性化调整空间。

---

## 2026-04-29 追加：Pages 历史项目索引提交范围修复

### 1. 问题来源

复核 workflow 时发现，`scripts/build_pages.py` 会生成：

```text
docs/projects.md
```

但 `.github/workflows/weekly.yml` 的自动提交范围只包含 `docs/index.md` 和 `docs/weekly`，没有包含 `docs/projects.md`。这会导致 GitHub Actions 运行后，历史项目索引可能没有随最新数据一起提交。

### 2. 本次修复

更新：

```text
.github/workflows/weekly.yml
```

将 `docs/projects.md` 加入自动提交范围，确保每次周报生成后，GitHub Pages 首页、周报页面和历史项目索引都能同步刷新。

---

## 2026-04-29 追加：Telegram 链接发送顺序调整

### 1. 问题来源

Telegram 已经改为推送 GitHub Pages 周报链接，但原流程是在 `main.py` 内生成报告后立即发送 Telegram。此时 `scripts/build_pages.py` 还没有生成 `docs/weekly/YYYY-MM-DD.md`，GitHub Actions 也还没有把页面提交到仓库，因此用户点击链接时可能遇到页面尚未发布的问题。

### 2. 本次调整

更新：

```text
main.py
scripts/send_report_link.py
.github/workflows/weekly.yml
tests/test_send_report_link.py
```

新的 Actions 顺序：

```text
python main.py（跳过 Telegram）
python scripts/build_pages.py
提交 reports/data/docs 归档
python scripts/send_report_link.py（发送 Pages 链接）
提交 data/runs 和 data/state 中的推送状态
```

### 3. 设计边界

1. 本地运行 `python main.py` 默认仍可直接尝试发送 Telegram，保持兼容。
2. GitHub Actions 中通过 `SKIP_TELEGRAM_SEND=true` 跳过主流程内发送，改由归档提交后的独立脚本发送。
3. 如果 Telegram 未配置或发送失败，脚本会记录状态，但不阻断已经完成的周报归档。

---

## 2026-04-30 追加：运行摘要记录 Telegram 周报链接

### 1. 开发目的

Telegram 改为推送 GitHub Pages 周报链接后，需要在运行摘要中记录实际发送的链接，方便从 GitHub 仓库直接排查本次推送是否指向正确页面。

### 2. 本次实现

更新：

```text
src/models.py
main.py
scripts/send_report_link.py
tests/test_send_report_link.py
```

新增运行摘要字段：

```text
telegram_report_url
```

该字段记录本次发送到 Telegram 的 GitHub Pages 周报页面地址，例如：

```text
https://windsky922.github.io/githubzhuaqu/weekly/YYYY-MM-DD.html
```

### 3. 使用价值

后续排查 Telegram 推送时，可以直接打开 `data/runs/YYYY-MM-DD.json`，确认：

1. `telegram_sent` 是否为 `true`。
2. `telegram_error` 是否为空。
3. `telegram_report_url` 是否是预期的周报页面。

---

## 2026-04-30 追加：GitHub Pages 内部链接修复

### 1. 开发目的

Telegram 已改为推送 GitHub Pages 的 `.html` 周报页面，但归档首页中仍使用 `weekly/YYYY-MM-DD.md` 作为周报入口。为了让手机端和 Pages 页面内的跳转路径保持一致，本次将页面导航链接统一改为最终网页地址。

### 2. 本次实现

更新：

```text
scripts/build_pages.py
tests/test_build_pages.py
```

调整内容：

1. 周报归档首页中的最新周报链接改为 `weekly/YYYY-MM-DD.html`。
2. 全部周报列表中的历史周报链接改为 `weekly/YYYY-MM-DD.html`。
3. 首页中的项目文档导航改为 `.html` 链接，适配 GitHub Pages 最终渲染页面。
4. 历史项目索引的返回链接改为 `index.html`。
5. 修复历史项目索引在暂无项目时的表格列数，避免表格结构不完整。

### 3. 验证方式

新增单元测试覆盖：

1. 首页是否输出 `.html` 周报链接。
2. 文档导航是否输出 `.html` 链接。
3. 暂无项目时，历史项目索引表格是否仍保持完整列数。

---

## 2026-04-30 追加：推送短消息结构预留

### 1. 开发目的

当前只需要 Telegram 推送，但后续可能接入微信、飞书或邮件。为了避免以后把 Telegram 的 HTML 文案复制到其他渠道，本次在不创建复杂 `channels/` 框架的前提下，先抽出统一的短消息结构。

### 2. 本次实现

更新：

```text
src/sender.py
tests/test_sender.py
```

新增：

```text
DeliveryMessage
build_delivery_message
```

字段说明：

1. `title`：周报标题。
2. `url`：GitHub Pages 周报链接。
3. `text`：纯文本消息，适合后续微信、飞书或邮件复用。
4. `html_text`：HTML 消息，当前 Telegram 使用它来发送可点击超链接。

### 3. 架构边界

本次没有提前创建 `src/channels/` 目录，也没有加入微信、飞书或邮件依赖。只有当第二个真实推送渠道接入时，再把各渠道发送函数拆出独立模块。

---

## 2026-04-30 追加：安全检查 allowlist 收紧

### 1. 开发目的

项目要求不能在代码中硬编码 API Key、Token、Chat ID 或任何密钥。原安全检查会对包含 `os.getenv(` 的整行直接放行，这在正常读取环境变量时没有问题，但如果有人写入带真实密钥的默认值，例如 `os.getenv("TOKEN", "真实 token")`，就可能被漏检。

### 2. 本次实现

更新：

```text
scripts/security_check.py
tests/test_security_check.py
```

调整内容：

1. allowlist 不再整行跳过所有规则。
2. 对 GitHub token 和 Telegram bot token 这类具有明确格式的密钥，始终执行检测。
3. 仍然允许 GitHub Actions Secrets 引用和环境变量示例通过通用配置检查，避免误报正常配置。
4. 新增测试覆盖 `os.getenv` 默认值中藏入 GitHub token 的情况。

### 3. 安全边界

该检查只能发现常见格式和明显硬编码的密钥，不能替代 GitHub Secret Scanning 或人工审查。后续如果接入更多外部服务，需要继续补充对应 token 格式规则。

---

## 2026-04-30 追加：排除生成周报目录的密钥误报

### 1. 开发目的

`docs/weekly/` 是由 `reports/` 同步生成的 GitHub Pages 周报目录，里面可能包含第三方仓库 README 摘要。安全检查的目标是保护本项目源码、配置和手写文档中不要硬编码密钥，不应把第三方生成内容误判为本项目自身泄漏。

### 2. 本次实现

更新：

```text
scripts/security_check.py
tests/test_security_check.py
```

调整内容：

1. 新增 `EXCLUDED_PATH_PREFIXES`，当前只排除 `docs/weekly/`。
2. 保留 `docs/setup.md`、`docs/operation-log.md` 等手写文档扫描。
3. 新增测试确认 `docs/weekly/` 中的疑似 token 会被跳过。
4. 新增测试确认普通 `docs/` 文档仍会被扫描。

### 3. 安全边界

该调整只处理误报来源，不降低对项目源码、workflow、配置、提示词和手写文档的检查强度。生成周报仍然会长期归档，因此后续可以考虑在报告生成阶段对 README 摘要做更保守的脱敏处理。

---

## 2026-04-30 追加：第三方内容入库前脱敏

### 1. 开发目的

周报会保存第三方仓库简介和 README 摘要。即使这些内容不是本项目自己的密钥，也不应该把疑似 token 原样写入 `reports/`、`data/selected/` 或 GitHub Pages 周报中。本次在采集边界增加脱敏，降低归档第三方敏感字符串的风险。

### 2. 本次实现

更新：

```text
src/security.py
src/collector.py
tests/test_security.py
tests/test_collector.py
```

新增：

```text
redact_sensitive_text
```

处理范围：

1. GitHub token 形态字符串。
2. Telegram bot token 形态字符串。
3. GitHub 仓库简介进入系统时脱敏。
4. README 摘要进入系统时脱敏。

### 3. 设计边界

该能力用于减少第三方内容归档风险，不改变安全扫描脚本的职责。后续如果接入更多服务，可以继续扩展 `redact_sensitive_text` 的模式列表。

---

## 2026-04-30 追加：报告生成层最终脱敏

### 1. 开发目的

采集层已经会对第三方仓库简介和 README 摘要做脱敏，但报告生成层仍需要最后一道保护，防止手工构造的数据、测试数据或模型输出绕过采集边界，把疑似密钥写入 Markdown 周报。

### 2. 本次实现

更新：

```text
src/reporter.py
tests/test_reporter.py
```

调整内容：

1. `normalize_report_markdown` 会先执行 `redact_sensitive_text`，再做链接和语言规范化。
2. `fallback_report` 返回前会做最终脱敏。
3. `_repository_payload` 会在发给 Kimi 前对 `description` 和 `readme_excerpt` 再次脱敏。
4. 新增测试覆盖报告归一化脱敏和 Kimi payload 脱敏。

### 3. 安全边界

该保护是“最后兜底”，不能替代采集层脱敏和仓库密钥扫描。未来如果报告中增加更多来自第三方的文本字段，应继续复用 `redact_sensitive_text`。
