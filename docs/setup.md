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

## 测试

```bash
python -m unittest
```
