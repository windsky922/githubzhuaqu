# GitHub 项目研究导师 V8 开发交接摘要

交接日期：2026-08-12

工作目录：`C:\Users\Administrator\Documents\New project 3`

当前分支：`main`
V8 P1-C 开始基线：`bd3f69d8e7e76a7f8957ee89f61aa63101bb2a46`
V8 P1-D1 开始基线：`8e6afb3e1abcada8e08018d7c3543c45283fe5dd`

## 1. 当前结论

V8 已按 V7 风险顺序完成 P0-A、P0-B、P1-A、P1-B1、P1-B2、P1-C，并在本阶段完成 P1-D1：真实 FastAPI + 临时 SQLite + 确定性教学模型的五轮 journey，以及私有 blind fresh/stale 成对证据和 Top-1 人审的 fail-closed 工具链。

普通 readiness 只读、无副作用、无外网。真实 Kimi canary 已实现但本阶段没有执行；它必须由用户针对一次外部请求再次明确授权，并同时设置 `KIMI_CANARY_ENABLED=1`。

私有 blind 工具仍未运行真实 pack，也不把合成数据写成独立验收。检查器只能验证外部 JSON 自洽，固定输出 `accepted=false`、`verification_level=self_attested`；P1-D 的独立证据状态仍为 `not_verified`。

## 2. 必读顺序

1. `AGENTS.md`
2. 本文
3. `docs/project-review-agent-v7-roadmap.md`
4. `docs/operation-log.md` 顶部
5. `src/api/readiness.py`
6. `src/assistant/orchestrator.py`、`src/api/app.py`
7. `scripts/check_assistant_readiness.py`、`scripts/run_kimi_canary.py`
8. `frontend/src/pages/AgentPage.tsx`、`frontend/src/components/AgentWorkspace.tsx`、`frontend/src/lib/api.ts`
9. `tests/test_assistant_readiness.py`、`tests/test_kimi_canary.py`
10. `docs/api.md`、`docs/architecture.md`、`docs/data-contracts.md`
11. `scripts/evaluate_blind_rag.py`、`scripts/check_blind_rag_acceptance.py`
12. `docs/private-blind-acceptance.md`
13. `e2e-real/real-rag.spec.ts`、`tests/test_blind_rag_evaluator.py`、`tests/test_blind_rag_acceptance.py`

## 3. P1-C 实际契约

- `GET /v1/assistant/readiness` 聚合 `api/model/snapshot/rag/access`，整体为 `ready|degraded|unavailable`。
- `capabilities` 分开报告 `can_chat`、通用教学、项目证据和当前项目事实能力；前端按能力禁用，不因单一依赖缺失误杀仍安全可用的链路。
- SQLite 探针使用 URI `mode=ro` 与 `PRAGMA query_only`，要求 `rag_chunks` 具备必需列且至少有一条非空证据；历史 JSON 必须能解析出规范仓库。空表、坏 schema、空/坏 JSON 全部失败关闭，不调用 `ensure_sqlite_index()`、`database_summary()` 或 `rag_diagnostics()`。
- 响应不包含 key、Authorization、base URL、绝对路径、provider body 或原始异常；readiness 不写入对话状态或 localStorage。
- canary 同时要求 `--confirm-real-kimi` 与 `KIMI_CANARY_ENABLED=1`，固定短 Prompt、最长 15 秒、零重试；默认拒绝发生在 Kimi 配置读取和 client 构造前。
- CLI 不探测 listener，固定显示 `api_listener_not_checked/degraded`；只有 HTTP 路由本身能证明 API 已响应。
- 前端分别消费通用教学、项目证据与当前项目事实 capability，并提供原地“重新检查”；固定 CI 只运行 stub/离线业务测试，不调用 canary。依赖安装与 Chromium 安装本身可能联网，不能把此边界描述成整个 CI 物理断网。

## 4. P1-D1 实际契约

- 真实浏览器 E2E 连续执行“列三点提纲 → 展开第三点 → 举例 → 换种说法 → 回到第一点”，每轮走真实 FastAPI SSE；锁定唯一 final、焦点、最小 state、客户端请求白名单、候选范围和来源身份不漂移。
- private pack 只能提交 `q/context`，关键标签各覆盖至少 25%；runner 固定 mode/model/limit/auto-build，并分别要求 `fresh|stale` cohort 与独立 snapshot。
- schema-v4 baseline 绑定预冻结 policy 与执行源码清单，并同时输出指标 rate、精确 numerator/denominator 与 Top-1 subject commitment；越界/错配/零分母、空指标、坏日期或四位小数掩盖 hard violation 都失败关闭。
- 冻结 policy 同时约束 Candidate Recall、Top-1 Acceptance/coverage、route、answer-quality、freshness 和 hard violation。公开阈值检查器显式拒绝全部 `blind_*` artifact，CI 不读取私有 pack、snapshot、人审或 policy。
- 自声明 JSON 无法证明独立持有/独立人审。checker 的 `policy_passed=true` 只表示结构自洽且达到门槛；`accepted` 固定为 false，真实验收还需要仓库外预提交或签名治理证据。

## 5. 已验证与未验证

已验证：P1-D 定向 Python 35 项、Python 全量 396 项、前端单元 34 项、mock Chromium 28 项与真实 FastAPI + 临时 SQLite 7 项全部通过；lint、生产构建、安全检查、六组固定 evaluator 和公开阈值门禁通过。`hybrid/local-hash-v1` Recall@3 为 0.9231、Top-1 为 0.8654，硬约束违规率为 0；构建产物与源码一致。远端 CI 仍需在推送后核验。

未验证：真实 Kimi 网络、真实 provider 延迟、真实 429/timeout、真实私有 fresh/stale blind pack、冻结 policy 和独立 Top-1 人审。没有外部证据时不得把工具存在、合成通过或 `policy_passed` 写成独立质量已确认。

## 6. 下一阶段

P1-D1 代码与合成验证收口后，下一步只能由独立持有人在仓库外冻结 fresh/stale pack、snapshot、policy 和 Top-1 判断，再按 `docs/private-blind-acceptance.md` 运行。若暂时没有这些输入，P1-D 保持 `not_verified`，不得继续用公开 fixture 推断泛化质量。

## 7. 常用命令

```powershell
python scripts\check_assistant_readiness.py --json
python scripts\run_kimi_canary.py
npm.cmd run lint
npm.cmd run test
npm.cmd run build
npm.cmd run test:e2e
npm.cmd run test:e2e:real
python -m unittest discover -q
python scripts\security_check.py
python scripts\evaluate_blind_rag.py --help
python scripts\check_blind_rag_acceptance.py --help
git diff --check
git diff --exit-code -- docs/app
```

`python scripts\run_kimi_canary.py` 的预期默认结果是 `refused` 且 `request_sent=false`。不要在固定验证中追加双重 opt-in，也不要把真实凭证写入命令、文件、日志或对话。

private blind 的真实命令不进入固定验证；仓库只运行合成临时输入测试。实际外部路径与退出语义以 `docs/private-blind-acceptance.md` 为准。
