# GitHub Weekly Agent 架构说明

本文档记录第一阶段最小可用版本的实际实现架构。

## 运行流程

```text
main.py
-> src.settings.load_settings
-> src.collector.collect_repositories
-> src.processor.process_repositories
-> src.reporter.generate_report
-> src.archive.archive_run
-> src.sender.send_report
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

暂缓实现：

1. README 深度抓取。
2. SQLite 历史数据库。
3. 网页仪表盘。
4. 正式发布技能包。
5. Telegram 交互式机器人。
