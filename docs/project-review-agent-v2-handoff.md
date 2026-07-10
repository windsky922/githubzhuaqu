# GitHub 项目研究 Agent V2 下一阶段开发交接报告

交接日期：2026-07-10

工作区：`C:\Users\Administrator\Documents\New project 3`

分支：`main`

远端：`origin = git@github.com:windsky922/githubzhuaqu.git`

最新已推送提交：`8f555ad docs: add v2 adversarial review roadmap`

## 1. 下一阶段目标

把当前“证据展示型项目研究工作台”升级为可评估、可澄清、可追溯的项目匹配系统。首要工作是证明推荐相关性，不是继续扩展视觉效果、会话持久化或多 Agent 编排。

## 2. 新窗口首先阅读

按此顺序阅读，之后再改代码：

1. `AGENTS.md`：项目约束、密钥规则和开发原则。
2. `C:\Users\Administrator\Desktop\毕业季\毕设\.memory-bank\codex-experience-profile.md`：用户偏好与本机经验。
3. `C:\Users\Administrator\.codex\memories\command-line-and-coding-standards.md`：PowerShell、Git、编码、测试和 SQLite 规范。
4. `README.md`：产品定位、入口和现有能力。
5. `docs/project-review-agent-v2-roadmap.md`：对抗性审查、风险、P0/P1/P2 和验收标准。
6. `docs/frontend-v2-summary.md`：React V2 已完成范围、发布路径与测试命令。
7. `docs/api.md` 与 `docs/architecture.md`：接口和持久化边界。
8. `docs/operation-log.md`：近期决策和历史问题。
9. 本报告：`docs/project-review-agent-v2-handoff.md`。

## 3. 已完成状态

### React 前端 V2

- 源码在 `frontend/`，Vite 产物在 `docs/app/`。
- Hash Router 提供 `#/agent`、`#/explore`、`#/recommendations`、`#/projects/:owner/:repo`、`#/compare`。
- Agent 页有顶部导航、会话侧栏、移动端抽屉、SSE 草稿、最终回答、证据抽屉和浏览器本地历史。
- 聊天输入框已修复为固定底部工作区行；只有消息列表滚动。
- 筛选页支持服务端分页，每页 50 条；项目对比最多 3 项，使用本地暂存和 `repos` URL 参数。

### 后端接口

- `/v1/rag/ask`、`/v1/rag/ask/stream` 保持证据约束：无证据拒答，LLM 质量失败回退规则答案。
- `/api/projects` 与 `/v1/projects` 已有兼容分页字段：`total`、`offset`、`limit`、`has_more`。
- 默认 Agent 请求：`mode=hybrid&limit=3&auto_build=true`。
- 不新增账号、服务端聊天会话表或历史回答作为事实证据。

### 已推送文档

- `docs/frontend-v2-summary.md`：V2 前端总结。
- `docs/project-review-agent-v2-roadmap.md`：V2 对抗性审查与路线图。
- README 和操作日志已引用/记录 V2 审查。

## 4. 已确认的关键风险

### 4.1 最不确定的事情

无法证明首选项目真的满足用户需求。系统没有人工标注的查询-项目相关性数据，也没有 Top-1 接受率、Recall@K、MRR、NDCG、硬约束违反率或拒答准确率。

### 4.2 置信度和质量门槛不代表正确性

- `src/rag/answering.py::_confidence` 只按 context 数量给出 `high/medium/low`。
- `_answer_quality` 主要按 context、citation、evidence 数量计分。
- `src/rag/answer_quality.py` 只检查长度、引用编号、未知仓库和是否有证据，不检查相关性或结论是否被证据支持。
- 规则降级回答与前端首选项目都偏向召回顺序的第一项，而不是结构化匹配排序。

不要把现有 `confidence=high` 当作概率，也不要对外宣称“智能推荐准确”。

### 4.3 `local-hash-v1` 不是语义 embedding

`src/rag/embeddings.py` 使用 64 维 token hash；中文按单字切分，存在碰撞，不理解同义词、否定和硬约束。向量检索只排除 `score <= 0`；hybrid 是文本排名 0.55 和 hash 排名 0.45 的名次融合。

### 4.4 RAG 语料存在实测噪声

本地 SQLite 审计：79 个唯一项目、162 个历史 selection、261 个 RAG chunk、11 个 RAG explanation、0 条项目反馈。chunk 中有 18 个 HTML 标签、17 个 Markdown 图片、16 个 HTML 属性、21 个 badge/Trendshift 文本和 10 组重复文本。

根因是 `src/storage/sqlite_store.py::_clean_text` 只压缩空白。README 摘要、项目画像和任务记忆会直接拼接切块。项目卡中的 `href`、`src` 和徽章残片属于后端语料问题，不是 React 转义问题。

### 4.5 连续对话未实现追问理解

每轮独立调用 `/v1/rag/ask/stream`。用户输入“继续”“那个项目呢”时，短语会被当成独立查询。后续只能传递最近用户意图和当前候选作为非证据上下文；禁止把历史模型回答当证据或写入后端会话表。

### 4.6 数据和运行边界

- 本地 `data/github_weekly.sqlite` 最新 selection 是 2026-06-03；GitHub 每周任务 2026-07-06 成功，产物在 `weekly-archive` 分支。必须区分本地 SQLite 与归档分支数据。
- 主工作流只在 schedule 和手动触发时运行；没有每次 push/PR 的完整 CI 门禁。
- SSE 使用 GET 的 `q` 参数，问题可能出现在 URL、历史或日志；对话还存入 `localStorage`。
- 只读 RAG/LLM 接口没有明显速率限制、并发预算或请求长度限制。
- 外部 README 文本进入 prompt_context 时没有明确的“不可信数据”隔离或提示注入策略。

## 5. 建议先做的 P0-1

下一阶段第一张开发任务限定为：建立项目匹配评估集与可重复基线，暂不改变现有用户 API 契约。

建议交付：

1. 新增 `evals/project_match_cases.jsonl`，首批至少 50 条中文需求。
2. 每条至少含 `query`、硬约束、可接受仓库、明确不相关仓库、预期澄清标记和最低证据要求。
3. 新增评估脚本，例如 `scripts/evaluate_project_match.py`，输出 FTS5、local-hash 和 hybrid 的结果。
4. 指标至少包含 Recall@3、Recall@10、MRR@10、硬约束违反率、零命中率和澄清正确率。
5. 新增 fixture 和测试，覆盖缺失期望仓库、无证据和歧义查询。
6. 文档记录 baseline；没有人工标注前不能写“准确率提升”。

后续顺序固定为：评估基线 -> 修正 confidence/quality -> 语料清洗和版本化 -> 结构化 recommendations -> 追问澄清 -> push/PR CI 与 Playwright -> 查询级反馈和真实 embedding 对照。

## 6. 关键代码地图

| 目的 | 文件 |
|---|---|
| RAG 回答、fallback、置信度 | `src/rag/answering.py` |
| 回答质量门槛 | `src/rag/answer_quality.py` |
| 本地 hash embedding | `src/rag/embeddings.py` |
| 语料重建、chunk、SQLite 操作 | `src/storage/sqlite_store.py` |
| 检索、hybrid、RAG Ask、项目查询 | `src/api/repository.py` |
| FastAPI 路由和鉴权 | `src/api/app.py` |
| RAG 提示词 | `prompts/rag_ask.md` |
| React Agent 页面和 SSE 生命周期 | `frontend/src/pages/AgentPage.tsx` |
| 聊天 UI、项目卡、输入框 | `frontend/src/components/AgentWorkspace.tsx` |
| 前端请求、SSE 解析和 API 模式 | `frontend/src/lib/api.ts` |
| 浏览器对话存储与迁移 | `frontend/src/lib/conversations.ts` |
| 周任务和当前 CI | `.github/workflows/weekly.yml` |

## 7. 必须保留的边界

1. `/v1/rag/ask` 和 `/v1/rag/ask/stream` 仅可非破坏性扩展。
2. 不新增 SQLite 聊天会话表，不引入账号系统。
3. 历史模型回答不能作为事实证据；事实只能来自本轮 citations、evidence、contexts 和 prompt_context。
4. API Key、Token、Chat ID、管理口令只能来自环境变量或 Secrets，绝不写入代码、文档、fixture 或浏览器存储。
5. 外部 HTTP 请求必须有超时和错误处理。
6. React 保持默认文本转义，禁止 `dangerouslySetInnerHTML`。
7. 管理写操作继续受 `ADMIN_API_TOKEN` 保护。
8. 不回退用户改动；`tmp/` 是临时目录，永不提交。

## 8. 本地运行与验证

PowerShell：

`cd "C:\Users\Administrator\Documents\New project 3"`

后端：

`python -m uvicorn src.api.app:create_app --factory --host 127.0.0.1 --port 8000`

前端开发：

`npm run dev`

入口：

- 开发：`http://127.0.0.1:5173/#/agent?api=1`
- 发布构建：`http://127.0.0.1:8000/app/#/agent?api=1`

若 8000 被占用，不要关闭未知进程；先确认现有进程是否就是本项目，或使用其他端口。

完成后运行：

`npm run lint`

`npm run test`

`npm run build`

`python -m unittest discover -q`

`python scripts\security_check.py`

`git diff --check`

PowerShell 偶尔会错误显示中文响应。不要仅凭 `$resp.answer` 的乱码判断 API 编码错误；可用 `curl.exe` 保存原始 JSON，再由 Python 按 UTF-8 读取验证。

## 9. Git 注意事项

- 开始前运行 `git status --short --branch`。
- 当前交接时唯一预期未跟踪项是 `tmp/`；不要提交它。
- 不使用 `git reset --hard`、`git checkout --` 或删除未确认文件。
- 先正常执行 `git push origin main`。此前 GitHub 曾拒绝损坏的 thin pack；若再次出现 `remote unpack failed` 或 `inflate`，先执行 `git fsck --full`，确认本地对象库正常后再用 `git push --no-thin origin main`。

## 10. 可直接粘贴到新 Codex 窗口的启动提示

```text
请继续开发 C:\Users\Administrator\Documents\New project 3。

先读取：AGENTS.md、C:\Users\Administrator\Desktop\毕业季\毕设\.memory-bank\codex-experience-profile.md、C:\Users\Administrator\.codex\memories\command-line-and-coding-standards.md、README.md、docs/project-review-agent-v2-handoff.md、docs/project-review-agent-v2-roadmap.md、docs/frontend-v2-summary.md、docs/api.md、docs/architecture.md。

当前分支 main，最近已推送提交是 8f555ad。不要提交 tmp/，不要回退已有改动。

下一阶段先做 P0-1：建立项目匹配评估集和可重复基线。创建不少于 50 条中文需求的 evals/project_match_cases.jsonl，新增评估脚本和测试，输出 FTS5、local-hash-v1、hybrid 的 Recall@3、Recall@10、MRR@10、硬约束违反率、零命中率和澄清正确率。不要改变 /v1/rag/ask 或 /v1/rag/ask/stream 的现有响应契约，不新增服务端聊天会话，不把历史模型回答作为证据。

当前关键风险：confidence/answer_quality 主要按证据数量计算；local-hash-v1 不是真实语义 embedding；RAG chunks 含 HTML/徽章噪声；“继续”等追问仍被独立检索；本地 SQLite 数据可能滞后 weekly-archive；没有 push/PR CI 门禁。先基线评估，再调检索或模型。

完成后运行 npm run lint、npm run test、npm run build、python -m unittest discover -q、python scripts\security_check.py、git diff --check；重建 docs/app；提交并推送 main，但排除 tmp/。
```

## 11. 立即下一步

新窗口第一件事：读取本报告和 V2 审查报告，运行当前全量测试确认基线，然后只为 P0-1 创建小而可验证的评估框架。不要在同一轮同时重写语料、embedding、前端和 API。
