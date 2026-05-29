# `/v1` 后端核心接口说明

本文记录后续核心功能建设中的 `/v1/*` 服务接口。`/api/*` 继续作为兼容的只读接口保留，`/v1/*` 用于后端服务化、任务调度和 Agent/RAG 能力扩展。

## 设计原则

1. 查询接口可以同步返回。
2. 采集、生成、推送等长任务必须走任务模型。
3. 采集、生成、推送必须先落到任务模型，再通过受控执行入口交给 job runner。
4. 查询接口只读取公开归档或本地派生索引，触发创建接口只写入任务状态，不返回密钥。
5. 当前已提供本地受控执行入口，后续再演进为异步 worker、队列和权限控制。

## 当前接口

### `GET /v1/health`

返回服务状态、归档状态和能力开关。

关键字段：

| 字段 | 说明 |
|---|---|
| `api_version` | 当前接口版本 |
| `capabilities.projects_query` | 是否支持项目查询 |
| `capabilities.project_detail` | 是否支持项目详情 |
| `capabilities.recommendations` | 是否支持个性化推荐查询 |
| `capabilities.subscriptions` | 是否支持本地订阅配置 |
| `capabilities.database_summary` | 是否支持 SQLite 数据库概览 |
| `capabilities.database_trends` | 是否支持 SQLite 运行趋势查询 |
| `capabilities.database_facets` | 是否支持 SQLite 分面统计查询 |
| `capabilities.project_search` | 是否支持项目语料搜索 |
| `capabilities.project_similarity` | 是否支持相似项目候选召回 |
| `capabilities.project_compare` | 是否支持项目横向对比 |
| `capabilities.rag_corpus` | 是否支持 RAG-ready 语料输出 |
| `capabilities.runs_query` | 是否支持运行记录 |
| `capabilities.jobs_query` | 是否支持任务查询 |
| `capabilities.job_events` | 是否支持任务审计事件查询 |
| `capabilities.run_trigger_preview` | 是否支持触发预检 |
| `capabilities.job_retry` | 是否支持 failed 任务重试 |
| `capabilities.local_job_runner` | 是否支持本地任务执行器 |
| `capabilities.run_trigger_execute` | 是否支持受控任务执行；当前为 `true` |

### `GET /v1/projects`

兼容 `/api/projects`，用于正式服务接口的项目检索。

支持参数：

| 参数 | 说明 |
|---|---|
| `language` | 按主要语言过滤 |
| `category` | 按项目方向过滤 |
| `profile` | 按个性化方向过滤 |
| `source` | 按来源过滤，例如 `github_trending` |
| `risk` | `has` 或 `none` |
| `quality_level` | `high`、`medium`、`low`、`unknown` |
| `min_quality` | 最低质量分 |
| `trending_top` | 只看 Trending TopN |
| `query` | 关键词 |
| `limit` | 返回数量 |
| `sort` | 排序方式 |

### `GET /v1/projects/{owner}/{repo}`

兼容 `/api/projects/{owner}/{repo}`，返回项目详情、历史入选记录、推荐理由、趋势判断、质量信号、风险提示和相似项目。

### `GET /v1/recommendations`

面向用户选择场景的个性化推荐接口。它复用 `/v1/projects` 的历史索引和 profile 过滤能力，但响应字段以推荐页为中心。

支持参数：

| 参数 | 说明 |
|---|---|
| `profile` | 个性化方向，例如 `agent_development`、`python`、`java` |
| `language` | 主要语言，例如 `Python`、`Java` |
| `category` | 项目方向，例如 `AI Agent`、`Backend` |
| `query` | 关键词 |
| `limit` | 返回数量，默认 20，最大 200 |
| `sort` | 排序方式，默认 `score` |

返回字段：

| 字段 | 说明 |
|---|---|
| `recommendations` | 推荐项目数组 |
| `selection_summary` | 筛选条件、命中数量、Trending 命中和首选项目说明 |
| `profile` / `language` / `category` / `query` | 当前筛选条件回显 |

该接口用于 `docs/recommendations.html`，后续也可作为用户订阅、移动端推送和多渠道精准推荐的统一读取入口。

### `GET /v1/subscriptions`

查询本地订阅配置。订阅用于保存用户选择的 profile、语言、方向、关键词、排序、数量和通道名称。该接口不返回任何 Token、Chat ID、Webhook 或密钥。

查询参数：

| 参数 | 说明 |
|---|---|
| `status` | 可选 `enabled` 或 `disabled` |
| `limit` | 返回数量，默认 50，最大 200 |

### `POST /v1/subscriptions`

创建订阅配置。请求字段：

| 字段 | 说明 |
|---|---|
| `name` | 订阅名称 |
| `profile` | 个性化方向 |
| `language` | 主要语言 |
| `category` | 项目方向 |
| `query` | 关键词 |
| `sort` | 排序方式 |
| `limit` | 推荐数量，最大 50 |
| `channels` | 通道名称数组，只保留 `telegram`、`feishu`、`wechat`、`wecom` |

### `PATCH /v1/subscriptions/{subscription_id}`

更新订阅配置或启停状态。常用场景是把 `status` 改为 `enabled` 或 `disabled`。

### `GET /v1/subscriptions/{subscription_id}/recommendations`

按订阅编号预览推荐结果。接口会读取该订阅保存的 profile、语言、方向、关键词、排序和数量，并复用 `/v1/recommendations` 的筛选逻辑返回匹配项目。该接口用于订阅页预览、推送前调试和后续多渠道精准推送，不读取任何密钥。

查询参数：

| 参数 | 说明 |
|---|---|
| `limit` | 可选，临时覆盖订阅保存的推荐数量，最大 200 |

### `GET /v1/runs`

兼容 `/api/runs`，返回公开运行记录。

### `GET /v1/database/summary`

返回 SQLite 数据库概览。该接口用于数据库健康检查、后续管理台数据库面板和 RAG 索引准备，不直接执行迁移以外的业务任务。

返回字段：

| 字段 | 说明 |
|---|---|
| `table_counts` | 核心表记录数 |
| `latest_run` | 最近运行记录 |
| `latest_job` | 最近任务记录 |
| `job_status_counts` | 任务状态分布 |
| `subscription_status_counts` | 订阅状态分布 |
| `top_languages` | 主要语言分布 |
| `top_categories` | 项目方向分布 |
| `recent_events` | 最近任务审计事件 |
| `rag_readiness` | 后续构建文本索引和向量检索的基础数据量提示 |

### `GET /v1/database/trends`

返回近 N 次运行的趋势点，默认 20 条，最大 100 条。趋势点按时间升序返回，字段包括运行日期、状态、采集数量、入选数量、新增 Star、Trending 命中率、Trending Top10 命中数、Kimi/降级/推送状态等。

该接口是后续数据库分析、管理台图表、推荐特征工程和 RAG 数据健康检查的基础，不触发外部请求。

### `GET /v1/database/facets`

返回 SQLite 分面统计，默认每类 20 条，最大 100 条。当前分面包括语言、项目方向、来源、质量等级、风险状态和订阅偏好分布。

该接口用于把项目库从“列表查询”推进到“可分析的数据资产”：前端可以直接用它生成筛选器和图表，推荐系统可以用它判断偏好覆盖情况，后续 RAG/向量索引也可以用它检查语料是否具备足够的语言、方向和来源分布。

### `GET /v1/search`

基于 SQLite `project_corpus` 派生语料表搜索历史入选项目。当前优先使用 SQLite FTS5，FTS 不可用时自动回退到普通文本匹配。参数包括 `q`、`language`、`category`、`source` 和 `limit`。

该接口是 RAG 的前置层：先把 README 摘要、项目描述、推荐理由、语言、方向和来源统一成可检索语料，再逐步升级到 Embedding、向量库或 LangChain 编排。当前版本不调用外部模型，也不写入密钥。

### `GET /v1/rag/corpus`

面向后续 RAG、向量检索和 LangChain 编排的语料出口。接口读取 SQLite `project_corpus`，返回 `documents[].text`、`documents[].metadata` 和 `documents[].evidence`，不调用模型、不生成 embedding、不写入外部服务。

支持参数包括 `q`、`language`、`category`、`source` 和 `limit`。传入 `q` 时优先使用 FTS5 检索，FTS 不可用时回退普通文本匹配；不传 `q` 时返回最新语料。

该接口是数据库能力升级的核心出口。后续新增向量表、embedding 作业或 RAG 问答时，应复用这个语料契约。

### `GET /v1/projects/{owner}/{repo}/similar`

基于项目详情和 `project_corpus` 语料索引生成相似项目候选。接口会自动提取项目名称、简介、方向和历史入选信息中的关键词，优先通过 SQLite FTS5 召回候选，再综合同语言、同方向、同来源、关键词重合、Trending 排名和新增 Star 生成可解释排序。

查询参数：

| 参数 | 说明 |
|---|---|
| `limit` | 返回候选数量，默认 10，最大 50 |

响应字段：

| 字段 | 说明 |
|---|---|
| `source_project` | 被查询项目的基础信息 |
| `similar_projects` | 相似项目候选列表 |
| `similarity_score` | 候选相似度分 |
| `similarity_reasons` | 同语言、同方向、同来源、关键词和热度等解释 |
| `search_engine` | 候选召回使用的检索引擎 |

该接口是 RAG/个性化推荐的候选池层，不调用外部模型，不读写密钥。后续可以在该接口结果上增加 Embedding 重排、LangChain 编排、用户反馈权重和模型生成解释。

### `GET /v1/projects/compare`

对多个历史入选项目做结构化横向比较。接口通过 `repos` 参数接收逗号分隔的仓库全名，最多比较 8 个项目，并返回缺失项目列表。

查询参数：

| 参数 | 说明 |
|---|---|
| `repos` | 必填，逗号分隔的 `owner/repo` 列表 |

响应字段：

| 字段 | 说明 |
|---|---|
| `projects` | 项目基础信息、历史热度、质量和风险摘要 |
| `matrix` | 按指标展开的对比矩阵 |
| `best_by` | 不同指标下的领先项目 |
| `missing` | 未找到的项目 |
| `selection_summary` | 对比摘要 |

该接口是项目对比页和 RAG 解释层的基础能力，不调用外部服务，不生成推送，不写入任务状态。后续可以在此基础上加入用户偏好权重、模型总结和前端可视化对比。

### `GET /v1/jobs`

从 SQLite 派生索引的 `jobs` 表读取任务视图。当前每次历史周报运行会同步为一个 `weekly_report` 任务，手动触发预览会写入一个 `preview:*` 计划任务。

查询参数：

| 参数 | 说明 |
|---|---|
| `status` | 按任务状态筛选，可选 `planned`、`running`、`succeeded`、`failed` |
| `kind` | 按任务类型筛选，当前为 `weekly_report` |
| `profile` | 按个性化 profile 精确筛选 |
| `query` | 按任务编号、日期、来源、报告链接等文本关键词筛选 |
| `limit` | 返回数量，默认 20，最大 200 |

任务字段：

| 字段 | 说明 |
|---|---|
| `job_id` | 任务编号，例如 `run:2026-05-09` |
| `kind` | 任务类型，当前为 `weekly_report` |
| `status` | `planned`、`running`、`succeeded` 或 `failed` |
| `run_date` | 对应运行日期 |
| `submitted_at` | 任务提交时间 |
| `request` | 标准化后的任务请求 |
| `result` | 任务执行结果摘要 |
| `selected_count` | 入选项目数 |
| `collected_count` | 候选项目数 |
| `kimi_used` | 是否使用 Kimi |
| `telegram_sent` | 是否已推送 Telegram |
| `report_url` | 周报页面路径 |

### `GET /v1/jobs/{job_id}`

查询单个任务详情。对于历史周报任务，会同时返回对应 `data/runs/YYYY-MM-DD.json` 的运行摘要。

### `GET /v1/jobs/{job_id}/events`

查询单个任务的审计事件，事件按创建时间升序返回。当前会记录：

| 事件类型 | 说明 |
|---|---|
| `job_created` | 创建 planned 任务 |
| `duplicate_trigger_ignored` | 命中已有 active 任务，未重复创建 |
| `execution_requested` | 收到执行请求 |
| `execution_blocked` | 执行请求被阻止 |
| `execution_started` | 任务已交给 job runner |
| `execution_finished` | job runner 返回执行结果 |
| `runner_started` | 本地任务执行器开始消费 planned 任务 |
| `runner_finished` | 本地任务执行器执行完成并写回结果 |
| `runner_failed` | 本地任务执行器执行失败并写回错误 |
| `retry_requested` | 收到重试请求 |
| `retry_blocked` | 重试请求被阻止 |
| `retry_duplicate_ignored` | 已存在相同 active 任务，未重复创建 |
| `retry_created` | 已创建新的 planned 重试任务 |

事件字段包括 `event_id`、`job_id`、`event_type`、`status`、`actor`、`created_at`、`message` 和 `payload`。事件只保存审计摘要，不保存 Token、Chat ID、Webhook 或请求头。

### `GET /v1/job-execution-check?job_id=...`

执行前检查接口，只判断任务是否可以被 `scripts/run_planned_job.py` 消费，不直接执行任务。

返回字段：

| 字段 | 说明 |
|---|---|
| `found` | 是否找到任务 |
| `executable` | 是否满足执行器消费条件 |
| `execution_path` | 建议执行入口 |
| `request` | 任务请求摘要 |
| `blockers` | 阻止执行的原因 |
| `warnings` | 执行前提示，例如真实推送风险 |
| `next_command` | 可执行时给出的本地执行命令 |

当前规则：只有 `kind=weekly_report` 且 `status=planned` 的任务可执行；如果 `dry_run=false` 但没有 `confirm_delivery=true`，会被阻止。

### `POST /v1/jobs/{job_id}/execute`

受控执行单个 planned 任务。该接口会先调用同一套执行前检查逻辑，检查不通过时只返回阻止原因，不会执行任务。

请求示例：

```json
{
  "confirm_execution": true
}
```

返回字段：

| 字段 | 说明 |
|---|---|
| `accepted` | 是否接受本次执行请求 |
| `executed` | runner 是否实际执行 |
| `job_id` | 任务编号 |
| `status` | runner 返回的任务状态 |
| `blockers` | 阻止执行的原因 |
| `warnings` | 执行前提示 |
| `precheck` | 执行前检查结果 |
| `runner_result` | `src.job_runner.run_planned_job()` 返回的结果摘要 |

执行规则：

1. 必须传入 `confirm_execution=true`。
2. 任务必须通过 `/v1/job-execution-check`。
3. `dry_run=false` 的真实推送任务仍必须在任务请求中包含 `confirm_delivery=true`。
4. API 只调用现有 job runner，不单独实现采集、生成或推送逻辑。

### `POST /v1/jobs/{job_id}/retry`

为 failed 任务创建一个新的 planned 重试任务。该接口只创建任务，不直接执行。

请求示例：

```json
{
  "requested_by": "local-user"
}
```

执行规则：

1. 原任务必须存在。
2. 原任务必须是 `weekly_report`。
3. 原任务状态必须是 `failed`。
4. 新任务复用原任务 `request`，并追加 `trigger_source=retry`、`requested_by` 和 `retry_of`。
5. 如果已经存在相同参数的 `planned` 或 `running` 任务，则返回已有任务，不重复创建。

返回字段：

| 字段 | 说明 |
|---|---|
| `accepted` | 是否接受重试请求 |
| `retry_created` | 是否创建了新的 planned 重试任务 |
| `original_job_id` | 原失败任务编号 |
| `job_id` | 新重试任务编号，或命中的已有 active 任务编号 |
| `status` | 新任务或已有任务状态 |
| `blockers` | 阻止重试的原因 |
| `duplicate_of` | 命中已有 active 任务时返回 |
| `retry_job` | 新任务或已有任务摘要 |

### `POST /v1/runs/trigger`

创建一次受控的周报计划任务并写入 `jobs` 表，不在 HTTP 请求中直接执行采集、生成或推送。

请求示例：

```json
{
  "profile": "agent_development",
  "sources": ["github_trending"],
  "dry_run": true,
  "days_back": 7,
  "trigger_source": "api",
  "requested_by": "local-user",
  "confirm_delivery": false
}
```

请求规则：

| 字段 | 说明 |
|---|---|
| `profile` | 个性化方向，可为空 |
| `sources` | 期望来源标签，当前用于审计和筛选 |
| `dry_run` | `true` 时执行器会跳过主流程内置推送 |
| `days_back` | 回看天数 |
| `trigger_source` | 触发来源，例如 `api`、`github_actions`、`manual` |
| `requested_by` | 触发人或系统标识，只保存非密钥文本 |
| `confirm_delivery` | 只有该值为 `true` 且 `dry_run=false` 时，才允许真实推送 |

当前返回：

| 字段 | 说明 |
|---|---|
| `job_id` | 预览任务编号，格式为 `preview:*` |
| `status` | 当前为 `planned` |
| `execution_supported` | 当前为 `false` |
| `planned_job_created` | 是否已创建 planned 任务 |
| `duplicate_of` | 如果命中已有 active 任务，则返回已有任务编号 |
| `execution_path` | 后续执行入口，例如 `scripts/run_planned_job.py` |
| `request` | 标准化后的请求参数 |
| `safety_warnings` | 安全降级提示，例如未确认推送时强制 dry_run |
| `next_steps` | 启用真实后台执行前需要完成的步骤 |

设计原因：GitHub 采集、LLM 生成、页面构建和推送都是长任务，不能直接塞进 HTTP 请求生命周期。当前先持久化任务计划，再由本地任务执行器把任务从 `planned` 推进到 `running`、`succeeded` 或 `failed`。如果请求传入 `dry_run=false` 但没有 `confirm_delivery=true`，接口会自动改为 `dry_run=true`，避免前端或脚本误触发真实推送。

重复任务防护：如果同一组 `profile`、`sources`、`dry_run`、`confirm_delivery` 和 `days_back` 已经存在 `planned` 或 `running` 任务，接口会返回已有 `job_id`，并设置 `planned_job_created=false`，不重复写入新任务。

### 任务状态页接入方式

`docs/jobs.html` 在本地后端环境或 URL 带 `api=1` 时优先读取 `/v1/jobs?limit=200`，读取失败时回退到 `jobs.json`。GitHub Pages 上默认使用静态 `jobs.json`，避免公开页面依赖常驻后端。

`docs/subscriptions.html` 在本地后端环境或 URL 带 `api=1` 时读取 `/v1/subscriptions`，并支持创建、启用和停用订阅。GitHub Pages 静态模式不写入订阅，只提示需要启动本地 API。

页面筛选参数和 `/v1/jobs` 保持同一语义：

| 页面参数 | API 参数 | 说明 |
|---|---|---|
| `status` | `status` | 任务状态 |
| `kind` | `kind` | 任务类型 |
| `profile` | `profile` | 个性化方向，精确匹配 |
| `q` | `query` | 关键词搜索，兼容旧的 `query` |
| `api` | 无 | 页面数据源开关，`1` 强制 API，`0` 强制静态 JSON |

任务状态页还提供一个最小 planned 任务创建表单。该表单只在本地后端或 `api=1` 模式下启用，提交时调用 `/v1/runs/trigger`，并固定写入 `trigger_source=jobs_page` 和 `requested_by=local-ui`。表单不会直接执行任务，只会创建 planned 记录；后续仍由 job runner 或 GitHub Actions 消费任务。

任务状态页的每条任务还提供“执行前检查”按钮。该按钮只在本地后端或 `api=1` 模式下调用 `/v1/job-execution-check?job_id=...`，用于展示任务是否可执行、阻止原因、提示信息和建议执行命令；页面不会直接运行任务。

任务状态页还提供“确认执行”按钮。该按钮只在 API 模式且任务状态为 `planned` 时启用，点击后需要浏览器二次确认，并调用 `POST /v1/jobs/{job_id}/execute` 传入 `confirm_execution=true`。执行后页面会重新读取任务列表。

任务状态页还提供“重试”按钮。该按钮只在 API 模式且任务状态为 `failed` 时启用，点击后需要浏览器二次确认，并调用 `POST /v1/jobs/{job_id}/retry`，固定写入 `requested_by=jobs_page`。接口只创建新的 planned 重试任务，不直接执行；请求结束后页面会重新读取任务列表。

任务编号会链接到 `job.html?job=...`。任务详情页在 API 模式下读取 `/v1/jobs/{job_id}` 和 `/v1/jobs/{job_id}/events?limit=200`，展示任务请求、执行结果、错误信息和审计事件时间线；在静态 Pages 模式下只从 `jobs.json` 展示基础任务信息。

任务详情页同时提供单任务操作区：执行前检查调用 `/v1/job-execution-check?job_id=...`，确认执行调用 `POST /v1/jobs/{job_id}/execute`，失败重试调用 `POST /v1/jobs/{job_id}/retry`。详情页固定写入 `requested_by=job_detail_page`，操作后刷新任务详情和事件时间线。静态 Pages 模式下操作按钮禁用。

`admin.html` 是本地管理首页，聚合项目筛选、运行状态、任务状态和任务详情入口。页面在静态模式下只显示只读入口；在本地后端或 `api=1` 模式下读取 `/v1/health`，展示能力开关和归档健康摘要。

本地 FastAPI 已挂载 `docs/` 静态页面，因此启动 `py -m uvicorn src.api.app:app --reload` 后可以直接访问 `http://127.0.0.1:8000/admin.html?api=1`。根路径 `/` 会跳转到该管理首页；`/v1/*` 路径仍保持 JSON API 语义。

管理首页同时读取 `projects.json`、`runs.json` 和任务数据，展示项目总数、最新运行、失败任务数和待执行任务数，并提供最新周报、失败任务和待执行任务的快捷入口。任务数据在 API 模式下优先读取 `/v1/jobs?limit=200`，失败时回退到 `jobs.json`；静态 Pages 模式仍只读取 `jobs.json`。该概览只读取公开归档或本地后端数据，不触发后端任务。

管理首页还会从任务数据中选出最近任务，展示任务编号、状态、完成时间、周报链接、错误信息和下一步建议。下一步建议由任务状态派生：`failed` 引导重试，`planned` 引导执行前检查，`running` 引导等待或查看详情，`succeeded` 引导打开周报或继续查看项目筛选结果。

管理首页新增“核心工作流”区域，把最近周报、Top 项目、失败任务和待执行任务聚合为四个入口。该区域只消费 `projects.json`、`runs.json` 和任务数据：最近周报链接到周报或运行面板，Top 项目链接到项目详情页，失败任务和待执行任务链接到单任务详情页。

管理首页还提供最小 planned 周报任务创建表单。表单在 API 模式下调用 `POST /v1/runs/trigger`，支持传入 `profile`、`days_back`、`sources`、`dry_run` 和 `confirm_delivery`，并固定写入 `trigger_source=admin_page` 与 `requested_by=local-admin`。接口只创建任务，创建成功后跳转到 `job.html?job=...&api=1` 继续人工确认。

管理首页的任务工作台复用同一任务数据源：API 模式优先读取 `/v1/jobs?limit=200`，读取失败时回退到静态 `jobs.json`；静态 Pages 模式默认读取 `jobs.json`。工作台支持按重点、失败、待执行、运行中和全部任务筛选。重点视图聚合 `failed`、`planned` 和 `running`，任务编号链接到 `job.html?job=...`。

管理首页的任务工作台也提供轻量任务操作：执行前检查调用 `/v1/job-execution-check?job_id=...`，planned 任务确认执行调用 `POST /v1/jobs/{job_id}/execute` 并传入 `confirm_execution=true`，failed 任务重试调用 `POST /v1/jobs/{job_id}/retry`。这些按钮只在 API 模式下启用，固定写入 `requested_by=admin_page`，操作完成后重新读取任务概览；静态 Pages 模式下按钮禁用，不会触发后端。

### 本地任务执行器

```bash
python scripts/create_planned_job.py --profile agent_development --days-back 7 --output .weekly-job.json
python scripts/run_planned_job.py --job-file .weekly-job.json
python scripts/run_planned_job.py
python scripts/run_planned_job.py --job-id preview:xxxx
```

执行器只消费 `jobs` 表中的 `planned` 任务。请求中的 `dry_run=true` 时会调用 `run_weekly_report(skip_telegram_send=True)`，避免本地验证误推送；`dry_run=false` 时仍会尊重运行环境中的推送配置。

GitHub Actions 的手动触发入口已接入同一套任务模型，支持输入：

| 输入 | 说明 |
|---|---|
| `profile` | 个性化 profile，例如 `agent_development`、`python`、`java` |
| `days_back` | 回看天数，默认 `7` |
| `skip_main_delivery` | 是否跳过主流程内置推送，默认 `true` |
| `send_link` | 是否在生成后推送 GitHub Pages 周报链接，默认 `true` |

### `GET /v1/reports/latest`

兼容 `/api/weekly/latest`，返回最新 Markdown 周报、运行日期、页面路径和运行摘要。

## 下一步

已完成：

1. `main.py` 主流程已封装为 `src.weekly_run.run_weekly_report()`，CLI 入口只负责输出状态和退出码。
2. `/v1/runs/trigger` 已具备任务计划预览，不会误执行长任务。
3. SQLite 派生索引已增加 `jobs` 和 `subscriptions` 表，历史运行会同步为任务记录，本地订阅会保存为可控配置。
4. `scripts/run_planned_job.py` 已可执行 planned 任务，并写回 running/succeeded/failed 状态。
5. weekly workflow 已接入任务创建和任务执行脚本，手动运行时可指定 profile 和回看天数。

下一步：

1. 增加任务状态页面或 API 管理入口。
2. 支持真实后台状态轮询。
3. 为 Agent/RAG 增加结构化 evidence 字段。
4. 再考虑 SSE 流式任务状态。
