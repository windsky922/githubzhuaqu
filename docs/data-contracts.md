# 数据契约说明

本文档记录当前公开 JSON 和 SQLite 派生索引的稳定字段。后续前端、微信、飞书、RSS 或外部脚本应优先依赖这些字段。

## 一、设计原则

1. JSON 归档仍是事实来源。
2. `docs/projects.json`、`docs/runs.json`、`docs/jobs.json` 和 `docs/profiles.json` 是公开展示与订阅入口。
3. SQLite 是可重建派生索引，不提交数据库文件。
4. 公共数据不能包含密钥、用户隐私、未脱敏配置或原始错误堆栈。
5. 修改字段时必须同步更新测试、文档和下游消费逻辑。
6. `weekly-archive` 只可包含 allowlist 中的 Pages 静态文件、周报及 `data/raw`、`data/runs`、`data/selected`、`data/trends` JSON；SQLite、WAL/SHM、`data/state`、用户状态、未知文件和符号链接均为私有或拒绝项。
7. 每次运行可由上述公开 JSON 重建 SQLite 派生索引；未来需要跨 Actions 保留的订阅、反馈或任务状态必须进入独立私有存储，不能依赖公开归档。

## 二、`docs/projects.json`

顶层字段：

```text
schema_version
count
projects
```

每个项目字段：

```text
run_date
full_name
html_url
description
readme_summary
category
language
stargazers_count
forks_count
star_growth
score
sources
trending_rank
selection_reasons
security_flags
security_score
security_level
quality_flags
quality_score
quality_level
report_url
```

用途：

1. 前端历史项目筛选。
2. 多渠道推送摘要生成。
3. 外部脚本按语言、方向、来源、风险提示做二次分析。
4. `security_score` 为 0 到 100 的基础安全分，`security_level` 为 `low`、`medium` 或 `high`。
5. `quality_score` 为 0 到 100 的基础质量分，`quality_level` 为 `high`、`medium`、`low` 或 `unknown`，`quality_flags` 记录信息完整度、维护活跃度和社区复用信号等提示。
6. `readme_summary` 是公开精简摘要，用于项目详情展开和后续前端详情面板。

当前 `docs/explorer.html` 已经直接消费该文件，并将筛选状态同步到 URL 查询参数。

## 三、`docs/profiles.json`

顶层字段：

```text
schema_version
count
profiles
```

每个 profile 字段：

```text
name
label
learning_goals
preferred_languages
preferred_topics
search_languages
search_topics
```

用途：

1. 前端展示 Java、Python、Agent 开发等个性化方向选项。
2. 项目筛选页按 profile 快速过滤历史项目。
3. 后续用户画像、订阅偏好和多渠道推送复用。

该文件只发布兴趣方向、语言和主题关键词，不发布权重、内部调参字段、密钥或用户私有配置。

## 四、`docs/runs.json`

顶层字段：

```text
schema_version
count
runs
```

每次运行字段：

```text
run_date
status
run_schema_version
report_url
selected_count
collected_count
previously_sent_selected_count
previously_sent_selected_rate
readme_fetched_count
readme_fetch_rate
star_history_updated_count
kimi_used
fallback_used
telegram_sent
telegram_report_url
telegram_explorer_url
telegram_runs_url
delivery_results
collector_error_count
collector_failed_count
collector_error_kinds
collector_error_summary
collector_query_count
collector_success_count
collector_success_rate
collector_stats
top_languages
top_categories
total_star_growth
trending_project_count
trending_top10_available_count
trending_top10_selected_count
trending_top10_fulfillment_rate
trending_selected_rate
summary_points
```

用途：

1. 首页运行状态展示。
2. 趋势概览和历史运行对比。
3. 监控周报是否降级、是否推送、采集是否异常。

`telegram_report_url` 记录本期周报正文页面。`telegram_explorer_url` 记录同一运行日期对应的项目筛选页面，例如 `explorer.html?date=YYYY-MM-DD`。`telegram_runs_url` 记录运行状态面板入口，例如 `runs.html`。

运行指标说明：

1. `collector_query_count`、`collector_success_count`、`collector_success_rate` 用于判断 GitHub Trending 和 Search 查询是否完整。
2. `readme_fetch_rate` 用于判断入选项目 README 摘要补充是否完整。
3. `trending_top10_available_count`、`trending_top10_selected_count`、`trending_top10_fulfillment_rate` 用于判断 Trending Top10 保底是否达成。
4. `previously_sent_selected_rate` 用于观察持续热门项目在本期周报中的占比。已推送项目不会被硬过滤，只会在评分中降权并保留解释。
5. `trending_selected_rate` 来自趋势摘要，表示入选项目中带有 GitHub Trending 来源的比例。

原始运行摘要 `data/runs/YYYY-MM-DD.json` 中的 `collector_stats` 会保留每个 GitHub Trending/Search 查询的采集状态。字段包括 `source`、`query`、`stage`、`status`、`count`、`error`、`error_kind`、`status_code`、`retry_after`、`rate_limit_remaining` 和 `rate_limit_reset`。这些字段用于判断失败来源是主限流、二级限流、认证失败、仓库不存在、GitHub 服务错误还是普通运行时错误。公开展示时只输出必要摘要，不能输出密钥、请求头或原始堆栈。

公开 `runs.json` 不直接输出完整 `collector_stats`，只输出脱敏后的运行异常摘要：`collector_failed_count` 记录失败或部分失败的查询数，`collector_error_kinds` 记录去重后的错误类型，`collector_error_summary` 记录最多 10 条公开错误摘要。摘要只包含来源、阶段、状态、错误类型、状态码、限流提示字段和截断后的错误消息，不包含请求头、Token、Chat ID、Webhook 或原始堆栈。

`delivery_results` 记录多推送通道状态。当前支持 `telegram`、`feishu`、`wechat`。该字段只记录通道名称、是否发送成功、错误摘要和是否跳过，不记录 Token、Chat ID、Webhook 或任何密钥。

## 五、只读后端 API

当前 API 位于：

```text
src/api/app.py
```

API 只读取公开归档和 SQLite 派生索引，不写入采集结果，也不读取任何密钥。当前稳定入口包括：

```text
GET /api/health
GET /api/projects
GET /api/runs
GET /api/profiles
GET /api/weekly/latest
GET /v1/search
GET /v1/rag/corpus
GET /v1/rag/retrieve
GET /v1/rag/vector-search
GET /v1/rag/explain
GET /v1/rag/ask
POST /v1/rag/ask
POST /v1/rag/ask/stream
GET /v1/rag/diagnostics
GET /v1/feedback
POST /v1/feedback
POST /v1/dev-context/index
POST /v1/dev-context/index-plan
GET /v1/dev-context/search
POST /v1/dev-context/ask
GET /v1/dev-context/runs/{id}
```

### 无状态项目匹配请求

`POST /v1/rag/ask` 与 `POST /v1/rag/ask/stream` 接收当前用户输入、筛选参数和浏览器提供的最小上下文。服务端不保存聊天会话，也不把历史 assistant 回答、引用或证据作为请求上下文。流式接口只在既有 `final` 事件中返回完整结果，事件名和顺序保持兼容。

`input_route.requirement_schema_version` 当前固定为 `capability-v1`。`requirements[]` 的稳定字段为 `field`、`operator`、`value` 和 `hard`，其中 `value` 为 `string | boolean`。项目能力使用相互独立的字段表达：

```text
hosting_mode: self_hosted | cloud_hosted
offline_capable: boolean
network_required: boolean
external_api_required: boolean
api_key_required: boolean
```

语言、分类、来源、许可证、成本和技术栈继续使用 `language/category/source/license/cost/tech_stack`。旧 `deployment` 只作为后端兼容输入，进入验证器前转换为上述能力字段；新规则路由和 Kimi 路由不得生成 `deployment`。

每个 recommendation 除已有排序、满足/不满足/未知要求和证据字段外，还返回 `requirement_evaluations[]`。每项包含原条件的 `field/operator/value`、`status: matched | unmet | unknown`、可审计 `reason` 和 `evidence_chunk_ids[]`。能力事实只从可信元数据及非 `model_enrichment` 清洗 chunk 确定性计算；模型增强不能把 unknown 或 rejected 改成 eligible。本阶段不新增 SQLite 表或第二套能力缓存。

候选序号追问扩展 `input_route`，不改变请求体：

```text
candidate_scope: archive | previous_candidates | primary_candidate | selected_candidates | none
selected_candidate_indexes: number[]
selected_repository_ids: string[]
```

`selected_candidate_indexes` 使用上一轮 `candidate_repository_ids` 的零基索引；`selected_repository_ids` 是后端实际传入 FTS5、vector 和 hybrid 候选过滤的权威范围。无上下文、序号越界或无法唯一解释时两者为空，并返回 clarification 且不检索。浏览器仍只提交上一轮用户目标、有序候选仓库 ID、确认的 primary、mode 和 resumable，不提交 assistant 文本、citations、evidence 或 prompt_context。

`/api/projects` 复用历史归档查询能力，支持按语言、方向、profile、来源、风险提示、质量分、Trending 排名和关键词筛选。返回结构保持为：

```text
schema_version
count
projects
```

其中 `projects` 内部字段与归档查询结果保持一致。后续如需新增字段，应先更新本文档、`docs/api.md` 和对应测试。

`/v1/recommendations` 会在存在匹配反馈时为项目附加：

```text
project_profile
recommendation_score
ranking_factors
preference_score
feedback_memory
feedback_reason
rag_reason
recommendation_reason
next_actions
```

`project_profile` 是项目研究档案，包含 `project_positioning`、`use_cases`、`strengths`、`risks`、`quality_summary`、`tracking_reason`、`rag_summary` 和 `agent_judgement`。`ranking_factors` 包含 `base_score`、`quality_score`、`trend_score`、`rag_relevance_score`、`preference_score`、`tracking_score` 和 `risk_penalty`。`next_actions` 是项目级 Agent 动作列表，包含 `task_id`、`task_type`、`priority`、`status`、`reason`、`source` 和 `subscription_action`。`feedback_memory` 只包含反馈计数、平均评分、最近评分、标签、最近备注和排序调整值，不包含密钥或私有请求头。三个 reason 字段只保存派生解释文本，不包含管理口令、请求头或推送密钥。

页面层反馈入口复用同一数据契约：`project.html` 和 `recommendations.html` 只向 `POST /v1/feedback` 写入仓库名、profile、评分、标签、备注和来源；`admin.html` 读取 `GET /v1/feedback?limit=200` 的列表与汇总，并读取 `/v1/recommendations?limit=20` 展示受反馈影响的推荐项目，不公开管理口令、请求头或任何密钥。

`/v1/dev-context/index` 会采集开发材料并写入 SQLite 开发上下文表。当前保存内容包括 README、API 文档、数据契约、操作日志、Git diff、测试输出和安全检查输出；写入前会对明显密钥形态做脱敏。`/v1/dev-context/index-plan` 只创建 `dev_context_index` planned job，任务请求公开 `run_checks`、`replace`、`max_command_chars`、`requested_by`、`trigger_source` 和 `confirm_execution`，不保存管理口令或请求头。`/v1/dev-context/search` 只返回匹配分块、来源、摘要和 metadata，不返回管理口令或请求头。`/v1/dev-context/ask` 复用已索引分块生成规则版回答，响应字段固定为 `answer`、`citations`、`evidence`、`confidence`、`question_type`、`retrieval` 和 `next_actions`；该接口不调用外部模型，不写入新的敏感数据。

## 六、`docs/jobs.json`

任务状态公开字段：

```text
job_id
kind
status
run_date
submitted_at
started_at
finished_at
request
result
error
report_url
```

`kind` 当前支持 `weekly_report`、`rag_backfill`、`rag_corpus_rebuild`、`rag_corpus_enrichment`、`rag_embedding_build`、`rag_search_evaluation` 和 `dev_context_index`。`rag_corpus_enrichment` 表示按内容哈希缓存、显式确认执行的 Kimi 结构化语料增强；无密钥或单项失败不影响确定性语料。

`request` 只公开 `profile`、`sources`、`dry_run`、`requested_dry_run`、`confirm_delivery`、`delivery_allowed`、`days_back`、`trigger_source`、`requested_by`、`safety_warnings`、`queries`、`language`、`category`、`source`、`limit`、`rag_limit`、`mode`、`model`、`auto_build`、`confirm_execution`、`maintenance_action`、`coverage_limit`、`min_gap_count`、`dimensions`、`run_checks`、`replace` 和 `max_command_chars`。这些字段用于任务审计、检索评估、开发上下文索引和受控推送/补库确认，不应包含 Token、Chat ID、Webhook 或其他密钥。

`result` 只公开运行日期、状态、项目数量、Kimi/降级状态、Telegram 状态、报告路径、报告链接、SQLite 同步状态、RAG 回填数量、回填前覆盖概况、语料/向量维护计数、检索评估摘要、开发上下文索引运行编号、来源数、分块数、embedding 数、命令数、回填项目摘要和截断后的错误摘要。RAG 回填任务中的 `processed_repositories` 只保留仓库名、状态、质量分、质量等级和解释编号，不保存完整解释正文；RAG 检索评估任务只保存样本查询、聚合命中结果、模式对比结果和概要建议；开发上下文索引任务只保存计数和 `run_id`，详细片段仍通过 `dev_chunks`/`dev_corpus` 查询，不保存密钥或私有请求头。

## 七、SQLite 表

当前 SQLite 表：

```text
runs
repositories
selections
project_corpus
project_corpus_fts
rag_chunks
rag_chunks_fts
rag_corpus_enrichments
rag_embeddings
rag_explanations
project_feedback
project_agent_tasks
project_agent_task_runs
subscription_events
notification_candidates
notification_deliveries
dev_runs
dev_corpus
dev_chunks
dev_chunks_fts
dev_embeddings
trend_summaries
sent_repositories
star_history
jobs
job_events
subscriptions
migration_meta
```

说明：

1. `runs` 保存运行摘要索引。
2. `repositories` 保存仓库基础信息。
3. `selections` 保存每次运行入选项目及排序信息。
4. `project_corpus` 保存从入选项目派生的公开文本语料、`payload_json.project_profile`、`payload_json.agent_tasks` 和 `payload_json.agent_task_runs`，用于本地搜索、后续向量检索和 RAG。`corpus_version`、`cleaner_version`、`content_hash` 标识可重复构建版本；`noise_json` 记录清洗计数；`source_manifest_json` 记录各原始归档来源的清洗后哈希和可信标记。原始 README 仍只保留在 selections/repository payload，不复制到语料表。
5. `project_corpus_fts` 保存 `project_corpus` 的 SQLite FTS5 搜索索引，可由派生语料重建。
6. `rag_chunks` 保存从 `project_corpus` 按 `source_type` 拆分出的短文本证据块，来源包括 `identity`、`description`、`readme`、`selection_reason`、`project_profile`、`risk`、`agent_memory` 和 `model_enrichment`。每个 chunk 保存语料/清洗器版本、内容哈希和 `is_untrusted`；同一 corpus 内去重，不跨运行日期删除历史证据。
7. `rag_chunks_fts` 保存 `rag_chunks` 的 SQLite FTS5 搜索索引，可由派生语料重建。
8. `rag_embeddings` 保存从 `rag_chunks` 派生的本地 embedding 向量索引；当前默认模型为 `local-hash-v1`，可重建，不保存密钥。
8.1 `rag_corpus_enrichments` 按来源哈希、清洗器版本、prompt 版本和 Kimi 模型缓存结构化字段、逐字段证据与截断错误；不保存完整模型原始回答。通过证据校验的结果写入 `project_corpus.structured_json` 和 `model_enrichment` chunk，但 P0-3 不用于硬过滤或首选排名。
9. `rag_explanations` 保存 RAG 解释结果、引用、检索参数、解释摘要和规则版质量评估，用于后续质量评估和模型替换对比；不保存密钥。
10. `project_feedback` 保存用户对项目的显式反馈，包括仓库名、profile、评分、标签、备注和来源，用于后续个性化记忆、RAG 重排和推荐校准；不保存密钥。
11. `project_agent_tasks` 保存项目级任务类型、优先级、状态、原因、执行结果、来源、去重键和生命周期时间。`payload_json.subscription_action` 只描述后续订阅动作，不保存推送密钥。
12. `project_agent_task_runs` 保存每次任务执行的输入、证据、引用、结构化结果、错误和生命周期。运行状态为 `running`、`succeeded` 或 `failed`；失败记录保留已采集证据。
13. `subscription_events` 保存项目变化事件、严重度、来源运行、证据、引用和稳定去重键。
14. `notification_candidates` 保存订阅规则匹配后生成的待确认推送内容和目标渠道，不代表已经发送。
15. `notification_deliveries` 保存逐渠道投递状态、尝试次数、错误和响应摘要；`dedupe_key` 约束同一订阅、事件、渠道的重复发送。
16. `dev_runs` 保存每次开发上下文索引任务的状态、来源数量、分块数量、embedding 数量和错误摘要。
13. `dev_corpus` 保存开发上下文原始材料，包括文档、Git diff、测试输出和安全检查输出；写入前应脱敏。
14. `dev_chunks` 保存从开发上下文材料拆分出的短文本片段。
15. `dev_chunks_fts` 保存 `dev_chunks` 的 SQLite FTS5 搜索索引。
16. `dev_embeddings` 保存从 `dev_chunks` 派生的本地确定性 embedding；当前只作为后续向量检索预留，不接外部向量库。
16. `trend_summaries` 保存趋势摘要。
17. `sent_repositories` 保存已推送仓库状态。
18. `star_history` 保存 Star 历史。
19. `jobs` 保存历史周报任务和触发预览任务状态。
20. `job_events` 保存任务创建、重复命中、执行请求、执行阻止和执行完成等审计事件。
21. `subscriptions` 保存本地订阅偏好，只记录筛选条件和通道名称，不记录 Token、Chat ID 或 Webhook。
22. `migration_meta` 保存迁移元数据。

事件订阅扩展契约：

1. `subscriptions.payload_json` 可保存 `full_names`、`event_types`、`min_severity` 和 `frequency`；`frequency` 当前允许 `immediate`、`daily`、`weekly`。
2. `subscription_events.event_type` 当前允许 `trending_entered`、`star_growth_spike`、`quality_changed`、`risk_added`、`risk_resolved`、`release_detected`、`agent_decision_changed`。
3. 每条 `subscription_events` 必须包含非空 `evidence_json` 和 `citations_json`；事件检测只写入新事件，不覆盖后续处理状态。
4. `notification_candidates` 由启用订阅与事件匹配生成，状态初始为 `pending`，`payload_json.requires_confirmation` 必须为 `true`。
5. 候选去重键由订阅和事件共同确定。重复构建不新增候选，也不重置已存在候选的状态。
6. `notification_candidates` 只表达待确认意图，不代表发送成功；真实发送结果必须进入 `notification_deliveries`。
7. 候选状态包括 `pending`、`delivering`、`partial`、`failed`、`delivered`；投递状态包括 `running`、`succeeded`、`failed`、`skipped`。
8. `notification_deliveries.dedupe_key` 由订阅、事件和规范化渠道共同确定；失败重试更新同一记录并递增 `attempt_count`，不得创建第二条渠道记录。
9. 真实外发必须同时满足 `dry_run=false` 和 `confirm_delivery=true`。预览和未确认请求不得写入投递记录，也不得调用外部渠道。
10. 渠道成功后对应事件状态更新为 `notified`；逐渠道响应只保存安全结果摘要，不保存密钥、Webhook 或请求头。

当前只读查询入口位于：

```text
scripts/query_archive.py
```

该脚本只消费 SQLite 派生索引和公开归档字段，支持按语言、方向、profile、来源、风险提示和关键词查询历史项目。它不改变 JSON 事实来源，也不会写入密钥或私有配置。

## 七、契约测试

契约测试位于：

```text
tests/test_data_contracts.py
```

该测试会检查：

1. `projects.json` 的字段集合。
2. `runs.json` 的字段集合。
3. `jobs.json` 的字段集合。
4. SQLite 关键表字段集合。

如果未来确实需要新增、删除或重命名字段，应先确认下游影响，再同步更新契约测试和本文档。

## 八、RSS 输出

RSS 文件位于：

```text
docs/feed.xml
```

用途：

1. RSS 阅读器订阅每周周报。
2. 后续自动化工具监听周报更新。
3. 作为微信、飞书、邮件等渠道之外的轻量订阅入口。

说明：

1. 每个条目对应一份周报。
2. 如果运行摘要中存在公开 Pages 地址，RSS 会优先使用完整链接。
3. RSS 描述只包含公开摘要，不包含密钥、原始错误堆栈或未脱敏配置。
