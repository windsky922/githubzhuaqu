# 后端 API 说明

本文档记录当前后端 API 的最小可用设计。`/api/*` 继续作为兼容只读接口，`/v1/*` 用于任务调度、受控执行和后续管理端能力。

## 一、定位

当前项目已经具备 JSON 归档、SQLite 派生索引、GitHub Pages 前端和多通道推送。后端 API 的第一阶段目标是把这些能力整理成稳定入口，方便后续接入更完整的前端、数据库管理、用户订阅和个性化推荐。

设计边界：

1. JSON 归档仍然是事实来源。
2. SQLite 仍然是可重建的派生索引，不提交到 GitHub。
3. API 不读取、不返回任何密钥。
4. `/v1/runs/trigger` 只创建 planned 任务，真实执行必须走任务模型和受控执行入口。
5. `/v1/jobs/{job_id}/execute` 复用执行前检查并调用现有 job runner，不单独实现采集、Kimi 或推送逻辑。

## 二、本地启动

先安装依赖：

```powershell
py -m pip install -r requirements.txt
```

启动服务：

```powershell
py -m uvicorn src.api.app:app --reload
```

默认访问：

```text
http://127.0.0.1:8000/api/health
```

本地管理首页：

```text
http://127.0.0.1:8000/admin.html?api=1
```

### 管理写接口鉴权

本地后端的只读接口不需要鉴权；所有会写入 SQLite、创建任务、执行任务、重试任务、写入反馈或修改订阅的管理型接口都需要管理口令。

配置方式：

```powershell
$env:ADMIN_API_TOKEN="<本地管理口令>"
py -m uvicorn src.api.app:app --reload
```

调用方式任选其一：

```text
X-Admin-Token: <本地管理口令>
Authorization: Bearer <本地管理口令>
```

如果未配置 `ADMIN_API_TOKEN`，管理写接口返回 `403`；如果配置后请求未带正确口令，返回 `401`。受保护接口包括 `/v1/runs/trigger`、`/v1/jobs/{job_id}/execute`、`/v1/jobs/{job_id}/retry`、`/v1/rag/*` 写入/计划接口、`/v1/subscriptions` 写入接口、事件检测、候选构建、候选投递、`POST /v1/feedback` 和项目 Agent 任务写接口。

`admin.html`、`subscriptions.html`、`jobs.html` 和 `job.html` 只从当前页面的密码框读取口令，并仅在写请求中发送 `X-Admin-Token`。新请求中的口令不进入 URL、localStorage、sessionStorage、应用日志或 SQLite，刷新或离开页面后需要重新输入。旧 `admin_token` URL 参数会被忽略并从地址栏删除，旧 `github_weekly_admin_token` 浏览器存储只会删除、不会迁移；这不能撤销旧 URL 已产生的浏览器历史、服务器、代理或 CDN 访问日志。若真实口令曾通过旧方式使用，应立即轮换。

根路径 `http://127.0.0.1:8000/` 会跳转到管理首页。`/v1/*` 路径是 JSON API，例如 `/v1/jobs?limit=50` 返回机器可读任务数据，不是 HTML 页面。

管理首页中的 RAG 区域会调用 `/v1/rag/ask`、`/v1/rag/retrieve`、`/v1/rag/vector-search` 和 `/v1/rag/hybrid-search`，用于查看问答结果、模型状态、降级原因、证据块、引用和 `prompt_context`；开发上下文区域会调用 `/v1/dev-context/index`、`/v1/dev-context/search` 和 `/v1/dev-context/ask`，用于索引开发材料、检索证据和生成规则版审查/诊断回答，并会展示最近 `dev_context_index` 任务状态。后端还提供 `/v1/rag/search-compare`、`/v1/rag/search-evaluation` 和 `/v1/rag/search-evaluation-trends`，用于比较、批量评估和长期观察三种检索模式的召回差异。管理首页会展示检索评估趋势，包括最近评估任务、平均样本数、零命中样本和推荐模式分布。RAG 诊断会调用 `/v1/rag/diagnostics`，用于判断语料、证据块、embedding、解释历史和问答能力是否可用；RAG 质量概览会调用 `/v1/rag/quality-summary`，用于查看解释数量、质量分布、改进建议和低质量样本；RAG 维护计划按钮会调用 `/v1/rag/maintenance-plan`，按诊断结果创建语料重建、embedding 构建或解释回填 planned 任务；维护历史可以通过 `/v1/rag/maintenance-report` 查看最近 RAG 维护任务状态、计数变化和下一步建议；RAG 回填区会调用 `/v1/rag/backfill-explanations`，先预览缺口项目，确认后再写入 SQLite。向量检索会在 `auto_build=true` 时自动构建本地 `local-hash-v1` 索引，也可以先手动运行 `py scripts\build_rag_embeddings.py`。

管理首页的 GPT 式 RAG 对话工作台仍然逐轮调用 `/v1/rag/ask`。对话历史只保存在浏览器 `localStorage.github_weekly_rag_chat_history`，最多 20 轮；后端不保存会话，不把历史回答作为事实证据，也不写入 SQLite。

React 项目匹配工作台位于 `app/#/agent?api=1`，旧 `agent.html?api=1` 自动跳转。它默认 POST `/v1/rag/ask/stream`，并把回答渲染为“最匹配项目、候选项目、折叠证据”。SSE 草稿只标记为质量校验中，`final` 到达后才成为正式结论；clarification、no_match、拒答和规则降级均显示独立状态。会话只保存在浏览器 `localStorage.github_weekly_agent_match_conversations_v1`；下一轮只提交上一轮用户目标、候选 ID、确认首选、模式和 resumable，不提交历史回答、citations、evidence 或 prompt_context。

`GET /api/projects` 与 `GET /v1/projects` 支持可选 `offset`（默认 0）和既有 `limit`（最大 200）。响应保留 `projects` 与 `count`，并新增 `total`、`offset`、`limit`、`has_more`，供 React 筛选页按每页 50 条展示完整历史归档。项目对比选择只保存在浏览器 `localStorage.github_weekly_project_compare_v1`，最多 3 个仓库；URL 中的 `repos` 参数优先于本地暂存。

如果本地没有 `data/github_weekly.sqlite`，查询项目接口会从 `data/` 下的 JSON 归档自动重建 SQLite 派生索引。

### 项目 Agent 任务执行

项目任务执行遵循“预检查 -> 事务抢占 -> 只读处理 -> 保存证据与结果 -> 写回 RAG”的流程：

| 接口 | 说明 |
|---|---|
| `GET /v1/agent-tasks/{task_id}/execution-check` | 返回机器可读执行条件，不写数据库 |
| `POST /v1/agent-tasks/{task_id}/execute` | 执行 planned 任务，受管理口令保护 |
| `POST /v1/agent-tasks/{task_id}/retry` | 重试 failed 任务，受管理口令保护 |
| `GET /v1/agent-tasks/{task_id}/runs` | 查询单任务执行历史 |
| `GET /v1/agent-task-runs` | 查询最近执行记录，供管理页汇总 |

处理器支持 `observe`、`review_risk`、`deep_analysis`、`continue_tracking`、`notify` 和 `ignore`。结果统一包含 `execution_summary`、`decision`、`confidence`、`evidence`、`citations`、`changes`、`risk_changes`、`recommended_actions` 和 `subscription_candidate`。`notify` 只创建订阅候选，不直接调用推送通道。

### 事件订阅与确认投递

| 接口 | 说明 |
|---|---|
| `POST /v1/subscription-events/detect` | 检测项目变化事件，受管理口令保护 |
| `GET /v1/subscription-events` | 按项目、类型、严重度和状态查询事件 |
| `POST /v1/notification-candidates/build` | 按启用订阅构建去重候选，受管理口令保护 |
| `GET /v1/notification-candidates` | 查询待确认或已处理候选 |
| `POST /v1/notification-candidates/{id}/deliver` | 预览或确认逐渠道投递，受管理口令保护 |
| `GET /v1/notification-deliveries` | 查询逐渠道投递审计记录 |

候选投递默认 `dry_run=true`。真实外发必须同时满足 `dry_run=false` 和 `confirm_delivery=true`：

```json
{
  "dry_run": false,
  "confirm_delivery": true,
  "channels": ["telegram", "feishu"],
  "retry_failed": false,
  "requested_by": "admin"
}
```

同一订阅、事件、渠道只保留一条投递记录。成功渠道不会重复发送；失败或配置缺失渠道必须显式设置 `retry_failed=true` 才会增加尝试次数。Telegram、飞书和企业微信继续从环境变量或 GitHub Secrets 读取配置，API 和数据库不保存 Token、Chat ID 或 Webhook。

本地命令入口：

```powershell
python scripts\manage_notifications.py detect --limit 500
python scripts\manage_notifications.py build --limit 500
python scripts\manage_notifications.py preview <candidate_id>
python scripts\manage_notifications.py deliver <candidate_id>
python scripts\manage_notifications.py deliver --no-dry-run --confirm-delivery <candidate_id>
```

`deliver` 和 `deliver-pending` 默认都是 dry-run。真实发送必须同时提供 `--no-dry-run` 与 `--confirm-delivery`；失败渠道重试还需要 `--retry-failed`。

通知记忆同时进入现有 Agent/RAG 返回契约：`GET /v1/recommendations` 的项目项包含 `event_memory` 和 `event_reason`；`POST /v1/rag/ask` 在订阅、通知、推送、触发等相关问题中返回 `notification_memory` 并把证据加入回答；`GET /v1/projects/{owner}/{repo}/rag` 返回该项目最近事件、候选和逐渠道投递摘要。新增字段不改变原有 `answer_model` 版本标识。

## 三、接口

### `GET /api/health`

检查 API 是否可用，并返回本地归档目录和 SQLite 文件是否存在。

### `GET /api/projects`

查询历史入选项目。支持参数：

| 参数 | 说明 |
|---|---|
| `language` | 按主要语言筛选，例如 `Python`、`Java` |
| `category` | 按项目方向筛选，例如 `AI Agent`、`Developer Tools` |
| `profile` | 按 `config/profiles.json` 或示例 profile 筛选 |
| `source` | 按来源筛选，例如 `github_trending`、`github_search` |
| `risk` | `has` 表示有风险提示，`none` 表示无风险提示 |
| `quality_level` | `high`、`medium`、`low` 或 `unknown` |
| `min_quality` | 最低质量分，范围 0 到 100 |
| `trending_top` | 只看进入 GitHub Trending TopN 的项目 |
| `query` | 关键词搜索项目名、简介、方向和推荐理由 |
| `limit` | 返回数量，范围 1 到 200 |
| `sort` | `recent`、`position`、`score`、`star-growth`、`trending`、`quality` |

示例：

```text
/api/projects?profile=agent_development&source=github_trending&trending_top=10&limit=20
```

### `GET /api/projects/{owner}/{repo}`

查询单个项目的历史详情。该接口会按 `owner/repo` 聚合历史入选记录，并返回：

1. 最近一次入选日期和第一次入选日期。
2. 历史入选次数。
3. 累计新增 Star。
4. 最好 GitHub Trending 排名。
5. 推荐理由和趋势判断。
6. 历史来源、质量提示和风险提示。
7. 最近一次完整项目记录。
8. 相似历史项目列表。

示例：

```text
/api/projects/owner/agent
```

这个接口用于后续项目详情页、项目对比、相似项目推荐和个性化订阅解释。

### `GET /api/recommendations`

返回面向用户选择场景的推荐项目列表。它复用历史归档、SQLite 派生索引和 profile 过滤逻辑，但响应字段更适合推荐页直接展示。

支持参数：

| 参数 | 说明 |
|---|---|
| `profile` | 个性化方向，例如 `agent_development`、`python`、`java` |
| `language` | 主要语言，例如 `Python`、`Java`、`TypeScript` |
| `category` | 项目方向，例如 `AI Agent`、`Developer Tools`、`Backend` |
| `query` | 关键词，匹配项目名、简介、方向和推荐理由 |
| `limit` | 返回数量，范围 1 到 200 |
| `sort` | `score`、`trending`、`star-growth`、`quality`、`recent` 等 |

示例：

```text
/api/recommendations?profile=agent_development&language=Python&limit=20
```

返回内容包含：

1. `recommendations`：推荐项目数组。
2. `selection_summary`：本次推荐的筛选条件、命中数量、Trending 命中和首选项目说明。
3. `profile`、`language`、`category`、`query`：前端回显当前筛选条件。
4. `feedback_memory`：当前筛选范围内的反馈记忆摘要。
5. 推荐项目会额外返回 `recommendation_score`、`ranking_factors`、`preference_score`、`feedback_memory`、`feedback_reason`、`rag_reason` 和 `recommendation_reason`。其中 `ranking_factors` 拆分基础分、质量分、趋势分、RAG 相关分、反馈偏好分、继续跟踪分和风险扣分；正向反馈会提高排序，负向反馈会降低排序，“继续跟踪”会额外提高 `tracking_score`。

对应的 v1 入口为：

```text
/v1/recommendations?profile=agent_development&limit=20
```

### `GET /api/runs`

返回公开运行记录，数据来源为 `docs/runs.json`。

### `GET /v1/database/summary`

返回 SQLite 派生索引的数据库概览，用于本地管理台、数据健康检查和后续 RAG 索引准备。该接口会返回：

1. `table_counts`：`runs`、`repositories`、`selections`、`jobs`、`job_events`、`subscriptions`、`project_feedback` 等表的记录数。
2. `latest_run` 和 `latest_job`：最近一次运行和最近一个任务。
3. `job_status_counts` 和 `subscription_status_counts`：任务状态和订阅状态分布。
4. `top_languages` 和 `top_categories`：当前归档中主要语言和项目方向分布。
5. `recent_events`：最近 10 条任务审计事件。
6. `rag_readiness`：后续构建文本索引或向量检索前的基础数据量提示。

该接口只读取本地 SQLite 统计摘要，不返回密钥、Webhook、请求头或完整原始载荷。

### `GET /v1/database/trends`

返回近 N 次运行的数据库趋势点，用于观察周报质量、数据变化和后续推荐特征。支持参数：

| 参数 | 说明 |
|---|---|
| `limit` | 返回最近运行数量，默认 20，最大 100 |

返回内容包括：

1. `points`：按时间升序排列的运行趋势点，包含入选数量、采集数量、新增 Star、Trending 命中率、Top10 命中数量、Kimi/降级/推送状态。
2. `summary`：聚合摘要，包含总入选数量、总新增 Star、平均 Trending 命中率、失败运行数、降级运行数和推送成功数。

该接口只做统计读取，不调用 GitHub、Kimi、Telegram 或任何外部服务。

### `GET /v1/database/facets`

返回数据库分面统计，用于前端筛选、个性化推荐和后续 RAG 索引建设。支持参数：

| 参数 | 说明 |
|---|---|
| `limit` | 每类分面最多返回数量，默认 20，最大 100 |

返回内容包括：

1. `languages`：按语言聚合项目数量、总 Star、总 Fork 和最近推送时间。
2. `categories`：按项目方向聚合入选次数、项目数、新增 Star、平均分和 Trending Top10 命中率。
3. `sources`：按来源聚合入选次数和项目数，例如 `github_trending`、`github_search`。
4. `quality_levels` 和 `risk_levels`：从入选项目载荷中提取质量等级和风险状态。
5. `subscriptions`：统计本地订阅的状态、profile、语言和方向分布。
6. `rag_readiness`：提示当前分面数据是否足够支撑个性化筛选和后续文本索引。

该接口只读取 SQLite 中的公开归档字段，不返回密钥、Webhook、请求头或完整原始载荷。

### `GET /v1/search`

读取 SQLite 派生的 `project_corpus` 语料表，按关键词搜索历史入选项目。当前优先使用 SQLite FTS5，FTS 不可用时自动回退到普通 SQL 文本匹配；不调用模型、不调用外部服务，后续可以平滑升级为向量检索或 RAG。

支持参数：

| 参数 | 说明 |
|---|---|
| `q` | 必填，搜索关键词，多个词用空格分隔 |
| `language` | 可选，按语言过滤 |
| `category` | 可选，按项目方向过滤 |
| `source` | 可选，按来源过滤，例如 `github_trending` |
| `limit` | 返回数量，默认 20，最大 100 |

返回内容包括：

1. `results`：搜索结果数组，包含项目名、链接、语言、方向、来源、命中片段、质量等级、Trending 排名和新增 Star。
2. `search_engine`：本次使用的搜索引擎，通常为 `fts5`，回退时为 `like`。
3. `summary`：本次搜索的命中数量、主要语言和主要方向。

示例：

```text
/v1/search?q=agent%20workflow&language=Python&limit=10
```

### `GET /v1/rag/corpus`

读取 SQLite 派生的 `project_corpus` 语料表，输出可直接进入 RAG 管道的文档列表。这个接口不会调用模型、不会生成 embedding、不会请求外部服务，只负责把历史项目语料整理成稳定的 `text + metadata + evidence` 数据契约，方便后续接入向量库、LangChain 或其他检索增强组件。

支持参数：

| 参数 | 说明 |
|---|---|
| `q` | 可选，关键词检索；传入后优先使用 SQLite FTS5，失败时回退普通文本匹配 |
| `language` | 可选，按语言过滤 |
| `category` | 可选，按项目方向过滤 |
| `source` | 可选，按来源过滤，例如 `github_trending` |
| `limit` | 返回文档数量，默认 20，最大 100 |

返回内容包括：

1. `documents`：RAG 文档数组，每条包含 `id`、`text`、`metadata` 和 `evidence`。
2. `metadata`：包含仓库全名、GitHub 链接、入选日期、语言、方向、来源、质量等级、Trending 排名和新增 Star。
3. `evidence`：从语料文本中抽取的证据片段，用于后续回答时引用或解释。
4. `retrieval`：本次读取使用的模式，可能是 `fts5`、`like` 或 `latest`。
5. `rag_readiness`：提示当前结果是否已经具备 embedding、检索器和 RAG 编排的基础条件。

示例：

```text
/v1/rag/corpus?q=agent%20workflow&language=Python&limit=10
```

该接口是数据库能力升级到 RAG 能力的第一层稳定出口。后续如果接入 embedding 或 LangChain，应优先复用这个接口的字段，而不是重新解析 Markdown 周报或原始 README。

### `GET /v1/rag/retrieve`

基于 SQLite `rag_chunks` 语料块执行 RAG 检索，返回短文本上下文、引用列表和可直接交给后续问答链的 `prompt_context`。这个接口仍然不调用模型、不生成 embedding、不请求外部服务，先用 SQLite FTS5 提供稳定的本地检索能力，后续可以替换或叠加向量检索。

支持参数：

| 参数 | 说明 |
|---|---|
| `q` | 必填，用户问题或检索关键词 |
| `language` | 可选，按语言过滤 |
| `category` | 可选，按项目方向过滤 |
| `source` | 可选，按来源过滤，例如 `github_trending` |
| `limit` | 返回上下文数量，默认 8，最大 30 |

返回内容包括：

1. `contexts`：召回的 RAG 短文本块，包含 `text`、`metadata`、`evidence` 和规则分。
2. `citations`：按上下文顺序生成的引用列表，包含项目名、GitHub 链接、入选日期和 chunk 编号。
3. `prompt_context`：拼接后的上下文文本，供后续 Kimi、OpenAI 或 LangChain 问答链直接使用。
4. `retrieval`：本次检索使用的模式，可能是 `fts5` 或 `like`。

示例：

```text
/v1/rag/retrieve?q=agent%20workflow&language=Python&limit=8
```

该接口是后续“项目知识库问答”和“基于证据的推荐解释”的核心入口。当前阶段只做本地证据召回，避免过早绑定某个向量库或模型供应商。

### `GET /v1/rag/vector-search`

基于本地 `rag_embeddings` 表执行向量检索，返回与用户问题最接近的 RAG 证据块。当前默认模型为确定性 `local-hash-v1`，用于打通向量索引表、构建命令和检索 API；它不调用外部模型、不需要密钥，后续可替换为真实 embedding 模型。

使用前先构建本地索引：

```powershell
py scripts\build_rag_embeddings.py
```

支持参数：

| 参数 | 说明 |
|---|---|
| `q` | 必填，用户问题或检索关键词 |
| `language` | 可选，按语言过滤 |
| `category` | 可选，按项目方向过滤 |
| `source` | 可选，按来源过滤，例如 `github_trending` |
| `limit` | 返回上下文数量，默认 8，最大 30 |
| `model` | 可选，默认 `local-hash-v1` |
| `auto_build` | 可选，为 `true` 且索引为空时自动构建本地索引 |

返回内容与 `/v1/rag/retrieve` 接近，包含 `contexts`、`citations`、`prompt_context` 和 `retrieval`。差异在于 `retrieval.mode` 为 `vector`，排序依据为本地向量相似度。

示例：

```text
/v1/rag/vector-search?q=agent%20workflow&language=Python&limit=8&auto_build=true
```

该接口是后续真正接入 embedding、向量库和 LangChain retriever 的预留层。当前实现只建设稳定数据边界，不改变周报采集、生成和推送流程。

### `GET /v1/rag/hybrid-search`

基于 SQLite FTS5 文本检索和本地 `rag_embeddings` 向量检索执行混合召回。该接口会分别调用文本检索和向量检索，再按同一项目和 chunk 去重，使用固定权重合并排序：文本召回权重 0.55，向量召回权重 0.45。

支持参数与 `/v1/rag/vector-search` 基本一致：

| 参数 | 说明 |
|---|---|
| `q` | 必填，用户问题或检索关键词 |
| `language` | 可选，按语言过滤 |
| `category` | 可选，按项目方向过滤 |
| `source` | 可选，按来源过滤，例如 `github_trending` |
| `limit` | 返回上下文数量，默认 8，最大 30 |
| `model` | 可选，默认 `local-hash-v1` |
| `auto_build` | 可选，为 `true` 且索引为空时自动构建本地索引 |

返回内容包括：

1. `contexts`：混合排序后的证据块，每条包含 `retrieval_sources` 和 `retrieval_scores`。
2. `citations`：按混合排序生成的引用列表。
3. `prompt_context`：拼接后的上下文文本，供后续问答链直接使用。
4. `retrieval`：包含 `mode=hybrid`、文本/向量命中数量、权重和向量模型。

示例：

```text
/v1/rag/hybrid-search?q=agent%20workflow&language=Python&limit=8&auto_build=true
```

该接口是后续接入 LangChain retriever、推荐解释重排和多策略检索评估的优先入口。它仍然只使用本地 SQLite 数据，不调用外部模型或推送服务。

### `GET /v1/rag/search-compare`

同时执行 FTS5 文本检索、本地向量检索和混合检索，并返回三种模式的命中数量、Top 项目、引用数量、项目重叠率和推荐使用的检索模式。该接口用于 RAG 调试、召回质量评估和后续 Agent 自动选择检索策略。

支持参数与 `/v1/rag/hybrid-search` 一致：

| 参数 | 说明 |
|---|---|
| `q` | 必填，查询问题或关键词 |
| `language` | 可选，按语言过滤 |
| `category` | 可选，按方向过滤 |
| `source` | 可选，按来源过滤 |
| `limit` | 返回数量，默认 8，最大 30 |
| `model` | 可选，默认 `local-hash-v1` |
| `auto_build` | 可选，为 `true` 且索引为空时自动构建本地索引 |

返回内容包含：

1. `modes`：`fts5`、`vector`、`hybrid` 三种模式的命中摘要。
2. `overlap`：三种模式的项目集合重叠情况和两两重叠率。
3. `recommendation`：当前查询建议优先使用的检索模式和原因。
4. `summary`：适合前端展示或 Agent 日志记录的中文摘要。

示例：

```text
/v1/rag/search-compare?q=agent%20workflow&language=Python&limit=8&auto_build=true
```

该接口只读 SQLite，不写入解释历史，不调用外部模型，也不触发推送。

### `GET /v1/rag/search-evaluation`

用固定查询样本或自定义查询样本批量调用 `/v1/rag/search-compare`，汇总 FTS5、向量和混合检索的平均命中数、命中率、推荐模式分布、项目覆盖数和零命中样本。该接口用于后续 RAG 质量评估、检索策略选择和 Agent 自动调参。

支持参数：

| 参数 | 说明 |
|---|---|
| `q` | 可选，可重复传入多个查询样本；不传时使用内置小样本 |
| `language` | 可选，按语言过滤 |
| `category` | 可选，按方向过滤 |
| `source` | 可选，按来源过滤 |
| `limit` | 每个样本的返回数量，默认 8，最大 30 |
| `model` | 可选，默认 `local-hash-v1` |
| `auto_build` | 可选，为 `true` 且索引为空时自动构建本地索引 |

返回内容包含：

1. `aggregate.modes`：三种检索模式的总命中、平均命中、引用数量和命中率。
2. `aggregate.preferred_mode_counts`：每个样本推荐模式的分布。
3. `aggregate.pairwise_average_overlap`：模式之间的平均项目重叠率。
4. `aggregate.zero_hit_queries`：三种模式都没有命中的样本。
5. `evaluations`：每个样本的完整 `/v1/rag/search-compare` 结果。

示例：

```text
/v1/rag/search-evaluation?language=Python&limit=8&auto_build=true
/v1/rag/search-evaluation?q=agent%20workflow&q=python%20automation&language=Python&auto_build=true
```

`GET /v1/rag/search-evaluation` 只读 SQLite，不写入解释历史，不调用外部模型，也不触发推送。

### `POST /v1/rag/search-evaluation`

执行一次 RAG 检索评估并把结果写入 SQLite `jobs` 和 `job_events`，任务类型为 `rag_search_evaluation`。该接口用于沉淀评估历史，方便后续查看 RAG 检索质量趋势。

请求体字段与 `GET /v1/rag/search-evaluation` 基本一致，额外要求：

| 参数 | 说明 |
|---|---|
| `queries` | 可选，查询样本列表；不传时使用内置小样本 |
| `confirm_execution` | 必填确认项；只有传入 `true` 才会写入 SQLite |
| `requested_by` | 可选，记录触发来源 |

如果没有传入 `confirm_execution=true`，接口会返回 `accepted=false`、`executed=false` 和阻塞原因，同时附带一次只读预览结果；不会写入任务记录。

示例：

```json
{
  "queries": ["agent workflow", "python automation"],
  "language": "Python",
  "limit": 8,
  "auto_build": true,
  "confirm_execution": true,
  "requested_by": "local-api"
}
```

写入后可通过以下接口查看：

```text
/v1/jobs?kind=rag_search_evaluation&status=succeeded
/v1/jobs/{job_id}/events
```

### `POST /v1/rag/search-evaluation-plan`

创建一个 `kind=rag_search_evaluation`、`status=planned` 的 RAG 检索质量评估任务，但不立即执行。请求字段与 `POST /v1/rag/search-evaluation` 一致，不需要额外触发推送或外部模型。

后续可用统一任务执行入口执行：

```text
GET /v1/job-execution-check?job_id=...
POST /v1/jobs/{job_id}/execute
```

命令行入口：

```powershell
py scripts\run_rag_search_evaluation.py --queries "agent workflow;python automation" --language Python --limit 8
```

该脚本会先创建 planned job，再调用本地 runner 执行。GitHub Actions 中的每周 workflow 会在生成 Pages 前调用该脚本。可用仓库变量调整行为：

| 变量 | 说明 |
|---|---|
| `RAG_EVALUATION_QUERIES` | 可选，评估查询样本，支持逗号、分号或换行分隔 |
| `RAG_EVALUATION_LANGUAGE` | 可选，语言过滤 |
| `RAG_EVALUATION_CATEGORY` | 可选，方向过滤 |
| `RAG_EVALUATION_SOURCE` | 可选，来源过滤 |
| `RAG_EVALUATION_LIMIT` | 每种检索模式最多返回多少条证据，默认 8 |
| `RAG_EVALUATION_AUTO_BUILD` | 是否缺少 embedding 时自动构建，默认 true |

### `GET /v1/rag/search-evaluation-trends`

读取已经写入 SQLite `jobs` 的 `rag_search_evaluation` 任务，汇总 RAG 检索质量趋势。该接口不重新执行检索，只读取历史评估结果，适合用于后续管理页、Agent 自检和定期质量报告。

支持参数：

| 参数 | 说明 |
|---|---|
| `limit` | 返回最近评估任务数量，默认 20，最大 100 |

返回内容包含：

1. `jobs`：最近评估任务摘要，包括样本数、平均命中、零命中数量、推荐模式分布和项目覆盖数。
2. `aggregate`：跨任务汇总的平均样本数、平均零命中数、模式平均命中、命中率和最新推荐模式。
3. `summary`：适合直接展示的中文趋势摘要。
4. `recommendations`：下一步改进建议，例如是否需要补充语料或继续使用 hybrid。

示例：

```text
/v1/rag/search-evaluation-trends?limit=20
```

### `GET /v1/rag/explain`

基于 `/v1/rag/retrieve` 或 `/v1/rag/vector-search` 的召回结果生成规则版 RAG 解释。该接口不调用外部模型，不请求 GitHub/Kimi/Telegram，只把已有证据块整理为“推荐解释、证据引用、风险提示、下一步动作”，用于后续接入模型总结、项目详情页解释和 LangChain 编排。

支持参数：

| 参数 | 说明 |
|---|---|
| `q` | 必填，用户问题或检索关键词 |
| `language` | 可选，按语言过滤 |
| `category` | 可选，按项目方向过滤 |
| `source` | 可选，按来源过滤，例如 `github_trending` |
| `limit` | 返回上下文数量，默认 8，最大 30 |
| `mode` | 可选，默认 `fts5`；传 `vector` 走本地向量检索，传 `hybrid` 同时使用文本和向量混合检索 |
| `model` | 可选，向量或混合模式下默认 `local-hash-v1` |
| `auto_build` | 可选，向量或混合模式下索引为空时自动构建本地索引 |

返回字段包含：

1. `contexts`：参与解释的 RAG 证据块。
2. `citations`：可引用的项目、日期和 chunk ID。
3. `prompt_context`：后续交给模型时可复用的上下文。
4. `explanation.answer`：规则版结论。
5. `explanation.why_recommended`：推荐依据。
6. `explanation.evidence`：裁剪后的证据摘要。
7. `explanation.risks`：证据缺口或人工复核提示。
8. `explanation.next_steps`：后续动作。

示例：

```text
/v1/rag/explain?q=agent%20workflow&language=Python&limit=8
/v1/rag/explain?q=agent%20workflow&mode=vector&auto_build=true
/v1/rag/explain?q=agent%20workflow&mode=hybrid&auto_build=true
```

这是当前 RAG 从“召回证据”升级到“解释输出”的第一层接口。`/v1/rag/ask` 会继续复用 `citations` 和 `prompt_context`，并要求模型按引用编号回答。

### `GET /v1/rag/ask`

面向前端和后续 Agent 编排的 RAG 问答入口。它复用 `/v1/rag/explain` 的检索、解释和 SQLite 解释历史写入能力，再把证据交给统一 LLM 客户端生成回答；未配置、超时、限流或响应异常时自动回退规则版。

真实模型只在 `KIMI_API_KEY` 和 `KIMI_MODEL` 同时配置时启用。没有证据时接口返回 `answer_mode=refusal`，不调用模型，也不编造项目结论。

支持参数与 `/v1/rag/explain` 一致：

| 参数 | 说明 |
|---|---|
| `q` | 必填，用户问题 |
| `language` | 可选，按语言过滤 |
| `category` | 可选，按项目方向过滤 |
| `source` | 可选，按来源过滤，例如 `github_trending` |
| `limit` | 返回上下文数量，默认 8，最大 30 |
| `mode` | 可选，默认 `fts5`；传 `vector` 走本地向量检索，传 `hybrid` 同时使用文本和向量混合检索 |
| `model` | 可选，向量或混合模式下默认 `local-hash-v1` |
| `auto_build` | 可选，向量或混合模式下索引为空时自动构建本地索引 |

返回字段包含：

1. `answer`：模型或规则版回答。
2. `answer_model`：回答生成策略，例如 `kimi:moonshot-v1-8k` 或 `rule:rag-ask-v1`。
3. `answer_mode`：`llm`、`fallback_rule` 或 `refusal`。
4. `fallback_reason`：未使用真实模型时的原因，正常模型回答为空字符串。
5. `citations`：回答引用的项目、日期和 chunk ID。
6. `evidence`：裁剪后的证据摘要。
7. `quality`：解释质量分与质量等级。
8. `prompt_context`：后续模型回答使用的上下文。
9. `next_actions`：建议的下一步核验或补库动作。
10. `source_explanation_id`：本次问答复用或写入的 RAG 解释编号。
11. `model_status`：模型是否配置、是否尝试、是否实际使用、模型名和超时配置。
12. `confidence`：旧兼容字段，值为 `low`、`medium` 或 `high`；当前仅表示证据覆盖量，不代表项目匹配置信度。
13. `evidence_coverage`：与兼容字段 `confidence` 等值，明确表示已召回、可引用证据的覆盖程度。
14. `match_confidence`：当前固定为 `unknown`；在没有标注数据校准前不输出 `medium` 或 `high`。
15. `answer_quality`：保留 `passed`、`issues`，并提供 `citation_validity`、`evidence_relevance`、`claim_support`、`claim_checks`、`source_latest_date`、`corpus_latest_date`、`embedding_latest_date`、`stale_days`、`as_of`、`reasons` 与 `data_freshness`。三层水位只读受控 `data/runs/<run_date>.json` 的版本化 `rag_freshness` attestation；默认超过 8 天为 `stale`，来源新而语料旧或语料新而 embedding 旧为 `lagging`，缺失或不一致为 `unknown`。项目事实与比较/排序结论必须在不可展示的 schema-v2 台账中逐项关联 citation、同项目证据块、原文摘录和结构化事实。每项 `claim_checks` 返回 `binding_status`、`polarity_status`、`scope_status`、`semantic_support_status`：只有引用绑定有效、极性一致、主体/组件/阶段/版本范围/条件/时间一致，且谓词/值/模态/数量一致并能由 quote 锚定时才为 `supported`。任一字段不匹配、未锚定或漏登记事实均失败闭合并走规则降级。

其中仓库主体由 citation/context metadata 绑定；`predicate/value/modality` 必须由后端从 quote 唯一、确定性地抽取后再与 evidence fact 比较，不能接受模型自报值。其余 scope 字段必须逐字出现在 quote。无法抽取、语义歧义或闭集外 predicate 均为 `insufficient`。
16. `recommendations`：当前归档内的确定性结构化推荐。每项包含 `full_name`、`rank`、`match_score`、`matched_requirements`、`unmet_requirements`、`unknown_requirements`、`reasons`、`citation_indexes`、`evidence_chunk_ids` 和 `eligibility`。`match_score` 只是本轮、同一检索模式内的相对排序分，不是概率或置信度。GET 继续验证显式 `language/category/source`；POST 还会验证路由器解析出的自然语言硬约束。

管理页 RAG 对话工作台使用同一接口。每轮问题独立检索；前端以用户/助手气泡展示回答，只把本轮问题、回答摘要、引用、证据、质量闸门结果和 `prompt_context` 保存到浏览器 localStorage，便于刷新后继续查看。

`agent.html?api=1` 的项目匹配对话同样使用该接口，不新增后端会话接口。前端默认降低 `limit` 到 3 来缩短响应等待，候选集合与顺序只读取 `recommendations`，详细引用、证据和 `prompt_context` 只进入折叠依据区。只有质量闸门通过、`data_freshness=fresh` 且第一项 `eligibility=eligible` 时才能显示“当前归档内最匹配候选”；其他情况必须显示“暂无可确认首选”。

### `GET /v1/rag/ask/stream`

React 项目匹配工作台使用的只读 SSE 接口，查询参数与 `/v1/rag/ask` 一致。事件依次为：`meta`（召回元数据、引用、证据摘要和 freshness 快照）、零到多条 `delta`（已通过当前引用、主张—证据与时效闸门的回答分段）、`final`（与 `/v1/rag/ask` 相同的完整最终响应）或 `error`（脱敏后的流协议错误）。后端完整缓冲 provider 输出；时效请求的水位非 `fresh` 或质量失败时不发送 provider delta，只返回规则降级 `final`。

新增的 `evidence_coverage`、`match_confidence`、`recommendations` 和质量维度只出现在完整 Ask 响应与 SSE `final` 中；不改变 `meta`、`delta`、`error` 的事件结构和顺序。

### `POST /v1/rag/ask` 与 `POST /v1/rag/ask/stream`

无状态追问入口。POST 与既有 GET 共用路径，但使用 JSON 请求体；GET 的查询参数和响应保持不变。请求体包含当前 `q`，以及可选的 `context.previous_user_goal`、`candidate_repository_ids`、`primary_repository_id`、`mode` 和 `resumable`。context 最多携带 10 个 `owner/repo`，不得提交历史 assistant 回答、citations、evidence 或 `prompt_context`。

POST 响应在 Ask 字段之外新增 `resolved_query`、`clarification_required`、`clarification_question` 和 `input_route`。`input_route` 记录 `new_search/resume/refine/clarify`、规则或 Kimi 路由器、候选范围、结构化 requirements、`requirement_schema_version="capability-v1"` 以及是否实际检索。无上下文的“继续、展开、嗯”等输入返回 `answer_mode=clarification`，contexts、citations、evidence 和 recommendations 均为空；流式响应只产生 `meta` 和 `final`，不产生草稿。

resume/展开只在上一轮 candidate IDs 内检索，“那个项目”只在 primary ID 内检索，refine 只重排上一轮候选，明确“重新找/换一批”才检索全归档。候选限制在 FTS5、vector 和 hybrid 内部查询阶段执行，不使用先取固定 Top-N 再过滤。

`capability-v1` 将项目能力拆成正交字段：`hosting_mode=self_hosted|cloud_hosted`、`offline_capable: boolean`、`network_required: boolean`、`external_api_required: boolean`、`api_key_required: boolean`。典型映射为“本地部署”→ `hosting_mode contains self_hosted`，“完全离线”→ `offline_capable=true`，“不要云 API”→ `external_api_required=false`，“不能联网”→ `network_required=false`，“不要 API Key”→ `api_key_required=false`。语言、分类、来源、许可证、成本和技术栈仍使用 `language/category/source/license/cost/tech_stack`；operator 为 `eq/not_eq/contains`，value 为 `string | boolean`。旧 `deployment` 仅作为后端兼容输入并在验证前规范化，新规则和 Kimi prompt 不再生成它。

规则解析按分句、连接词和谓词限定否定作用域；同一目标冲突、析取或“不要求/无所谓”等无法安全表示的条件返回 clarification。能力事实使用 repositories 可信元数据及非 `model_enrichment` 清洗 chunk，句子证据区分 `supports/contradicts/conditional/trial_only/external_dependency/unknown`。免费试用不满足“免费”，self-hosted UI 加 hosted inference 不满足“完全离线”；模型增强只能补充理由，不能改变硬约束结论。recommendation 新增 `requirement_evaluations[]`，逐项返回条件、matched/unmet/unknown 状态、原因和证据 chunk IDs。冲突为 rejected，无法验证为 unknown，全部通过为 eligible；没有 eligible 且全部冲突时返回 `answer_mode=no_match`，存在 unknown 时返回 clarification。clarification 的 `answer_quality.applicable=false`。

候选序号追问由确定性规则处理。`candidate_scope` 新增 `selected_candidates`；`input_route.selected_candidate_indexes[]` 使用零基索引，`selected_repository_ids[]` 是本轮实际检索范围的权威值。“第二个呢”只检索上一轮第二个候选，“比较第一个和第二个”只检索这两个候选。越界序号、无上下文序号或无法唯一解释且没有已确认 primary 的“上一个项目”返回 clarification，`retrieval_performed=false`。有 `primary_repository_id` 时，“上一个项目”按该已确认项目处理。普通 POST 与流式 `final` 返回相同的 requirements、recommendations 和序号范围；GET Ask 与 SSE 事件顺序不变。

路由优先使用确定性规则；只有规则无法可靠判断时才调用 Kimi 严格 JSON 路由。模型不可用、超时、非法 JSON 或越权字段都会保守转为澄清。contextual POST 不写入 `rag_explanations`、任务、反馈或服务端会话。

示例：

```text
/v1/rag/ask?q=agent%20workflow&language=Python&limit=8
/v1/rag/ask?q=agent%20workflow&mode=vector&auto_build=true
/v1/rag/ask?q=agent%20workflow&mode=hybrid&auto_build=true
```

### `GET /v1/rag/explanations`

查询已经写入 SQLite 的 RAG 解释历史。每次调用 `/v1/rag/explain` 都会把解释结果写入 `rag_explanations` 表，便于后续查看解释质量、比较 FTS 与向量模式、评估模型替换效果。

支持参数：

| 参数 | 说明 |
|---|---|
| `q` | 可选，按 query 或 answer 做模糊过滤 |
| `repo` | 可选，按解释覆盖的仓库过滤，格式为 `owner/name` |
| `limit` | 返回数量，默认 20，最大 100 |

返回字段包含 `query`、`repo`、`explanations`。每条解释包含 `explanation_id`、`query`、`mode`、`model`、`confidence`、`quality_score`、`quality_level`、`quality`、`answer`、`repositories`、`citations`、`explanation`、`retrieval` 和 `created_at`。

`quality` 是规则版质量评估，当前会统计证据块数量、引用数量、覆盖项目数量、解释依据数量、风险数量和是否包含 `prompt_context`。它用于判断解释是否足够可靠，不代表项目本身质量分。

示例：

```text
/v1/rag/explanations?limit=20
/v1/rag/explanations?q=agent
/v1/rag/explanations?repo=owner/agent
```

该接口只读取 SQLite 中的解释历史，不触发新的检索、不调用外部模型，也不包含密钥。

### `GET /v1/rag/quality-summary`

汇总 SQLite 中 RAG 解释历史的质量状态，用于判断当前 RAG 数据是否足够支撑模型总结、项目详情解释和后续 LangChain 编排。该接口只读 `rag_explanations`，不触发新检索。

支持参数：

| 参数 | 说明 |
|---|---|
| `limit` | 返回最近低质量样本和最近解释数量，默认 10，最大 50 |

返回字段包含：

1. `total_count`：解释历史总数。
2. `average_quality_score`：平均质量分。
3. `quality_levels`：高/中/低质量解释数量。
4. `confidence_levels`：解释置信度分布。
5. `modes`：FTS、向量等检索模式分布。
6. `recent_low_quality`：最近低质量解释样本。
7. `latest`：最近解释样本。
8. `recommendations`：下一步改进建议。

示例：

```text
/v1/rag/quality-summary?limit=10
```

### `GET /v1/rag/coverage`

检查历史项目的 RAG 覆盖缺口，用于判断哪些项目缺少证据块、embedding 或解释历史。该接口只读 SQLite，不触发外部请求，适合作为后续补库脚本、Agent 自动优化和管理页健康检查的数据源。

支持参数：

| 参数 | 说明 |
|---|---|
| `limit` | 返回缺口项目数量，默认 20，最大 100 |

返回字段包含：

1. `total_projects`：项目语料中覆盖的项目数量。
2. `healthy_project_count`：证据块、embedding 和解释历史均具备的项目数量。
3. `coverage_rate`：健康项目占比。
4. `gap_count`：存在 RAG 覆盖缺口的项目数量。
5. `gaps`：缺口项目列表，每项包含 `chunk_count`、`embedding_count`、`explanation_count`、`average_quality_score` 和 `gap_reasons`。
6. `recommendations`：下一步补库建议。

示例：

```text
/v1/rag/coverage?limit=20
```

可用 `scripts/backfill_rag_explanations.py` 按该接口的缺口结果批量生成规则版解释：

```text
python scripts/backfill_rag_explanations.py --dry-run
python scripts/backfill_rag_explanations.py --limit 10
```

### `GET /v1/rag/diagnostics`

返回数据库/RAG 的统一健康诊断。它组合 SQLite 表计数、RAG 质量摘要和覆盖缺口，不写入数据、不调用外部模型，适合本地管理页、GitHub Actions 或后续 Agent 自检使用。

支持参数：

| 参数 | 说明 |
|---|---|
| `limit` | 返回低质量样本和覆盖缺口数量，默认 10，最大 50 |

返回字段包含：

1. `status`：诊断状态，例如 `needs_corpus`、`needs_explanations`、`needs_maintenance`、`ready_for_text_rag` 或 `ready`。
2. `level`：健康等级，可能为 `low`、`medium` 或 `high`。
3. `signals`：布尔信号，包括是否已有语料、证据块、embedding、解释历史，以及是否可回答。
4. `table_counts`：核心 RAG 表记录数。
5. `quality`：解释历史数量、平均质量分和质量分布。
6. `coverage`：项目覆盖率、缺口数量和缺口样本。
7. `next_actions`：建议的下一步维护动作。
8. `corpus_versions`：期望和已观察到的语料/清洗器版本；`needs_corpus_rebuild=true` 时维护计划优先创建受控语料重建任务。

示例：

```text
/v1/rag/diagnostics?limit=10
```

### `POST /v1/rag/backfill-explanations`

按 `/v1/rag/coverage` 的缺口结果，为缺少解释历史的项目批量生成规则版 RAG 解释。该接口只使用本地 SQLite 和现有 RAG 检索逻辑，不调用外部模型、不请求 GitHub/Kimi/Telegram。

为避免误写数据库，接口默认 `dry_run=true`。如果请求中传入 `dry_run=false` 但没有同时传入 `confirm_execution=true`，后端会自动改回预览模式，并在 `safety_warnings` 中说明原因。

请求 JSON 支持字段：

| 字段 | 说明 |
|---|---|
| `limit` | 回填项目数量，默认 10，最大 100 |
| `rag_limit` | 每个项目解释时召回的证据块数量，默认 8，最大 30 |
| `mode` | 检索模式，支持 `fts5` 或 `vector` |
| `model` | 向量模式使用的 embedding 模型名，默认 `local-hash-v1` |
| `auto_build` | 向量模式缺少索引时是否自动构建本地索引 |
| `dry_run` | 是否只预览，不写入 SQLite；API 默认 `true` |
| `confirm_execution` | API 写库确认开关；只有 `dry_run=false` 且该字段为 `true` 才会创建解释历史 |
| `trigger_source` | 可选调用来源，默认 `rag_backfill_api` |
| `requested_by` | 可选调用者标识，默认 `api` |

返回字段包含：

1. `accepted`：请求是否被后端接受处理。
2. `dry_run`：本次实际执行模式。
3. `job_id`：本次回填任务编号，可用于查询任务详情和事件。
4. `safety_warnings`：安全降级提示。
5. `coverage_before`：回填前的覆盖概况。
6. `processed`：本次计划或创建的项目记录。

每次 API 调用都会写入一个 `kind=rag_backfill` 的任务记录。可以通过 `GET /v1/jobs?kind=rag_backfill` 查看最近回填任务，通过 `GET /v1/jobs/{job_id}/events` 查看 `rag_backfill_started` 和 `rag_backfill_completed` 等审计事件。脚本入口 `scripts/backfill_rag_explanations.py` 仍只执行补库逻辑，不额外写入任务审计。

示例：

```text
POST /v1/rag/backfill-explanations
{"limit": 3, "dry_run": true}

POST /v1/rag/backfill-explanations
{"limit": 3, "dry_run": false, "confirm_execution": true}
```

### `POST /v1/rag/backfill-plan`

创建一个 `kind=rag_backfill`、`status=planned` 的 RAG 回填计划任务，但不立即执行。请求字段与 `/v1/rag/backfill-explanations` 一致。接口会返回 `job_id`，后续可调用：

```text
GET /v1/job-execution-check?job_id=...
POST /v1/jobs/{job_id}/execute
```

执行时必须传入 `confirm_execution=true`。如果计划任务自身为 `dry_run=false`，创建计划时也必须传入 `confirm_execution=true`，否则后端会自动改为 `dry_run=true`，避免误写 SQLite。

### `POST /v1/rag/corpus-enrichment-plan`

创建 Kimi 结构化语料增强 planned job。请求支持 `limit`、`replace`、`dry_run`、`confirm_execution`、`requested_by`；默认 `dry_run=true`，真实调用模型并写入 `rag_corpus_enrichments` 必须同时传入 `dry_run=false` 和 `confirm_execution=true`。任务按清洗内容哈希、cleaner/prompt 版本和 Kimi 模型复用缓存；无密钥或单项目失败不会改变确定性语料。通过逐字段原文证据校验的结果进入 `model_enrichment` chunk，但不执行硬约束过滤或首选排名。

### `POST /v1/rag/maintenance-plan`

检查 RAG 诊断状态与覆盖缺口，并按需创建 RAG 维护 planned 任务。该接口会先调用 `/v1/rag/diagnostics`，再按优先级创建任务：

1. 如果 `project_corpus` 或 `rag_chunks` 还没有准备好，创建 `kind=rag_corpus_rebuild` 任务，并返回 `reason=rag_diagnostics_needs_corpus`。
2. 如果语料已准备但缺少 embedding，创建 `kind=rag_embedding_build` 任务，并返回 `reason=rag_diagnostics_needs_embeddings`。
3. 如果 embedding 已准备但解释覆盖仍有缺口，创建 `kind=rag_backfill` 任务，并返回 `reason=rag_coverage_gap_detected`。
4. 如果 `gap_count` 小于 `min_gap_count`，创建 `kind=rag_search_evaluation` 任务，并返回 `reason=rag_coverage_healthy_search_evaluation`，用于持续评估 FTS5、向量和混合检索质量。

返回结果会包含 `diagnostics`、`coverage`、`gap_count` 和 `min_gap_count`，方便 GitHub Actions、后台管理页或后续 Agent 判断下一步应先建语料、补向量、创建解释回填任务，还是创建检索评估任务。四类任务都会写入 `jobs` 表，可以继续通过 `GET /v1/job-execution-check?job_id=...` 和 `POST /v1/jobs/{job_id}/execute` 检查与执行。

任务详情页 `job.html?job=...&api=1` 会针对 RAG 维护任务展示结构化执行摘要：语料、证据块、embedding 的 before/after 计数、回填候选数、处理数和处理仓库列表，同时保留原始 JSON 结果用于调试。

### `GET /v1/rag/maintenance-report`

汇总最近 RAG 维护任务，用于判断数据库/RAG 维护链路是否持续生效。该接口只读取 SQLite，不创建任务、不执行任务、不调用外部服务。

支持参数：

| 字段 | 说明 |
|---|---|
| `limit` | 读取最近多少个 RAG 维护任务，默认 20，最大 100 |

返回内容包括：

1. `status_counts` 和 `kind_counts`：最近维护任务的状态分布和类型分布。
2. `by_kind`：按 `rag_corpus_rebuild`、`rag_embedding_build`、`rag_backfill`、`rag_search_evaluation` 分组的任务统计。
3. `latest_success` 和 `latest_failed`：最近成功和最近失败的维护任务摘要。
4. `recent_jobs`：最近维护任务列表，包含 before/after 计数、检索评估摘要和关键执行结果。
5. `diagnostics`：当前 RAG 诊断摘要，便于把历史任务与当前数据库状态对照。
6. `recommendations`：基于任务历史和诊断结果给出的下一步维护建议。

示例：

```text
/v1/rag/maintenance-report?limit=20
```

常用请求字段：

| 字段 | 说明 |
|---|---|
| `limit` | 本次计划回填项目数量，默认不超过缺口数和 10 |
| `coverage_limit` | 覆盖缺口检查数量，默认 100，最大 500 |
| `min_gap_count` | 至少发现多少缺口才创建任务，默认 1 |
| `dry_run` | 创建的任务是否只预览，默认 `true` |
| `confirm_execution` | 如果 `dry_run=false`，必须显式确认 |

本地脚本入口：

```text
python scripts/plan_rag_maintenance.py
python scripts/plan_rag_maintenance.py --limit 20 --coverage-limit 200
```

### `GET /v1/projects/{owner}/{repo}/rag`

返回单个项目的 RAG 聚合包，用于项目详情页、后续 Agent 工具调用和 LangChain/RAG 编排。该接口会读取项目详情、结构化项目研究档案、项目 Agent 任务及执行结果，执行本地 RAG 检索，并合并该项目已经入库的解释历史，不调用外部模型、不请求 GitHub/Kimi/Telegram。

支持参数：

| 参数 | 说明 |
|---|---|
| `limit` | 证据块数量，默认 8，最大 30 |
| `explanation_limit` | 解释历史数量，默认 5，最大 50 |
| `mode` | 检索模式，默认 `fts5`；传 `vector` 时使用本地向量检索 |
| `model` | 向量模型名称，默认 `local-hash-v1` |
| `auto_build` | 向量检索时是否自动构建本地 embedding 索引 |

返回字段包含：

1. `project`：项目摘要，包含语言、方向、历史入选次数、新增 Star 和最好 Trending 排名。
2. `project_profile`：项目研究档案，包含 `project_positioning`、`use_cases`、`strengths`、`risks`、`quality_summary`、`tracking_reason`、`rag_summary` 和 `agent_judgement`。
3. `contexts`、`citations`、`prompt_context`：可直接交给后续问答链的证据与引用；`contexts.metadata.project_profile` 会携带对应证据块的项目档案。
4. `explanations`：该项目已入库的 RAG 解释历史。
5. `explanation_summary`：该项目解释数量、平均质量分、质量等级分布和改进建议。

示例：

```text
/v1/projects/owner/agent/rag?limit=8&explanation_limit=5
/v1/projects/owner/agent/rag?mode=vector&auto_build=true
```

### `GET /v1/projects/{owner}/{repo}/similar`

基于单项目详情和 `project_corpus` 语料索引生成相似项目候选。该接口优先使用 SQLite FTS5 召回候选，再结合语言、方向、来源、关键词重合、Trending 排名和新增 Star 计算 `similarity_score`。

支持参数：

| 参数 | 说明 |
|---|---|
| `limit` | 返回相似候选数量，默认 10，最大 50 |

返回内容包括：

1. `source_project`：被查询项目的基础信息。
2. `similar_projects`：相似项目候选，包含 `similarity_score` 和 `similarity_reasons`。
3. `search_engine`：本次候选召回使用的检索引擎。
4. `selection_summary`：候选生成摘要。

示例：

```text
/v1/projects/owner/agent/similar?limit=10
```

该接口只读取本地公开归档数据，不调用外部模型或外部服务。它是后续 RAG、向量检索、项目对比和个性化推荐重排的前置候选层。

### `GET /v1/projects/compare`

对多个历史入选项目做结构化横向比较。该接口读取单项目详情聚合结果，返回统一对比矩阵和基础结论，用于后续对比页、RAG 解释和个性化推荐重排。

支持参数：

| 参数 | 说明 |
|---|---|
| `repos` | 必填，逗号分隔的仓库全名，例如 `owner/a,owner/b`，最多 8 个 |
| `profile` | 可选，当前个性化方向，例如 `agent_development`、`java`、`python` |
| `language` | 可选，当前优先语言，例如 `Python`、`Java` |
| `category` | 可选，当前优先方向，例如 `AI Agent`、`Backend` |
| `query` | 可选，当前关键词，例如 `agent`、`spring`、`rag` |

返回内容包括：

1. `projects`：每个项目的基础信息、历史热度、质量和风险摘要。
2. `matrix`：按指标展开的对比矩阵。
3. `best_by`：按累计新增 Star、最近新增 Star、质量分、Trending 排名等维度给出的领先项目。
4. `preference`：本次对比使用的个性化偏好上下文。
5. `recommendation`：规则版推荐结论，包含优先查看项目、推荐理由、注意事项、下一步动作和 `scoring_model`。没有偏好时为 `rule:v1`，传入 `profile`、`language`、`category` 或 `query` 后为 `rule:v2-preference`。
6. `missing`：未找到的项目。
7. `selection_summary`：本次对比摘要。

示例：

```text
/v1/projects/compare?repos=owner/agent,owner/agent-helper&profile=agent_development&language=Python
```

该接口只读公开归档数据，不调用外部服务，不写入任务或推送状态。

### `GET /api/profiles`

返回公开个性化方向，数据来源为 `docs/profiles.json`。

### `GET /api/weekly/latest`

返回最新 Markdown 周报正文、运行日期、周报页面路径和对应运行摘要。这个接口主要用于后续后台管理页、移动端入口或调试页面。

### `/v1` 订阅接口

订阅接口用于保存本地个性化偏好，后续精准推送和多用户订阅可以复用这个入口。当前订阅只保存筛选条件和通道名称，不保存 Token、Chat ID、Webhook 或请求头。

推送消息会使用这些订阅生成推荐入口：如果 SQLite 中存在启用订阅，Telegram、飞书和企业微信消息会追加最多 3 个 `recommendations.html` 个性化推荐链接。没有订阅时，消息仍只发送周报正文、项目筛选、运行状态和订阅配置页入口。

周报正文也会读取启用订阅生成“订阅推荐分区”。该分区只基于本期已经入选的项目做二次筛选，不改变采集、评分和入选逻辑。

当前支持：

1. `GET /v1/subscriptions`：查询订阅列表。
2. `POST /v1/subscriptions`：创建订阅。
3. `PATCH /v1/subscriptions/{subscription_id}`：更新订阅条件或启停状态。
4. `GET /v1/subscriptions/{subscription_id}/recommendations`：按订阅编号预览推荐结果。
5. `POST /v1/subscriptions/{subscription_id}/trigger`：把启用订阅转换成 planned 周报任务，默认 `dry_run=true`，不直接真实推送。

订阅字段包括：

| 字段 | 说明 |
|---|---|
| `name` | 订阅名称 |
| `status` | `enabled` 或 `disabled` |
| `profile` | 个性化方向 |
| `language` | 主要语言 |
| `category` | 项目方向 |
| `query` | 关键词 |
| `sort` | 推荐排序方式 |
| `limit` | 推荐数量 |
| `channels` | 推送通道名称，例如 `telegram`、`feishu`、`wecom` |

示例：

```text
POST /v1/subscriptions
```

```json
{
  "name": "Agent 开发订阅",
  "profile": "agent_development",
  "language": "Python",
  "channels": ["telegram"]
}
```

预览某个订阅的推荐结果：

```text
GET /v1/subscriptions/sub:xxxx/recommendations?limit=10
```

该接口会复用 `/v1/recommendations` 的筛选和排序逻辑，只把订阅保存的 profile、语言、方向、关键词和排序条件作为输入，不读取任何推送密钥。

按订阅生成计划任务：

```text
POST /v1/subscriptions/sub:xxxx/trigger
```

```json
{
  "dry_run": true,
  "requested_by": "subscriptions_page"
}
```

该接口只创建 planned 任务，不在 HTTP 请求里执行采集、生成或推送。订阅必须是 `enabled` 状态；如果传入 `dry_run=false`，仍需要 `confirm_delivery=true`，否则会自动降级为 `dry_run=true`。

### `/v1` 项目反馈接口

项目反馈接口用于沉淀用户对单个仓库的显式评价，作为后续个性化记忆、RAG 重排和推荐校准的数据基础。该接口只写入 SQLite 派生索引，不读取、不返回任何 Token、Chat ID、Webhook 或请求头。

当前入口包括：

1. `POST /v1/feedback`：写入一条项目反馈。
2. `GET /v1/feedback`：按仓库名或 profile 查询反馈记录。

`POST /v1/feedback` 请求体支持：

| 字段 | 说明 |
|---|---|
| `full_name` | 必填，仓库名，例如 `owner/repo` |
| `profile` | 可选，反馈所属偏好方向，例如 `agent_development` |
| `rating` | 可选，整数评分，范围为 `-2` 到 `2` |
| `labels` | 可选，标签列表，例如 `useful`、`too_complex` |
| `note` | 可选，用户备注，会截断保存，避免写入过长原文 |
| `source` | 可选，反馈来源，例如 `admin_page` 或 `telegram` |

示例：

```text
POST /v1/feedback
```

```json
{
  "full_name": "owner/agent",
  "profile": "agent_development",
  "rating": 2,
  "labels": ["useful", "agent"],
  "note": "适合作为 Agent 工作流参考",
  "source": "admin_page"
}
```

查询示例：

```text
GET /v1/feedback?full_name=owner/agent&limit=20
GET /v1/feedback?profile=agent_development&limit=20
```

响应会返回 `feedback` 列表和 `summary` 汇总，其中 `summary.ready_for_preference_memory=true` 表示已经具备后续个性化记忆建模的基础样本。

当前推荐接口已经会读取这些反馈、项目档案和 Agent 任务：`GET /v1/recommendations` 会把匹配 profile 的反馈聚合为项目级 `feedback_memory`，读取 `project_profile`，并生成 `recommendation_score`、`ranking_factors`、`preference_score`、解释字段和结构化 `next_actions`。`GET /v1/projects/{owner}/{repo}/rag` 会返回该项目的 `feedback_memory`、`project_profile`、`agent_tasks` 和 `next_actions`。

前端入口已经接入反馈闭环：`project.html?repo=...&api=1` 和 `recommendations.html?api=1` 会通过 `POST /v1/feedback` 写入“有用 / 不适合 / 继续跟踪”反馈；`admin.html?api=1` 会读取 `GET /v1/feedback?limit=200` 展示反馈记忆汇总，并读取 `/v1/recommendations?limit=20` 展示受反馈影响的推荐项目。所有页面写请求仍需提供管理口令；浏览器端只能使用当前页面的内存输入和 `X-Admin-Token` 请求头，不接受 URL 或持久化浏览器存储传递。

### `/v1/agent-tasks` 项目 Agent 任务

项目 Agent 任务用于承载“观察、判断、行动、复盘”工作流。任务类型包括 `observe`、`review_risk`、`deep_analysis`、`notify`、`ignore` 和 `continue_tracking`；状态包括 `planned`、`in_progress`、`completed`、`failed` 和 `cancelled`。

接口：

1. `GET /v1/agent-tasks`：按 `full_name`、`profile`、`status` 查询任务。
2. `GET /v1/projects/{owner}/{repo}/agent-tasks`：查询单项目任务。
3. `POST /v1/projects/{owner}/{repo}/agent-tasks`：创建项目任务，相同去重键返回已有任务。
4. `PATCH /v1/agent-tasks/{task_id}`：更新优先级、原因、执行结果或任务状态。

创建请求示例：

```json
{
  "task_type": "deep_analysis",
  "priority": 2,
  "reason": "验证项目核心能力和真实落地场景。",
  "profile": "agent_development",
  "source": "project_page",
  "payload": {"subscription_action": "notify"}
}
```

状态迁移受到限制：完成任务不能重新打开；失败任务可以重新计划；进入 `in_progress` 时记录 `started_at`，进入终态时记录 `finished_at`。任务更新后会重建项目语料，使原因和 `result_summary` 可被 RAG 召回。

### `/v1/dev-context` 开发上下文 RAG

开发上下文接口用于把本仓库的开发材料沉淀到 SQLite，作为后续代码审查、运行诊断、历史追踪和开发决策问答的记忆层。当前阶段提供本地索引、FTS5 检索和规则版问答，不接入外部模型。

当前入口包括：

1. `POST /v1/dev-context/index`：采集并索引开发上下文，写入 `dev_runs`、`dev_corpus`、`dev_chunks`、`dev_chunks_fts` 和 `dev_embeddings`。
2. `POST /v1/dev-context/index-plan`：创建 `kind=dev_context_index`、`status=planned` 的开发上下文索引任务，可由 `scripts/run_planned_job.py` 或 `/v1/jobs/{id}/execute` 执行。
3. `GET /v1/dev-context/search?q=...`：按关键词检索开发上下文片段，支持可选 `source_type=document|git_diff|test_output|security_check`。
4. `POST /v1/dev-context/ask`：基于已索引的开发上下文生成规则版回答，返回 `answer`、`citations`、`evidence`、`confidence`、`question_type`、`retrieval` 和 `next_actions`。
5. `GET /v1/dev-context/runs/{id}`：查看一次索引任务的来源和样例分块。

`POST /v1/dev-context/index` 和 `POST /v1/dev-context/index-plan` 是管理写接口，必须提供 `X-Admin-Token` 或 `Authorization: Bearer ...`。直接索引默认会采集 README、API 文档、数据契约、操作日志、`git diff`、单元测试输出和安全检查输出；接口会对明显密钥形态做脱敏，并给外部命令设置超时。测试、调试或 GitHub Actions 轻量刷新时可传入 `{"run_checks": false}` 跳过单元测试和安全检查。

示例：

```text
POST /v1/dev-context/index
POST /v1/dev-context/index-plan {"run_checks":false,"replace":false}
GET /v1/dev-context/search?q=最近测试失败&limit=8
GET /v1/dev-context/search?q=反馈入口&source_type=document
POST /v1/dev-context/ask {"question":"哪些 API 和数据契约相关？","limit":8}
GET /v1/dev-context/runs/dev-context:xxxx
```

`POST /v1/dev-context/ask` 支持测试诊断、最近变更、API/数据契约一致性、下一步开发和安全架构风险等问题类型。它只读取 SQLite 中已经脱敏的开发上下文分块，不调用 GitHub、Kimi、Telegram 或外部 embedding 服务。管理页 `admin.html?api=1` 已提供“索引开发上下文”、搜索、问答和最近索引任务入口。GitHub Actions 会在生成 Pages 前运行 `scripts/plan_dev_context_index.py --run-checks false --output .dev-context-job.json`，再交给 `scripts/run_planned_job.py --job-file .dev-context-job.json` 执行。

### `/v1` 任务接口

`/v1` 是后端服务化入口，当前已经支持：

1. `GET /v1/jobs`：查询任务列表。
2. `GET /v1/job-execution-check?job_id=...`：检查 planned 任务是否可执行。
3. `GET /v1/jobs/{job_id}/events`：查询任务审计事件。
4. `POST /v1/runs/trigger`：创建 planned 周报任务，不直接执行。
5. `POST /v1/jobs/{job_id}/execute`：显式传入 `confirm_execution=true` 后，把检查通过的 planned 任务交给 job runner 执行。
6. `POST /v1/jobs/{job_id}/retry`：为 failed 任务创建新的 planned 重试任务。

执行接口仍然遵守任务请求中的 `dry_run` 和 `confirm_delivery`。如果任务允许真实推送，执行前需要确认 Telegram、飞书或微信等推送配置已经正确。

## 四、前端读取方式

当前 `docs/explorer.html` 已支持渐进式读取后端 API：

1. 在 `localhost`、`127.0.0.1` 或 `::1` 打开时，默认优先读取 `/api/projects` 和 `/api/profiles`。
2. 在任意环境中给 URL 增加 `api=1` 时，会尝试读取后端 API。
3. 给 URL 增加 `api=0` 时，会强制读取静态 `projects.json` 和 `profiles.json`。
4. API 不可用时会自动回退到静态 JSON，GitHub Pages 线上页面不受影响。

示例：

```text
explorer.html?api=1&profile=agent_development
explorer.html?api=0&profile=python
```

`docs/project.html` 使用同样的读取策略：

1. 默认通过 `project.html?repo=owner/name` 读取静态 `projects.json` 并在浏览器中聚合详情。
2. 在本地后端或 URL 带 `api=1` 时，优先读取 `/api/projects/{owner}/{repo}`。
3. API 模式下会额外调用 `/v1/projects/{owner}/{repo}/rag`，一次展示该项目相关的 Agent 研究摘要、RAG 证据块、引用、`prompt_context`、解释历史和解释质量摘要。
4. API 不可用时自动回退到静态 `projects.json`。

示例：

```text
project.html?repo=owner/agent
project.html?repo=owner/agent&api=1
```

`docs/recommendations.html` 是个性化推荐页：

1. 本地后端或 URL 带 `api=1` 时优先读取 `/v1/recommendations`。
2. GitHub Pages 静态模式下读取 `projects.json` 并在浏览器中完成基础筛选和排序。
3. 页面预留 Agent 开发、Python、Java、后端、前端、AI 工具等快捷方向，后续可以接入用户订阅数据库。

示例：

```text
recommendations.html?api=1&profile=agent_development
recommendations.html?api=0&language=Java&q=spring
```

`docs/subscriptions.html` 是订阅配置页：

1. 本地后端或 URL 带 `api=1` 时读取 `/v1/subscriptions`。
2. 支持创建订阅，并通过 `PATCH /v1/subscriptions/{subscription_id}` 启用或停用订阅。
3. 支持调用 `/v1/subscriptions/{subscription_id}/recommendations` 在当前页面预览该订阅命中的推荐项目。
4. 静态 GitHub Pages 模式只展示说明，不写入任何配置。

示例：

```text
subscriptions.html?api=1
subscriptions.html?api=1&profile=agent_development
```

## 五、后续扩展

下一阶段可以在这个 API 层继续扩展：

1. 项目详情页增强：继续补充跨周对比、更多趋势解释和项目收藏入口。
2. 订阅接口：保存用户选择的语言、方向、profile 和推送渠道。
3. 后台任务接口：触发采集、重建 SQLite、重新生成 Pages。
4. 数据库演进：从当前派生 SQLite 过渡到持久化服务数据库，但保留 JSON 归档作为可读审计源。
5. 前端演进：先让现有静态页面读取 API，再逐步迁移到更完整的前端工程。

