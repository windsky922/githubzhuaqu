# GitHub Weekly Agent

GitHub Weekly Agent 是一个每周自动追踪 GitHub 热点项目的中文周报 Agent。当前版本以 [GitHub Trending](https://github.com/trending) 周榜作为第一优先级信号，结合 GitHub Search、Star 增量、主题匹配、近期活跃度和基础安全风险提示，生成中文周报并把 GitHub Pages 阅读链接推送到 Telegram。

项目目标不是简单按总 Star 排名，而是尽量识别“本周正在变热、值得关注、适合继续跟踪或学习”的项目。

## 当前能力

1. 每周通过 GitHub Actions 自动运行，也支持手动触发。
2. 采集 GitHub Trending 周榜，并保证 Trending 前 10 中至少 7 个有效项目进入热点周报候选结果。
3. 使用 GitHub Search API 作为辅助来源，保留 Java、Python、Agent 开发等垂直方向的补充能力。
4. 记录 Star 历史，用新增 Star 作为重要排序依据。
5. 对候选项目做去重、活跃度过滤、主题匹配、个性化方向匹配、风险提示和推荐理由生成。
6. 使用 Kimi 生成中文结构化周报；Kimi 不可用或质量检查失败时生成规则版周报。
7. 生成 GitHub Pages 可访问的 HTML 周报页面。
8. Telegram 只推送可点击的周报链接，完整内容保存在仓库归档中。
9. 运行摘要、原始数据、入选项目、趋势摘要和周报都会归档。
10. 提供本仓库密钥扫描和外部项目基础安全风险提示。
11. 支持个性化 profile，例如 `java`、`python`、`agent_development`、`learning`、`developer_tools`。

## 主流程

```text
GitHub Actions
-> main.py
-> collector
-> processor
-> reporter
-> archive
-> sender
```

当前仍保持单体 Python 流程，避免过早引入复杂框架。后续当前端、数据库、多渠道推送变复杂后，再按模块拆分。

## 目录说明

| 路径 | 说明 |
|---|---|
| `main.py` | 主流程入口 |
| `src/collector.py` | GitHub Trending、Search、README 摘要采集 |
| `src/processor.py` | 去重、过滤、评分、入选项目选择 |
| `src/reporter.py` | Kimi 周报生成和规则版降级周报 |
| `src/report_checks.py` | 周报质量检查 |
| `src/security.py` | 脱敏和外部项目风险提示 |
| `src/personalization.py` | 个性化 profile 合并逻辑 |
| `src/sender.py` | Telegram 推送 |
| `scripts/build_pages.py` | 生成 GitHub Pages 归档页面 |
| `scripts/send_report_link.py` | 推送 GitHub Pages 周报链接 |
| `scripts/security_check.py` | 本仓库疑似密钥扫描 |
| `config/interests.example.json` | 默认兴趣和评分配置示例 |
| `config/profiles.example.json` | 个性化方向配置示例 |
| `prompts/` | Kimi 提示词 |
| `reports/` | Markdown 周报归档 |
| `docs/` | GitHub Pages 页面和项目文档 |
| `data/runs/` | 每次运行摘要 |
| `data/raw/` | 采集结果归档 |
| `data/selected/` | 入选项目归档 |
| `data/trends/` | 趋势摘要归档 |
| `data/state/` | Star 历史和已推送状态 |

## 个性化推荐

个性化推荐通过 profile 实现。用户后续可以在前端选择 Java、Python、Agent 开发等方向；当前阶段先用配置文件和环境变量表达这些选择。

示例：

```text
INTEREST_PROFILE=java,agent_development
```

上面的配置表示同时关注 Java 工程方向和 Agent 开发方向。程序会把对应 profile 中的语言、主题、搜索补充项和评分权重叠加到基础兴趣配置中。
入选项目会记录匹配到的个性化方向，例如“匹配当前个性化方向：Java 后端与工程实践、Agent 开发”，用于后续周报解释和前端筛选。

可用示例 profile 位于：

```text
config/profiles.example.json
```

如需自定义，可以新建：

```text
config/profiles.json
```

GitHub Actions 中建议把 `INTEREST_PROFILE` 配置为仓库变量：

```text
Settings -> Secrets and variables -> Actions -> Variables
```

注意：profile 配置不应包含 API Key、Token、Chat ID 或任何密钥。

## 必要配置

在 GitHub 仓库中进入：

```text
Settings -> Secrets and variables -> Actions
```

建议配置以下 Secrets：

| 名称 | 是否必须 | 说明 |
|---|---:|---|
| `GH_SEARCH_TOKEN` | 推荐 | 提高 GitHub API 访问额度 |
| `KIMI_API_KEY` | 可选 | 启用 Kimi 中文周报生成 |
| `KIMI_BASE_URL` | 可选 | 默认 `https://api.moonshot.cn/v1` |
| `KIMI_MODEL` | 可选 | Kimi 模型名称 |
| `TELEGRAM_BOT_TOKEN` | 可选 | 启用 Telegram 推送 |
| `TELEGRAM_CHAT_ID` | 可选 | Telegram 接收方 |
| `REPORT_BASE_URL` | 可选 | 自定义周报公开访问地址 |

建议配置以下 Variables：

| 名称 | 说明 |
|---|---|
| `INTEREST_PROFILE` | 个性化方向，例如 `java,agent_development` |
| `REPORT_BASE_URL` | 如果不想放在 Secret 中，也可以作为普通变量配置 |

没有 Kimi 时会生成规则版周报；没有 Telegram 时仍会归档周报和运行摘要。

## GitHub Pages

Telegram 推送的是 GitHub Pages 上的周报链接。仓库需要手动启用一次 Pages：

```text
Settings -> Pages
Source: Deploy from a branch
Branch: main
Folder: /docs
```

启用后，每次 workflow 运行都会刷新：

```text
docs/index.md
docs/projects.md
docs/weekly/YYYY-MM-DD.html
```

默认周报链接格式：

```text
https://<owner>.github.io/<repo>/weekly/YYYY-MM-DD.html
```

## 本地运行

```bash
python -m unittest
python main.py
```

本地运行时，程序不会自动读取 `.env` 文件。需要测试真实 API 时，请先在当前终端手动设置环境变量。

## 安全约束

1. 不要把 API Key、Token、Chat ID 写入代码、文档或配置示例。
2. 密钥只能通过环境变量或 GitHub Actions Secrets 读取。
3. `scripts/security_check.py` 会在测试前扫描本仓库中的疑似密钥。
4. 外部仓库的简介和 README 摘要会做基础脱敏后再进入报告生成流程。
5. 外部项目风险提示只作为辅助判断，不代表项目已经被完整安全审计。

## 后续发展方向

近期重点：

1. 完善个性化 profile，让用户可以按 Java、Python、Agent 开发、学习型项目等方向精准订阅。
2. 继续观察 GitHub Trending 在 Actions 环境中的稳定性。
3. 强化推荐理由和风险提示，让每个入选项目的原因更透明。
4. 继续改善 GitHub Pages 页面，但暂不引入复杂前端工程。

中期重点：

1. 建设轻量前端，用于筛选历史项目、语言、方向、风险提示和 Trending 排名。
2. 当历史数据足够后，引入 SQLite 作为派生索引层，JSON 继续作为可读归档源。
3. 为微信、飞书、邮件等推送渠道预留统一入口。
4. 通过更多质量指标补充判断，例如 Release 活跃度、Issue 状态、README 完整度、异常 Star 增长提示。
