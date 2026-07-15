# GitHub 项目研究 Agent V4 下一阶段开发交接报告

交接日期：2026-07-15

当前分支：`main`

功能基线：`63712587bc1f9a2348653218c7c477702488b1f1 docs: add project review agent v4 roadmap`

基线远端验证：GitHub Actions run `29412784296` 已完成，核心质量检查、Playwright mock 浏览器回归和 Playwright 真实 FastAPI 回归全部成功。新窗口仍必须以 GitHub 当前 run 为准重新核对。本文提交会位于功能基线之后，因此不要把 `6371258` 当成交接完成后的最终 HEAD。

## 1. 一句话交接

下一阶段先完成 V4 路线图 **P0-14：统一公共归档 manifest，并在 push 前验证完整 staged tree**，关闭“源文件来自 allowlist，但归档分支最终 tree 仍可能残留未知旧文件”的绕过路径。

这里的“P0-14”是 V4 路线图中的正式编号。它也是当前阶段排在第一位的 P0；后续交流统一使用 `P0-14`，避免与历史报告里的 `P0-1`、`P0-11A` 混淆。

## 2. 当前已确认状态

### 2.1 Git 与工作区

文档编写前已确认：

```text
branch = main
HEAD = 63712587bc1f9a2348653218c7c477702488b1f1
origin/main = 63712587bc1f9a2348653218c7c477702488b1f1
tracked modifications = 0
untracked = output/、tmp/
```

`output/` 和 `tmp/` 属于受保护的本地诊断/临时区域。新窗口不得读取其业务内容，不得删除、覆盖、暂存或发布；提交前必须再次确认它们没有进入 index。

### 2.2 已完成的相关安全阶段

- P0-11A 已将公开归档与运行态 SQLite 分开，发布器改为公共源 allowlist，并使用 `git add -A` 暂存旧文件删除。
- P0-11B 已修复未经校验的 provider delta 先展示：服务端完整缓冲并通过当前基础闸门后，才按既有 `meta → delta* → final` 顺序发送。
- P0-11C 已为公共 JSON 建立字段级投影，避免直接复制 query、note、payload、错误详情和投递结果等运行态字段。
- P0-13 已通过受控修复 workflow 清理远端最新 `weekly-archive` tree，并完成远端 tree attestation；这不等于 Git 历史已被重写。
- 历史数据库脱敏结构扫描已完成。用户已确认历史归档不存在真实用户信息、真实 token 或真实通知地址，因此当前不执行历史重写、缓存清理、凭据轮换或用户通知。
- V4 对抗性审查与三角色只读审查协议已经落库，当前优先级以 V4 路线图为准。

### 2.3 当前不能过度解释的事实

- 当前远端最新 tree 已知安全，不代表发布器未来不可能把未知旧路径先 push 上去。P0-14 修的是未来发布闭环。
- `answer_quality.passed=true` 仍主要证明当前基础格式、引用和安全闸门通过，不证明每条主张都由证据支持，也不证明数据足够新。
- 固定评估通过只证明公开 fixture 的确定性回归，没有证明真实用户自然语言、真实 provider 或独立 blind 集已经校准。
- GitHub CI 当前是 push 后报警，不是 main 合并前保护；在启用 required checks 和分支保护前，不得表述为“坏提交不能进入 main”。

## 3. 新窗口必读文档与顺序

不要一上来全仓搜索或直接改代码。按以下顺序阅读，前一组决定后一组应如何解释。

### 第一组：规则、交接和最新结论

1. `AGENTS.md`
   - 当前项目的写入、敏感信息、Ask/SSE、运行态、完整验证和 Git 边界。
2. `docs/project-review-agent-v4-handoff.md`
   - 本交接包；当前基线、第一任务、文件地图和验收方式。
3. `docs/project-review-agent-v4-roadmap.md`
   - V4 的第一性原理审查、最大遗漏、P0-14 至 P2 的顺序和阶段验收。
4. `docs/multi-agent-review-protocol.md`
   - 只有需要独立只读复核时才启用多 Agent；主 Agent 始终是唯一写入者。
5. `README.md`
   - 当前产品能力、运行入口、公开归档说明和文档入口。
6. `docs/operation-log.md` 顶部近期记录
   - 只先读 2026-07-15 的近期阶段；不要从文件尾部旧记录推断当前实现。

### 第二组：接口、数据和架构契约

7. `docs/api.md`
   - `/v1/rag/ask`、`/v1/rag/ask/stream`、管理鉴权和写入确认契约。
8. `docs/data-contracts.md`
   - 公共 JSON 投影、SQLite 派生索引和私有运行态边界。
9. `docs/architecture.md`
   - 周报、归档、FastAPI、RAG、React、任务、通知和 CI 数据流。
10. `docs/archive-history-audit-protocol.md`
    - 历史归档只读取证边界；P0-14 不重新执行结构扫描。
11. `docs/command-line-and-coding-standards.md`
    - PowerShell、编码、路径和项目命令规范。

### 第三组：P0-14 直接相关实现

12. `scripts/publish_archive_branch.py`
    - 当前源选择、归档 worktree 同步、staged tree 扫描、commit/push 顺序。
13. `scripts/audit_public_archive.py`
    - 当前远端 latest/history 路径 attestation。项目中不存在 `scripts/verify_remote_archive.py`；不要按旧建议虚构该文件。
14. `src/public_archive.py`
    - 公共 JSON 字段级投影和公共数据字段边界。
15. `.github/workflows/weekly.yml`
    - 正常周报发布、发布器调用和 push 后远端 attestation。
16. `.github/workflows/archive-remediation.yml`
    - 仅公开归档修复发布通道；不采集、不调用 Kimi、不外发。
17. `tests/test_workflows.py`
    - 发布器临时 worktree、workflow 顺序、SQLite 清理、canary 和未知文件测试。
18. `tests/test_audit_public_archive.py`
    - 远端 tree/history 路径审计测试。
19. `tests/test_public_archive.py`（如存在）以及 `tests/test_archive.py`
    - 公共字段投影与归档事实来源回归；先用 `rg --files tests` 确认实际文件名。
20. `src/storage/schema.sql`
    - 只用于确认“公开派生数据”和“私有运行态”分类；P0-14 不需要修改 schema。

## 4. 新窗口首先执行的命令

使用 PowerShell，从只读基线核验开始：

```powershell
cd "C:\Users\Administrator\Documents\New project 3"
git status --short --branch
git log -6 --oneline
git rev-parse HEAD
git rev-parse origin/main
git fsck --connectivity-only --no-dangling --no-reflogs
rg --files config scripts tests .github docs src | Sort-Object
```

预期：

- 当前分支是 `main`；
- `HEAD` 与 `origin/main` 一致，并包含 `6371258` 和最新 V4 交接提交；
- 除 `output/`、`tmp/` 外没有用户已有修改；
- connectivity-only fsck 通过；
- 当前没有统一公共归档 manifest，下一阶段将新增；
- 当前远端验证脚本名是 `scripts/audit_public_archive.py`。

如果工作区出现其他修改，先执行：

```powershell
git diff -- <file>
git diff --cached -- <file>
```

确认归属后再继续。不得覆盖、删除、回退或顺手暂存用户已有改动。

## 5. 已知 Git 对象问题

本地存在一个不在可达历史中的损坏 loose object：

```text
0d5add93193596c7597490811fc0cd23952335aa
```

已知边界：

- connectivity-only fsck 通过；
- full fsck 会报告该不可达损坏对象；
- 它曾导致 fetch 失败；
- 不得直接删除对象、运行强制 prune、`git gc --prune=now`、hard reset 或强制清理；
- 如确需修复，必须另开任务，先备份 `.git` 和目标对象，再说明恢复路径并取得授权。

P0-14 不以修复该对象为前置条件，也不得顺手处理它。

## 6. P0-14 为什么必须先做

当前发布器已经“从 main 选择允许公开的文件”，但还没有“证明归档分支最终准备 push 的完整 Git tree 只包含这些文件”。

直白地说：

```text
main 中本轮复制的文件很干净
≠
weekly-archive 旧分支里没有别的历史残留文件
```

当前 `_synchronize_archive_tree()` 只重建：

```text
docs/
reports/
data/
```

如果 `weekly-archive` 根目录或其他旧目录曾经存在：

```text
legacy/private.db
backup/.env
old/debug.log
unknown-root-file
```

它们不一定会被当前同步步骤删除。`_scan_staged_tree()` 虽然扫描完整 index，但路径规则主要拒绝 SQLite 形式，并没有逐项证明“每个 staged path 都属于公共 allowlist”。因此未知旧文件可能先被 commit/push，随后远端审计才发现失败。

P0-14 要把这个顺序改成：

```text
读取统一 manifest
→ 生成本轮期望公共路径集合
→ 清理或拒绝全部额外 tracked path
→ git add -A
→ 对完整 staged tree 做精确集合校验
→ 内容与禁止后缀扫描
→ 允许 commit/push
→ 远端 latest tree 用同一 manifest 再证明一次
```

## 7. P0-14 决策完成的实施方案

### 7.1 单一版本化 manifest

建议新增：

```text
config/public-archive-manifest.json
```

并增加一个只负责解析、校验和匹配规则的小模块，例如：

```text
src/public_archive_manifest.py
```

不要同时在 Python 常量、workflow、测试和 Markdown 中维护四套独立规则。manifest 至少应表达：

- `schema_version`；
- 精确允许的公共文档路径；
- 允许递归的公共子树及其后缀；
- 显式禁止的文件名/后缀；
- 明确私有的运行态类别；
- 是否允许 symlink（本项目固定为否）；
- 归档根级允许文件（如无必要则为空）。

第一版 schema 保持小而确定，不要加入可执行表达式、正则脚本或任意 glob 解释器。加载失败、未知 schema、重复规则、相互冲突规则都应 fail closed。

### 7.2 期望路径集合是最终判定依据

发布器从 manifest 选择源文件后，生成本轮 `expected_paths`。执行 `git add -A` 后读取：

```powershell
git ls-files --cached -z
```

得到 `staged_paths`，要求：

```text
staged_paths == expected_paths
```

任何额外 path、缺失 path、未知 path 或禁止后缀都必须在 commit/push 前失败。若保留少量归档元数据文件，也必须显式属于 manifest 和 `expected_paths`，不能写隐式例外。

### 7.3 清理旧 tree

不要只删除 `docs/reports/data`。应在临时归档 worktree 内枚举 tracked path，并按 manifest/`expected_paths` 删除全部不应存在的旧路径；随后 `git add -A`，让删除进入最终 index。

清理必须满足：

- 只作用于临时 archive worktree；
- 不跟随 symlink；
- 所有 resolve 后路径仍位于 worktree；
- 不读取、打印或复制被删除文件的业务内容；
- 任何路径穿越、绝对路径、`.`/`..` 或非法编码直接失败；
- 删除结果仍由完整 staged tree 集合校验兜底。

### 7.4 明确禁止类别

即使未来有人错误扩大 allowlist，下列类别仍应无条件拒绝：

```text
.sqlite
.sqlite3
.db
.db3
-wal
-shm
.env
.pem
.key
.log
```

同时保留现有敏感 canary 和凭据模式扫描，但不要把内容正则当成路径 allowlist 的替代品。

`.map` 当前仍在 `PUBLIC_APP_SUFFIXES` 中；V4 将移除生产 source map 列为 P2。P0-14 实施时可把它从 manifest 排除，但必须先验证生产 Pages 不依赖 `.map`，并增加测试，不能只凭偏好删除。

`reports/**/*.md` 当前范围偏宽。P0-14 至少要让它受 manifest 驱动；如果本阶段缩小为明确周报/报告路径，需要先枚举当前 Pages 所需报告并补回归，避免破坏公开入口。

### 7.5 远端 attestation 复用同一 manifest

当前远端验证实现是 `scripts/audit_public_archive.py`。它应复用同一 manifest 判断 latest tree，而不是维护另一份后缀 denylist。

发布顺序必须保持：

```text
本地 staged 完整校验成功
→ commit/push
→ 远端 latest tree attestation
```

P0-14 的关键是让危险文件在 push 前被阻止；push 后 attestation 是独立复核，不是第一道防线。

### 7.6 文档同步

实现稳定后至少检查并按实际变化同步：

- `AGENTS.md`：公共归档修改规则和 manifest 单一来源；
- `README.md`：只发布 manifest 允许的公共投影；
- `docs/data-contracts.md`：manifest schema、公共/私有边界；
- `docs/architecture.md`：选择、staging、pre-push、remote attestation 数据流；
- `docs/operation-log.md`：实际变更、验证和未验证项；
- `docs/api.md`：仅当公共 API 字段发生变化时修改，不做无关文档重写。

## 8. P0-14 必须增加的测试

### 8.1 manifest 单元测试

- schema version 支持/拒绝；
- 未知字段或冲突规则 fail closed；
- 精确路径和允许子树匹配；
- 大小写、反斜杠、绝对路径、`.`、`..`、空路径拒绝；
- symlink 拒绝；
- manifest 与选择器规则没有第二套常量漂移。

### 8.2 临时归档 worktree 回归

在测试归档分支预先植入：

```text
legacy/private.db
legacy/private.sqlite3
legacy/private.db3
backup/.env
backup/private.pem
backup/private.key
old/debug.log
old/harmless-unknown.txt
docs/app/source.js.map
```

验证：

- 旧未知路径在 commit/push 前被删除，或发布器安全失败；
- 失败时不会调用 commit/push；
- SQLite/WAL/SHM、环境文件、密钥文件、日志和未知路径不在最终 index；
- 公共 Pages、周报、报告和四类公共 JSON 仍在最终 index；
- 已允许路径中的敏感 canary 仍会 fail closed；
- canary 原文不进入报告、日志或异常消息；
- 旧 tree 删除使用 `git add -A` 正确暂存。

### 8.3 本地与远端规则一致性

- 对同一 synthetic tree，本地 staged validator 和远端 auditor 得到相同结论；
- manifest 变更会同时影响选择器、staged validator、auditor 和测试；
- workflow 中 publish 在 audit 之前，且 publish 内部 pre-push validation 在 commit/push 之前；
- remote latest tree 的未知路径和禁止后缀计数均为 0。

### 8.4 不应发生的测试行为

- 不读取本机 `data/github_weekly.sqlite`；
- 不下载历史 SQLite blob；
- 不调用真实 GitHub、Kimi、Telegram、飞书、企业微信或其他外部网络；
- 不将测试数据库、canary、Playwright 输出或临时 worktree 放入提交；
- 不依赖本机现有 `tmp/` 或 `output/`。

## 9. 绝对不能改变的产品契约

P0-14 是归档发布边界修复，不是产品功能重构。保持以下契约不变：

- `/v1/rag/ask` 和 `/v1/rag/ask/stream` 既有字段兼容；
- SSE 顺序继续为 `meta → delta* → final`；
- 追问继续无状态，不新增服务端聊天会话；
- 浏览器不提交历史 assistant 回答、引用、证据或 `prompt_context`；
- 硬约束、候选范围和 `model_enrichment` 权限不变；
- 管理写入继续要求鉴权和显式确认；
- 真实 Telegram、通知和其他外发不自动执行；
- 不迁移 Responses API 或 Agents SDK；
- 不调整 hybrid 权重、不替换 embedding 模型；
- 不新增 SQLite 表或修改 schema；
- 不把历史 assistant 回答当证据。

如果实现过程中发现必须突破任一边界，停止编码，说明为何 P0-14 无法在既有范围内完成，再请求用户决定。

## 10. 多 Agent 使用规则

默认由主 Agent 单线程实施。只有用户明确要求多 Agent，或确有两个以上相互独立的只读问题时，才按 `docs/multi-agent-review-protocol.md` 启动最多三个只读角色。

可选的只读拆分：

- code-explorer：只读 `publish_archive_branch.py`、manifest loader 和调用链；
- reviewer：只读路径边界、symlink、staged/push 顺序和 fail-closed 行为；
- test-analyst：只读测试、workflow 和远端 attestation 覆盖。

主 Agent 是唯一写入、测试执行、提交、推送和远端操作责任人。子 Agent 禁止读取 `tmp/`、`output/`、`.git/`、环境变量、运行态数据库和真实历史 blob。

## 11. 实施顺序

严格按以下顺序推进：

1. 只读核对 HEAD、工作区、现有发布器、auditor、workflow 和测试。
2. 在 `docs/operation-log.md` 顶部记录 P0-14 开始、范围和边界。
3. 冻结当前公开 Pages/报告/JSON 必需路径清单。
4. 新增版本化 manifest 与严格 loader。
5. 让源选择器读取 manifest，删除重复常量。
6. 清理所有不属于本轮期望集合的旧 tracked path。
7. `git add -A` 后验证完整 staged tree 与 `expected_paths` 精确一致。
8. 让 `audit_public_archive.py` 复用同一 manifest。
9. 增加 manifest、旧 tree、禁止后缀、canary、无 push 和规则一致性测试。
10. 同步 README、架构、数据契约、操作日志和必要的 AGENTS 规则。
11. 运行最小测试，定位失败后再运行完整基线。
12. 只暂存 P0-14 文件，确认 `tmp/`、`output/` 未进入 index。
13. 提交并 push `main`，核验远端三个 CI job。
14. 三项 CI 全部成功后关闭 P0-14，再进入 P0-15。

## 12. 本地完整验证

在项目根目录使用 PowerShell，普通评估只使用固定 fixture 或临时 SQLite，不接入真实外部网络：

```powershell
npm run lint
npm run test
npm run build
npm run test:e2e
npm run test:e2e:real
python -m unittest discover -q
python scripts\security_check.py
python scripts\evaluate_project_match.py
python scripts\evaluate_project_recommendations.py
python scripts\evaluate_follow_up_routing.py
python scripts\evaluate_constraint_parsing.py
git diff --check
git diff --exit-code -- docs/app
git status --short --branch
```

如果任一 P0-1/P0-4/P0-5 固定指标下降，停止提交，先定位原因。不得用“测试脚本存在”代替“命令已经成功执行”。

提交前额外检查：

```powershell
git diff --name-only
git diff --cached --name-only
git status --short
```

暂存列表只能包含 P0-14 明确修改文件，不得包含：

```text
tmp/
output/
data/github_weekly.sqlite
任何 .env、token、日志、测试数据库或真实历史 blob
```

## 13. 远端提交与验证闭环

稳定改动完成后：

```powershell
git add <本阶段明确文件>
git diff --cached --check
git diff --cached --name-only
git commit -m "fix: enforce public archive manifest"
git push origin main
```

然后核验与新提交 SHA 关联的三个 CI job：

```text
核心质量检查
Playwright mock 浏览器回归
Playwright 真实 FastAPI 回归
```

验收记录至少包含：

- main commit SHA；
- GitHub Actions run ID；
- 三个 job 的结论；
- staged tree manifest 测试结论；
- 远端 latest tree attestation 结论；
- Pages/报告是否仍可用；
- 未验证项和残余风险。

“已 push”不能写成“远端验证通过”。只有三项 job 成功并取得远端 attestation 证据，P0-14 才算关闭。

## 14. P0-14 完成定义

必须同时满足：

1. 一个 schema-versioned manifest 成为公共归档路径规则的单一来源；
2. 源选择、完整 staged tree 校验、测试和远端 auditor 复用该 manifest；
3. `staged_paths == expected_paths`，未知路径和禁止后缀数量为 0；
4. 旧根目录和未知目录文件在 commit/push 前被删除或导致安全失败；
5. SQLite/WAL/SHM、用户状态、未知文件、symlink 和路径穿越被拒绝；
6. 敏感 canary 不进入 staging、日志、异常或报告；
7. 公共 Pages、周报、报告和公共 JSON 仍然可用；
8. 不改写历史、不触碰真实运行态数据库、不真实外发；
9. 完整本地基线通过，`docs/app` 一致；
10. 新提交远端三个 CI job 成功，remote attestation 成功。

未同时满足以上条件时，不进入 P0-15。

## 15. P0-14 之后的顺序

```text
P0-14 最终 staged tree 统一 manifest
→ P0-15 评估阈值与 CI 门禁
→ P0-16 真实主张支持闸门
→ P0-17 数据新鲜度门禁
→ P0-18 项目级能力作用域
→ P1 顶层回答决策、私有决策快照、管理读边界和独立验证
```

不要提前调整 hybrid 权重、迁移 Agent 框架或建立反馈自动调权。当前先证明公开边界是封闭的，再把质量指标变成真正会失败的门禁。

## 16. 可直接复制到新窗口的启动提示

```text
继续开发 C:\Users\Administrator\Documents\New project 3，默认中文沟通。

先按顺序阅读：
1. AGENTS.md
2. docs/project-review-agent-v4-handoff.md
3. docs/project-review-agent-v4-roadmap.md
4. docs/multi-agent-review-protocol.md
5. README.md
6. docs/operation-log.md 顶部近期记录
7. docs/api.md
8. docs/data-contracts.md
9. docs/architecture.md
10. docs/archive-history-audit-protocol.md
11. docs/command-line-and-coding-standards.md
12. scripts/publish_archive_branch.py
13. scripts/audit_public_archive.py
14. src/public_archive.py
15. .github/workflows/weekly.yml
16. .github/workflows/archive-remediation.yml
17. tests/test_workflows.py
18. tests/test_audit_public_archive.py
19. src/storage/schema.sql

先只读确认当前分支、HEAD、origin/main、最近提交、工作区和 connectivity-only fsck。功能基线为 63712587bc1f9a2348653218c7c477702488b1f1，交接提交会位于其后，以当前 git log 为准。工作区预期仅有未跟踪 output/、tmp/；不要读取、修改、删除、暂存或发布它们，不要覆盖或回退用户已有改动。

第一任务是 V4 P0-14：新增 schema-versioned 公共归档 manifest，让源选择、完整 staged tree push 前校验、测试和 scripts/audit_public_archive.py 复用同一规则。git add -A 后必须证明 staged path 集合与本轮 expected public projection 精确一致；未知路径默认拒绝，并显式拒绝 SQLite/SQLite3/DB/DB3/WAL/SHM、.env、PEM、key、log、symlink 和路径穿越。测试要证明归档根目录和未知旧目录遗留在 commit/push 前被删除或安全失败，失败时不调用 push，敏感 canary 不进入 staging/log，同时公共 Pages、周报、报告和四类公共 JSON 仍可用。

本阶段不重新扫描历史数据库，不改写 weekly-archive 历史，不处理损坏 loose object 0d5add93193596c7597490811fc0cd23952335aa，不读取本机运行态 SQLite，不迁移 Responses API/Agents SDK，不调整 hybrid 权重，不新增服务端会话或 schema，不改变 Ask/SSE 字段、meta → delta* → final、无状态追问、硬约束、管理鉴权和真实外发确认。

稳定改动先更新 docs/operation-log.md 顶部，再运行前端 lint/test/build、两套 Playwright、Python 全量、安全检查、四套评估、git diff --check 和 docs/app 一致性。只暂存 P0-14 文件，排除 output/、tmp/，提交并 push main，核验远端核心质量、mock Playwright 和真实 FastAPI Playwright 三项 job；三项成功并取得远端 latest tree attestation 后才进入 P0-15。
```

新窗口的第一个实际动作：执行第 4 节只读命令并对照预期；基线一致后，先冻结当前必要公共路径清单，再设计 manifest schema，不要直接重写发布器。
