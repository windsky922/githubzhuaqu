# 项目配置

## GitHub Actions 密钥

请在 GitHub 仓库的 `Settings -> Secrets and variables -> Actions` 中配置以下密钥。

| 密钥名称 | 是否必须 | 用途 |
|---|---:|---|
| `GH_SEARCH_TOKEN` | 推荐 | 提高 GitHub Search API 速率限制 |
| `KIMI_API_KEY` | 可选 | 启用模型生成周报 |
| `KIMI_BASE_URL` | 可选 | 默认值为 `https://api.moonshot.cn/v1` |
| `KIMI_MODEL` | 可选 | 配合 `KIMI_API_KEY` 使用，指定 Kimi 模型 |
| `KIMI_TIMEOUT_SECONDS` | 可选 | Kimi 请求超时时间，默认 `120` 秒 |
| `TELEGRAM_BOT_TOKEN` | 可选 | 启用 Telegram 推送 |
| `TELEGRAM_CHAT_ID` | 可选 | Telegram 接收方 Chat ID |
| `REPORT_BASE_URL` | 可选 | 周报公开访问目录，留空时 GitHub Actions 会根据仓库名推导 GitHub Pages 地址 |

如果未配置 Kimi，程序会生成降级版周报。

如果未配置 Telegram，程序仍会归档周报和运行摘要。

Telegram 当前只推送周报链接，不推送完整 Markdown 正文。这个链接指向 GitHub Pages 上的周报页面，也就是 GitHub Actions 运行后由 Kimi 生成并归档的那份周报。默认链接格式为：

```text
https://<owner>.github.io/<repo>/weekly/YYYY-MM-DD.html
```

如果你的 Pages 域名或路径不同，可以配置 `REPORT_BASE_URL`，例如：

```text
REPORT_BASE_URL=https://example.com/weekly
```

每次运行后，实际推送链接会写入：

```text
data/runs/YYYY-MM-DD.json
```

字段名为：

```text
telegram_report_url
```

## 本地运行

```bash
python main.py
```

本地运行时，可以参考 `.env.example` 手动设置环境变量。为了避免增加依赖，程序不会自动读取 `.env` 文件。

## 兴趣配置

默认配置文件是：

```text
config/interests.example.json
```

如果需要自定义关注方向，可以复制一份为：

```text
config/interests.json
```

程序会优先读取 `config/interests.json`，不存在时才回退到 `config/interests.example.json`。

常用字段：

1. `preferred_topics`：优先关注的话题关键词。
2. `preferred_languages`：优先关注的主要语言。
3. `exclude_keywords`：需要排除的仓库关键词。
4. `max_projects`：每期周报最多入选项目数。
5. `min_stars`：候选仓库最低 Star 数。
6. `enable_github_trending`：是否启用 GitHub Trending 周榜采集，默认启用。
7. `trending_languages`：额外采集的 Trending 语言榜，例如 `["Python", "TypeScript"]`。默认只采集全站周榜，避免请求过多。
8. `trending_max_repositories`：每个 Trending 榜最多补齐多少个仓库详情。
9. `search_topics`：Search API 用于补充垂直方向的 topic 查询。
10. `search_languages`：Search API 用于补充垂直方向的语言查询。
11. `score_weights`：综合评分权重。当前默认把 `trending` 作为第一指标，其余信号作为辅助。
12. `min_trending_top10_projects`：Trending 周榜前 10 中至少保留多少个项目进入周报，默认 `7`。

如果希望 GitHub Actions 也使用你的自定义兴趣配置，需要把 `config/interests.json` 提交到仓库。该文件不应包含 API Key、Token 或 Chat ID。

## 测试

```bash
python -m unittest
```

## 检查 Secrets 配置

仓库中提供了 `Secrets 配置检查` 工作流，用于验证 GitHub、Kimi 和 Telegram 的密钥配置。

路径：

```text
Actions -> Secrets 配置检查 -> Run workflow
```

验证内容：

1. `GH_SEARCH_TOKEN` 是否可以访问 GitHub API。
2. `KIMI_API_KEY`、`KIMI_BASE_URL`、`KIMI_MODEL` 是否可以访问 Kimi API。
3. `TELEGRAM_BOT_TOKEN` 和 `TELEGRAM_CHAT_ID` 是否可以发送 Telegram 测试消息。

## 状态文件说明

`data/state/sent_repos.json` 由程序自动生成，用于记录已经成功推送到 Telegram 的仓库。

`data/state/star_history.json` 由程序自动生成，用于记录仓库上次采集时的 Star 数，后续运行会据此计算新增 Star 并优化排序。

不需要手动创建该文件。首次成功推送后，GitHub Actions 会把它和周报归档一起提交回仓库。

如果需要重新推送历史项目，可以在确认风险后手动编辑该文件，删除对应仓库记录。不要删除 `reports/` 和 `data/runs/` 中的历史归档。

## GitHub Pages 配置

项目会自动生成 GitHub Pages 可用的周报归档文件：

```text
docs/index.md
docs/weekly/YYYY-MM-DD.md
```

如需启用网页访问，请在 GitHub 仓库中进入：

```text
Settings -> Pages
```

然后设置：

```text
Source: Deploy from a branch
Branch: main
Folder: /docs
```

启用后，后续每次 GitHub Actions 生成周报，都会同步刷新归档页面。

## 个性化 profile 配置

如果希望按 Java、Python、Agent 开发等方向精准推荐，可以使用个性化 profile。

示例 profile 文件：

```text
config/profiles.example.json
```

如需自定义，可以新建：

```text
config/profiles.json
```

本地或 GitHub Actions 中通过 `INTEREST_PROFILE` 选择方向，多个方向用英文逗号分隔：

```text
INTEREST_PROFILE=java,agent_development
```

当前示例 profile 包括：

1. `java`：Java 后端与工程实践。
2. `python`：Python 工具与应用开发。
3. `agent_development`：Agent 框架、工具调用和自动化工作流。
4. `learning`：更适合学习和跟练的项目。
5. `developer_tools`：开发者工具和 CLI 自动化。

在 GitHub Actions 中，建议把 `INTEREST_PROFILE` 配置为仓库变量：

```text
Settings -> Secrets and variables -> Actions -> Variables
```

profile 配置只保存兴趣方向、语言、主题和权重，不要写入 API Key、Token、Chat ID 或其他密钥。

启用 profile 后，入选项目会在推荐理由中记录匹配到的方向，例如：

```text
匹配当前个性化方向：Java 后端与工程实践、Agent 开发。
```

这部分信息会进入 `data/selected/YYYY-MM-DD.json`，并可被 Kimi 周报、规则版周报和后续前端筛选复用。
