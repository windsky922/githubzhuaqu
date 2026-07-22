# GitHub Weekly Agent 架构说明

本文档记录第一阶段最小可用版本的实际实现架构。

## 提交级质量检查

质量 job 除构建、测试和安全检查外，还在临时工作目录运行四套离线固定 evaluator。版本化阈值配置先核验公开 fixture 的 SHA-256，再比较核心 retrieval/recommendation、追问路由和约束安全指标；结果、commit 与 hash 作为短期 CI artifact 保存。此门禁只检测固定基线回归，不替代真实用户评估或分支保护。

`.github/workflows/ci.yml` 独立于定时周报主流程，在 `push main` 和 pull request 上运行。它执行确定性测试、静态检查、安全检查、前端构建一致性及两套 Chromium Playwright 回归。mock E2E 由本地固定 server 提供 SSE、分页、对比和桌面/手机状态，快速定位前端渲染问题；real E2E 启动真实 FastAPI，将已构建 `docs/`、固定项目归档、FTS5、语料和 `local-hash-v1` embedding 放入系统临时目录中的 SQLite，以单 worker 验证普通 POST、SSE final、无状态追问、能力约束和 `X-Admin-Token` 鉴权。真实回归显式清空 Kimi、GitHub 和 Telegram 凭据，管理写入只创建临时 planned 任务；两套回归失败时分别短期上传截图、trace 和报告。当前只提供自动检查与失败报警，不配置 GitHub 分支保护，因此仍允许直接推送 `main`。

## 管理写接口凭证边界

FastAPI 管理写接口继续接受 `X-Admin-Token` 或 `Authorization: Bearer`，只读接口不需要鉴权。浏览器管理页通过共享 `admin-auth.js` 从当前页面密码框生成 `X-Admin-Token`，新请求中的口令不写入 URL、localStorage、sessionStorage、应用日志或 SQLite；刷新、关闭或跨页导航都会丢失。页面在加载最早阶段忽略并清理旧 `admin_token` 参数、删除旧浏览器存储，并使用 `Referrer-Policy: no-referrer` 阻止旧 URL 继续向资源请求传播。清理只能阻止未来传播，不能撤销旧 URL 已进入的浏览器历史或服务器、代理、CDN 日志；页面会明确要求轮换旧口令。安全检查会阻止生产页面重新引入 URL 或浏览器持久化口令。

## React 项目匹配工作台

`docs/app/#/agent` 是面向普通用户的 React 项目匹配入口。前端只在浏览器 `localStorage` 保存有限的会话标题、问题和最终响应；不创建后端会话表，也不把历史回答视为事实证据。它通过 POST `/v1/rag/ask/stream` 提交当前输入和最小用户意图上下文，只包含上一轮用户目标、候选 ID、确认首选、模式和 resumable。历史 assistant answer、citations、evidence、prompt_context 均不进入请求。页面只从后端 `recommendations[]` 读取候选顺序和资格状态。

Agent 路由使用独立的全高工作区，消息列表是唯一可滚动区域，输入框固定在工作区底部。项目筛选通过 `offset` 分页从 SQLite 归档读取项目；对比选择只保存在浏览器并同步到 `repos` URL 参数，对比结果复用既有只读项目对比 API，不增加用户数据或后端状态。

## 事件订阅与候选层

```text
历史 selections + 最新 project_corpus + project_agent_task_runs
-> src/notifications/service.py 项目变化检测
-> subscription_events（证据、引用、严重度、稳定去重键）
-> subscriptions 规则匹配
-> notification_candidates（pending、必须确认）
-> dry_run 预览 / confirm_delivery 双重门禁
-> SQLite 逐渠道事务抢占
-> sender 通用 DeliveryMessage 分发
-> notification_deliveries（状态、尝试、错误、响应摘要）
```

当前事件检测支持进入 Trending、Star 增长显著、质量分变化、风险新增、风险解除、新版本和 Agent 决策变化。快照事件使用 `selections` 计算前后差异，并由 `project_corpus` 补充语言、方向、搜索文本和公开来源；Agent 事件复用任务执行结果中的证据与引用。

订阅规则支持项目、profile、语言、方向、关键词、事件类型、最低严重度、渠道和频率。候选 ID 由“订阅 ID + 事件 ID”稳定生成，重复检测和重复构建不会新增记录，也不会重置已有状态。

候选投递默认只预览。真实发送必须同时满足 `dry_run=false` 和 `confirm_delivery=true`；每个渠道在发送前通过 SQLite 事务写入 `running` 抢占状态，并复用 `src/sender.py` 的密钥读取、20 秒超时和错误隔离。成功渠道禁止重复发送；失败渠道只有显式重试才更新同一审计记录并增加 `attempt_count`。现有每周周报链接推送不经过该事件门禁，保持原流程独立运行。

通知记忆通过三个出口进入 Agent：推荐接口返回项目级 `event_memory` 和排序解释，RAG 问答在通知相关问题中召回 `notification_memory`，单项目 RAG 聚合返回事件、候选和投递审计摘要。项目详情页负责创建项目订阅，管理页负责检测、构建、预览、确认和失败重试；`scripts/manage_notifications.py` 为本地和自动化提供同一服务入口。

GitHub Actions 默认执行事件检测与候选构建，但 `send_event_notifications` 默认为 `false`。只有显式开启该输入时，工作流才会同时传入 `--no-dry-run` 和 `--confirm-delivery`；通知步骤设置为非阻塞，不影响 Pages 生成和现有每周链接推送。

## 证据约束 RAG Ask 层

流式 Ask 不转发未经验证的 provider delta：后端先完整缓冲输出，执行硬约束、引用、未知仓库、危险指令和主张—引用—证据检查；仅通过后才以既有 `meta → delta* → final` 顺序发送。项目事实与比较/排序结论必须由不可展示的 schema-v2 台账关联同项目 citation、证据块、原文摘录及结构化事实。验证器分别检查绑定、极性、作用域（主体/组件/阶段/版本范围/条件/时间）和语义字段（谓词/值/模态/数量），并要求证据事实可由 quote 锚定；任一不匹配、未锚定或漏登记事实只发送规则降级 `final`，前端不会渲染 provider 草稿；普通 POST 与 SSE final 保持等值。

RAG 语料先经过确定性清洗和版本化，再进入 FTS5、local-hash 与 Ask。外部 README/描述按不可信输入处理：图片、徽章、HTML 属性、重复模板和提示注入式行不进入检索或模型上下文，原文仍可从 JSON 归档追溯。`corpus_version`、`cleaner_version` 和内容哈希用于判断派生索引是否过期；确认执行语料重建时旧 embedding 同步失效，随后由独立任务重建。

确定性语料按来源单独分块，避免 README、风险、项目画像和 Agent 记忆互相污染。Kimi 结构化增强是独立 planned job，不在查询或语料重建中隐式调用；其输出只有在逐字段证据能从清洗原文精确定位时才进入 `model_enrichment` chunk。增强结果可参与召回和推荐理由，但不能决定硬约束；P0-4 的 recommendations 层只以确定性仓库元数据验证显式筛选。

```text
/v1/rag/ask
-> rag_explain 生成证据、引用和解释编号
-> project_recommendations 按仓库聚合、验证显式约束并生成可审计排序
-> src/rag/answering.py 检查证据充足性
-> src/llm/client.py 调用 Kimi 兼容聊天接口
-> prompts/rag_ask.md 约束模型只能基于证据回答并标注引用
-> 未配置、超时、限流、错误或无证据时规则降级/拒答
```

`/v1/rag/ask` 不是普通聊天接口。它必须先有 RAG 证据，再尝试真实模型回答；没有证据时直接拒答。模型失败不会阻断接口，响应会保留 `citations`、`evidence`、`answer_mode`、`fallback_reason` 和 `model_status`，管理页据此展示模型状态和降级原因。提示词保存在 `prompts/rag_ask.md`，业务代码只负责装配结构化证据。

POST Ask 在检索前经过 `follow_up_router`。确定性规则优先识别 resume/refine/new_search/clarify，并按分句、连接词和谓词限定否定作用域；同一目标冲突、析取或无法表达的可选条件直接澄清。`capability-v1` 将托管方式、离线能力、联网要求、外部 API 依赖和 API Key 依赖分别建模，旧 deployment 只在验证器入口规范化。规则无法判断时才调用 Kimi 严格 JSON 路由；模型只能建议路由、改写和约束，不能选择项目。候选范围直接下推到 FTS5 SQL、vector 行过滤和 hybrid 两路召回。`constraint_verifier` 从仓库/语料确定性元数据及非模型增强 chunk 计算能力事实，按句子区分支持、冲突、条件、仅试用、外部依赖或未知；模型增强不能覆盖硬约束结论。`project_recommendations` 统一生成 eligible/unknown/rejected，并通过 `requirement_evaluations[]` 公开逐条件状态、原因和证据；没有合格候选时由规则闸门返回 clarification 或 no_match，不调用回答模型。

候选序号同样在 `follow_up_router` 中确定性解析。序号先映射到上一轮有序 `candidate_repository_ids`，再生成 `selected_candidate_indexes[]` 和权威 `selected_repository_ids[]`；repository 层只把这些 ID 下推到实际检索，不先取大 Top-K 再过滤。越界、无上下文和不确定引用在检索前短路为 clarification。浏览器只负责回传最小无状态上下文，不根据 citations、evidence 或历史 assistant 文本解释序号。

Ask 响应把证据覆盖与匹配把握分开表达：旧 `confidence` 仅作为兼容字段保留，`evidence_coverage` 复用其按证据数量计算的 `low/medium/high`，`match_confidence` 在未校准阶段固定为 `unknown`。`answer_quality` 保留原有通过状态和问题列表，并显式标记引用有效性、证据相关性、主张支持度、逐项 `claim_checks` 的 binding/polarity/scope/semantic 状态和数据新鲜度。freshness 只读取受控运行 JSON；weekly 在来源 JSON 成功后重建可丢弃的 SQLite corpus 和 embedding，并仅在三层同一 `run_date` 成功时原子写入 schema-v1 `rag_freshness`。attestation 含日期、哈希、corpus version、模型和计数，公开投影只保留 allowlist 字段；schema、哈希或日期缺失为 unknown。默认超过 8 天为 stale，层级落后为 lagging。时效性请求在非 fresh 状态下于 provider 调用前规则降级，SSE 只保留 `meta → final`，首选也必须要求 fresh。该水位不代表 blind 泛化或推荐正确率。

P0-16C 将主张证据再分为 metadata-bound subject、quote-extracted `predicate/value/modality` 与 quote-bound scope。后端只能接受从 quote 唯一确定性抽取出的语义组合；模型自报 evidence fact 不构成证明。抽取不到或有歧义时，质量闸门失败关闭，provider 内容不进入 delta，首选关闭。

管理页 RAG 对话工作台是该接口的 GPT 式前端封装，不新增后端会话状态。对话历史只保存在浏览器 localStorage，最多 20 轮；每轮问题独立检索，历史回答只用于页面回看，不进入 `prompt_context`，也不作为事实证据。管理页和 React 工作台显示“证据覆盖”与“匹配把握尚未校准”，不再把 `confidence` 渲染为匹配置信度。

`frontend/` 是 React + TypeScript 用户前端，构建产物写入 `docs/app/`，通过 Hash Router 提供项目匹配、筛选、推荐、详情和对比页面；旧 `agent.html`、`explorer.html`、`recommendations.html`、`project.html`、`compare.html` 仅保留 query 参数并跳转到对应路由。`app/#/agent?api=1` 默认 POST `/v1/rag/ask/stream`。流中的 `delta` 只展示已通过当前主张—证据与时效闸门的内容；质量或时效失败不产生 provider delta。`final` 中只有第一项 recommendation 为 eligible、回答质量通过且 `data_freshness=fresh` 时才显示首选。clarification 不展示项目卡或质量失败，no_match 展示冲突候选与原因。它不新增数据库表或后端会话。

## 项目级 Agent 执行层

```text
project_agent_tasks
-> execution-check
-> src/agent/task_executor.py
-> 只读项目语料与历史快照
-> project_agent_task_runs（证据、引用、结果、错误）
-> project_corpus / rag_chunks 执行记忆
-> 推荐下一步动作
```

执行器不修改 GitHub 仓库、不调用外部推送，也不读取推送密钥。任务抢占和运行记录创建在同一 SQLite 事务中完成，同一任务不能并发执行；completed 默认不可重复，failed 必须通过显式重试入口执行。GitHub Actions 仅在 `run_agent_tasks=true` 时限量运行，并设置 `continue-on-error`，不会阻塞周报归档与 Telegram 链接推送。

## 运行流程

```text
main.py
-> src.settings.load_settings
-> src.collector.collect_repositories
-> src.state.load_sent_repository_names
-> src.processor.process_repositories
-> src.collector.enrich_repositories_with_readmes
-> src.reporter.generate_report
-> src.archive.archive_run
-> src.sender.send_report
-> src.state.write_sent_repositories
-> src.archive.write_run_summary
```

## 最小可用版本范围

第一阶段已实现：

1. 通过 GitHub Search API 采集仓库。
2. 对仓库进行过滤、去重、评分和排序。
3. 使用 Kimi 聊天补全接口生成周报。
4. 当 Kimi 不可用时生成降级版 Markdown 周报。
5. Telegram 长消息自动分段发送。
6. Markdown 周报归档到 `reports/`。
7. 运行摘要归档到 `data/runs/`。
8. GitHub Actions 支持每周定时运行和手动触发。
9. Telegram 推送成功后记录已推送仓库，后续运行过滤重复项目。
10. 对最终入选仓库抓取 README 摘要，作为 Kimi 和降级报告的补充上下文。
11. 维护 Star 历史状态，并将 Star 增量纳入排序评分。
12. 生成 GitHub Pages 周报归档页面。
13. 生成数据驱动的趋势摘要，并归档到 `data/trends/`。
14. 在运行摘要中记录部分采集失败，便于排查 GitHub API 限流或网络异常。

暂缓实现：

1. SQLite 历史数据库。
2. 网页仪表盘。
3. 正式发布技能包。
4. Telegram 交互式机器人。

## 状态文件

`data/state/sent_repos.json` 用于记录已经成功推送到 Telegram 的仓库。

写入时机：

1. 本次运行成功生成周报。
2. Telegram 推送成功。
3. 本次筛选列表不为空。

如果 Telegram 未配置或发送失败，程序仍然归档周报和运行摘要，但不会把仓库写入已推送状态，避免后续遗漏应推送项目。

## 兴趣配置

程序优先读取用户配置：

```text
config/interests.json
```

如果该文件不存在，再回退到示例配置：

```text
config/interests.example.json
```

这样可以保留示例文件，同时允许用户维护自己的关注方向、语言偏好、排除关键词和项目数量阈值。

## 数据归档

本地 JSON 归档是运行事实来源，SQLite 仅为可重建索引。公开 `weekly-archive` 由 `config/public-archive-manifest.json` 约束：发布器从 manifest 选择公开投影，清理旧 worktree 内容，暂存后要求完整 Git index 路径集合与本轮预期投影精确一致；远端 tree attestation 复用相同规则。未知路径、禁止后缀、符号链接和路径穿越在 commit/push 前失败关闭。

`weekly-archive` 是公开静态归档，不是运行态备份：发布器仅从 allowlist 复制 Pages 静态资产、周报及 `raw/runs/selected/trends` 的字段级公共 JSON 投影，并在每次发布前清理归档 worktree 的 `docs`、`reports`、`data` 后暂存删除。本地 JSON 事实来源不被改写；投影只保留 SQLite 重建和 Pages 所需的明确字段，未知字段、查询、原始错误详情、运行/状态路径及投递结果在写入公开 worktree 前移除。SQLite、WAL/SHM、`data/state`、用户订阅/反馈/任务、未知文件和符号链接均不进入公开分支。工作流恢复历史时只取公开 JSON 和报告；SQLite 由这些 JSON 重建。未来跨 Actions 的真实用户状态必须使用私有持久化位置。

发布完成后，`audit_public_archive.py` 使用 GitHub tree API 对远端最新 commit 做只读 attestation：只枚举路径和 SHA，拒绝数据库、密钥和日志类文件；失败则 weekly workflow 失败。历史审计通过显式 `--history-limit` 单独运行，不读取 blob 内容，也不触发历史改写。

归档目录职责：

1. `data/raw/YYYY-MM-DD.json`：保存 GitHub API 本次采集到的原始候选仓库。
2. `data/selected/YYYY-MM-DD.json`：保存经过去重、过滤和排序后的最终入选仓库。
3. `data/runs/YYYY-MM-DD.json`：保存运行摘要，包括采集数量、入选数量、降级原因、推送结果和部分采集错误。
4. `data/trends/YYYY-MM-DD.json`：保存趋势摘要。

## README 摘要

程序只对最终入选周报的仓库抓取 README，不对全部搜索结果抓取，避免 GitHub API 请求量过大。

处理规则：

1. 使用 GitHub README API 读取仓库默认 README。
2. 每个请求设置超时。
3. 单个仓库 README 获取失败时跳过，不影响整体周报。
4. 只保留前 2000 个字符的清洗后摘要，避免提示词过长。

## Trending 优先采集与评分

当前采集链路以 GitHub Trending 周榜作为第一优先级候选来源，GitHub Search API 作为辅助候选来源。

处理顺序：

```text
GitHub Trending weekly
-> GitHub Search API 辅助查询
-> 按仓库名去重并合并来源信号
-> 最近一周活跃过滤
-> 综合评分排序
```

`Repository` 会记录以下来源字段：

1. `sources`：项目来自 `github_trending`、`github_search` 或多个来源。
2. `trending_rank`：项目在 GitHub Trending 周榜中的排名。
3. `trending_period`：当前为 `weekly`。
4. `source_priority`：来源优先级，Trending 高于 Search。

GitHub Trending 是网页来源，不是稳定的官方 API。因此它失败时不会中断整个流程，程序会继续使用 GitHub Search API 生成周报，并把失败原因写入运行摘要。

## 综合热度评分

`data/state/star_history.json` 用于记录仓库上次采集时的 Star 数。

评分时会计算：

```text
star_growth = 当前 Star - 历史 Star
```

如果仓库没有历史记录，则 `star_growth` 为 0。

当前综合评分以 Trending 为第一指标，其余信号作为辅助：

1. GitHub Trending 周榜排名：45%
2. Star 增量：25%
3. 兴趣主题匹配：15%
4. 活跃时间新鲜度：10%
5. 社区基础信号：5%，由总 Star 和 Fork 共同构成。

这种设计把 Trending 作为本周热度的最高优先级，同时保留新增 Star、垂直兴趣匹配、近期活跃度和社区基础信号，避免只按单一 Star 数判断项目热度。

评分权重可以通过 `config/interests.json` 中的 `score_weights` 调整。后续如果要做更细的个性化推荐，可以在不改主流程的前提下扩展该配置。

周报候选项目以最近一周 `pushed_at` 或 `updated_at` 活跃为准，不要求仓库必须在最近一周创建。当前采集查询不再使用 `created` 条件，避免候选池偏向“新建项目”。

## GitHub Pages 归档页面

`scripts/build_pages.py` 会读取 `reports/` 和 `data/runs/`，生成：

1. `docs/index.md`：周报归档首页。
2. `docs/weekly/YYYY-MM-DD.md`：适合 GitHub Pages 浏览的周报副本。

每次 GitHub Actions 生成周报后，都会自动刷新归档页面并提交到仓库。

首页会显示最新周报链接、最新运行摘要和趋势要点，方便不打开完整周报也能快速确认生成方式、Telegram 推送状态和采集健康度。

## 趋势摘要

`src/trends.py` 会根据本期入选仓库生成趋势摘要，输出到：

```text
data/trends/YYYY-MM-DD.json
```

趋势摘要包含：

1. 入选项目总数。
2. 累计新增 Star。
3. 主要语言分布。
4. 项目方向分布。
5. 新增 Star 最高的项目列表。
6. 可直接写入周报的一组趋势要点。

Kimi 生成周报时会收到该趋势摘要；降级版周报也会直接展示趋势要点。

## 安全风险提示

`src/security.py` 会对最终入选仓库生成元数据级风险提示，写入：

```text
security_flags
```

当前检查范围：

1. 是否缺少许可证信息。
2. 是否为归档仓库。
3. 是否为 fork。
4. 仓库名称、简介、主题和 README 摘要中是否包含明显风险关键词。

注意：该检查不会执行第三方仓库代码，也不会把项目判定为“安全”。它只提供保守提示，提醒用户在学习、复用或运行项目之前进行人工审查。

## 入选原因

`src/processor.py` 会在评分后为最终候选仓库生成：

```text
selection_reasons
```

当前原因来源：

1. 新增 Star。
2. 当前累计 Star。
3. 主题、语言或名称与关注方向匹配。
4. 最近一周仍有更新或维护活动。

该字段会写入 `data/selected/YYYY-MM-DD.json`，并传给 Kimi。降级版周报也会展示该字段，方便用户理解项目为什么入选。

## 报告质量检查

`src/report_checks.py` 会对 Kimi 生成的周报进行基础质量检查。

当前检查范围：

1. 不允许出现“蟒蛇”这类不合适的技术语言翻译。
2. 每个入选项目的完整仓库名必须出现在报告中。
3. 每个入选项目的 GitHub 链接必须以完整 URL 的 Markdown 链接形式出现。

如果 Kimi 周报未通过质量检查，程序会记录 `report_error`，并回退到规则周报，避免把结构不完整的模型输出推送给用户。

## 采集分项统计

`src/collector.py` 会为 GitHub Trending 和每条 GitHub Search 查询记录：

```text
collector_stats
```

每条记录包含：

1. 数据来源。
2. 查询条件。
3. 成功、失败或部分失败状态。
4. 返回仓库数量。
5. 失败原因。

该字段写入 `data/runs/YYYY-MM-DD.json`，用于判断本次采集是否完整，并为后续多数据源扩展预留统一统计结构。

## 后续扩展边界

未来扩展应遵循“稳定核心 + 可插拔增强”的方式，不提前重构当前主流程。

稳定核心继续保持：

```text
collector -> processor -> reporter -> archive -> sender
```

当某类能力明显变复杂时，再按职责拆分：

1. `sources`：多数据源采集。
2. `quality`：仓库质量评估和异常过滤。
3. `report_checks`：周报结构和内容校验。
4. `channels`：多推送渠道。
5. `storage`：长期历史数据存储。

详细演进计划见：

```text
docs/future-plan.md
```
