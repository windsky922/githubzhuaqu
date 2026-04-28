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
11. 维护 Star 历史状态，并将 Star 增量纳入排序评分。
12. 生成 GitHub Pages 周报归档页面。

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

## Star 增量评分

`data/state/star_history.json` 用于记录仓库上次采集时的 Star 数。

评分时会计算：

```text
star_growth = 当前 Star - 历史 Star
```

如果仓库没有历史记录，则 `star_growth` 为 0。

当前综合评分权重：

1. Star 增量：40%
2. 总 Star：25%
3. 兴趣主题匹配：20%
4. 活跃时间新鲜度：10%
5. Fork：5%

这种设计把新增 Star 作为本周热度的核心信号，同时保留总 Star、主题匹配和近期活跃度，避免只按历史体量筛出长期热门老项目。

周报候选项目以最近一周 `pushed_at` 或 `updated_at` 活跃为准，不要求仓库必须在最近一周创建。`created` 查询只作为补充，用于捕捉新出现且增长快的项目。

## GitHub Pages 归档页面

`scripts/build_pages.py` 会读取 `reports/` 和 `data/runs/`，生成：

1. `docs/index.md`：周报归档首页。
2. `docs/weekly/YYYY-MM-DD.md`：适合 GitHub Pages 浏览的周报副本。

每次 GitHub Actions 生成周报后，都会自动刷新归档页面并提交到仓库。
