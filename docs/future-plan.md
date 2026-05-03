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
5. Telegram 使用可点击超链接消息，微信、飞书后续复用同一份短消息结构。

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

## 新增重点方向：前端、数据库与个性化分析

### 1. 当前成熟度判断

前端、数据库和个性化分析都应该提上日程，但不建议立即同时进入完整开发。

当前更适合的策略是：

1. 先继续稳定采集、评分、报告质量检查和 Telegram 链接推送。
2. 再做轻量级展示增强和个性化配置增强。
3. 等历史数据达到一定规模后，再正式引入数据库和更完整的前端。

原因：

1. 当前历史周报数量还少，GitHub Pages Markdown 已能满足基础阅读。
2. 数据结构仍在快速演进，过早建数据库会增加迁移成本。
3. 前端需要稳定的数据接口，否则容易反复返工。
4. 个性化分析已经具备配置基础，可以比数据库和复杂前端更早推进。

### 2. 前端建设计划

前端目标不是做营销页，而是做一个轻量的热点项目浏览与筛选界面。

建议阶段：

1. 短期：继续使用 GitHub Pages，由 `scripts/build_pages.py` 生成更易读的 Markdown/HTML 页面。
2. 中期：增加历史项目筛选能力，例如按日期、语言、方向、Trending 排名、风险提示筛选。
3. 后期：如果交互需求明显增加，再引入轻量前端应用。

成熟触发条件：

1. 历史周报超过 4 周。
2. `data/selected/` 中累计项目足够多，纯 Markdown 表格浏览效率下降。
3. 用户需要按方向、语言、风险、热度来源进行交互式筛选。

预留位置：

```text
docs/assets/
scripts/build_pages.py
```

如果后续引入前端工程，再考虑：

```text
frontend/
```

### 3. 数据库建设计划

数据库目标是支持长期趋势查询，而不是替代当前 JSON 归档。

短期继续使用：

```text
data/runs/
data/raw/
data/selected/
data/trends/
data/state/
```

中期可以增加 SQLite 作为索引层，保留 JSON 作为可读归档。

成熟触发条件：

1. 历史运行超过 3 个月。
2. 需要跨周查询项目热度变化。
3. 需要统计某项目多次入选、Star 增长曲线、方向变化。
4. JSON 文件开始影响维护或查询效率。

预留位置：

```text
src/storage.py
tests/test_storage.py
data/github_weekly.sqlite
```

数据库第一版建议只做派生索引，不做唯一事实来源。即使数据库损坏，也能通过 JSON 重新构建。

### 4. 个性化分析计划

个性化分析应优先于完整数据库和复杂前端推进。

当前已有基础：

1. `config/interests.json` 可以承载关注主题、语言、排除关键词和评分权重。
2. `score_weights` 已经支持调整 Trending、Star 增量、主题、活跃度和社区基础信号。
3. 周报已经记录 `selection_reasons`，便于解释为什么推荐某个项目。

下一步建议：

1. 增加用户画像字段，例如关注方向、学习目标、避雷方向、偏好语言。
2. 在报告中增加“与你关注方向的匹配原因”。
3. 支持多个 profile，例如 `default`、`ai_agent`、`developer_tools`、`learning`。
4. 先用配置文件实现，不急于做数据库或登录系统。

预留位置：

```text
config/profiles.example.json
src/personalization.py
tests/test_personalization.py
```

### 5. 分支策略

当前小步修复和规划更新继续在 `main` 上提交即可。

当进入下列任务时，建议创建独立分支：

```text
codex/frontend-pages
codex/storage-sqlite
codex/personalization-profiles
```

是否需要多个分支取决于任务是否能独立推进：

1. 前端和数据库可以分支隔离，因为它们改动范围不同。
2. 个性化分析会影响评分、报告和配置，建议单独分支。
3. 如果三者同时开发，应避免在同一分支混合提交，降低回滚和排查成本。
4. 当前还没有必要立刻创建这些分支；等开始实际实现对应大功能时再创建。

### 6. 最终成品展望

最终成品应是一套自动化热点追踪系统：

1. 每周自动抓取 GitHub Trending 和辅助数据源。
2. 根据个人关注方向进行筛选和排序。
3. 生成中文结构化周报。
4. 将可点击的 GitHub Pages 链接推送到 Telegram，并预留微信、飞书、邮件入口。
5. 在前端页面中浏览历史项目、趋势、风险提示和个性化匹配原因。
6. 使用 SQLite 或其他轻量存储支持长期趋势分析。
7. 对外部项目和自身仓库都保留安全检查与脱敏保护。

### 7. 继续推进前需要解决的问题

1. 继续观察 GitHub Trending 解析在 GitHub Actions 中的稳定性。
2. 减少 Kimi 可修复质量问题导致的降级周报。
3. 稳定 `data/selected/`、`data/trends/` 和 `data/runs/` 的字段结构。
4. 明确个性化 profile 的最小字段集合。
5. 等历史数据积累后，再决定数据库表结构和前端筛选方式。

## 优先级建议

近期优先级：

1. 修复 GitHub Pages 与 Telegram 推送状态的一致性。
2. 观察 GitHub Trending 页面解析在 GitHub Actions 中的稳定性。
3. 设计重复入选项目的新颖度策略，不硬性排除持续热门项目。
4. 个性化 profile 配置设计。
5. 导出公共 JSON，为后续前端和多渠道入口打底。

中期优先级：

1. SQLite 双写和历史 JSON 迁移校验。
2. GitHub Pages 历史项目筛选。
3. 报告结构校验和自动重试。
4. GitHub GraphQL 细粒度热度补充。
5. 多推送渠道抽象。

长期优先级：

1. 趋势可视化。
2. 团队订阅和交互式机器人。
3. 需要在线多用户能力后，再评估 Postgres 或独立服务。

## 暂不建议做的事

1. 暂不重构为大型框架。
2. 暂不引入复杂前端工程。
3. 暂不把所有模块提前拆成目录。
4. 暂不直接替换 JSON；数据库只按 SQLite 双写和可重建索引的方式逐步引入。
5. 暂不追求完全消除降级报告；外部 API 不可用时仍需要降级兜底，但应持续减少可避免的降级原因。
