# GitHub 项目研究 Agent V3 下一阶段开发交接报告

交接日期：2026-07-13

当前分支：`main`

功能审查基线：`4d5c1a014fc343f6974f0ab8d343e48d4e4b4799 docs: add project review agent v3 roadmap`。本交接文档提交会位于其后，新窗口以 `git log -1` 的最新交接提交为实际 HEAD。

远端状态：审查时 `origin/main` 与本地 HEAD 一致；GitHub Actions `29260874582` 的核心检查、mock Playwright 和真实 FastAPI Playwright 全部成功。

## 1. 新窗口当前任务

先完成 V3 路线图的第一个 P0：**把公开 `weekly-archive` 与私有运行态数据分开，停止发布原始 SQLite，并建立显式公共文件白名单。**

完成该阶段后，按顺序进入：

```text
P0-11A 公共归档白名单与运行态持久化边界
→ P0-11B 安全流式输出与真实引用校验
→ P0-12 顶层意图、回答类型与结构化比较
→ 数据新鲜度、独立 blind 评估和查询级决策快照
```

当前不要先做：

- Responses API 或 Agents SDK 迁移；
- 服务端聊天会话；
- hybrid 权重调整；
- 真实 embedding 替换；
- 查询级反馈表；
- UI 外观扩展。

原因：当前最高风险是公开边界和错误确定性，不是 Agent 框架能力。

## 2. 新窗口首先执行

使用 PowerShell，先确认现场，不要立即改文件：

```powershell
cd "C:\Users\Administrator\Documents\New project 3"
git status --short --branch
git log -5 --oneline
git rev-parse HEAD
git rev-parse origin/main
git fsck --connectivity-only --no-dangling --no-reflogs
```

预期状态：

```text
main 与 origin/main 一致，且历史包含 4d5c1a0 和最新 V3 交接提交
仅 tmp/ 未跟踪
connectivity-only fsck 通过
```

如出现其他修改：先读取 `git diff -- <file>`，确认归属；不得覆盖、删除、暂存或回退用户已有改动。

不要把 full fsck 失败误判为当前 main 已损坏。已知存在一个不在可达历史中的损坏 loose object：

```text
0d5add93193596c7597490811fc0cd23952335aa
```

它曾导致 fetch 解包失败。修复前必须备份 `.git` 和该对象；本阶段不得直接删除、`git gc --prune=now` 或强制重写仓库。

## 3. 必读文档与顺序

### 第一组：规则和当前结论

1. `AGENTS.md`
   - 当前项目规则、测试、密钥、Prompt、外部 README、数据契约和 Git 边界。
2. `docs/project-review-agent-v3-handoff.md`
   - 本交接包；当前基线、第一任务、命令和边界。
3. `docs/project-review-agent-v3-roadmap.md`
   - 第一性原理审查、事实/推断/待验证、P0/P1/P2 和验收标准。
4. `README.md`
   - 当前能力、运行方式、环境变量、归档分支和页面入口。
5. `docs/operation-log.md`
   - 只需先读顶部近期记录；不要从尾部旧状态推断当前能力。

### 第二组：接口、数据和架构

6. `docs/api.md`
   - `/v1/rag/ask`、`/v1/rag/ask/stream`、管理接口和只读/写入契约。
7. `docs/data-contracts.md`
   - SQLite 表、归档数据和字段契约；新增表或字段时必须同步。
8. `docs/architecture.md`
   - FastAPI、React、RAG、任务、通知、两套 Playwright 和 CI 边界。
9. `docs/command-line-and-coding-standards.md`
   - 项目内命令与编码规范。
10. `C:\Users\Administrator\.codex\memories\command-line-and-coding-standards.md`
    - 全局 PowerShell 与通用编码规则；若与当前项目文件冲突，以当前项目文件为准。

### 第三组：P0-11A 直接相关代码

11. `scripts/publish_archive_branch.py`
    - 当前 `ARCHIVE_PATHS = ("docs", "reports", "data")`，会整目录复制并 `git add`。
12. `.github/workflows/weekly.yml`
    - 恢复 `weekly-archive` 历史数据、生成周报和调用发布脚本的真实流程。
13. `.gitignore`
    - main 会忽略 SQLite，但这不能约束独立归档分支。
14. `src/archive.py`
    - JSON 归档和 SQLite 派生索引的生成边界。
15. `src/storage/schema.sql`、`src/storage/sqlite_store.py`
    - 运行态 SQLite 同时包含公开项目数据和可能的用户查询、反馈、订阅、任务、通知状态。
16. `tests/test_workflows.py`、`tests/test_archive.py`
    - 现有归档/工作流测试和需要补齐的发布白名单测试。

### 已失效的旧路径

以下旧交接曾引用的文件当前不存在，不要把它作为启动阻塞条件：

```text
C:\Users\Administrator\Desktop\毕业季\毕设\.memory-bank\codex-experience-profile.md
```

项目根目录当前也没有 `.memory-bank/`。当前事实以仓库文件、命令结果和上述全局规范文件为准。

## 4. 当前已完成状态

### P0-1 至 P0-4

- 52 条中文项目匹配固定评估及 FTS5、local-hash-v1、hybrid 基线；
- Ask 质量语义拆分为证据覆盖和未校准匹配把握；
- 语料清洗、版本、哈希、来源分层和 Kimi 结构化增强边界；
- 后端结构化 `recommendations[]`，前端不再从 citations 第一项猜首选。

### P0-5 至 P0-7

- 无状态 POST 追问、澄清、候选范围和最小浏览器上下文；
- 提交级 CI、mock Playwright；
- 复合硬约束、句子级能力/成本证据和 capability-v1。

### P0-8 至 P0-10

- 浏览器管理口令仅保存在当前页面内存并通过 Header 发送；
- 正交能力模型、候选序号追问；
- 真实 Chromium → FastAPI → 临时 SQLite → 本地 RAG 回归；
- CI 独立运行核心、mock Playwright 和真实后端 Playwright。

### 最近提交

```text
4d5c1a0 docs: add project review agent v3 roadmap
fea50ce ci: run real FastAPI browser regression
3342ab3 test: add real FastAPI browser regression
025ac0c feat: resolve ordinal candidate follow-ups
3e9fdb8 fix: separate project capability constraints
```

## 5. 已确认事实与不能过度解释的结果

### 固定评估基线

| 评估 | 当前结果 |
| --- | --- |
| 项目匹配 FTS5 | Recall@3/10=`0.0962`，MRR@10=`0.0962`，零命中=`0.9038` |
| 项目匹配 local-hash/hybrid | Recall@3/10=`0.9231`，MRR@10=`0.8878` |
| 结构化推荐 local-hash/hybrid | Top-1=`0.8654`，Recall@3=`0.9231`，MRR@10=`0.8878` |
| 追问 60 条 | 固定集路由、澄清、范围、改写、约束均=`1.0` |
| 约束解析 100 条、证据 60 条 | 固定集准确率=`1.0`，错误合格/错误拒绝/违反率=`0` |

这些结果只证明固定合成回归没有失败。语料只有 8 个合成仓库，样本由实现过程共同维护，没有独立 blind 结果。不得写成“真实自然语言已经校准”。

### 当前数据状态

- 本地 `data/github_weekly.sqlite` 约 7.7 MB；业务来源最大日期仍为 2026-06-03。
- 162 条 corpus、261 条 chunk 均为 `legacy-v0`。
- 语料审计仍发现 HTML、Markdown 图片、badge URL 和属性残留。
- 审查时远端 `weekly-archive` 已更新到 2026-07-13，且公开分支跟踪约 24 MB 的 `data/github_weekly.sqlite`。

不要在下一窗口把“数据库今天被修改”或“embedding 已存在”解释为来源新鲜。

## 6. 当前关键风险

### 6.1 P0：公开归档混入运行态 SQLite

当前发布器无条件复制 `docs/`、`reports/`、`data/`。同一 SQLite schema 可包含：

- RAG query、answer、citations 和 `prompt_context`；
- 用户反馈备注；
- 订阅规则；
- planned jobs 和 Agent tasks；
- 通知候选、投递状态和响应摘要。

已证明远端公开分支包含 SQLite；尚未证明远端库已经包含真实敏感用户内容。下一窗口必须保持这个表述边界。

### 6.2 P0：未校验模型 delta 先显示

服务端当前先发送 provider delta，完整聚合后才做质量校验；前端立即显示 delta。后续 final 降级不能撤回屏幕上已经出现的内容。

同时 `_ensure_citation_marker()` 会在校验前自动补引用；现有闸门不验证证据相关性、主张支持度和数据新鲜度。

### 6.3 P0：缺少顶层回答类型

现有路由主要判断本轮与上一轮的关系，未独立表达 search、explain、compare、learning_plan。已复现：

- “对比这两个/他俩”进入全归档新搜索；
- “我想学习 Agent 开发”进入项目搜索；
- “第三方”可能被序号正则识别为“第三个候选”；
- 明确序号比较可能选对范围但丢失当前比较意图。

### 6.4 P0/P1：GET 副作用和模型 provenance

部分无鉴权 GET 会持久化解释或在 `auto_build=true` 时构建 embedding。任意 `model` 标签最终仍执行相同的 local hash 算法，可能产生伪 provenance 和写放大。

### 6.5 P1：没有查询级可复现决策闭环

项目级反馈不能关联原始需求、路由、候选顺序、约束判定、语料版本和最终回答。该任务必须在公共/私有存储拆分之后进行。

## 7. 下一阶段 P0-11A 详细目标

### 7.1 目标

建立显式、默认拒绝的公共归档投影：

```text
工作区运行态数据
→ 文件级分类与脱敏检查
→ 公共 allowlist staging tree
→ weekly-archive
```

原始 SQLite、WAL、SHM、用户状态、凭据、临时文件和未分类文件不得进入公共分支。

### 7.2 开始编码前的只读审计

1. 重新确认仓库和 `weekly-archive` 的可见性、远端 HEAD 和 SQLite 是否仍存在。
2. 统计 `data/` 每个子目录的文件类型、字段和来源。
3. 按以下类别生成审计表：
   - 明确公共：公开项目元数据、公开周报、静态页面；
   - 需要脱敏：运行摘要、错误字段、来源响应；
   - 明确私有：SQLite、用户查询、反馈、订阅、任务、通知、凭据；
   - 未知：默认不发布。
4. 不下载或公开展示远端数据库中的完整 query、note、token 或 payload。只输出计数、字段存在性、日期和哈希。
5. 如果必须下载远端 SQLite 到临时目录审计，先向用户说明原因；不得放入项目工作区或提交。

### 7.3 发布器修改原则

- 使用文件 allowlist，不使用不断增长的敏感文件 denylist。
- staging 前先清理目标 `docs/`、`reports/`、`data/`，否则旧 SQLite 会继续留在归档树。
- 使用 `git add -A` 或等价方式显式暂存删除，确保最新归档 tree 移除旧 SQLite。
- 拒绝 symlink、路径穿越、工作区外目标和未知扩展名。
- 发布前扫描 staged tree；发现 `*.sqlite*`、凭据模式或 canary 时立即失败。
- `.gitignore` 不是归档安全边界，不能作为验收证据。
- 本阶段只停止未来发布和移除最新 tree 中的 SQLite；清理 Git 历史属于破坏性操作，必须另行获得用户明确授权。

### 7.4 必须先决定的持久化问题

当前 SQLite 同时承担派生索引和运行态用户状态。排除它后，GitHub Actions 下一次运行如何恢复状态必须明确。

#### 方案 A：每次从公共 JSON 重建派生 SQLite

最简单、最安全。周报项目数据仍可恢复，但用户反馈、订阅、任务和通知状态不会跨 Actions 保存。

适合：当前没有真实持久用户状态，先快速关闭公开风险。

代价：有状态功能在自动任务间不能延续。

#### 方案 B：把运行态 SQLite 放到私有持久化位置

保留全部状态，但需要私有仓库、受控对象存储或数据库服务，并新增凭据、备份和恢复运维。

适合：已经有真实订阅、反馈或任务需要长期保存。

代价：复杂度和维护成本更高。

#### 方案 C：继续公开完整 SQLite，仅尝试删除敏感表

不推荐。表结构会继续增长，导出遗漏很难被发现，历史版本仍可能保留旧数据。

默认建议：先只读确认真实运行态表是否为空。若为空，采用方案 A 作为安全过渡；若存在需要保留的真实状态，停止写入并用通俗语言向用户解释 A/B 的影响，等待选择，不擅自丢数据。

### 7.5 必须新增的测试

- allowlist 中的公共 docs、reports 和已批准 JSON 能发布；
- `github_weekly.sqlite`、`-wal`、`-shm` 永远不进入 staging tree；
- 未知文件和隐藏文件默认拒绝；
- 植入测试口令、query canary 和 note canary 后，staged tree 扫描必须失败或排除；
- 旧归档 worktree 中预置 SQLite 时，新发布必须把它删除并暂存删除；
- symlink 指向工作区外时拒绝；
- dry-run 输出只含相对路径和计数，不回显敏感内容；
- workflow 恢复步骤不再把公开分支的原始 SQLite 当私有状态源；
- 不改变周报生成、Pages 文件、Ask 契约和真实外发确认机制。

### 7.6 P0-11A 验收

- `weekly-archive` 最新 tree 不含 `*.sqlite*`；
- 测试 canary 不出现在复制目录、Git index、日志或失败产物；
- 公开报告、Pages 和项目 JSON 仍可使用；
- 运行态持久化策略已写入 README、架构和数据契约；
- 远端历史是否清理被单独记录，不在本阶段静默 force-push；
- 本地 `data/github_weekly.sqlite` 内容和本机归档不被测试修改；
- 完整本地验证与远端三个 CI job 全绿；
- `tmp/` 不进入提交。

## 8. 后续 P0-11B：安全流式输出

P0-11A 稳定后执行：

1. 使用本地假 Kimi HTTP/SSE provider，不调用业务 Kimi。
2. 服务端完整缓冲 provider 输出。
3. 对原始答案执行策略、引用和质量检查；禁止先自动补引用再判通过。
4. 通过后按现有 `meta → delta* → final` 事件顺序重新切片发送。
5. 恶意或不合格 provider 文本不得出现在任何 SSE frame、DOM、console 或 localStorage。
6. 保持普通 POST 与 SSE final 等值，不改变已有字段和事件名。

该阶段的代价是首个可见 token 延迟增加。安全性优先于“看起来立即开始输出”。

## 9. 后续 P0-12：顶层意图与结构化比较

新增非破坏性决策结构，至少分离：

```text
conversation_relation
answer_type
retrieval_scope
retrieval_query
resolved_user_request
evidence_policy
```

`answer_type` 至少支持：

```text
search
explain
compare
learning_plan
clarify
unsupported
```

保持无状态：浏览器只提交上一轮用户目标、候选 ID、确认首选、mode 和 resumable；不提交历史 assistant answer、citations、evidence 或 `prompt_context`。

## 10. 关键代码地图

| 路径 | 职责 |
| --- | --- |
| `scripts/publish_archive_branch.py` | 归档 worktree、复制、提交和推送 |
| `.github/workflows/weekly.yml` | 周报、历史恢复、RAG 维护和归档发布 |
| `src/archive.py` | JSON 归档与 SQLite 索引同步 |
| `src/storage/schema.sql` | SQLite 数据契约源 |
| `src/storage/sqlite_store.py` | 初始化、迁移和导入 |
| `src/rag/answering.py` | Ask 普通/流式回答、质量降级 |
| `src/rag/answer_quality.py` | 当前引用格式质量闸门 |
| `src/rag/follow_up_router.py` | 无状态追问与约束路由 |
| `src/api/repository.py` | API 业务聚合；当前 8,219 行，改动回归面大 |
| `frontend/src/pages/AgentPage.tsx` | POST/SSE、最小上下文和本地会话 |
| `e2e/` | mock 浏览器回归 |
| `e2e-real/` | 真实 FastAPI + 临时 SQLite 回归 |
| `evals/` | 固定项目、追问和约束回归样本 |

## 11. 不可突破的边界

1. 不硬编码、输出或要求用户粘贴 API Key、Token、Chat ID、Webhook、Cookie、管理口令。
2. Prompt 只放 `prompts/`。
3. 外部 README、HTML 和仓库文本是不可信输入，不能当系统指令。
4. Kimi enrichment 只能补充理由，不能让 unknown/rejected 变为 eligible。
5. 不新增服务端聊天会话，不把历史 assistant 回答当证据。
6. 不破坏 `/v1/rag/ask`、`/v1/rag/ask/stream` 或 SSE 事件顺序。
7. 真实外发必须显式确认；本地测试不得发送 Telegram、飞书、企业微信。
8. 不修改本机现有 SQLite；归档和数据库测试只用临时目录。
9. 新增 SQLite 表或字段时同步修改：
   - `src/storage/schema.sql`
   - `src/storage/sqlite_store.py`
   - `docs/data-contracts.md`
   - `tests/test_data_contracts.py`
10. 稳定改动先在 `docs/operation-log.md` 顶部记录，再验证、提交、推送。
11. 只暂存本阶段文件；`tmp/` 永远排除。
12. 不启用分支保护是已接受风险，不要把它重复包装成当前待办。

## 12. 环境变量

复用现有 Kimi 配置，但 P0-11A 不应调用 Kimi：

```text
KIMI_API_KEY
KIMI_BASE_URL
KIMI_MODEL
KIMI_TIMEOUT_SECONDS
KIMI_MAX_RETRIES
KIMI_RETRY_SECONDS
```

管理接口使用：

```text
ADMIN_API_TOKEN
```

只检查变量是否配置，不输出值。CI 和 E2E 不读取业务 Secrets。

## 13. 本地运行

后端：

```powershell
cd "C:\Users\Administrator\Documents\New project 3"
py -m uvicorn src.api.app:app --reload
```

React 开发服务器：

```powershell
cd "C:\Users\Administrator\Documents\New project 3"
npm.cmd run dev
```

PowerShell 若阻止 `npm.ps1`，使用 `npm.cmd`，不要修改系统执行策略。

## 14. 完整验证

每个稳定阶段运行：

```powershell
cd "C:\Users\Administrator\Documents\New project 3"
npm.cmd run lint
npm.cmd run test
npm.cmd run build
npm.cmd run test:e2e
npm.cmd run test:e2e:real
python -m unittest discover -q
python scripts\evaluate_project_match.py
python scripts\evaluate_project_recommendations.py
python scripts\evaluate_follow_up_routing.py
python scripts\evaluate_constraint_parsing.py
python scripts\security_check.py
git diff --check
git diff --exit-code -- docs/app
git status --short --branch
```

P0-11A 还要增加：

- 临时 archive worktree staged tree 审计；
- 敏感 canary 排除测试；
- 旧 SQLite 删除测试；
- 发布 dry-run 测试；
- 本机 SQLite 和归档文件修改前后哈希一致性。

## 15. Git 与提交

不要使用 Bash heredoc、`&&` 或把 PowerShell 路径枚举结果交给另一 shell 删除。

使用 `apply_patch` 做手动文件修改。提交前：

```powershell
cd "C:\Users\Administrator\Documents\New project 3"
git status --short --branch
git diff --check
git diff --cached --name-only
```

只暂存明确文件：

```powershell
git add <changed-files>
git commit -m "<type>: <summary>"
git push origin main
```

推送后检查远端核心、mock Playwright、真实 FastAPI Playwright。不要把 `tmp/`、本地 SQLite、下载的远端数据库或测试输出加入提交。

## 16. 可直接粘贴到新 Codex 窗口的启动提示

```text
继续开发 C:\Users\Administrator\Documents\New project 3，默认中文沟通。

先按顺序阅读：
1. AGENTS.md
2. docs/project-review-agent-v3-handoff.md
3. docs/project-review-agent-v3-roadmap.md
4. README.md
5. docs/api.md
6. docs/data-contracts.md
7. docs/architecture.md
8. docs/operation-log.md 顶部近期记录
9. docs/command-line-and-coding-standards.md
10. scripts/publish_archive_branch.py
11. .github/workflows/weekly.yml
12. src/archive.py
13. src/storage/schema.sql

当前分支 main，确认 HEAD 与 origin/main 一致，并确认历史包含 4d5c1a0 及最新 V3 交接提交。工作区预期仅有未跟踪 tmp/；不要提交 tmp/，不要覆盖或回退用户已有改动。

下一阶段先做 P0-11A：公共归档白名单与运行态持久化边界。当前 scripts/publish_archive_branch.py 会整包复制 docs、reports、data；公开 weekly-archive 已确认跟踪 data/github_weekly.sqlite。先只读审计 data/ 文件和远端归档，严格区分已确认公开、需要脱敏、明确私有和未知；未知默认不发布。不要查看、输出或保存完整敏感 query、note、token、payload。

发布器必须使用显式 allowlist，清理旧目标并暂存删除，拒绝 SQLite/WAL/SHM、用户状态、未知文件、symlink 和路径穿越。测试要证明旧归档中的 SQLite 会从最新 tree 删除、敏感 canary 不进入 staging/log、公共 Pages/报告仍可用。不要在本阶段擅自重写 weekly-archive Git 历史。

先确认运行态表是否有必须保留的真实数据：若为空，优先从公共 JSON 每次重建派生 SQLite；若有真实订阅/反馈/任务需要跨 Actions 保存，先向我用通俗语言解释“无状态重建”和“私有持久化”两种方案的影响，等待选择，不擅自丢数据。

已知本地 Git full fsck 有一个不在可达历史中的损坏 loose object 0d5add93193596c7597490811fc0cd23952335aa。connectivity-only fsck 通过，但 fetch 曾失败。不要直接删除对象或强制清理；需要修复时先备份并单独说明。

保持 Ask/SSE 契约、无状态追问、硬约束、管理鉴权和真实外发确认不变。不迁移 Responses API/Agents SDK，不调整 hybrid 权重，不新增服务端会话，不把历史 assistant 回答当证据。

稳定改动先更新 docs/operation-log.md 顶部，再运行前端 lint/test/build、两套 Playwright、Python 全量、四个评估脚本、安全检查、git diff --check 和 docs/app 一致性检查。只暂存本阶段文件，提交并推送 main，核验远端三个 CI job。
```

## 17. 立即下一步

新窗口第一项实际工作不是直接改发布脚本，而是生成一份**归档文件分类与运行态表非敏感统计**：

```text
data/ 文件 → public / redact / private / unknown
SQLite 表 → count / max date / sensitive-field presence（不输出内容）
weekly-archive 最新 tree → 是否含 sqlite / wal / shm / 未分类状态文件
```

完成该只读清单后，再确认采用“公共 JSON 重建”还是“私有运行态持久化”。这个选择决定 P0-11A 的正确实现，不能靠猜测。
