# 项目路线图

本文档根据当前代码状态和外部研究报告重新整理。项目后续目标不是继续做更复杂的抓取脚本，而是演进为面向个人和小团队的开源项目情报系统。

## 一、当前定位

GitHub Weekly Agent 当前已经完成从“脚本验证”到“自动化周报闭环”的第一阶段：

1. 以 GitHub Trending 周榜作为第一优先级热点信号。
2. 使用 GitHub Search 补充 Java、Python、Agent 开发等垂直方向。
3. 记录 Star 历史，并将新增 Star 纳入排序。
4. 支持个性化 profile 和推荐理由。
5. 生成中文周报、趋势摘要、历史项目索引和 GitHub Pages 页面。
6. Telegram 推送可点击的周报链接。
7. 对本仓库做疑似密钥扫描，对外部项目做基础风险提示。

后续北极星是：把“发现、解释、交付、归档、反馈”做成长期可复盘、可订阅、可个性化的情报闭环。

## 二、近期阶段：稳定化

目标：先保证事实一致、发布可靠、推荐结果可信。

优先任务：

1. 修复 Pages 页面与 Telegram 真实推送状态不一致的问题。
2. 增加 Pages 与运行摘要的一致性测试。
3. 为重复入选项目增加新颖度提示或重复惩罚，但不硬性排除持续热门项目。已完成基础版本。
4. 继续减少 Kimi 可修复格式问题导致的降级。
5. 继续观察 GitHub Trending 在 GitHub Actions 环境中的稳定性。

验收标准：

1. `docs/index.md` 中的 Telegram 状态与 `data/runs/*.json` 保持一致。
2. 同一项目重复入选时，周报能解释“为什么仍值得关注”或标记“此前已推送”。已完成基础版本。
3. 每次运行能清楚记录采集错误、模型错误、发送错误和降级原因。

## 三、中期阶段：数据底座

目标：从纯 JSON 归档演进到可查询、可校验、可迁移的数据层。

推荐方案：

1. 保留 JSON 作为可读归档和公开工件。
2. 增加 SQLite 双写，不直接替代 JSON。已完成基础版本。
3. 编写历史 JSON 到 SQLite 的迁移脚本。已完成基础版本。
4. 增加迁移一致性测试，确保 SQLite 可由 JSON 重建。已完成基础版本。
5. 输出公共 JSON，例如 `docs/projects.json`、`docs/runs.json`，为前端和第三方订阅做准备。已完成基础版本。

暂不建议：

1. 立即引入 Postgres。
2. 立即做复杂多用户系统。
3. 立即把所有模块拆成微服务。

预留位置：

```text
src/storage/
scripts/migrate_json_to_sqlite.py
scripts/verify_migration.py
tests/test_storage_sqlite.py
tests/test_migration_parity.py
```

## 四、中期阶段：数据源与预算

目标：在不浪费 GitHub API 配额的前提下获得更稳定的候选和补全字段。

推荐策略：

1. GitHub Trending 继续作为第一热点信号。
2. GitHub REST Search 继续负责候选发现。
3. GitHub GraphQL 只用于 Top-N 候选字段补全，例如许可证、Issue、Release、维护活跃度。
4. 增加请求预算器，分别记录 Search、REST Core 和 GraphQL 的消耗与降级。
5. Trending 解析独立成 source adapter，便于网页结构变化时快速替换。

预留位置：

```text
src/sources/
src/enrichers/
src/http/
tests/test_source_adapters.py
tests/test_rate_budget.py
```

## 五、中期阶段：个性化与反馈

目标：从“热门项目”升级为“适合当前用户方向的热门项目”。

重点方向：

1. 继续完善 `java`、`python`、`agent_development`、`learning`、`developer_tools` 等 profile。
2. 为每个入选项目保留 profile 命中原因。
3. 增加学习导向、工程落地、工具链、基础设施等标签。
4. 增加收藏、忽略、重复、值得深入研究等反馈入口。
5. 后续将反馈转化为排序权重，而不是只作为文本记录。

预留位置：

```text
src/personalization.py
src/feedback.py
src/ranking/
tests/test_personalization.py
tests/test_feedback.py
```

## 六、中期阶段：展示与订阅

目标：让 GitHub Pages 不只是周报目录，而是轻量情报面板。

执行顺序：

1. 短期继续用 Python 生成静态 Markdown/HTML 页面。
2. 先导出公共 JSON，再考虑前端工程。
3. 当历史项目数量明显增加后，增加按日期、语言、方向、来源、风险提示筛选。
4. 如果交互需求变强，再考虑 Astro 这类静态优先框架。
5. Telegram、微信、飞书、邮件等渠道复用同一份“短消息 + 周报链接”结构。

暂不建议直接引入重型 SPA 或 SSR 框架。

## 七、长期阶段：产品化

目标：把当前批处理系统升级为团队可用的开源情报台。

长期能力：

1. 多 profile 订阅。
2. 历史趋势对比。
3. RSS、GitHub Issue 或 Discussion 反馈入口。
4. 可公开消费的 JSON API。
5. 风险评分进入排序公式。
6. 前端筛选和可视化。
7. 必要时再从 SQLite 升级到 Postgres 或独立服务。

## 八、安全路线

安全能力必须贯穿全部阶段：

1. 所有密钥继续只从环境变量或 GitHub Actions Secrets 读取。
2. 本仓库继续运行疑似密钥扫描。
3. 外部 README、描述和 topic 继续视为不可信内容。
4. LLM 输入继续做敏感信息脱敏。
5. GitHub Pages 是公开发布面，不能写入用户隐私、点击反馈明细或未脱敏配置。
6. 后续将 `security_flags` 演进为可量化的 `risk_penalty_score`。

## 九、下一步执行清单

最近应优先完成：

1. 修复 Pages 与 Telegram 状态一致性。
2. 补充发布链路契约测试。
3. 设计重复入选项目的新颖度策略。
4. 设计 SQLite 双写的最小表结构。已完成基础版本。
5. 基于公共 JSON 设计前端筛选和多渠道入口。公共 JSON 基础版本已完成。
