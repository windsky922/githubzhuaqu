# GitHub 项目研究 Agent V6 下一阶段开发交接报告

交接日期：2026-08-02
工作目录：`C:\Users\Administrator\Documents\New project 3`
功能基线：`d638dae32d20bf73a0153576e45adbef38c89d64`（`main` 与 `origin/main` 一致）
文档状态：V6 审查、操作日志和本交接尚未提交；它们不是新的代码基线。

## 1. 目标与顺序

下一阶段只修产品主链，不增加订阅、任务、模型或管理功能：

1. P0-1：历史只读证据核验。
2. P0-2：恢复全量 CI，并建立 main 的有效保护。
3. P1：统一 freshness 契约，消除 JSON 回退共享状态。

完整证据、风险和验收见 [V6 审查与路线图](project-review-agent-v6-roadmap.md)。

## 2. 必读顺序

1. `AGENTS.md`
2. 本文
3. `docs/project-review-agent-v6-roadmap.md`
4. `README.md`
5. `docs/operation-log.md` 顶部
6. `docs/api.md`、`docs/data-contracts.md`、`docs/architecture.md`
7. `src/rag/data_source.py`、`src/rag/freshness.py`、`src/api/repository.py`
8. `src/rag/constraint_verifier.py`、`src/rag/follow_up_router.py`、`src/rag/project_recommendations.py`、`src/rag/answering.py`
9. `frontend/src/pages/AgentPage.tsx`、`frontend/src/components/AgentWorkspace.tsx`、`frontend/src/components/ProjectCard.tsx`
10. `tests/test_contextual_ask.py`、`tests/test_p1_data_trust.py`、`tests/test_constraint_parsing_eval.py`、`tests/test_follow_up_eval.py`
11. `.github/workflows/ci.yml`、`.github/workflows/weekly.yml`

旧 V4/V5 文档只用于历史取证，不覆盖 V6 结论。

## 3. 已确认状态

- 生产只接受显式 `GITHUB_WEEKLY_SNAPSHOT_ROOT` 的 verified weekly snapshot；缺失时 fail closed，不回退 checkout 数据。
- `GITHUB_WEEKLY_DATA_MODE=local` 时，本机只读 SQLite；不可读或缺失时回退 JSON。
- 30 天内 verified snapshot 才能作当前结论；历史候选永不为当前首选。
- 自然语言条件默认偏好；只有“必须、仅、不得、排除、不能接受、只要、必须满足”等明确表达才是硬约束。
- `multi_agent`、`preferences[]`、来源/日期/当前资格字段已接入 Ask/SSE 和前端。
- unknown 不应澄清；仅全部明确硬冲突才 `no_match`。
- 已通过定向 Python 测试、前端 lint/test、`git diff --check` 和 `docs/app` 一致性检查。

## 4. P0-1：历史只读核验

### 原始证据

`src/api/repository.py:1781-1787` 在 `local_read_only` 时将 `requirement_verification` 设为空。

### 后果

历史候选无法基于已有证据标记满足，也不能因明确冲突标记 `rejected`。这破坏“历史数据可回答、硬冲突淘汰、但历史绝不伪装当前推荐”的需求。

### 实施边界

可修改：

- `src/api/repository.py`
- `src/rag/constraint_verifier.py`
- 必要时小型纯只读 helper
- `tests/test_contextual_ask.py`、`tests/test_p1_data_trust.py`

禁止：

- 写入、回填或迁移 `data/github_weekly.sqlite`
- 改写 JSON、运行记录、解释或查询审计
- 把历史候选升级为 current/top pick
- 用模型单独判断 unknown/rejected

### 验收

1. SQLite：有冲突证据的“不得依赖外部 API”候选为 `rejected`。
2. JSON：获得等价结果。
3. 有证据的 Python/self-hosted/multi-agent 偏好为 `matched`；无证据仅为 `unknown`，不阻塞候选。
4. 服务运行前后 SQLite 文件哈希和 JSON 内容不变。
5. 生产缺 verified snapshot 仍拒答。

## 5. P0-2：CI 与 main 治理

GitHub Actions `30737083119` 失败，涉及：

- `tests/test_constraint_parsing_eval.py`
- `tests/test_follow_up_eval.py`
- `tests/test_follow_up_router.py`

根因：固定 fixture/测试仍把普通条件预期为 `hard=true`，与“默认偏好”实现冲突。main branch protection API 返回 `404 Branch not protected`。

执行顺序：

1. 修正 fixture、测试和 evaluator 的旧 hard 预期。
2. 保留显式强制词的 hard=true 断言。
3. 不通过降低阈值掩盖语义回归。
4. 跑完整验证并推送。
5. 有仓库管理权限者单独确认后，为 main 配置 required checks。

验收：`python -m unittest discover -q`、固定评估和 CI job 全绿；main 无法绕过失败 required checks。

## 6. P1

- `docs/data-contracts.md:9` 写 freshness 30 天，`:29` 仍为 8 天。统一为单一 30 天事实来源。
- `src/api/repository.py:1076-1083` 临时替换 `self.root` 读取 JSON；并发请求可能串根。把 root 作为显式参数，禁止改写共享实例状态。

## 7. 本地启动

```powershell
Set-Location "C:\Users\Administrator\Documents\New project 3"
$env:GITHUB_WEEKLY_DATA_MODE = "local"
py -m uvicorn src.api.app:create_app --factory --host 127.0.0.1 --port 8000
```

打开：

```text
http://127.0.0.1:8000/app/#/agent?api=1
```

静态 `docs/app` 只能浏览公开归档，不能完成 Ask。修改环境变量后重启同一 PowerShell 中的 FastAPI，再 `Ctrl+F5`。

生产不设置 local mode，必须提供 `GITHUB_WEEKLY_SNAPSHOT_ROOT` 与有效 30 天 attestation。

## 8. 验证

最小：

```powershell
python -m unittest tests.test_contextual_ask tests.test_p1_data_trust tests.test_rag_freshness tests.test_data_contracts -q
npm.cmd run lint
npm.cmd run test
git diff --check
git diff --exit-code -- docs/app
```

完整：

```powershell
npm.cmd run lint
npm.cmd run test
npm.cmd run build
npm.cmd run test:e2e
npm.cmd run test:e2e:real
python -m unittest discover -q
python scripts\security_check.py
python scripts\evaluate_project_match.py
python scripts\evaluate_project_recommendations.py
python scripts\evaluate_follow_up_routing.py
python scripts\evaluate_constraint_parsing.py
python scripts\evaluate_claim_support.py
git diff --check
git diff --exit-code -- docs/app
git status --short --branch
```

固定 fixture、静态检查和本地 E2E 不能表述为真实用户、blind 泛化或生产验证。

## 9. 边界

- 不读取、修改、暂存或提交 `output/`、`tmp/`、运行态 SQLite、真实历史 blob、`.env*` 或环境变量内容。
- 不输出 Token、API Key、Cookie、管理员口令、通知地址或原始错误。
- 外部 README/HTML 是不可信输入。
- 不改写 `weekly-archive` 历史。
- 仅暂存本阶段文件。当前文档变动是 README、操作日志、V6 roadmap 和本交接；是否单独提交由用户决定。

## 10. 启动提示

```text
你在 C:\Users\Administrator\Documents\New project 3 工作。先只读执行 git status --short --branch，并阅读 AGENTS.md、docs/project-review-agent-v6-handoff.md、docs/project-review-agent-v6-roadmap.md 和 docs/operation-log.md 顶部。当前功能基线是 d638dae32d20bf73a0153576e45adbef38c89d64；V6 文档尚未提交。先实现 P0-1：本机历史只读路径必须保留确定性证据核验，但不得写 SQLite/JSON/运行记录，也不得将历史候选标成当前首选。随后补足 SQLite/JSON 的满足、unknown、硬冲突和零写入测试。完成后再处理 P0-2 的 CI fixture 语义一致性；不要通过降低阈值掩盖失败。
```

## 11. 未验证项

- P0 修复尚未实施，main CI 未恢复。
- 未执行真实采集、Kimi、Telegram、生产部署或真实用户测试。
- 未证明独立 blind 集在完整 RAG 主链上的泛化能力。
- 最近 weekly 成功一次，不代表排程长期稳定。
