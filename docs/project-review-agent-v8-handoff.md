# GitHub 项目研究导师 V8 开发交接摘要

交接日期：2026-08-12

工作目录：`C:\Users\Administrator\Documents\New project 3`

当前分支：`main`
V8 P1-C 开始基线：`bd3f69d8e7e76a7f8957ee89f61aa63101bb2a46`

## 1. 当前结论

V8 已按 V7 风险顺序完成 P0-A、P0-B、P1-A、P1-B1、P1-B2，并在本阶段完成 P1-C 本机 readiness 与显式 Kimi canary。Assistant 现在先展示真实依赖状态，再允许用户发送；无模型、无 verified snapshot、stale/lagging、显式历史归档与非只读访问均有稳定状态码和恢复提示。

普通 readiness 只读、无副作用、无外网。真实 Kimi canary 已实现但本阶段没有执行；它必须由用户针对一次外部请求再次明确授权，并同时设置 `KIMI_CANARY_ENABLED=1`。

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

## 3. P1-C 实际契约

- `GET /v1/assistant/readiness` 聚合 `api/model/snapshot/rag/access`，整体为 `ready|degraded|unavailable`。
- `capabilities` 分开报告 `can_chat`、通用教学、项目证据和当前项目事实能力；前端按能力禁用，不因单一依赖缺失误杀仍安全可用的链路。
- SQLite 探针使用 URI `mode=ro` 与 `PRAGMA query_only`，要求 `rag_chunks` 具备必需列且至少有一条非空证据；历史 JSON 必须能解析出规范仓库。空表、坏 schema、空/坏 JSON 全部失败关闭，不调用 `ensure_sqlite_index()`、`database_summary()` 或 `rag_diagnostics()`。
- 响应不包含 key、Authorization、base URL、绝对路径、provider body 或原始异常；readiness 不写入对话状态或 localStorage。
- canary 同时要求 `--confirm-real-kimi` 与 `KIMI_CANARY_ENABLED=1`，固定短 Prompt、最长 15 秒、零重试；默认拒绝发生在 Kimi 配置读取和 client 构造前。
- CLI 不探测 listener，固定显示 `api_listener_not_checked/degraded`；只有 HTTP 路由本身能证明 API 已响应。
- 前端分别消费通用教学、项目证据与当前项目事实 capability，并提供原地“重新检查”；固定 CI 只运行 stub/离线业务测试，不调用 canary。依赖安装与 Chromium 安装本身可能联网，不能把此边界描述成整个 CI 物理断网。

## 4. 已验证与未验证

已验证：readiness/canary 后端定向 23 项、Python 全量 378 项、前端单元 34 项、mock Chromium 28 项与真实 FastAPI + 临时 SQLite 6 项全部通过；lint、生产构建、安全检查和六组固定 evaluator 通过。`hybrid/local-hash-v1` Recall@3 为 0.9231、Top-1 为 0.8654，硬约束违规率为 0；构建产物已由当前源码重新生成。远端 CI 仍需在推送后核验。

未验证：真实 Kimi 网络、真实 provider 延迟、真实 429/timeout、私有 fresh/stale blind pack。没有用户再次授权时不得把 canary 脚本的存在写成真实连通性已确认。

## 5. 下一阶段

下一项按路线图进入 P1-D：五轮 journey 验收、独立持有的 private fresh/stale blind 证据和 Top-1 人工判断。固定 fixture 与 private blind 指标必须分开报告；不得把当前公开 fixture 的通过率冒充独立质量证据。

## 6. 常用命令

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
git diff --check
git diff --exit-code -- docs/app
```

`python scripts\run_kimi_canary.py` 的预期默认结果是 `refused` 且 `request_sent=false`。不要在固定验证中追加双重 opt-in，也不要把真实凭证写入命令、文件、日志或对话。
