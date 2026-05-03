# 数据契约说明

本文档记录当前公开 JSON 和 SQLite 派生索引的稳定字段。后续前端、微信、飞书、RSS 或外部脚本应优先依赖这些字段。

## 一、设计原则

1. JSON 归档仍是事实来源。
2. `docs/projects.json` 和 `docs/runs.json` 是公开展示与订阅入口。
3. SQLite 是可重建派生索引，不提交数据库文件。
4. 公共数据不能包含密钥、用户隐私、未脱敏配置或原始错误堆栈。
5. 修改字段时必须同步更新测试、文档和下游消费逻辑。

## 二、`docs/projects.json`

顶层字段：

```text
schema_version
count
projects
```

每个项目字段：

```text
run_date
full_name
html_url
description
category
language
stargazers_count
forks_count
star_growth
score
sources
trending_rank
selection_reasons
security_flags
report_url
```

用途：

1. 前端历史项目筛选。
2. 多渠道推送摘要生成。
3. 外部脚本按语言、方向、来源、风险提示做二次分析。

## 三、`docs/runs.json`

顶层字段：

```text
schema_version
count
runs
```

每次运行字段：

```text
run_date
status
report_url
selected_count
collected_count
previously_sent_selected_count
readme_fetched_count
star_history_updated_count
kimi_used
fallback_used
telegram_sent
telegram_report_url
collector_error_count
top_languages
top_categories
total_star_growth
trending_project_count
summary_points
```

用途：

1. 首页运行状态展示。
2. 趋势概览和历史运行对比。
3. 监控周报是否降级、是否推送、采集是否异常。

## 四、SQLite 表

当前 SQLite 表：

```text
runs
repositories
selections
trend_summaries
sent_repositories
star_history
migration_meta
```

说明：

1. `runs` 保存运行摘要索引。
2. `repositories` 保存仓库基础信息。
3. `selections` 保存每次运行入选项目及排序信息。
4. `trend_summaries` 保存趋势摘要。
5. `sent_repositories` 保存已推送仓库状态。
6. `star_history` 保存 Star 历史。
7. `migration_meta` 保存迁移元数据。

## 五、契约测试

契约测试位于：

```text
tests/test_data_contracts.py
```

该测试会检查：

1. `projects.json` 的字段集合。
2. `runs.json` 的字段集合。
3. SQLite 关键表字段集合。

如果未来确实需要新增、删除或重命名字段，应先确认下游影响，再同步更新契约测试和本文档。
