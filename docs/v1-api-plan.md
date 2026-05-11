# `/v1` 后端核心接口说明

本文记录后续核心功能建设中的 `/v1/*` 服务接口。`/api/*` 继续作为兼容的只读接口保留，`/v1/*` 用于后端服务化、任务调度和 Agent/RAG 能力扩展。

## 设计原则

1. 查询接口可以同步返回。
2. 采集、生成、推送等长任务必须走任务模型。
3. 当前阶段先提供任务预检和历史任务视图，不直接在 HTTP 请求中执行长任务。
4. 所有接口只读取公开归档或本地派生索引，不返回密钥。
5. 后续接入 worker 后，再把 `run_trigger_execute` 从 `false` 切换为 `true`。

## 当前接口

### `GET /v1/health`

返回服务状态、归档状态和能力开关。

关键字段：

| 字段 | 说明 |
|---|---|
| `api_version` | 当前接口版本 |
| `capabilities.projects_query` | 是否支持项目查询 |
| `capabilities.project_detail` | 是否支持项目详情 |
| `capabilities.runs_query` | 是否支持运行记录 |
| `capabilities.jobs_query` | 是否支持任务查询 |
| `capabilities.run_trigger_preview` | 是否支持触发预检 |
| `capabilities.run_trigger_execute` | 是否支持真实后台执行；当前为 `false` |

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

兼容 `/api/projects/{owner}/{repo}`，返回项目详情、历史入选记录、趋势、质量信号、风险提示和相似项目。

### `GET /v1/runs`

兼容 `/api/runs`，返回公开运行记录。

### `GET /v1/jobs`

把历史运行记录映射成任务视图。当前每次周报运行显示为一个 `weekly_report` 任务。

任务字段：

| 字段 | 说明 |
|---|---|
| `job_id` | 任务编号，例如 `run:2026-05-09` |
| `kind` | 任务类型，当前为 `weekly_report` |
| `status` | `succeeded` 或 `failed` |
| `run_date` | 对应运行日期 |
| `selected_count` | 入选项目数 |
| `collected_count` | 候选项目数 |
| `kimi_used` | 是否使用 Kimi |
| `telegram_sent` | 是否已推送 Telegram |
| `report_url` | 周报页面路径 |

### `GET /v1/jobs/{job_id}`

查询单个任务详情。对于历史周报任务，会同时返回对应 `data/runs/YYYY-MM-DD.json` 的运行摘要。

### `POST /v1/runs/trigger`

返回一次采集任务的计划预览，不立即执行真实后台任务。

请求示例：

```json
{
  "profile": "agent_development",
  "sources": ["github_trending"],
  "dry_run": true
}
```

当前返回：

| 字段 | 说明 |
|---|---|
| `job_id` | 预览任务编号，格式为 `preview:*` |
| `status` | 当前为 `planned` |
| `execution_supported` | 当前为 `false` |
| `request` | 标准化后的请求参数 |
| `next_steps` | 启用真实后台执行前需要完成的步骤 |

设计原因：GitHub 采集、LLM 生成、页面构建和推送都是长任务，不能直接塞进 HTTP 请求生命周期。下一步应封装主流程 use case，再接入持久化 job 表和 worker。

### `GET /v1/reports/latest`

兼容 `/api/weekly/latest`，返回最新 Markdown 周报、运行日期、页面路径和运行摘要。

## 下一步

1. 把 `main.py` 主流程封装成可复用 use case。
2. 增加持久化 job 表。
3. 支持真实后台执行和状态轮询。
4. 为 Agent/RAG 增加结构化 evidence 字段。
5. 再考虑 SSE 流式任务状态。
