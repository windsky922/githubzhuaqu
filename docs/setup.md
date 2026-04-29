# 项目配置

## GitHub Actions 密钥

请在 GitHub 仓库的 `Settings -> Secrets and variables -> Actions` 中配置以下密钥。

| 密钥名称 | 是否必须 | 用途 |
|---|---:|---|
| `GH_SEARCH_TOKEN` | 推荐 | 提高 GitHub Search API 速率限制 |
| `KIMI_API_KEY` | 可选 | 启用模型生成周报 |
| `KIMI_BASE_URL` | 可选 | 默认值为 `https://api.moonshot.cn/v1` |
| `KIMI_MODEL` | 可选 | 配合 `KIMI_API_KEY` 使用，指定 Kimi 模型 |
| `TELEGRAM_BOT_TOKEN` | 可选 | 启用 Telegram 推送 |
| `TELEGRAM_CHAT_ID` | 可选 | Telegram 接收方 Chat ID |

如果未配置 Kimi，程序会生成降级版周报。

如果未配置 Telegram，程序仍会归档周报和运行摘要。

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
