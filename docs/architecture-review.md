# 架构审查报告

审查日期：2026-04-27

审查对象：`D:\liulanqixiazai\github-weekly-agent-architecture.md`

## 总体结论

原始文档的目标、核心流程和技术选型基本清晰，适合作为第一版需求说明。它已经正确区分了 Codex 与运行时 Agent 的职责：Codex 负责开发、维护和调试，真正每周运行的是 GitHub Actions 中的 Python 程序。

但如果直接按原文档开发，后续容易遇到几个问题：热点定义不够准确、模块边界偏粗、GitHub Actions 自提交细节不足、Telegram Markdown 兼容性未展开、运行日志与数据归档设计不够明确。因此建议在原始架构基础上做一次工程化收敛，而不是完全重建。

## 清晰的部分

1. 项目目标明确：每周获取 GitHub 热点项目，生成中文周报并推送到 Telegram。
2. 角色分工清楚：Codex 是开发工具，不是每周在线运行的模型服务。
3. MVP 范围合理：先实现 GitHub 搜索、Kimi 总结、Telegram 推送、Markdown 归档和 GitHub Actions。
4. 安全要求正确：密钥必须通过环境变量或 GitHub Secrets 注入，不写入代码。
5. 阶段路线可执行：从 MVP 到 README 抓取、兴趣推荐、历史去重、网页展示逐步扩展。

## 主要问题

### 1. “热点项目”的定义需要更准确

原文档主要使用：

```text
created:>=YYYY-MM-DD stars:>20 sort:stars
```

这个查询只能找到最近创建且 Star 数较高的项目，容易漏掉“不是本周创建，但本周突然变热”的项目。

建议第一阶段仍使用 GitHub Search API 保持简单，但文档中要明确这是“新项目热度近似值”。第二阶段可以加入：

1. `pushed:>=YYYY-MM-DD stars:>N` 捕捉近期活跃项目。
2. 多查询源合并，例如 `topic:ai`、`topic:agent`、`language:Python`。
3. 历史数据对比，计算 Star 增量。
4. 可选抓取 GitHub Trending 页面作为增强来源，但需要注意页面结构变化风险。

### 2. GitHub Actions 自提交需要防循环设计

工作流运行后提交 `reports/`，可能触发新的 workflow。建议：

1. `on.push.paths-ignore` 忽略 `reports/**` 或者提交信息使用 `[skip ci]`。
2. 提交前检查是否真的有文件变化。
3. 明确 `permissions: contents: write`。
4. 使用 `github-actions[bot]` 作为提交用户。

### 3. 模块边界可以更细

原文档的模块划分方向正确，但建议把外部 API 调用、业务处理、报告生成、归档分开，避免主流程越来越重。

建议增加：

1. `clients/github_client.py`
2. `clients/kimi_client.py`
3. `clients/telegram_client.py`
4. `models.py`
5. `settings.py`
6. `prompts/weekly_report.md`
7. `logging_config.py`

这样后续替换模型、增加推送渠道或改热点来源时，不会影响主流程。

### 4. Telegram 推送格式需要提前约束

Telegram 单条消息限制约 4096 字符，MarkdownV2 还需要转义特殊字符。建议第一阶段优先使用纯文本或 HTML parse mode，减少 MarkdownV2 转义成本。

推送策略建议：

1. 长报告按章节分段。
2. 每段小于 3500 字符，预留链接和标题空间。
3. 发送失败不影响报告归档。
4. 可以先发送摘要，再发送 GitHub 报告链接。

### 5. 日志归档需要区分“运行日志”和“项目文档日志”

用户要求把每一步操作动向和日志上传到 GitHub。建议分两类处理：

1. 当前开发阶段：使用 `docs/operation-log.md` 记录 Codex 操作。
2. 自动运行阶段：GitHub Actions 保留完整日志，仓库只提交本次运行摘要，例如 `data/runs/YYYY-MM-DD.json`，避免把过长或含敏感信息的日志提交进仓库。

### 6. Kimi API 降级方案需要写清楚

原文档提到了降级，但没有定义降级输出。建议第一阶段规定：

1. Kimi 成功：输出中文分析周报。
2. Kimi 失败：输出规则模板版周报，包括项目列表、Star、语言、描述和链接。
3. Telegram 失败：仍保存报告并让 workflow 失败或警告，具体由配置决定。

## 推荐结论

不需要推翻原架构。建议采用“原始架构 + 工程化增强”的方案：

1. 保留 GitHub Actions + Python + GitHub Search API + Kimi API + Telegram 的主链路。
2. 将外部 API client、数据模型、处理器、报告生成器、推送器、归档器拆分清楚。
3. 先做 MVP，不做复杂推荐算法。
4. 从第一版就保留运行日志摘要、原始数据快照和报告归档接口。

