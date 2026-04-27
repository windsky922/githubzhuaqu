# AGENTS.md

## Project

GitHub Weekly Agent collects recent GitHub repositories, filters and ranks them, generates a Chinese weekly report, sends it to Telegram, and archives the output.

## Development Rules

1. Do not hard-code API keys, tokens, chat IDs, or secrets.
2. Read secrets only from environment variables or GitHub Actions secrets.
3. Keep modules small and focused.
4. Do not delete existing reports or historical data unless explicitly requested.
5. External HTTP requests must use timeouts and handle errors clearly.
6. If Kimi API is unavailable or not configured, generate a fallback Markdown report.
7. If Telegram is unavailable or not configured, still archive the report and run summary.
8. Keep prompts in `prompts/`, not embedded in business code.
9. Keep generated reports under `reports/` and run summaries under `data/runs/`.
10. Avoid adding new directories or abstractions until they are needed.

## Main Workflow

```text
GitHub Actions
-> main.py
-> collector
-> processor
-> reporter
-> archive
-> sender
```

## Validation

Use:

```bash
python -m unittest
python main.py
```

`python main.py` may fall back to a basic report if model or Telegram secrets are missing.
