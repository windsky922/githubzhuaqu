# GitHub Weekly Agent 架构说明

本文档记录第一阶段最小可用版本的实际实现架构。

## 运行流程

```text
main.py
-> src.settings.load_settings
-> src.collector.collect_repositories
-> src.state.load_sent_repository_names
-> src.processor.process_repositories
-> src.collector.enrich_repositories_with_readmes
-> src.reporter.generate_report
-> src.archive.archive_run
-> src.sender.send_report
-> src.state.write_sent_repositories
-> src.archive.write_run_summary
```

## 最小可用版本范围

第一阶段已实现：

1. 通过 GitHub Search API 采集仓库。
2. 对仓库进行过滤、去重、评分和排序。
3. 使用 Kimi 聊天补全接口生成周报。
4. 当 Kimi 不可用时生成降级版 Markdown 周报。
5. Telegram 长消息自动分段发送。
6. Markdown 周报归档到 `reports/`。
7. 运行摘要归档到 `data/runs/`。
8. GitHub Actions 支持每周定时运行和手动触发。
9. Telegram 推送成功后记录已推送仓库，后续运行过滤重复项目。
10. 对最终入选仓库抓取 README 摘要，作为 Kimi 和降级报告的补充上下文。

暂缓实现：

1. SQLite 历史数据库。
2. 网页仪表盘。
3. 正式发布技能包。
4. Telegram 交互式机器人。

## 状态文件

`data/state/sent_repos.json` 用于记录已经成功推送到 Telegram 的仓库。

写入时机：

1. 本次运行成功生成周报。
2. Telegram 推送成功。
3. 本次筛选列表不为空。

如果 Telegram 未配置或发送失败，程序仍然归档周报和运行摘要，但不会把仓库写入已推送状态，避免后续遗漏应推送项目。

## README 摘要

程序只对最终入选周报的仓库抓取 README，不对全部搜索结果抓取，避免 GitHub API 请求量过大。

处理规则：

1. 使用 GitHub README API 读取仓库默认 README。
2. 每个请求设置超时。
3. 单个仓库 README 获取失败时跳过，不影响整体周报。
4. 只保留前 2000 个字符的清洗后摘要，避免提示词过长。
