# `/v1` 后端核心接口说明

本文记录后续核心功能建设中的 `/v1/*` 服务接口。`/api/*` 继续作为兼容的只读接口保留，`/v1/*` 用于后端服务化、任务调度和 Agent/RAG 能力扩展。

## 设计原则

1. 查询接口可以同步返回。
2. 采集、生成、推送等长任务必须走任务模型。
3. 当前阶段先提供任务预检和历史任务视图，不直接在 HTTP 请求中执行长任务。
4. 查询接口只读取公开归档或本地派生索引，触发接口只写入任务状态，不返回密钥。
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
| `capabilities.local_job_runner` | 是否支持本地任务执行器 |
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

### `POST /v1/runs/trigger`

创建一次采集任务的计划预览并写入 `jobs` 表，不立即执行真实后台任务。

请求示例：

```json
{
  "profile": "agent_development",
  "sources": ["github_trending"],
  "dry_run": true,
  "days_back": 7
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

设计原因：GitHub 采集、LLM 生成、页面构建和推送都是长任务，不能直接塞进 HTTP 请求生命周期。当前先持久化任务计划，再由本地任务执行器把任务从 `planned` 推进到 `running`、`succeeded` 或 `failed`。

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
3. SQLite 派生索引已增加 `jobs` 表，历史运行会同步为任务记录，触发预览会写入 `planned` 任务。
4. `scripts/run_planned_job.py` 已可执行 planned 任务，并写回 running/succeeded/failed 状态。
5. weekly workflow 已接入任务创建和任务执行脚本，手动运行时可指定 profile 和回看天数。

下一步：

1. 增加任务状态页面或 API 管理入口。
2. 支持真实后台状态轮询。
3. 为 Agent/RAG 增加结构化 evidence 字段。
4. 再考虑 SSE 流式任务状态。
