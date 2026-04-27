# GitHub Weekly Agent

用于自动整理每周 GitHub 热点项目，并将中文周报推送到手机端的 Agent 项目规划仓库。

当前阶段只做架构审查和项目文档沉淀，暂不进入代码开发。

## 当前文档

| 文件 | 说明 |
|---|---|
| `docs/architecture-review.md` | 对原始架构文档的审查结论、问题和优化建议 |
| `docs/project-architecture.md` | 优化后的完整项目架构、MVP 范围、目录规划和开发路线 |
| `docs/operation-log.md` | 本次 Codex 操作过程和日志记录 |

## 项目目标

构建一个每周自动运行的信息整理 Agent：

```text
GitHub 热点项目采集
→ 数据清洗、去重、排序
→ 生成中文周报
→ Telegram 手机推送
→ 周报与运行结果归档
```

## 推荐技术路线

| 模块 | 技术 |
|---|---|
| 定时触发 | GitHub Actions |
| 主程序 | Python |
| 数据来源 | GitHub Search API，后续可扩展 GitHub Trending |
| 周报生成 | Kimi API，失败时降级为规则模板 |
| 手机推送 | Telegram Bot API |
| 归档 | Markdown 报告、JSON 原始数据、运行日志摘要 |

## 第一阶段范围

第一阶段只实现稳定可用的 MVP：

1. 每周一自动运行，支持手动触发。
2. 搜索最近 7 天 GitHub 热点项目。
3. 清洗、去重、排序并生成结构化项目列表。
4. 使用 Kimi API 生成中文周报。
5. 将周报推送到 Telegram。
6. 将周报保存到 `reports/YYYY-MM-DD.md`。
7. GitHub Actions 自动提交新增周报。

暂不开发 README 深度抓取、历史去重数据库、网页展示和复杂推荐模型。

## 后续开发前置事项

开发前需要准备以下 GitHub Secrets：

| Secret | 用途 |
|---|---|
| `GH_SEARCH_TOKEN` | GitHub Search API 访问令牌，可先使用低权限 token |
| `KIMI_API_KEY` | Kimi API Key |
| `KIMI_BASE_URL` | Kimi API 地址 |
| `KIMI_MODEL` | Kimi 模型名称 |
| `TELEGRAM_BOT_TOKEN` | Telegram Bot Token |
| `TELEGRAM_CHAT_ID` | Telegram 接收方 Chat ID |

`GITHUB_TOKEN` 由 GitHub Actions 自动提供，用于把新增周报提交回仓库。

