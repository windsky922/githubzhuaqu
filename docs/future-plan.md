# 未来更新规划

本文档记录 GitHub Weekly Agent 后续可扩展方向。原则是：先保持当前每周自动运行链路稳定，再逐步增强数据质量、报告质量、展示体验和可维护性。

## 总体原则

1. 主流程保持简单，不把实验性功能直接塞进 `main.py`。
2. 新能力优先作为独立模块加入，再接入主流程。
3. 每次新增外部服务都必须支持超时、错误记录和降级策略。
4. 所有新增配置优先使用环境变量或 `config/` 配置文件。
5. 所有面向用户的文档继续使用中文。
6. 不删除历史报告、运行摘要和状态数据。

## 推荐架构演进

后续架构应保持“稳定核心 + 可插拔增强”的方向：

```text
稳定核心：
collector -> processor -> reporter -> archive -> sender

可插拔增强：
sources      数据源扩展
quality      数据质量评估
insights     趋势与洞察
security     安全风险检查
channels     推送渠道
presentation 展示页面
```

当前不需要马上创建这些目录。只有当某一类能力开始包含多个实现或明显变复杂时，再拆出对应模块。

## 第四阶段：数据质量增强

目标：让“本周最火爆”判断更可靠。

建议任务：

1. 增加仓库质量评分：README 完整度、最近提交频率、Issue 活跃度、Release 活跃度。
2. 增加异常过滤：刷 Star 嫌疑、空壳项目、广告项目、镜像仓库。
3. 增加语言和主题的可配置权重。
4. 记录每个入选项目的入选原因，写入 `data/selected/YYYY-MM-DD.json`。
5. 为评分结果增加解释字段，便于在周报中说明为什么推荐该项目。

预留位置：

```text
src/quality.py
tests/test_quality.py
```

触发条件：当评分逻辑超过 `src/processor.py` 的清晰边界时再拆分。

## 第五阶段：多数据源采集

目标：避免只依赖 GitHub Search API。

已经完成：

1. 运行摘要新增 `collector_stats`，记录每条 GitHub Search 查询的成功、失败、返回数量和错误原因。
2. 保留 `collector_errors`，兼容旧的失败摘要字段。
3. 接入 GitHub Trending 周榜作为第一优先级候选来源。
4. `Repository` 增加 `sources`、`trending_rank`、`trending_period`、`source_priority`，为后续多来源融合保留字段。
5. 评分权重改为以 Trending 排名为第一指标，Star 增量、垂直兴趣、活跃度和社区基础信号作为辅助。

候选数据源：

1. GitHub Trending 页面：当前第一优先级来源。
2. GitHub Search API：继续作为辅助来源和垂直方向补充。
3. GitHub GraphQL API：用于获取更细的 Star、Issue、Release、Commit 数据。
4. 用户自定义仓库列表：用于长期关注项目。

预留位置：

```text
src/sources/
tests/test_sources.py
```

设计要求：

1. 每个数据源返回统一的 `Repository` 结构。
2. 数据源失败不应阻断其他数据源。
3. 运行摘要记录每个数据源的成功、失败和返回数量。基础版本已完成。
4. 个性化配置先保留在 `config/interests.json` 中，重点字段包括 `search_topics`、`search_languages`、`trending_languages` 和 `score_weights`。
5. 暂不立即拆出 `src/sources/` 目录；当 Trending、Search、GraphQL、自定义仓库列表都需要独立维护时，再拆分来源模块。

## 第六阶段：报告质量增强

目标：减少模型自由发挥，提高报告稳定性和可读性。

已经完成：

1. 新增 `src/report_checks.py`，对 Kimi 输出做基础质量检查。
2. 检查项目名称、完整 Markdown 链接和不合适技术语言翻译。
3. Kimi 输出不合格时自动回退到规则周报，并记录 `report_error`。

建议任务：

1. 将周报拆成固定结构：趋势摘要、项目总览、重点项目、行动建议。
2. 检查是否包含非入选项目。
3. Kimi 生成后针对结构问题自动重试一次，而不只是直接回退。
4. 为每个项目生成“适合人群”字段。
5. 支持同一份数据生成短版 Telegram 周报和长版 Markdown 周报。

预留位置：

```text
src/report_checks.py
tests/test_report_checks.py
```

## 第七阶段：安全风险检查

目标：降低推荐高风险项目、误提交密钥和执行不可信内容的风险。

已经完成的基础保护：

1. 新增 `scripts/security_check.py`，扫描源码、配置、workflow、文档和提示词中的疑似硬编码密钥。
2. GitHub Actions 在测试前运行安全检查。
3. 检查范围排除 `data/` 和 `reports/`，避免把第三方仓库 README 或生成报告当成项目自身密钥。
4. 新增 `src/security.py`，为入选仓库生成元数据级风险提示。
5. `data/selected/YYYY-MM-DD.json` 会保存每个入选仓库的 `security_flags`。
6. 降级版周报会展示风险提示，Kimi 也会收到该结构化字段。

后续建议任务：

1. 为入选仓库增加安全信号：是否归档、是否 fork、是否有许可证、是否有近期维护、Issue 风险提示。
2. 检查 README 和简介中是否包含明显诈骗、钓鱼、盗版、恶意软件下载等关键词。
3. 对新增 Star 异常增长增加提示，不直接判定恶意，但在周报中标记“需人工复核”。
4. 扩展 `security_flags` 的规则来源，例如许可证、维护状态、依赖文件和 Release 信息。
5. 在 Kimi 周报提示词中更明确要求展示风险提示。

预留位置：

```text
src/security.py
tests/test_security.py
scripts/security_check.py
tests/test_security_check.py
```

设计要求：

1. 安全检查不能执行第三方仓库代码。
2. 安全结论必须保守表达，避免把未验证项目写成“安全”。
3. 安全检查失败时应阻止自动提交疑似密钥。
4. 外部项目风险只作为评分和周报提示，不应让整个工作流随意失败。

## 已完成：入选原因记录

目标：让每个入选项目的推荐逻辑更可解释。

已经完成：

1. `Repository` 增加 `selection_reasons` 字段。
2. `src/processor.py` 根据新增 Star、累计 Star、主题匹配和近期活跃生成入选原因。
3. `data/selected/YYYY-MM-DD.json` 保存入选原因。
4. 降级版周报展示入选原因。
5. Kimi 周报提示词要求优先使用 `selection_reasons` 解释项目为什么值得关注。

## 第八阶段：推送渠道扩展

目标：不只依赖 Telegram。

候选渠道：

1. Telegram：继续作为默认渠道。
2. 邮件：适合长周报。
3. 企业微信或飞书：适合团队使用。
4. GitHub Issue：把每周报告作为仓库 Issue 归档。

预留位置：

```text
src/channels/
tests/test_channels.py
```

设计要求：

1. 每个渠道独立失败，不能影响归档。
2. 运行摘要记录每个渠道的发送状态。
3. 默认仍保持 Telegram 单渠道，避免过早复杂化。
4. 推送内容优先使用统一的短消息和周报链接，完整 Markdown 继续归档在 `reports/` 和 GitHub Pages 中。

## 第九阶段：展示页面增强

目标：让 GitHub Pages 不只是 Markdown 归档，而是更容易浏览和筛选。

已经完成：

1. 首页显示最新运行摘要。
2. 首页显示最新趋势要点。
3. 首页保留项目文档入口。
4. 历史周报列表显示主语言、主方向和累计新增 Star。
5. 生成 `docs/projects.md` 历史项目索引。

建议任务：

1. 支持更细的按语言、方向、日期筛选历史项目。
2. 增加项目卡片，但保持页面轻量。
3. 增加 `data/trends/` 的可视化摘要。
4. 保留 Markdown 周报作为长期稳定归档。

预留位置：

```text
docs/assets/
scripts/build_pages.py
```

触发条件：当历史周报超过 4 周后再优先处理。

## 第十阶段：长期状态与数据库

目标：当 JSON 状态文件开始难以维护时，再引入轻量数据库。

候选方案：

1. 继续使用 JSON：适合当前规模。
2. SQLite：适合长期保存仓库历史、每周评分、趋势变化。

暂不立即引入 SQLite。触发条件：

1. 历史运行超过 3 个月。
2. 需要跨周趋势查询。
3. JSON 文件冲突或体积明显影响维护。

预留位置：

```text
src/storage.py
tests/test_storage.py
```

## 优先级建议

近期优先级：

1. 观察 GitHub Trending 页面解析在 GitHub Actions 中的稳定性。
2. 根据真实周报结果微调 `score_weights`。
3. GitHub Pages 历史项目筛选。

中期优先级：

1. 报告结构校验和自动重试。
2. GitHub GraphQL 细粒度热度补充。
3. 多推送渠道抽象。

长期优先级：

1. SQLite 历史库。
2. 趋势可视化。
3. 团队订阅和交互式机器人。

## 暂不建议做的事

1. 暂不重构为大型框架。
2. 暂不引入复杂前端工程。
3. 暂不把所有模块提前拆成目录。
4. 暂不添加数据库，除非 JSON 状态已经成为实际问题。
5. 暂不追求完全消除降级报告；外部 API 不可用时仍需要降级兜底，但应持续减少可避免的降级原因。
