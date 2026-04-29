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
13. 生成数据驱动的趋势摘要，并归档到 `data/trends/`。
14. 在运行摘要中记录部分采集失败，便于排查 GitHub API 限流或网络异常。

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

## 兴趣配置

程序优先读取用户配置：

```text
config/interests.json
```

如果该文件不存在，再回退到示例配置：

```text
config/interests.example.json
```

这样可以保留示例文件，同时允许用户维护自己的关注方向、语言偏好、排除关键词和项目数量阈值。

## 数据归档

归档目录职责：

1. `data/raw/YYYY-MM-DD.json`：保存 GitHub API 本次采集到的原始候选仓库。
2. `data/selected/YYYY-MM-DD.json`：保存经过去重、过滤和排序后的最终入选仓库。
3. `data/runs/YYYY-MM-DD.json`：保存运行摘要，包括采集数量、入选数量、降级原因、推送结果和部分采集错误。
4. `data/trends/YYYY-MM-DD.json`：保存趋势摘要。

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

周报候选项目以最近一周 `pushed_at` 或 `updated_at` 活跃为准，不要求仓库必须在最近一周创建。当前采集查询不再使用 `created` 条件，避免候选池偏向“新建项目”。

## GitHub Pages 归档页面

`scripts/build_pages.py` 会读取 `reports/` 和 `data/runs/`，生成：

1. `docs/index.md`：周报归档首页。
2. `docs/weekly/YYYY-MM-DD.md`：适合 GitHub Pages 浏览的周报副本。

每次 GitHub Actions 生成周报后，都会自动刷新归档页面并提交到仓库。

## 趋势摘要

`src/trends.py` 会根据本期入选仓库生成趋势摘要，输出到：

```text
data/trends/YYYY-MM-DD.json
```

趋势摘要包含：

1. 入选项目总数。
2. 累计新增 Star。
3. 主要语言分布。
4. 项目方向分布。
5. 新增 Star 最高的项目列表。
6. 可直接写入周报的一组趋势要点。

Kimi 生成周报时会收到该趋势摘要；降级版周报也会直接展示趋势要点。

## 后续扩展边界

未来扩展应遵循“稳定核心 + 可插拔增强”的方式，不提前重构当前主流程。

稳定核心继续保持：

```text
collector -> processor -> reporter -> archive -> sender
```

当某类能力明显变复杂时，再按职责拆分：

1. `sources`：多数据源采集。
2. `quality`：仓库质量评估和异常过滤。
3. `report_checks`：周报结构和内容校验。
4. `channels`：多推送渠道。
5. `storage`：长期历史数据存储。

详细演进计划见：

```text
docs/future-plan.md
```
