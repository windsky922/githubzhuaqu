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

### `GET /api/runs`

返回公开运行记录，数据来源为 `docs/runs.json`。

### `GET /api/profiles`

返回公开个性化方向，数据来源为 `docs/profiles.json`。

### `GET /api/weekly/latest`

返回最新 Markdown 周报正文、运行日期、周报页面路径和对应运行摘要。这个接口主要用于后续后台管理页、移动端入口或调试页面。

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

## 五、后续扩展

下一阶段可以在这个 API 层继续扩展：

1. 项目详情页增强：继续补充跨周对比、更多趋势解释和项目收藏入口。
2. 订阅接口：保存用户选择的语言、方向、profile 和推送渠道。
3. 后台任务接口：触发采集、重建 SQLite、重新生成 Pages。
4. 数据库演进：从当前派生 SQLite 过渡到持久化服务数据库，但保留 JSON 归档作为可读审计源。
5. 前端演进：先让现有静态页面读取 API，再逐步迁移到更完整的前端工程。

