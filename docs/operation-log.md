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
