# AGENTS.md

## 项目说明

GitHub Weekly Agent 用于采集近期 GitHub 仓库，对仓库进行筛选和排序，生成中文周报，推送到 Telegram，并归档运行结果。

## 开发规则

1. 不要在代码中硬编码 API Key、Token、Chat ID 或任何密钥。
2. 密钥只能从环境变量或 GitHub Actions Secrets 中读取。
3. 模块应保持小而聚焦，每个模块只负责一类任务。
4. 除非用户明确要求，不要删除已有周报或历史数据。
5. 所有外部 HTTP 请求必须设置超时，并清晰处理错误。
6. 如果 Kimi API 不可用或未配置，必须生成降级版 Markdown 周报。
7. 如果 Telegram 不可用或未配置，仍然要归档周报和运行摘要。
8. 提示词必须保存在 `prompts/` 中，不要硬编码在业务代码里。
9. 生成的周报保存在 `reports/`，运行摘要保存在 `data/runs/`。
10. 不要提前增加不必要的目录、抽象层或复杂框架。

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

## 验证方式

使用：

```bash
python -m unittest
python main.py
```

如果模型或 Telegram 密钥缺失，`python main.py` 会降级生成基础周报或跳过 Telegram 推送。
