---
name: github-weekly-agent
description: Maintain and extend this repository's GitHub Weekly Agent. Use when working on the weekly GitHub hot-project collector, scoring, Kimi report generation, Telegram delivery, GitHub Actions workflow, report archives, Chinese docs, or related tests.
---

# GitHub Weekly Agent

## 核心约束

1. 所有文档面向用户的内容使用中文。
2. 不在代码、文档或测试中硬编码 API Key、Token、Chat ID 或其他密钥。
3. 密钥只从环境变量或 GitHub Actions Secrets 读取。
4. 保持模块小而清晰，不提前加入复杂框架、数据库或无用目录。
5. 所有外部 HTTP 请求必须设置超时，并保留清晰错误信息。
6. Kimi 不可用时允许降级，但必须记录原因；遇到内容过滤时先移除 README 摘要重试。
7. Telegram 不可用时仍要归档周报和运行摘要。
8. 不删除历史周报、运行摘要或状态文件，除非用户明确要求。

## 主流程

维护主流程时遵循当前架构：

```text
main.py
-> src.settings.load_settings
-> src.collector.collect_repositories
-> src.state.load_sent_repository_names
-> src.processor.process_repositories
-> src.collector.enrich_repositories_with_readmes
-> src.trends.build_trend_summary
-> src.reporter.generate_report
-> src.archive.write_*
-> src.sender.send_report
-> src.state.write_sent_repositories
```

## 目录职责

1. `reports/`：Markdown 周报。
2. `data/raw/`：GitHub API 原始候选仓库。
3. `data/selected/`：最终入选周报的仓库。
4. `data/runs/`：运行摘要。
5. `data/state/`：可变状态，包括已推送仓库和 Star 历史。
6. `data/trends/`：趋势摘要。
7. `docs/`：中文项目文档和 GitHub Pages 内容。
8. `prompts/`：模型提示词，业务代码中不要硬编码长提示词。

## 常见任务

### 修改采集或排序

1. 优先改 `src/collector.py` 和 `src/processor.py`。
2. 保持“本周热点”定义为最近一周 `pushed_at` 或 `updated_at` 活跃，不按创建时间筛选。
3. 新增 Star 是主要热度信号，调整权重时同步更新 `docs/architecture.md`。
4. 补充或更新 `tests/test_collector.py`、`tests/test_processor.py`。

### 修改周报生成

1. 优先改 `src/reporter.py` 和 `prompts/weekly_report.md`。
2. Kimi 失败时保留 fallback，但必须在运行摘要中写入 `report_error`。
3. 链接显示为完整 URL Markdown 链接。
4. 技术语言名保留英文，例如 `Python`、`TypeScript`。
5. 补充或更新 `tests/test_reporter.py`。

### 修改归档或 Pages

1. 归档写入逻辑在 `src/archive.py`。
2. Pages 生成逻辑在 `scripts/build_pages.py`。
3. GitHub Actions 自动提交范围需要同步更新。
4. 补充或更新 `tests/test_archive.py`、`tests/test_build_pages.py`。

### 修改 GitHub Actions

1. 工作流文件是 `.github/workflows/weekly.yml`。
2. 保留 `workflow_dispatch` 和每周定时触发。
3. 保留 `permissions: contents: write`，用于自动提交归档。
4. 保留 `[skip ci]`，避免自动提交再次触发不必要流程。
5. 更新 action 版本时记录到 `docs/operation-log.md`。

## 验证

本地修改后至少运行：

```bash
py -m unittest
py -m compileall main.py src tests scripts
```

真实链路验证优先使用 GitHub 网页手动触发：

```text
Actions -> GitHub 每周热点项目智能体 -> Run workflow -> main
```

检查 `data/runs/YYYY-MM-DD.json`：

1. `status` 应为 `success`。
2. `collector_errors` 应为空或可解释。
3. `kimi_used` 应优先为 `true`。
4. `telegram_sent` 应符合当前 Secrets 配置。
5. `raw_repositories_path`、`selected_repositories_path`、`trend_summary_path` 应存在。
