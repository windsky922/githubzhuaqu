# Setup

## GitHub Secrets

Configure these in GitHub repository settings under `Settings -> Secrets and variables -> Actions`.

| Secret | Required | Purpose |
|---|---:|---|
| `GH_SEARCH_TOKEN` | Recommended | Higher GitHub Search API rate limits |
| `KIMI_API_KEY` | Optional | Enables model-generated report |
| `KIMI_BASE_URL` | Optional | Defaults to `https://api.moonshot.cn/v1` |
| `KIMI_MODEL` | Optional | Required with `KIMI_API_KEY` for Kimi generation |
| `TELEGRAM_BOT_TOKEN` | Optional | Enables Telegram sending |
| `TELEGRAM_CHAT_ID` | Optional | Telegram recipient chat ID |

If Kimi is not configured, the program writes a fallback report.

If Telegram is not configured, the program still archives reports and run summaries.

## Local Run

```bash
python main.py
```

Optional local environment variables can be copied from `.env.example` into your shell environment. The program does not read `.env` automatically to avoid adding dependencies.

## Tests

```bash
python -m unittest
```
