# 后端 API 说明

本文档记录当前后端 API 的最小可用设计。它暂时只提供只读接口，不改变采集、评分、周报生成和推送流程。

## 一、定位

当前项目已经具备 JSON 归档、SQLite 派生索引、GitHub Pages 前端和多通道推送。后端 API 的第一阶段目标是把这些能力整理成稳定入口，方便后续接入更完整的前端、数据库管理、用户订阅和个性化推荐。

设计边界：

1. JSON 归档仍然是事实来源。
2. SQLite 仍然是可重建的派生索引，不提交到 GitHub。
3. API 只读取公开归档数据，不读取、不返回任何密钥。
4. API 不负责采集 GitHub，也不负责调用 Kimi 或 Telegram。
5. 后续可以在不破坏现有 Actions 工作流的前提下，把前端逐步切换到 API。

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

### `GET /api/runs`

返回公开运行记录，数据来源为 `docs/runs.json`。

### `GET /api/profiles`

返回公开个性化方向，数据来源为 `docs/profiles.json`。

### `GET /api/weekly/latest`

返回最新 Markdown 周报正文、运行日期、周报页面路径和对应运行摘要。这个接口主要用于后续后台管理页、移动端入口或调试页面。

## 四、后续扩展

下一阶段可以在这个 API 层继续扩展：

1. 项目详情接口：按 `full_name` 查看历史入选次数、Star 增长曲线、相似项目和质量变化。
2. 订阅接口：保存用户选择的语言、方向、profile 和推送渠道。
3. 后台任务接口：触发采集、重建 SQLite、重新生成 Pages。
4. 数据库演进：从当前派生 SQLite 过渡到持久化服务数据库，但保留 JSON 归档作为可读审计源。
5. 前端演进：先让现有静态页面读取 API，再逐步迁移到更完整的前端工程。

