# GitHub Weekly Agent

`main` 的每次 push 和所有 pull request 都会运行独立提交质量检查：Python 3.12 全量测试与安全检查、Node.js 22 前端类型检查/单元测试/生产构建、`docs/app` 构建产物一致性，以及两套 Chromium Playwright 回归。`npm run test:e2e` 使用本地固定 mock 覆盖桌面/手机界面状态；`npm run test:e2e:real` 使用真实 FastAPI、系统临时目录中的 SQLite 和确定性本地 RAG 覆盖同源静态应用、SSE、无状态追问、硬约束及管理鉴权。两套测试都不读取业务 Secrets，不运行采集、Kimi 或真实推送。

GitHub Weekly Agent 的长期定位是 GitHub 项目研究 Agent：持续采集热门仓库，沉淀项目知识库，通过 RAG 检索、相似项目比较、反馈记忆和推荐解释，帮助开发者判断哪些项目值得关注、学习、集成或持续跟踪。

当前版本仍保留每周热点周报作为稳定输出形态。系统以 [GitHub Trending](https://github.com/trending) 周榜作为第一优先级信号，结合 GitHub Search、Star 增量、主题匹配、近期活跃度、仓库质量信号和基础安全风险提示，生成中文周报，并把 GitHub Pages 阅读链接推送到 Telegram、飞书或企业微信。

项目目标不是简单按总 Star 排名，而是形成“采集项目 -> 建立知识库 -> RAG 检索解释 -> Agent 判断推荐 -> 用户反馈记忆 -> 订阅推送分发”的闭环。每周推送后续会作为可订阅模块存在，用于按用户关注方向定期分发项目研究结果和推荐摘要。

最新 V3 第一性原理对抗性审查、当前最大遗漏与整改路线见：[GitHub 项目研究 Agent V3 审查与路线图](docs/project-review-agent-v3-roadmap.md)。

新窗口继续开发的阅读顺序、当前基线、P0-11A 第一任务和完整验证命令见：[GitHub 项目研究 Agent V3 开发交接报告](docs/project-review-agent-v3-handoff.md)。

多 Agent 只读审查的角色分工、安全边界、汇总格式与实施后复核流程见：[多 Agent 只读审查协议](docs/multi-agent-review-protocol.md)。

V2 历史审查见：[GitHub 项目研究 Agent V2 审查与路线图](docs/project-review-agent-v2-roadmap.md)。

V1 产品闭环基线见：[GitHub 项目研究 Agent v1 审查报告](docs/project-review-agent-v1-roadmap.md)。

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
22. 后端提供 RAG 语料接口 `/v1/rag/corpus`，把历史项目语料输出为 `text + metadata + evidence`，为后续 embedding、向量库和 LangChain 检索器预留稳定入口。
23. 后端提供 RAG 检索接口 `/v1/rag/retrieve`，从 `rag_chunks` 召回短文本证据块，返回上下文、引用和可直接交给后续问答链的 `prompt_context`。
24. 后端提供可选本地 embedding 构建命令和向量检索接口 `/v1/rag/vector-search`，当前使用确定性 `local-hash-v1`，后续可替换真实 embedding 模型。
25. 后端提供 RAG 混合检索接口 `/v1/rag/hybrid-search`，合并 FTS5 文本召回和本地向量召回，按权重去重排序后输出统一证据块。
26. 后端提供 RAG 检索对比接口 `/v1/rag/search-compare`，同时比较 FTS5、向量和混合检索的命中项目、重叠率与推荐模式，为后续 RAG 评估和 Agent 自动选择检索策略打底。
27. 后端提供 RAG 检索评估接口 `/v1/rag/search-evaluation`，用固定或自定义查询样本批量评估三种检索模式的命中率、平均召回和推荐模式分布，并可在显式确认后把评估结果写入 SQLite jobs。
28. 后端提供 RAG 检索质量趋势接口 `/v1/rag/search-evaluation-trends`，从历史评估任务中汇总平均命中、零命中样本、推荐模式分布和覆盖项目变化。
29. GitHub Actions 每次运行后可自动创建并执行一次 RAG 检索质量评估 planned job，并在生成 Pages 前把评估结果写入 SQLite jobs，用于长期质量趋势观测。
30. 后端提供 RAG 解释接口 `/v1/rag/explain` 和证据约束问答接口 `/v1/rag/ask`，把召回证据整理为推荐解释、引用、模型回答、降级原因、风险提示和下一步动作，并支持 `fts5`、`vector`、`hybrid` 三种检索模式。
30.1 管理页提供 GPT 式证据约束 RAG 对话工作台，可连续提问并通过用户/助手气泡查看引用、证据、降级原因和质量闸门结果；对话历史只保存在浏览器 localStorage，不写入后端。
31. 后端会把 RAG 解释结果写入 SQLite `rag_explanations`，并通过 `/v1/rag/explanations` 查询历史解释、质量分、引用完整度和指定项目的解释历史。
32. 后端提供 RAG 质量概览接口 `/v1/rag/quality-summary`，汇总解释数量、平均质量分、质量分布和低质量样本。
33. 后端提供 RAG 覆盖缺口接口 `/v1/rag/coverage`，列出缺少证据块、embedding 或解释历史的项目，便于补库和后续 Agent 自动优化。
34. 后端提供 RAG 解释回填接口 `/v1/rag/backfill-explanations`、计划任务接口 `/v1/rag/backfill-plan` 和维护计划接口 `/v1/rag/maintenance-plan`，可按诊断结果创建语料重建、embedding 构建、解释回填或检索评估任务；默认 dry-run 预览，只有显式传入 `confirm_execution=true` 才允许写入 SQLite。
35. 后端提供 RAG 维护历史汇总接口 `/v1/rag/maintenance-report`，聚合语料重建、embedding 构建、解释回填和检索评估任务的状态、最近结果、计数变化和维护建议。
36. 后端提供单项目 RAG 聚合接口 `/v1/projects/{owner}/{repo}/rag`，一次返回项目摘要、结构化 `project_profile`、证据块、引用、prompt_context、解释历史和项目级解释质量摘要。
37. 后端提供相似项目候选接口，基于 FTS5 召回，并结合语言、方向、来源、关键词和热度信号生成可解释的相似项目列表。
38. 项目详情页在本地后端或 `api=1` 模式下会展示后端相似项目候选、相似度分和相似原因。
39. 后端提供项目对比接口和前端对比页，可一次比较多个仓库的语言、方向、历史入选次数、Star 增长、Trending 排名、质量分和风险提示。
40. 后端提供项目反馈接口 `/v1/feedback`，支持记录用户对单个仓库的评分、标签和备注，为后续个性化记忆、RAG 重排和推荐校准预留数据入口。
41. 推荐接口会读取 `project_feedback` 和项目级 `project_profile`，把正负反馈转换为 `preference_score` 和 `feedback_memory`，并生成 `recommendation_score`、`ranking_factors`、`feedback_reason`、`rag_reason` 和 `recommendation_reason`，让用户反馈、RAG 档案、质量信号、热度和风险共同影响推荐排序。
42. 单项目 RAG 聚合接口会返回 `feedback_memory` 和项目研究档案，便于项目详情页和后续 Agent 判断该项目是否值得继续跟踪。
43. 项目详情页在本地 API 模式下提供“有用 / 不适合 / 继续跟踪”反馈入口，写入 `/v1/feedback`，并展示项目级反馈记忆和 Agent 研究摘要。
44. 个性化推荐页会展示推荐分、评分因子、推荐解释、RAG 解释、`preference_score` 和反馈记忆摘要，并支持对推荐结果直接提交反馈后刷新排序。
45. 管理页会展示最近反馈记忆汇总和受反馈影响的推荐项目，便于检查反馈样本是否已经进入数据库并影响推荐链路。
46. 后端提供开发上下文索引接口 `/v1/dev-context/index`，可采集 README、API 文档、数据契约、操作日志、Git diff、测试输出和安全检查结果。
47. 后端提供开发上下文 FTS5 检索接口 `/v1/dev-context/search` 和索引运行详情接口 `/v1/dev-context/runs/{id}`，用于代码审查、运行诊断和历史追踪。
48. 管理页提供开发上下文索引与搜索入口，先完成本地 SQLite 记忆层，不引入复杂聊天 UI 或外部向量数据库。
49. 后端提供开发上下文问答接口 `/v1/dev-context/ask`，基于已索引的开发材料生成规则版回答、证据、引用、置信度和下一步动作，不依赖外部模型。
50. 管理页提供开发上下文问答入口，可直接询问测试诊断、最近变更、API/数据契约一致性、下一步开发和安全架构风险。
51. 开发上下文索引已接入 planned job：`POST /v1/dev-context/index-plan` 会创建 `kind=dev_context_index` 任务，可由 `scripts/run_planned_job.py` 或任务详情页执行。
52. GitHub Actions 每次周报和 RAG 评估后会在生成 Pages 前轻量刷新开发上下文索引，默认 `run_checks=false`，避免重复跑完整测试。
53. SQLite 新增 `project_agent_tasks`，保存项目级观察、风险复查、深度分析、订阅推送和继续跟踪任务，并使用稳定去重键避免周期任务重复创建。
54. 后端提供项目 Agent 任务查询、创建和状态更新接口；状态机覆盖 `planned`、`in_progress`、`completed`、`failed` 和 `cancelled`。
55. `/v1/recommendations` 为每个项目返回结构化 `next_actions`，已有活跃任务优先复用任务记忆，没有任务时根据风险、质量和推荐分生成建议。
56. 每周 SQLite 同步会为最新入选项目自动生成去重任务；任务原因和执行结果会写入项目 RAG 语料。
57. 项目详情页可以创建建议任务、开始任务和完成任务；管理页汇总项目 Agent 任务、状态和覆盖项目数。推送任务通过 `subscription_action` 与现有订阅模块保持边界。
58. 项目 Agent 任务提供只读执行引擎：支持机器可读预检查、并发阻止、失败重试、逐次运行审计以及结构化证据和引用。
59. 执行结论写回项目 RAG 记忆并抑制已完成的重复建议；`notify` 只生成订阅候选，不直接发送 Telegram，现有每周链接推送保持独立。
60. 事件订阅支持项目变化检测、订阅规则匹配、候选去重和确认式多渠道投递；默认只预览，真实发送需要双重确认，并按 Telegram、飞书、企业微信逐渠道保存审计与重试次数。
61. 推荐接口、RAG 问答和单项目 RAG 聚合会读取项目事件、通知候选与投递结果，返回 `event_memory` 或 `notification_memory`，让 Agent 在推荐和回答时引用最新项目变化。
62. 项目详情页支持一键创建覆盖七类项目事件的订阅；管理页提供事件检测、候选构建、发送预览、显式确认和失败重试工作台。
63. `scripts/manage_notifications.py` 提供事件检测、候选构建、预览和批量投递命令；GitHub Actions 默认只构建候选，只有手动开启发送输入后才会执行真实外发，原有每周周报链接推送保持不变。

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

当前仍保持单体 Python 主流程，避免过早引入复杂框架。FastAPI 层作为查询、轻量管理、反馈记忆、RAG 检索和任务调度入口，不直接替代采集、生成和推送主流程；后续当前端、数据库、多渠道推送变复杂后，再按项目研究、RAG、反馈推荐、订阅分发和任务执行等边界拆分。

## 目录说明

| 路径 | 说明 |
|---|---|
| `main.py` | 主流程入口 |
| `src/collector.py` | GitHub Trending、Search、README 摘要采集 |
| `src/processor.py` | 去重、过滤、评分、入选项目选择 |
| `src/reporter.py` | Kimi 周报生成和规则版降级周报 |
| `src/llm/` | 统一 LLM 客户端和提示词装配，当前复用 Kimi 兼容接口 |
| `src/report_checks.py` | 周报质量检查 |
| `src/quality.py` | 仓库质量信号、质量分和质量等级 |
| `src/security.py` | 脱敏和外部项目风险提示 |
| `src/personalization.py` | 个性化 profile 合并逻辑 |
| `src/sender.py` | 推送消息构造和通道发送，当前支持 Telegram、飞书和企业微信 Webhook |
| `src/api/` | 后端 API，用于查询历史项目、运行记录、个性化方向、项目反馈、开发上下文和最新周报 |
| `src/rag/` | RAG 基础能力，当前包含本地确定性 embedding 构建逻辑和证据约束问答编排 |
| `src/job_runner.py` | 执行 SQLite jobs 表中的计划任务 |
| `scripts/build_pages.py` | 生成 GitHub Pages 归档页面 |
| `frontend/` | React + TypeScript 项目研究工作台源码，构建后发布到 `docs/app/` |
| `scripts/build_rag_embeddings.py` | 从 `rag_chunks` 构建本地 RAG embedding 索引 |
| `scripts/backfill_rag_explanations.py` | 为缺少解释历史的项目批量生成规则版 RAG 解释 |
| `scripts/plan_rag_maintenance.py` | 检查 RAG 诊断与覆盖缺口，并按需创建语料重建、embedding 构建或解释回填 planned 任务 |
| `scripts/plan_dev_context_index.py` | 创建开发上下文索引 planned 任务，供本地命令或 GitHub Actions 执行 |
| `scripts/run_project_agent_tasks.py` | 限量执行优先级 1/2 的项目 Agent 只读任务，支持 dry-run 和任务类型过滤 |
| `scripts/manage_notifications.py` | 检测订阅事件、构建推送候选，并以默认 dry-run 和双重确认门禁执行通知投递 |
| `scripts/create_planned_job.py` | 创建 planned 周报任务 |
| `scripts/migrate_json_to_sqlite.py` | 将历史 JSON 归档导入 SQLite 派生索引 |
| `scripts/verify_migration.py` | 校验 SQLite 派生索引和 JSON 归档计数 |
| `scripts/run_planned_job.py` | 执行一个 planned 任务，当前支持周报、RAG 语料重建、embedding 构建、解释回填、检索评估和开发上下文索引任务 |
| `scripts/query_archive.py` | 按语言、方向、profile、来源、风险和关键词查询历史项目 |
| `scripts/send_report_link.py` | 推送 GitHub Pages 周报正文和项目筛选链接 |
| `scripts/check_delivery_channels.py` | 检查 Telegram、飞书、企业微信推送通道配置 |
| `scripts/security_check.py` | 本仓库疑似密钥扫描 |
| `config/interests.example.json` | 默认兴趣和评分配置示例 |
| `config/profiles.example.json` | 个性化方向配置示例 |
| `prompts/` | Kimi 周报与 RAG 问答提示词 |
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
docs/command-line-and-coding-standards.md
docs/core-development-plan.md
docs/v1-api-plan.md
docs/weekly/YYYY-MM-DD.md
```

其中 `explorer.html` 是轻量项目筛选页，默认读取 `projects.json` 和 `profiles.json`；在本地后端或 URL 带 `api=1` 时会优先读取 `/api/projects` 和 `/api/profiles`，失败后自动回退到静态 JSON。页面支持按关键词、日期、语言、个性化方向、来源、风险提示和排序方式筛选历史入选项目。页面会根据 profile 自动生成快捷视图按钮，筛选状态会同步到 URL，便于后续在 Telegram、微信、飞书或浏览器中分享同一个筛选视图。项目行支持展开详情，查看 README 精简摘要、推荐理由、质量信号、风险提示、项目指标、完整链接和相似历史项目。
`recommendations.html` 是个性化推荐页，支持 `recommendations.html?profile=agent_development` 或 `recommendations.html?language=Java&q=spring`。本地后端或 URL 带 `api=1` 时会优先读取 `/v1/recommendations`，否则使用 `projects.json` 静态筛选。页面预留 Agent 开发、Python、Java、后端、前端、AI 工具等快捷方向，后续可以继续接入用户订阅数据库。

`admin.html` 是本地管理首页。本地后端或 URL 带 `api=1` 时会展示数据库概览、语料搜索、RAG 证据检索、本地向量检索、GPT 式证据约束 RAG 对话、RAG 质量概览、RAG 检索评估趋势、RAG 解释回填、planned 任务创建和任务工作台；静态 GitHub Pages 模式下只展示可读归档入口。

本地管理页涉及写入、任务创建、执行、重试、订阅修改或反馈写入时，需要后端配置 `ADMIN_API_TOKEN`。`admin.html`、`subscriptions.html`、`jobs.html` 和 `job.html` 只接受页面密码框输入，口令仅保留在当前页面内存并通过 `X-Admin-Token` 发送；刷新或离开页面后需要重新输入。`?admin_token=` 已停用，旧浏览器存储会被删除。删除地址栏参数无法撤销已产生的浏览器历史、服务器、代理或 CDN 访问日志；若此前曾把真实口令放入 URL 或浏览器存储，应立即轮换该口令。

`subscriptions.html` 是订阅配置页，支持在本地后端模式下保存、查看、启用和停用订阅偏好。页面会读取 `profiles.json` 生成 Java、Python、Agent 开发等快捷方向按钮，点击后自动填充订阅名称、profile、语言和关键词。订阅列表支持把已启用订阅生成 planned 周报任务，生成后仍需要在任务详情页确认执行。订阅只保存 profile、语言、方向、关键词、排序、数量和通道名称，不保存 Token、Chat ID 或 Webhook。

`project.html` 是单项目详情页，支持 `project.html?repo=owner/name`，展示历史入选次数、首次和最近入选日期、累计新增 Star、最好 Trending 排名、质量提示、风险提示、历史趋势、历史入选记录和相似项目。本地后端或 URL 带 `api=1` 时会优先读取 `/api/projects/{owner}/{repo}`，并通过 `/v1/projects/{owner}/{repo}/rag` 一次展示该项目相关 RAG 证据块、引用、`prompt_context`、解释历史和解释质量摘要；否则使用 `projects.json` 静态聚合。

`compare.html` 是项目对比页，支持 `compare.html?repos=owner/a,owner/b`，也支持追加 `profile`、`language`、`category` 和 `q` 做个性化加权。页面会读取 `profiles.json` 生成 Java、Python、Agent 开发等快捷方向按钮。本地后端或 URL 带 `api=1` 时会优先读取 `/v1/projects/compare`，否则使用 `projects.json` 静态聚合，展示推荐结论、对比矩阵、领先指标和缺失项目。项目筛选页、推荐页和项目详情页会提供直接进入对比的入口。

`runs.html` 是运行状态面板，直接读取 `runs.json`，用于查看 Kimi/规则版生成状态、Telegram 推送状态、采集成功率、Trending Top10 命中率和 README 抓取率。

`jobs.html` 是任务状态面板，直接读取 `jobs.json`，用于查看 planned、running、succeeded、failed 任务状态，以及任务输入、执行结果和错误摘要。
订阅生成的 planned 任务会把 profile、语言、方向、关键词和数量作为任务上下文传给 job runner；执行结果会记录 `request_context`，便于回看定向任务到底使用了哪些筛选条件。
`job.html` 是单任务详情页；对 RAG 语料重建、embedding 构建和解释回填任务，会在原始 JSON 结果上方展示 before/after 计数、候选数、处理数和回填仓库摘要。

本地管理首页 `admin.html?api=1` 的 RAG 区域可以查看检索评估趋势，也可以直接生成维护计划；后端会根据诊断结果创建语料重建、embedding 构建或解释回填 planned 任务，随后可进入任务详情页检查并执行。开发上下文区域会展示最近 `dev_context_index` 任务，便于查看状态、分块数、embedding 数、错误摘要和索引运行详情。

`profiles.html` 是个性化方向页，直接读取 `profiles.json`，展示 Java、Python、Agent 开发、学习型项目、开发者工具等方向，并提供一键打开对应项目筛选视图的入口。

`profiles.json` 是个性化方向公开配置，包含 Java、Python、Agent 开发、学习型项目、开发者工具等方向的公开标签、语言和主题关键词。筛选页会读取该文件生成“个性化方向”下拉框，后续前端也可以直接复用。

`feed.xml` 是 RSS 订阅入口，适合在 RSS 阅读器或后续自动化工具中订阅每周周报更新。
`api.md` 记录只读后端 API 的启动方式和接口说明，后续前端工程、数据库管理和个性化订阅会优先复用这层接口。
`command-line-and-coding-standards.md` 记录本项目 PowerShell、Git、环境变量、Actions、编码和测试相关规范。
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

Kimi 返回 `429`、过载或临时网关错误时会自动重试；多次重试仍失败时，周报会生成规则版报告并继续推送，`/v1/rag/ask` 会返回 `answer_mode=fallback_rule`、`fallback_reason` 和已召回证据。没有 Telegram 时仍会归档周报和运行摘要。

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

说明：`weekly-archive` 是 GitHub Actions 自动维护的归档分支。代码开发继续提交到 `main`，每周生成的 `docs/`、`reports/` 和 `data/` 会发布到 `weekly-archive`，这样 Actions 不会再频繁把 `main` 往前推进，日常开发提交冲突会明显减少。每次周报任务执行后，Actions 会按 RAG 覆盖缺口自动创建维护计划任务，并在生成归档页面前轻量刷新开发上下文索引；可以在手动触发时把 `plan_rag_maintenance` 或 `run_dev_context_index` 设为 `false` 跳过。

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

`weekly-archive` 只发布显式允许的 GitHub Pages 静态文件、周报和 `data/raw`、`data/runs`、`data/selected`、`data/trends` 的字段级公开 JSON 投影。发布器不会原样复制这些本地事实文件：未知字段、查询、原始错误详情、运行路径、状态路径和投递结果会在写入公开 worktree 前丢弃。SQLite、WAL/SHM、`data/state`、用户反馈、订阅、任务运行态、未知文件和符号链接不发布。SQLite 是本地可重建派生索引，每次运行从公共 JSON 投影重建；真实用户状态如未来需要跨 Actions 保留，必须放入独立私有存储，不能回流公开归档。

每次周报发布完成后，工作流会通过 GitHub tree API 只读验证 `weekly-archive` 最新 tree 不含数据库、密钥和日志类文件；验证器只输出路径、提交 SHA 和计数，不下载或记录归档内容。

如需在不采集项目、不调用 Kimi、也不发送任何通知的前提下把当前安全投影应用到公开分支，可在 GitHub Actions 手动运行“公开归档修复发布”，并显式勾选 `confirm_public_archive_release`。该流程只恢复既有公开归档数据、重建 Pages、发布字段投影并验证远端 tree；不会改写归档历史。

历史归档取证遵循 [脱敏取证协议](docs/archive-history-audit-protocol.md)：默认只枚举路径和 blob SHA；只有经用户单独授权的结构扫描才会下载临时副本，且统计报告只写入未跟踪 `tmp/`。

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

构建本地 RAG embedding 索引：

```bash
python scripts/build_rag_embeddings.py
```

本地前端现在提供两个 RAG 入口：`admin.html?api=1` 用于管理、诊断和证据检查；`app/#/agent?api=1` 是 React 项目匹配工作台，旧 `agent.html?api=1` 会自动跳转。工作台使用顶部导航、会话历史、移动端抽屉和 GPT 式输入区；候选集合、顺序和首选状态只读取 Ask `final` 的后端 `recommendations[]`，不再从 citations 或 contexts 第一项推断。它默认 POST `/v1/rag/ask/stream`，使用 hybrid、limit=3 和 auto_build；每轮只提交上一轮用户目标、候选仓库 ID、确认首选、模式和 resumable，不提交历史模型回答、citations、evidence 或 prompt_context。对话只保存在浏览器 `localStorage`，不保存密钥，不新增后端会话。

React 开发入口为 `http://127.0.0.1:5173/#/agent?api=1`，发布构建入口为 `http://127.0.0.1:8000/app/#/agent?api=1`；页面会标记当前环境。项目筛选使用后端分页，每页 50 条，不再受默认 20 条项目限制。项目可加入浏览器本地对比暂存，最多 3 个，并通过 URL `repos` 参数分享对比视图。

当前 embedding 使用本地确定性 `local-hash-v1`，不调用外部模型、不需要密钥。它用于打通向量索引表和检索 API，后续可以替换为真实 embedding 模型。

RAG Ask 的旧 `confidence` 字段继续保留以兼容现有客户端，但它只表示证据覆盖量，不代表项目匹配正确率。新客户端应读取同值的 `evidence_coverage`，并把 `match_confidence=unknown` 展示为“匹配把握尚未校准”。`answer_quality` 当前能确认引用格式与证据边界，尚未评估证据相关性、主张支持度和数据新鲜度。

### 项目匹配检索基线

`evals/project_match_cases.jsonl` 保存 52 条中文项目需求及其期望仓库、硬约束和是否应澄清。运行 `python scripts/evaluate_project_match.py` 会在固定 fixture 语料上输出 FTS5、`local-hash-v1` 和 hybrid 的 Recall@3、Recall@10、MRR@10、硬约束违反率、零命中率和澄清正确率；不调用问答接口，也不保存模型回答。传入 `--root <weekly-archive-root>` 可测量指定归档，但只有期望仓库与该归档一致时才适合作为对比基线。

`evals/constraint_parsing_cases.jsonl` 保存 100 条 capability-v1 分句级约束样本，固定划分为 60 条 development、20 条 locked regression 和 20 条 adversarial；`evals/constraint_evidence_cases.jsonl` 保存 60 条能力/成本句子证据。运行 `python scripts/evaluate_constraint_parsing.py` 会输出约束精确匹配、operator、澄清、证据状态准确率、错误合格率、错误拒绝率和硬约束违反率；可通过 `--blind-dataset <path>` 接入由独立审查者提供的未见样本。未完成 blind 验证前，不宣称能力模型已经校准。

RAG 派生语料使用标准库清洗器移除 Markdown 图片、徽章、HTML 标签/属性、重复模板和提示注入式文本，同时保留可读链接标题、安装命令和限制说明。语料与 chunks 保存版本、内容哈希和噪声计数；`python scripts/audit_rag_corpus.py` 可只读检查现有 SQLite。旧版本不会在只读请求中自动重建，维护诊断会建议创建受控 `rag_corpus_rebuild` 任务。

证据块按 identity、description、readme、selection reason、project profile、risk 和 Agent memory 分层。可选的 `POST /v1/rag/corpus-enrichment-plan` 会创建 Kimi 结构化增强 planned job，默认 dry-run，真实执行必须显式确认；结果按内容哈希缓存，每个字段必须引用清洗文本中的原句。无 Kimi 配置或调用失败不会阻断语料，模型增强只参与召回，不作为硬约束或首选排名依据。

Ask 现在返回当前归档内的可审计 `recommendations[]`：后端按仓库聚合本轮证据，返回相对匹配分、显式 `language/category/source` 约束状态、理由和证据映射。只有质量闸门通过且第一项 `eligibility=eligible` 时，React 才显示“当前归档内最匹配候选”；否则显示“暂无可确认首选”。`python scripts/evaluate_project_recommendations.py` 使用同一 52 条评估集输出三种检索模式的 Top-1、Recall@3、MRR@10、硬约束违反率和无首选率。

POST Ask 支持无状态追问和自然语言硬约束。resume/refine 在 SQL 或向量候选读取阶段限制到上一轮仓库，明确“重新找”才扩大到全归档。`input_route.requirement_schema_version=capability-v1`；托管方式、离线能力、联网要求、外部 API 依赖和 API Key 依赖分别由 `hosting_mode/offline_capable/network_required/external_api_required/api_key_required` 表达，避免把 self-hosted、cloud hosting 和外部模型 API 混成一个 deployment 字段。旧 deployment 仅作后端兼容输入。language、license、category、source 和 tech_stack 只由确定性元数据验证；能力和 cost 只接受非 `model_enrichment` 清洗 chunk 的句子级证据。recommendation 的 `requirement_evaluations[]` 逐项公开 matched/unmet/unknown、原因和证据 chunk IDs。任一冲突为 rejected，证据不足或冲突保持 unknown；没有 eligible 且全冲突时返回 `answer_mode=no_match`，存在 unknown 时返回 clarification。既有 GET/POST 契约与 SSE 事件顺序保持不变。

候选序号追问不做全归档重搜：“第二个呢”只检索上一轮第二个仓库，“比较第一个和第二个”只检索这两个仓库。后端通过 `selected_candidate_indexes[]` 和权威 `selected_repository_ids[]` 公开实际范围；越界、无上下文或未确认 primary 的“上一个项目”先澄清，检索调用为 0。`evals/follow_up_cases.jsonl` 当前包含 60 条样本，其中 20 条覆盖序号、比较、越界和不可恢复状态；`python scripts/evaluate_follow_up_routing.py` 同时输出序号索引与仓库范围准确率。

回填缺少解释历史的项目：

```bash
python scripts/backfill_rag_explanations.py --dry-run
python scripts/backfill_rag_explanations.py --limit 10
```

该脚本会读取 `/v1/rag/coverage` 同源逻辑，优先为缺少 RAG 解释历史的项目生成规则版解释并写入 SQLite。
本地后端也提供同源接口 `POST /v1/rag/backfill-explanations`。接口默认只预览；如果要通过 API 真正写库，需要同时传入 `dry_run=false` 和 `confirm_execution=true`。
该接口会返回 `job_id`，并把本次预览或写库记录到 `/v1/jobs?kind=rag_backfill` 和 `/v1/jobs/{job_id}/events`。如果希望先创建计划任务，再人工确认执行，可以调用 `POST /v1/rag/backfill-plan`，随后通过 `POST /v1/jobs/{job_id}/execute` 执行。

自动检查缺口并按需创建 RAG 维护计划任务：

```bash
python scripts/plan_rag_maintenance.py
python scripts/plan_rag_maintenance.py --limit 20 --coverage-limit 200
```

维护计划会先读取 RAG 诊断：缺少语料时创建 `rag_corpus_rebuild`，缺少向量索引时创建 `rag_embedding_build`，解释覆盖不足时创建 `rag_backfill`；当覆盖缺口低于阈值时创建 `rag_search_evaluation`，用于持续评估 FTS5、向量和混合检索质量。所有任务都可通过 `/v1/jobs` 查看，并通过 `scripts/run_planned_job.py` 或 `/v1/jobs/{job_id}/execute` 执行。

执行 planned 任务：

```bash
python scripts/create_planned_job.py --profile agent_development --days-back 7 --output .weekly-job.json
python scripts/run_planned_job.py --job-file .weekly-job.json
python scripts/plan_dev_context_index.py --run-checks false --output .dev-context-job.json
python scripts/run_planned_job.py --job-file .dev-context-job.json
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

1. 把项目定位从周报工具继续推进为 GitHub 项目研究 Agent，围绕“发现、理解、比较、推荐、跟踪”组织能力。
2. 强化反馈驱动推荐闭环，让“有用 / 不适合 / 继续跟踪”等反馈稳定影响推荐排序，并在 API 和页面中解释影响原因。
3. 完善项目级 RAG 档案，让每个仓库都有可检索的定位、适用场景、风险点、质量信号、历史入选原因和用户反馈记忆。
4. 保留每周周报和链接推送，把 Telegram、飞书、企业微信推送逐步沉淀为订阅分发模块，支持按 profile、语言、主题和关注项目池生成定向摘要。
5. 继续观察 GitHub Trending 在 Actions 环境中的稳定性，保证每周自动运行、归档和推送链路可靠。

中期重点：

1. 建设跨项目比较 Agent，支持按技术方向比较多个仓库的成熟度、活跃度、学习价值、生产风险和推荐结论。
2. 强化 SQLite + FTS5 + embedding 的本地 RAG 底座，优先保证数据契约、检索质量评估、维护任务和解释引用稳定，再考虑外部向量数据库。
3. 建设方向雷达，按 Agent、RAG、AI coding、开发者工具、LLM infra 等主题聚合项目，输出趋势变化、代表项目和跟踪建议。
4. 继续改善轻量前端，用于项目筛选、推荐解释、RAG 证据查看、反馈记忆和订阅配置，但暂不引入复杂前端工程。
5. 通过更多质量指标补充判断，例如 Release 活跃度、Issue 状态、README 完整度、异常 Star 增长提示和依赖风险提示。
