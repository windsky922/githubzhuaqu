# GitHub Weekly Agent

GitHub Weekly Agent 是一个每周自动追踪 GitHub 热点项目的中文周报 Agent。当前版本以 [GitHub Trending](https://github.com/trending) 周榜作为第一优先级信号，结合 GitHub Search、Star 增量、主题匹配、近期活跃度、仓库质量信号和基础安全风险提示，生成中文周报并把 GitHub Pages 阅读链接推送到 Telegram。

项目目标不是简单按总 Star 排名，而是尽量识别“本周正在变热、值得关注、适合继续跟踪或学习”的项目。

## 当前能力

1. 每周通过 GitHub Actions 自动运行，也支持手动触发。
2. 采集 GitHub Trending 周榜，并保证 Trending 前 10 中至少 7 个有效项目进入热点周报候选结果。
3. 使用 GitHub Search API 作为辅助来源，保留 Java、Python、Agent 开发等垂直方向的补充能力。
4. 记录 Star 历史，用新增 Star 作为重要排序依据。
5. 对候选项目做去重、活跃度过滤、主题匹配、个性化方向匹配、重复入选新颖度提示、质量评分、风险提示和推荐理由生成。
6. 使用 Kimi 生成中文结构化周报；Kimi 不可用或质量检查失败时生成规则版周报。
7. 生成 GitHub Pages 可访问的 HTML 周报页面。
8. Telegram、飞书和企业微信只推送可点击链接，默认包含周报正文、项目筛选、运行状态和订阅配置入口，完整内容保存在仓库归档中。
9. 运行摘要、原始数据、入选项目、趋势摘要、公共 JSON、项目筛选页和周报都会归档。
10. 提供本仓库密钥扫描和外部项目基础安全风险提示。
11. 支持个性化 profile，例如 `java`、`python`、`agent_development`、`learning`、`developer_tools`。
12. 提供 FastAPI 后端接口，支持历史项目查询、单项目详情聚合、个性化推荐、订阅配置、运行记录、个性化方向和最新周报读取。
13. 推送消息已接入订阅配置入口；本地存在启用订阅时，会附加对应的个性化推荐链接。
14. 周报正文会读取启用订阅并追加“订阅推荐分区”，用于按个人方向拆分本期项目。
15. 后端支持按订阅编号预览推荐结果，后续 Telegram、微信、飞书和前端订阅页可以复用同一推荐入口。
16. 订阅配置页支持在本地 API 模式下直接预览每条订阅的推荐结果。
17. 本地任务执行器会写入任务审计事件，便于追踪 planned 任务从开始执行到成功或失败的完整过程。
18. 后端提供数据库概览接口，返回 SQLite 表计数、最近运行、任务状态、订阅状态、Top 语言/方向和 RAG 索引准备度。
19. 后端提供数据库趋势接口，返回近 N 次运行的入选数量、新增 Star、Trending 命中率、失败率和推送状态。
20. 后端提供数据库分面接口，返回语言、方向、来源、质量、风险和订阅偏好分布，为前端筛选、个性化推荐和后续 RAG 索引做准备。
21. 后端提供项目语料搜索接口，优先使用 SQLite FTS5 检索历史项目，并保留普通文本匹配回退，为后续向量检索、RAG 和 LangChain 编排打底。
22. 后端提供相似项目候选接口，基于 FTS5 召回，并结合语言、方向、来源、关键词和热度信号生成可解释的相似项目列表。
23. 项目详情页在本地后端或 `api=1` 模式下会展示后端相似项目候选、相似度分和相似原因。
24. 后端提供项目对比接口和前端对比页，可一次比较多个仓库的语言、方向、历史入选次数、Star 增长、Trending 排名、质量分和风险提示。

## 主流程

```text
GitHub Actions
-> main.py
-> collector
-> processor
-> reporter
-> archive
-> sender
```

当前仍保持单体 Python 主流程，避免过早引入复杂框架。新增 FastAPI 层只作为只读查询入口，不接管采集、生成和推送流程；后续当前端、数据库、多渠道推送变复杂后，再按模块拆分。

## 目录说明

| 路径 | 说明 |
|---|---|
| `main.py` | 主流程入口 |
| `src/collector.py` | GitHub Trending、Search、README 摘要采集 |
| `src/processor.py` | 去重、过滤、评分、入选项目选择 |
| `src/reporter.py` | Kimi 周报生成和规则版降级周报 |
| `src/report_checks.py` | 周报质量检查 |
| `src/quality.py` | 仓库质量信号、质量分和质量等级 |
| `src/security.py` | 脱敏和外部项目风险提示 |
| `src/personalization.py` | 个性化 profile 合并逻辑 |
| `src/sender.py` | 推送消息构造和通道发送，当前支持 Telegram、飞书和企业微信 Webhook |
| `src/api/` | 只读后端 API，用于查询历史项目、运行记录、个性化方向和最新周报 |
| `src/job_runner.py` | 执行 SQLite jobs 表中的计划任务 |
| `scripts/build_pages.py` | 生成 GitHub Pages 归档页面 |
| `scripts/create_planned_job.py` | 创建 planned 周报任务 |
| `scripts/migrate_json_to_sqlite.py` | 将历史 JSON 归档导入 SQLite 派生索引 |
| `scripts/verify_migration.py` | 校验 SQLite 派生索引和 JSON 归档计数 |
| `scripts/run_planned_job.py` | 执行一个 planned 周报任务 |
| `scripts/query_archive.py` | 按语言、方向、profile、来源、风险和关键词查询历史项目 |
| `scripts/send_report_link.py` | 推送 GitHub Pages 周报正文和项目筛选链接 |
| `scripts/check_delivery_channels.py` | 检查 Telegram、飞书、企业微信推送通道配置 |
| `scripts/security_check.py` | 本仓库疑似密钥扫描 |
| `config/interests.example.json` | 默认兴趣和评分配置示例 |
| `config/profiles.example.json` | 个性化方向配置示例 |
| `prompts/` | Kimi 提示词 |
| `reports/` | Markdown 周报归档 |
| `docs/` | GitHub Pages 页面和项目文档 |
| `data/runs/` | 每次运行摘要 |
| `data/raw/` | 采集结果归档 |
| `data/selected/` | 入选项目归档 |
| `data/trends/` | 趋势摘要归档 |
| `data/state/` | Star 历史和已推送状态 |

## GitHub Pages 展示页

当前 Pages 会生成：

```text
docs/index.md
docs/projects.md
docs/explorer.html
docs/recommendations.html
docs/subscriptions.html
docs/compare.html
docs/project.html
docs/runs.html
docs/jobs.html
docs/profiles.html
docs/projects.json
docs/runs.json
docs/jobs.json
docs/profiles.json
docs/feed.xml
docs/api.md
docs/core-development-plan.md
docs/v1-api-plan.md
docs/weekly/YYYY-MM-DD.md
```

其中 `explorer.html` 是轻量项目筛选页，默认读取 `projects.json` 和 `profiles.json`；在本地后端或 URL 带 `api=1` 时会优先读取 `/api/projects` 和 `/api/profiles`，失败后自动回退到静态 JSON。页面支持按关键词、日期、语言、个性化方向、来源、风险提示和排序方式筛选历史入选项目。页面会根据 profile 自动生成快捷视图按钮，筛选状态会同步到 URL，便于后续在 Telegram、微信、飞书或浏览器中分享同一个筛选视图。项目行支持展开详情，查看 README 精简摘要、推荐理由、质量信号、风险提示、项目指标、完整链接和相似历史项目。
`recommendations.html` 是个性化推荐页，支持 `recommendations.html?profile=agent_development` 或 `recommendations.html?language=Java&q=spring`。本地后端或 URL 带 `api=1` 时会优先读取 `/v1/recommendations`，否则使用 `projects.json` 静态筛选。页面预留 Agent 开发、Python、Java、后端、前端、AI 工具等快捷方向，后续可以继续接入用户订阅数据库。

`subscriptions.html` 是订阅配置页，支持在本地后端模式下保存、查看、启用和停用订阅偏好。订阅只保存 profile、语言、方向、关键词、排序、数量和通道名称，不保存 Token、Chat ID 或 Webhook。

`project.html` 是单项目详情页，支持 `project.html?repo=owner/name`，展示历史入选次数、首次和最近入选日期、累计新增 Star、最好 Trending 排名、质量提示、风险提示、历史趋势、历史入选记录和相似项目。本地后端或 URL 带 `api=1` 时会优先读取 `/api/projects/{owner}/{repo}`，否则使用 `projects.json` 静态聚合。

`compare.html` 是项目对比页，支持 `compare.html?repos=owner/a,owner/b`，也支持追加 `profile`、`language`、`category` 和 `q` 做个性化加权。本地后端或 URL 带 `api=1` 时会优先读取 `/v1/projects/compare`，否则使用 `projects.json` 静态聚合，展示推荐结论、对比矩阵、领先指标和缺失项目。项目筛选页、推荐页和项目详情页会提供直接进入对比的入口。

`runs.html` 是运行状态面板，直接读取 `runs.json`，用于查看 Kimi/规则版生成状态、Telegram 推送状态、采集成功率、Trending Top10 命中率和 README 抓取率。

`jobs.html` 是任务状态面板，直接读取 `jobs.json`，用于查看 planned、running、succeeded、failed 任务状态，以及任务输入、执行结果和错误摘要。

`profiles.html` 是个性化方向页，直接读取 `profiles.json`，展示 Java、Python、Agent 开发、学习型项目、开发者工具等方向，并提供一键打开对应项目筛选视图的入口。

`profiles.json` 是个性化方向公开配置，包含 Java、Python、Agent 开发、学习型项目、开发者工具等方向的公开标签、语言和主题关键词。筛选页会读取该文件生成“个性化方向”下拉框，后续前端也可以直接复用。

`feed.xml` 是 RSS 订阅入口，适合在 RSS 阅读器或后续自动化工具中订阅每周周报更新。
`api.md` 记录只读后端 API 的启动方式和接口说明，后续前端工程、数据库管理和个性化订阅会优先复用这层接口。
`core-development-plan.md` 记录后续核心功能优先建设路线，明确先建设后端服务化、数据层、Agent/RAG 和任务调度，再处理前端和末端体验优化。
`v1-api-plan.md` 记录 `/v1/*` 核心服务接口、任务状态模型和后续真实后台执行的演进路径。

## 公共 JSON

GitHub Pages 会额外生成两个公开 JSON，供后续前端、RSS、微信、飞书或外部脚本复用：

```text
docs/projects.json
docs/runs.json
docs/jobs.json
docs/profiles.json
```

说明：

1. `projects.json` 汇总历次入选项目的公开摘要字段，例如项目名、链接、README 精简摘要、语言、方向、来源、Trending 排名、新增 Star、推荐理由、质量分、质量等级、质量提示、风险提示、安全分和风险等级。
2. `runs.json` 汇总历次运行摘要的公开字段，例如运行日期、入选数量、采集数量、Kimi/降级状态、Telegram 状态、周报正文链接、项目筛选链接和趋势要点。
3. `jobs.json` 汇总公开任务状态字段，例如任务编号、状态、提交时间、完成时间、任务请求和执行结果摘要。
4. `profiles.json` 汇总公开个性化方向，例如方向名称、学习目标、偏好语言和主题关键词。
4. 这些文件只作为公开展示和订阅入口，不写入密钥、用户隐私或未脱敏配置。

## 个性化推荐

个性化推荐通过 profile 实现。用户后续可以在前端选择 Java、Python、Agent 开发等方向；当前阶段先用配置文件和环境变量表达这些选择。

示例：

```text
INTEREST_PROFILE=java,agent_development
```

上面的配置表示同时关注 Java 工程方向和 Agent 开发方向。程序会把对应 profile 中的语言、主题、搜索补充项和评分权重叠加到基础兴趣配置中。
入选项目会记录匹配到的个性化方向，例如“匹配当前个性化方向：Java 后端与工程实践、Agent 开发”，用于后续周报解释和前端筛选。

可用示例 profile 位于：

```text
config/profiles.example.json
```

如需自定义，可以新建：

```text
config/profiles.json
```

GitHub Actions 中建议把 `INTEREST_PROFILE` 配置为仓库变量：

```text
Settings -> Secrets and variables -> Actions -> Variables
```

注意：profile 配置不应包含 API Key、Token、Chat ID 或任何密钥。

## 必要配置

在 GitHub 仓库中进入：

```text
Settings -> Secrets and variables -> Actions
```

建议配置以下 Secrets：

| 名称 | 是否必须 | 说明 |
|---|---:|---|
| `GH_SEARCH_TOKEN` | 推荐 | 提高 GitHub API 访问额度 |
| `KIMI_API_KEY` | 可选 | 启用 Kimi 中文周报生成 |
| `KIMI_BASE_URL` | 可选 | 默认 `https://api.moonshot.cn/v1` |
| `KIMI_MODEL` | 可选 | Kimi 模型名称 |
| `TELEGRAM_BOT_TOKEN` | 可选 | 启用 Telegram 推送 |
| `TELEGRAM_CHAT_ID` | 可选 | Telegram 接收方 |
| `FEISHU_WEBHOOK_URL` | 可选 | 启用飞书机器人 Webhook 推送 |
| `WECHAT_WEBHOOK_URL` | 可选 | 启用企业微信机器人 Webhook 推送 |
| `WECOM_WEBHOOK_URL` | 可选 | 企业微信 Webhook 备用变量名；`WECHAT_WEBHOOK_URL` 为空时使用 |
| `REPORT_BASE_URL` | 可选 | 自定义周报公开访问地址 |

建议配置以下 Variables：

| 名称 | 说明 |
|---|---|
| `INTEREST_PROFILE` | 个性化方向，例如 `java,agent_development` |
| `REPORT_BASE_URL` | 如果不想放在 Secret 中，也可以作为普通变量配置 |
| `DELIVERY_CHANNELS` | 推送通道列表，例如 `telegram,feishu,wechat` |
| `KIMI_TIMEOUT_SECONDS` | Kimi 请求超时时间，可选 |
| `KIMI_MAX_RETRIES` | Kimi 临时错误重试次数，可选 |
| `KIMI_RETRY_SECONDS` | Kimi 临时错误重试等待秒数，可选 |

常用兴趣配置还包括：

| 名称 | 说明 |
|---|---|
| `min_trending_top10_projects` | Trending 前 10 中至少保留的项目数量，默认 `7` |
| `novelty_penalty_weight` | 已推送项目再次入选时的轻量新颖度惩罚，默认 `0.08`；Trending 前 10 项目不受该惩罚 |
| `score_weights` | Trending、新增 Star、主题、活跃度和社区基础信号的评分权重 |

Kimi 返回 `429`、过载或临时网关错误时会自动重试；多次重试仍失败时会生成规则版周报并继续推送。没有 Telegram 时仍会归档周报和运行摘要。

## 推送通道

当前支持 Telegram、飞书和企业微信 Webhook。程序内部已经把“消息构造”和“通道发送”分开，`DELIVERY_CHANNELS` 可以声明要启用的通道：

```text
DELIVERY_CHANNELS=telegram
```

如果配置为：

```text
DELIVERY_CHANNELS=telegram,feishu,wechat
```

需要同时在 Secrets 中配置 `FEISHU_WEBHOOK_URL` 和 `WECHAT_WEBHOOK_URL` 或 `WECOM_WEBHOOK_URL`。未配置的通道会被记录为跳过，不会导致周报生成失败。飞书和企业微信当前都只推送 GitHub Pages 周报链接，不推送完整 Markdown 正文。

本地检查通道配置：

```bash
python scripts/check_delivery_channels.py
```

严格检查模式会在启用通道缺少配置时返回失败，适合 GitHub Actions：

```bash
python scripts/check_delivery_channels.py --strict
```

## GitHub Pages

Telegram、飞书和企业微信推送的是 GitHub Pages 上的三个阅读入口：周报正文 `weekly/YYYY-MM-DD.html`、项目筛选 `explorer.html?date=YYYY-MM-DD` 和运行状态 `runs.html`。仓库需要手动启用一次 Pages：

```text
Settings -> Pages
Source: Deploy from a branch
Branch: weekly-archive
Folder: /docs
```

启用后，每次 workflow 运行都会刷新：

```text
docs/index.md
docs/projects.md
docs/weekly/YYYY-MM-DD.html
```

说明：`weekly-archive` 是 GitHub Actions 自动维护的归档分支。代码开发继续提交到 `main`，每周生成的 `docs/`、`reports/` 和 `data/` 会发布到 `weekly-archive`，这样 Actions 不会再频繁把 `main` 往前推进，日常开发提交冲突会明显减少。

默认周报链接格式：

```text
https://<owner>.github.io/<repo>/weekly/YYYY-MM-DD.html
```

## 本地运行

```bash
python -m unittest
python main.py
```

本地运行时，程序不会自动读取 `.env` 文件。需要测试真实 API 时，请先在当前终端手动设置环境变量。

## SQLite 派生索引

当前事实来源仍然是 `data/` 下的 JSON 归档。SQLite 只作为后续前端筛选、历史查询、趋势分析、任务状态和本地订阅配置的派生索引。

每次运行主流程后，程序会自动把 JSON 归档同步到 SQLite；如果同步失败，不会阻断周报生成和 Telegram 推送，错误会记录在运行摘要的 `sqlite_error` 字段中。

导入现有 JSON：

```bash
python scripts/migrate_json_to_sqlite.py
```

校验迁移结果：

```bash
python scripts/verify_migration.py
```

查询历史项目：

```bash
python scripts/query_archive.py --refresh --language Python --source github_trending --limit 10
python scripts/query_archive.py --profile agent_development --query workflow --format json
```

执行 planned 周报任务：

```bash
python scripts/create_planned_job.py --profile agent_development --days-back 7 --output .weekly-job.json
python scripts/run_planned_job.py --job-file .weekly-job.json
python scripts/run_planned_job.py
python scripts/run_planned_job.py --job-id preview:xxxx
```

如果任务请求中的 `dry_run` 为 `true`，执行时会跳过 Telegram 推送，适合本地验证。
如果任务请求中的 `dry_run` 为 `false`，必须同时提供 `confirm_delivery=true` 才允许真实推送；否则系统会自动降级为 `dry_run=true`，避免误触发。

GitHub Actions 的手动运行入口已经支持 `profile`、`days_back`、`skip_main_delivery` 和 `send_link`。其中 `skip_main_delivery=true` 时，主流程不直接推送 Telegram，而是由后续步骤统一推送 GitHub Pages 链接。

更多命令示例见 `docs/archive-query.md`。

默认数据库路径：

```text
data/github_weekly.sqlite
```

该数据库文件不提交到 GitHub；如需重建，重新运行迁移脚本即可。

可选环境变量：

| 名称 | 说明 |
|---|---|
| `SQLITE_INDEX_PATH` | 自定义 SQLite 派生索引路径 |
| `SKIP_SQLITE_INDEX` | 设置为 `true` 时跳过 SQLite 同步 |

## 安全约束

1. 不要把 API Key、Token、Chat ID 写入代码、文档或配置示例。
2. 密钥只能通过环境变量或 GitHub Actions Secrets 读取。
3. `scripts/security_check.py` 会在测试前扫描本仓库中的疑似密钥。
4. 外部仓库的简介和 README 摘要会做基础脱敏后再进入报告生成流程。
5. 外部项目风险提示只作为辅助判断，不代表项目已经被完整安全审计。

## 后续发展方向

近期重点：

1. 完善个性化 profile，让用户可以按 Java、Python、Agent 开发、学习型项目等方向精准订阅。
2. 继续观察 GitHub Trending 在 Actions 环境中的稳定性。
3. 强化推荐理由、质量信号和风险提示，让每个入选项目的原因更透明。
4. 继续改善 GitHub Pages 页面，但暂不引入复杂前端工程。

中期重点：

1. 强化 SQLite 数据库层，让运行记录、项目、趋势、任务、订阅和后续向量索引有稳定的数据边界。
2. 建设轻量前端，用于筛选历史项目、语言、方向、风险提示和 Trending 排名。
3. 在数据库结构稳定后接入 RAG 能力，例如基于项目 README 摘要、历史入选原因和用户订阅构建检索增强推荐；LangChain 只作为可选编排层，不提前绑定核心流程。
4. 为微信、飞书、邮件等推送渠道预留统一入口。
5. 通过更多质量指标补充判断，例如 Release 活跃度、Issue 状态、README 完整度、异常 Star 增长提示。
