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

根路径 `http://127.0.0.1:8000/` 会跳转到管理首页。`/v1/*` 路径是 JSON API，例如 `/v1/jobs?limit=50` 返回机器可读任务数据，不是 HTML 页面。

如果本地没有 `data/github_weekly.sqlite`，查询项目接口会从 `data/` 下的 JSON 归档自动重建 SQLite 派生索引。

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

对应的 v1 入口为：

```text
/v1/recommendations?profile=agent_development&limit=20
```

### `GET /api/runs`

返回公开运行记录，数据来源为 `docs/runs.json`。

### `GET /v1/database/summary`

返回 SQLite 派生索引的数据库概览，用于本地管理台、数据健康检查和后续 RAG 索引准备。该接口会返回：

1. `table_counts`：`runs`、`repositories`、`selections`、`jobs`、`job_events`、`subscriptions` 等表的记录数。
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
3. API 不可用时自动回退到静态 `projects.json`。

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

