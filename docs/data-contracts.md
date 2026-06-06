# 数据契约说明

本文档记录当前公开 JSON 和 SQLite 派生索引的稳定字段。后续前端、微信、飞书、RSS 或外部脚本应优先依赖这些字段。

## 一、设计原则

1. JSON 归档仍是事实来源。
2. `docs/projects.json`、`docs/runs.json`、`docs/jobs.json` 和 `docs/profiles.json` 是公开展示与订阅入口。
3. SQLite 是可重建派生索引，不提交数据库文件。
4. 公共数据不能包含密钥、用户隐私、未脱敏配置或原始错误堆栈。
5. 修改字段时必须同步更新测试、文档和下游消费逻辑。

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
GET /v1/rag/diagnostics
```

`/api/projects` 复用历史归档查询能力，支持按语言、方向、profile、来源、风险提示、质量分、Trending 排名和关键词筛选。返回结构保持为：

```text
schema_version
count
projects
```

其中 `projects` 内部字段与归档查询结果保持一致。后续如需新增字段，应先更新本文档、`docs/api.md` 和对应测试。

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

`kind` 当前支持 `weekly_report`、`rag_backfill`、`rag_corpus_rebuild`、`rag_embedding_build` 和 `rag_search_evaluation`。`weekly_report` 表示周报任务，`rag_backfill` 表示 RAG 解释回填任务，`rag_corpus_rebuild` 表示从 JSON 归档重建 SQLite RAG 语料与证据块，`rag_embedding_build` 表示从 `rag_chunks` 构建本地 embedding 索引，`rag_search_evaluation` 表示一次 RAG 检索质量评估任务。

`request` 只公开 `profile`、`sources`、`dry_run`、`requested_dry_run`、`confirm_delivery`、`delivery_allowed`、`days_back`、`trigger_source`、`requested_by`、`safety_warnings`、`queries`、`language`、`category`、`source`、`limit`、`rag_limit`、`mode`、`model`、`auto_build`、`confirm_execution`、`maintenance_action`、`coverage_limit`、`min_gap_count` 和 `dimensions`。这些字段用于任务审计、检索评估和受控推送/补库确认，不应包含 Token、Chat ID、Webhook 或其他密钥。

`result` 只公开运行日期、状态、项目数量、Kimi/降级状态、Telegram 状态、报告路径、报告链接、SQLite 同步状态、RAG 回填数量、回填前覆盖概况、语料/向量维护计数、检索评估摘要、回填项目摘要和截断后的错误摘要。RAG 回填任务中的 `processed_repositories` 只保留仓库名、状态、质量分、质量等级和解释编号，不保存完整解释正文；RAG 检索评估任务只保存样本查询、聚合命中结果、模式对比结果和概要建议，不保存密钥或私有请求头。

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
rag_embeddings
rag_explanations
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
4. `project_corpus` 保存从入选项目派生的公开文本语料，用于本地搜索、后续向量检索和 RAG。
5. `project_corpus_fts` 保存 `project_corpus` 的 SQLite FTS5 搜索索引，可由派生语料重建。
6. `rag_chunks` 保存从 `project_corpus` 拆分出的短文本证据块，用于 RAG 检索、引用和后续 embedding。
7. `rag_chunks_fts` 保存 `rag_chunks` 的 SQLite FTS5 搜索索引，可由派生语料重建。
8. `rag_embeddings` 保存从 `rag_chunks` 派生的本地 embedding 向量索引；当前默认模型为 `local-hash-v1`，可重建，不保存密钥。
9. `rag_explanations` 保存 RAG 解释结果、引用、检索参数、解释摘要和规则版质量评估，用于后续质量评估和模型替换对比；不保存密钥。
10. `trend_summaries` 保存趋势摘要。
11. `sent_repositories` 保存已推送仓库状态。
12. `star_history` 保存 Star 历史。
13. `jobs` 保存历史周报任务和触发预览任务状态。
14. `job_events` 保存任务创建、重复命中、执行请求、执行阻止和执行完成等审计事件。
15. `subscriptions` 保存本地订阅偏好，只记录筛选条件和通道名称，不记录 Token、Chat ID 或 Webhook。
16. `migration_meta` 保存迁移元数据。

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
