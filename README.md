# GitHub Weekly Agent

GitHub Weekly Agent 是一个自动追踪 GitHub 每周热点项目的中文周报工具。它以 GitHub Trending 周榜为第一优先级，结合 Star 增量、主题匹配、个性化 profile 和基础风险提示，生成中文周报，并把 GitHub Pages 阅读链接推送到 Telegram。

## 当前状态

已实现可运行版本：

1. 每周自动运行，也支持在 GitHub Actions 中手动触发。
2. 优先采集 GitHub Trending 周榜，辅助使用 GitHub Search 补充垂直方向项目。
3. 记录 Star 历史，把新增 Star 作为重要热度依据。
4. 支持 `java`、`python`、`agent_development`、`learning`、`developer_tools` 等个性化方向。
5. 生成中文周报、运行摘要、入选项目数据和 GitHub Pages 归档页面。
6. Telegram 推送可点击的周报链接，而不是完整 Markdown 文件。
7. Kimi 不可用时自动生成规则版周报，保证流程不中断。
8. 提供本仓库密钥扫描和外部项目基础风险提示。

## 主流程

```text
GitHub Actions
-> main.py
-> collector
-> processor
-> reporter
-> archive
-> sender
```

## 快速配置

在仓库中进入：

```text
Settings -> Secrets and variables -> Actions
```

建议配置 Secrets：

| 名称 | 说明 |
|---|---|
| `GH_SEARCH_TOKEN` | 提高 GitHub API 访问额度 |
| `KIMI_API_KEY` | 启用 Kimi 周报生成 |
| `KIMI_BASE_URL` | Kimi API 地址，默认可不填 |
| `KIMI_MODEL` | Kimi 模型名称 |
| `TELEGRAM_BOT_TOKEN` | Telegram Bot Token |
| `TELEGRAM_CHAT_ID` | Telegram 接收方 |

建议配置 Variables：

| 名称 | 示例 |
|---|---|
| `INTEREST_PROFILE` | `java,python,agent_development,developer_tools` |
| `REPORT_BASE_URL` | 自定义 Pages 地址，可选 |

## 个性化方向

当前内置示例位于：

```text
config/profiles.example.json
```

常用组合：

```text
agent_development,python,developer_tools
java,agent_development
java,python,agent_development,developer_tools
```

项目会把匹配到的个性化方向写入推荐理由，后续前端筛选和数据库分析也会复用这部分信息。

## GitHub Pages

Telegram 推送的是 Pages 周报链接。仓库需要手动启用一次：

```text
Settings -> Pages
Source: Deploy from a branch
Branch: main
Folder: /docs
```

默认周报地址格式：

```text
https://<owner>.github.io/<repo>/weekly/YYYY-MM-DD.html
```

## 本地验证

```bash
python -m unittest
python scripts/security_check.py
python main.py
```

本地不会自动读取 `.env` 文件；如需调用真实 API，请在终端中手动设置环境变量。

## 主要文档

| 文档 | 说明 |
|---|---|
| `docs/setup.md` | Secrets、Variables、Pages 和个性化配置 |
| `docs/project-architecture.md` | 当前项目架构 |
| `docs/future-plan.md` | 前端、数据库、安全检查、多渠道推送等后续规划 |
| `docs/operation-log.md` | 开发过程和变更日志 |

## 安全原则

不要把 API Key、Token、Chat ID 写入代码、README、配置示例或周报。所有密钥只能通过环境变量或 GitHub Actions Secrets 读取。
