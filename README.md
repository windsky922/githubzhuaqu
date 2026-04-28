# GitHub Weekly Agent

用于自动整理每周 GitHub 热点项目，并将中文周报推送到手机端的 Agent 项目规划仓库。

当前已完成第一阶段最小可用版本，并开始第二阶段数据质量增强：项目可以搜索 GitHub 热点仓库，读取入选项目 README 摘要，结合历史 Star 增量评分，生成中文 Markdown 周报，按配置推送到 Telegram，归档运行摘要，并记录已成功推送过的仓库。

## 当前文档

| 文件 | 说明 |
|---|---|
| `docs/architecture-review.md` | 对原始架构文档的审查结论、问题和优化建议 |
| `docs/project-architecture.md` | 优化后的完整项目架构、MVP 范围、目录规划和开发路线 |
| `docs/pi-mono-rearchitecture-review.md` | 基于 `badlogic/pi-mono` 学习后的新版架构审查和采纳建议 |
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

第一阶段最小可用版本范围：

1. 每周一自动运行，支持手动触发。
2. 搜索最近 7 天 GitHub 热点项目。
3. 清洗、去重、排序并生成结构化项目列表。
4. 使用 Kimi API 生成中文周报。
5. 将周报推送到 Telegram。
6. 将周报保存到 `reports/YYYY-MM-DD.md`。
7. GitHub Actions 自动提交新增周报。
8. Telegram 推送成功后，将本次仓库记录到 `data/state/sent_repos.json`，后续运行会跳过已推送仓库。
9. 对最终入选项目抓取 README 摘要，提升周报分析质量。
10. 在 `data/state/star_history.json` 中记录仓库 Star 历史，用于后续评分时计算新增 Star。

暂不开发 SQLite 历史数据库、网页展示和复杂推荐模型。

## 本地运行

```bash
py -m unittest discover -v
py main.py
```

在 GitHub Actions 中会使用：

```bash
python -m unittest
python main.py
```

未配置 Kimi 时会生成基础版周报；未配置 Telegram 时会跳过推送但保留归档。

## 后续开发前置事项

开发前需要准备以下 GitHub Actions 密钥：

| 密钥名称 | 用途 |
|---|---|
| `GH_SEARCH_TOKEN` | GitHub Search API 访问令牌，可先使用低权限 token |
| `KIMI_API_KEY` | Kimi API Key |
| `KIMI_BASE_URL` | Kimi API 地址 |
| `KIMI_MODEL` | Kimi 模型名称 |
| `TELEGRAM_BOT_TOKEN` | Telegram Bot Token |
| `TELEGRAM_CHAT_ID` | Telegram 接收方 Chat ID |

`GITHUB_TOKEN` 由 GitHub Actions 自动提供，用于把新增周报提交回仓库。

## 状态文件

`data/state/sent_repos.json` 由程序自动生成，用于记录已经成功推送到 Telegram 的仓库。

`data/state/star_history.json` 由程序自动生成，用于记录仓库上次被采集时的 Star 数，后续运行会据此计算新增 Star。

如果需要重新推送历史项目，可以在确认风险后手动编辑该文件，删除对应仓库记录。不要删除 `reports/` 和 `data/runs/` 中的历史归档。
