# GitHub Weekly Agent 项目架构文档

版本：v0.1

日期：2026-04-27

状态：架构规划阶段，暂不开发代码

## 1. 项目定位

GitHub Weekly Agent 是一个轻量级自动化信息整理 Agent，用于每周发现 GitHub 上值得关注的热点项目，生成中文周报，并推送到用户手机。

它不是一个长期在线服务，而是一个定时运行的自动化任务：

```text
GitHub Actions 定时触发
→ Python Agent 执行任务
→ GitHub API 获取项目
→ 数据清洗和排序
→ Kimi API 生成中文周报
→ Telegram Bot 推送
→ 报告和摘要归档到 GitHub
```

## 2. 设计原则

1. 先稳定可用，再增强智能。
2. Codex 负责开发和维护，运行时不依赖 Codex。
3. 所有密钥只通过 GitHub Secrets 或本地环境变量读取。
4. 外部 API 调用必须有超时、重试和降级。
5. 运行结果可追踪，但不提交敏感日志。
6. 模块边界要清楚，方便后续替换数据源、模型和推送渠道。

## 3. 推荐架构

```text
               +----------------------+
               |   GitHub Actions     |
               | schedule / manual    |
               +----------+-----------+
                          |
                          v
               +----------------------+
               |      main.py         |
               | orchestration        |
               +----------+-----------+
                          |
      +-------------------+-------------------+
      |                   |                   |
      v                   v                   v
+------------+     +---------------+   +---------------+
| settings   |     | logging       |   | run context   |
| secrets    |     | run summary   |   | dates/paths   |
+------------+     +---------------+   +---------------+
      |
      v
+-------------------+
| GitHub Collector  |
| github_client     |
+---------+---------+
          |
          v
+-------------------+
| Data Processor    |
| clean/dedupe/rank |
+---------+---------+
          |
          v
+-------------------+
| Report Generator  |
| kimi_client       |
| fallback template |
+---------+---------+
          |
          v
+-------------------+
| Archive           |
| reports/data/runs |
+---------+---------+
          |
          v
+-------------------+
| Telegram Sender   |
| telegram_client   |
+-------------------+
```

## 4. 数据流

1. GitHub Actions 在每周一触发，也允许手动触发。
2. 程序读取配置、环境变量和日期范围。
3. Collector 执行多组 GitHub Search API 查询。
4. Processor 对项目去重、过滤、分类、评分和排序。
5. Reporter 优先调用 Kimi API 生成中文周报。
6. 如果 Kimi API 失败，Reporter 生成基础模板版报告。
7. Archive 保存 Markdown 报告、原始数据摘要和运行摘要。
8. Sender 将摘要或完整报告分段推送到 Telegram。
9. GitHub Actions 将新增报告和运行摘要提交回仓库。

## 5. 第一阶段 MVP 范围

必须实现：

1. GitHub Actions 每周一自动运行。
2. `workflow_dispatch` 手动运行。
3. GitHub Search API 搜索最近 7 天项目。
4. 支持多查询源合并和去重。
5. 过滤 archived、fork、无描述项目。
6. 按 Star、Fork、主题相关度和新鲜度排序。
7. Kimi API 生成中文周报。
8. Kimi 失败时生成基础项目列表报告。
9. Telegram 分段推送。
10. 报告保存为 `reports/YYYY-MM-DD.md`。
11. 运行摘要保存为 `data/runs/YYYY-MM-DD.json`。
12. GitHub Actions 自动提交归档文件。

暂不实现：

1. README 深度抓取。
2. SQLite 历史去重。
3. GitHub Pages 网页展示。
4. 多用户系统。
5. 复杂推荐模型。
6. Telegram 交互式 Bot。

## 6. 推荐目录结构

```text
github-weekly-agent/
├── README.md
├── requirements.txt
├── .env.example
├── .gitignore
├── main.py
├── config/
│   └── interests.example.json
├── prompts/
│   └── weekly_report.md
├── reports/
│   └── .gitkeep
├── data/
│   ├── runs/
│   │   └── .gitkeep
│   └── raw/
│       └── .gitkeep
├── docs/
│   ├── architecture-review.md
│   ├── project-architecture.md
│   └── operation-log.md
├── src/
│   ├── __init__.py
│   ├── settings.py
│   ├── models.py
│   ├── collector.py
│   ├── processor.py
│   ├── reporter.py
│   ├── sender.py
│   ├── archive.py
│   ├── logging_config.py
│   ├── utils.py
│   └── clients/
│       ├── __init__.py
│       ├── github_client.py
│       ├── kimi_client.py
│       └── telegram_client.py
└── .github/
    └── workflows/
        └── weekly.yml
```

## 7. 模块职责

| 模块 | 职责 |
|---|---|
| `main.py` | 串联完整执行流程，只做编排，不堆业务逻辑 |
| `src/settings.py` | 读取环境变量、默认配置、运行参数 |
| `src/models.py` | 定义项目、报告、运行摘要等数据结构 |
| `src/collector.py` | 组织 GitHub 查询策略，返回原始项目列表 |
| `src/clients/github_client.py` | 封装 GitHub API 请求、分页、超时和错误处理 |
| `src/processor.py` | 去重、过滤、分类、评分和排序 |
| `src/reporter.py` | 生成 Kimi prompt，调用模型或降级模板 |
| `src/clients/kimi_client.py` | 封装 Kimi API 调用 |
| `src/sender.py` | 分段发送 Telegram 消息 |
| `src/clients/telegram_client.py` | 封装 Telegram Bot API |
| `src/archive.py` | 保存报告、原始数据和运行摘要 |
| `src/logging_config.py` | 标准化日志格式，避免输出密钥 |
| `prompts/weekly_report.md` | 周报生成提示词模板 |
| `.github/workflows/weekly.yml` | 定时运行、安装依赖、执行程序、提交报告 |

## 8. 搜索策略

第一阶段使用 GitHub Search API，采用多查询合并：

```text
created:>=YYYY-MM-DD stars:>20
topic:ai created:>=YYYY-MM-DD stars:>20
topic:agent created:>=YYYY-MM-DD stars:>10
topic:llm created:>=YYYY-MM-DD stars:>10
language:Python created:>=YYYY-MM-DD stars:>20
language:TypeScript created:>=YYYY-MM-DD stars:>20
pushed:>=YYYY-MM-DD stars:>100
```

说明：

1. `created` 捕捉新项目。
2. `pushed` 捕捉近期活跃的已有项目。
3. 多查询结果按 `full_name` 去重。
4. 第一阶段不承诺精准 Star 增量，只做热点近似。

## 9. 推荐评分

第一阶段采用简单可解释评分：

```text
score = 0.45 * star_score
      + 0.20 * fork_score
      + 0.25 * topic_score
      + 0.10 * freshness_score
```

其中：

1. `star_score`：在本次候选项目内归一化。
2. `fork_score`：在本次候选项目内归一化。
3. `topic_score`：命中用户兴趣关键词的比例。
4. `freshness_score`：创建时间越近分数越高。

## 10. 周报格式

报告保存为 Markdown：

```markdown
# GitHub 每周热点项目周报 - YYYY-MM-DD

## 一、本周趋势

## 二、热点项目总览

| 序号 | 项目 | 方向 | Star | Fork | 语言 | 链接 |
|---|---|---|---:|---:|---|---|

## 三、重点项目分析

## 四、最适合关注的项目

## 五、本周结论

## 附录：搜索条件与生成信息
```

报告必须遵守：

1. 不编造未提供的信息。
2. 链接必须来自 GitHub API 返回值。
3. 信息不足时明确说明“仅根据项目名称和简介判断”。
4. 不虚构 Star、作者、License 或发布时间。

## 11. Telegram 推送策略

第一阶段推荐发送“摘要 + 仓库报告路径/链接”，而不是把完整长报告全部塞进一条消息。

规则：

1. 单条消息控制在 3500 字符以内。
2. 优先使用纯文本或 HTML parse mode。
3. 报告过长时按章节分段。
4. 发送失败不阻止报告归档。
5. Telegram API 错误写入运行摘要。

## 12. 运行归档

每次运行保存两类文件：

```text
reports/YYYY-MM-DD.md
data/runs/YYYY-MM-DD.json
```

`reports` 保存给用户看的中文周报。

`data/runs` 保存机器可读摘要，例如：

```json
{
  "run_date": "2026-04-27",
  "status": "success",
  "queries": ["created:>=2026-04-20 stars:>20"],
  "collected_count": 35,
  "selected_count": 10,
  "report_path": "reports/2026-04-27.md",
  "telegram_sent": true,
  "fallback_used": false
}
```

不建议提交完整 debug 日志，避免泄露响应头、token 片段或过多噪声。

## 13. GitHub Actions 要求

工作流需要：

1. `schedule`：每周一运行。
2. `workflow_dispatch`：允许手动运行。
3. `permissions: contents: write`：允许提交周报。
4. 安装 Python 和依赖。
5. 注入 GitHub Secrets。
6. 执行 `python main.py`。
7. 检查是否有 `reports/` 或 `data/runs/` 变化。
8. 有变化才提交，提交信息带 `[skip ci]`。

## 14. 安全要求

1. `.env` 必须加入 `.gitignore`。
2. 所有 token 和 API key 只能来自环境变量。
3. 日志中不得输出完整 token。
4. GitHub token 使用最小权限。
5. Telegram Chat ID 和 Bot Token 不写入文档示例真实值。

## 15. 迭代路线

### 阶段一：MVP

完成自动搜索、周报生成、Telegram 推送、归档和 GitHub Actions。

### 阶段二：README 增强

抓取 README，增强项目定位、使用场景和学习价值分析。

### 阶段三：历史记忆

引入 JSON 或 SQLite 记录已推荐项目、首次出现时间、上次推送时间和 Star 变化。

### 阶段四：个性化推荐

通过 `config/interests.example.json` 和用户偏好权重提升推荐相关度。

### 阶段五：网页周刊

生成 GitHub Pages 页面，展示历史周报、趋势统计和分类榜单。

## 16. 开发建议

下一步开发时建议按以下顺序推进：

1. 创建项目骨架和配置文件。
2. 实现 GitHub API client 和 collector。
3. 实现 processor 和基础 Markdown 报告模板。
4. 实现 Kimi reporter。
5. 实现 Telegram sender。
6. 实现 archive。
7. 添加 GitHub Actions。
8. 本地测试后再启用定时运行。

