# 历史归档查询说明

本项目的事实来源仍然是 `data/` 下的 JSON 归档。SQLite 是可重建的派生索引，用于提升历史查询、前端筛选和后续个性化推荐的效率。

## 使用场景

1. 按语言查看历史热点项目，例如 Python、Java、TypeScript。
2. 按方向查看历史项目，例如 AI Agent、Developer Tools。
3. 按个性化 profile 查看项目，例如 `agent_development`、`java`、`python`。
4. 按来源查看项目，例如 `github_trending` 或 `github_search`。
5. 按风险提示查看项目，例如只查看存在风险提示的仓库。
6. 用关键词搜索项目名、简介、方向和推荐理由。
7. 按质量等级、最低质量分和 Trending TopN 回看更可靠的历史项目。

## 常用命令

查询前先重建 SQLite 派生索引：

```bash
python scripts/query_archive.py --refresh --language Python --source github_trending --limit 10
```

按个性化方向查询：

```bash
python scripts/query_archive.py --profile agent_development --limit 10
```

输出 JSON，方便后续脚本或前端复用：

```bash
python scripts/query_archive.py --profile agent_development --query workflow --format json
```

只查看存在风险提示的项目：

```bash
python scripts/query_archive.py --risk has --limit 20
```

查看 Trending Top10 中质量分不低于 80 的项目：

```bash
python scripts/query_archive.py --trending-top 10 --min-quality 80 --sort quality --limit 20
```

按新增 Star 或综合评分排序：

```bash
python scripts/query_archive.py --sort star-growth --limit 20
python scripts/query_archive.py --sort score --limit 20
```

## 设计边界

1. 查询脚本只读取 JSON 归档、SQLite 派生索引和公开 profile 配置。
2. 查询脚本不读取 API Key、Token、Chat ID 或 Webhook。
3. SQLite 文件不提交到 GitHub，需要时可以从 JSON 重新生成。
4. 当前查询能力是后续前端后台、数据库页面和个性化推荐的基础，不替代主流程。
5. 质量分、质量等级和 Trending TopN 查询来自已归档的入选项目，不会重新请求 GitHub，也不会改变历史周报。

## 后续扩展

后续可以在不改变现有数据契约的前提下继续扩展：

1. 在 GitHub Pages 中加入查询预设和趋势图。
2. 将 CLI 查询逻辑迁移为轻量 API 或静态构建阶段的数据切片。
3. 加入收藏、忽略、继续追踪等反馈入口。
4. 将用户反馈转化为 profile 权重和相似项目推荐依据。
