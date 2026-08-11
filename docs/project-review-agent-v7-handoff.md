# GitHub 项目研究导师 V7 开发交接摘要

交接日期：2026-08-11
工作目录：`C:\Users\Administrator\Documents\New project 3`
功能审查基线：`9d54346000c8668102305ce69342aa066896fd77`
当前分支：`main`，审查开始时与 `origin/main` 一致
当前目标：先做可连续对话的个人本机 AI Agent 学习与 GitHub 项目研究助手，再谈公开部署或写工具。

## 1. 结论与固定顺序

V1 已完成安全只读外壳，但教学多轮仍会断链。下一阶段固定顺序：

1. schema-v2 教学对话帧与“第三点/继续/举例/换种说法”确定性解析。
2. 教学主链与项目 RAG 解耦，混合意图保留完整硬约束。
3. SSE 必达 final、断流恢复和真实模型流式。
4. 教学事实边界、`any_of/optional/撤销`、本机 readiness。
5. 五轮旅程、opt-in 真实 Kimi canary、private fresh/stale blind 与 Top-1 人工判断。

完整风险、失败链和验收见 [V7 审查与路线图](project-review-agent-v7-roadmap.md)。

## 2. 必读顺序

1. `AGENTS.md`
2. 本文
3. `docs/project-review-agent-v7-roadmap.md`
4. `docs/operation-log.md` 顶部
5. `README.md`
6. `docs/api.md`、`docs/architecture.md`、`docs/data-contracts.md`
7. `src/assistant/orchestrator.py`、`src/assistant/state.py`
8. `src/llm/prompts.py`、`src/llm/client.py`、`prompts/assistant_answer.md`、`prompts/assistant_router.md`
9. `frontend/src/pages/AgentPage.tsx`、`frontend/src/lib/api.ts`、`frontend/src/lib/conversations.ts`
10. `tests/test_assistant_orchestrator.py`、`tests/test_assistant_api.py`、`frontend/src/lib/api.test.ts`
11. `e2e/agent.spec.ts`、`e2e-real/real-rag.spec.ts`、`.github/workflows/ci.yml`

V6 及更早 roadmap/handoff 只作历史取证，不覆盖 V7 顺序。

## 3. 已完成与已确认

- `/v1/assistant/turn` 与 `/v1/assistant/turn/stream` 只读，旧 Ask 保持兼容。
- 客户端只提交当前问题、检索参数和白名单化上一轮 `assistant_state`。
- 项目候选自然追问限定上一轮集合，显式 reset 才允许回全归档。
- 项目事实必须经过 RAG 证据、硬约束、claim 与 freshness 闸门。
- Kimi 未配置或失败时显式降级，不伪造教程。
- 浏览器历史默认关闭；开启后 30 天、10 会话、每会话 20 轮，禁止证据、Prompt、错误详情和凭证落盘。
- 当前固定 CI 定义包含 Python、前端、构建、安全、六套 evaluator、mock 与真实 FastAPI E2E。
- branch protection 按用户决定暂不启用；这是已接受风险，不是待确认事项。

## 4. 当前问题与原始现象

### P0-A：教学指代断链

确定性诊断：

```text
第一轮：我想学习 AI Agent 开发方向的知识。
first_mode = knowledge
first_candidates = 1

第二轮：把第三点展开
second_mode = clarify
second_clarification = true
candidate_scope = none
```

根因：schema-v1 不含教学提纲；知识 Prompt 只收到当前问题。

### P0-B：教学被 RAG 故障阻断

`knowledge` normal/stream 都先运行 contextual RAG；stream 收到 repository error 会直接结束，未执行知识模型。混合问题还会把 RAG query 压成 `AI Agent` 加语言，可能丢失离线/API Key 等硬约束。

### 其他未关闭问题

- 200 SSE 静默 EOF 未强制要求 `final`；当前教学 delta 是完整模型输出后的字符切块。
- `model_general` 具体项目事实仅用 `owner/repo` 正则拦截，覆盖不足。
- requirement schema 仍不能稳定表达 OR、optional 和取消旧条件。
- 没有真实 Kimi 多轮、private blind 或真实 Top-1 质量证据。

本轮没有阻塞性原始报错。尝试用 `gh run view` 刷新附件中的两个 run ID 时只得到固定失败码，未输出或记录凭证信息；因此远端状态继续以附件证据标注，不能写成本轮独立确认。

## 5. 第一工作包：schema-v2 教学对话帧

允许修改：

- `src/assistant/state.py`
- `src/assistant/orchestrator.py`
- `src/llm/prompts.py`
- `prompts/assistant_answer.md`、必要的新 Assistant Prompt
- 前端 state 类型、API 白名单和 `conversations.ts`
- Assistant 单测/API 测试、一个五轮浏览器主链
- README、API、架构和数据契约

建议契约：

```json
{
  "schema_version": 2,
  "knowledge_context": {
    "topic": "Agent 核心组成",
    "outline": [
      {"id": "k1", "title": "模型与推理"},
      {"id": "k2", "title": "工具与行动"},
      {"id": "k3", "title": "记忆与反馈"}
    ],
    "focus_id": "k3"
  }
}
```

强制边界：

- 兼容接收 schema-v1，服务端发出 schema-v2。
- 只保存主题、提纲短标题和 focus ID；不保存历史回答正文、sections、citations、evidence、`prompt_context` 或模型原始输出。
- state 仍是不可信提示；长度、数量、ID、来源和候选每轮重新校验。
- 序号/“刚才”只能解析到上一轮服务端提纲，不允许凭空构造上下文。

验收：五轮教学轨迹全部保持主题、可切换 focus、无项目候选漂移、请求体/本机存储继续满足白名单。

## 6. 第二工作包：独立教学与混合意图

实施：

1. 纯教学先生成/流式生成 model-general guidance。
2. 项目 RAG 是可选增强；失败时追加 limitations，不阻断通用教学 final。
3. 用户同时提到项目和硬条件时，RAG 使用原始问题或等价结构化 requirements，不得用泛化 `AI Agent` 查询覆盖。
4. 具体仓库事实仍只能来自 project evidence；纯项目请求继续 fail closed。

验收场景：

```text
解释 ReAct 的原理
继续，并举一个不涉及具体仓库的例子
我想学习一个必须完全离线、无需 API Key 的 Python Agent 项目
```

fake repository 抛错时前两轮仍有教学 final；第三轮保留 offline/api-key/Python requirements，冲突候选不能 eligible。

## 7. 第三工作包：SSE、readiness 与质量证据

- 客户端必须检测 authoritative final；无 final 时同体 POST fallback 或提供原问题重试。
- 接入 `KimiChatClient.stream_chat()`，保留 `meta → delta* → final`；只有 final 更新权威 state。
- 提供脱敏 preflight：API、模型是否配置、snapshot/freshness、RAG、只读模式分开显示。
- 真实 Kimi 仅作为显式 opt-in canary，不进入固定 CI，不记录凭证或原始 provider 输出。
- 独立持有 fresh/stale blind pack；固定 fixture 与 blind 指标分开报告。

## 8. 验证命令

先跑当前工作包相关测试，再执行完整矩阵：

```powershell
npm.cmd run lint
npm.cmd run test
npm.cmd run build
$env:CI='1'; npm.cmd run test:e2e
$env:CI='1'; npm.cmd run test:e2e:real
python -m unittest discover -q
python scripts\security_check.py
python scripts\evaluate_project_match.py
python scripts\evaluate_project_recommendations.py
python scripts\evaluate_follow_up_routing.py
python scripts\evaluate_constraint_parsing.py
python scripts\evaluate_claim_support.py
python scripts\evaluate_capability_scope.py
git diff --check
git diff --exit-code -- docs/app
git status --short --branch
```

不得把固定 fixture、fake Kimi、临时 SQLite 或静态审查表述为真实模型、blind 泛化、生产部署或真实用户验证。

## 9. 提交、推送与边界

- 每个稳定工作包先更新 `docs/operation-log.md`，再验证、只暂存本阶段文件、提交并推送 `main`。
- 推送完成后单独核验远端 CI；“已推送”不等于“远端通过”。
- 不触碰 `output/`、`tmp/`、运行态 SQLite、真实历史 blob、`.env*` 或环境变量内容。
- 不输出 Token、API Key、Cookie、管理员口令、通知地址或原始 provider 错误。
- 不新增写工具、通知、订阅、Provider 或公开部署，除非用户重新授权并完成对应威胁模型。

## 10. 启动提示

```text
你在 C:\Users\Administrator\Documents\New project 3 工作。先只读执行 git status --short --branch，并阅读 AGENTS.md、docs/project-review-agent-v7-handoff.md、docs/project-review-agent-v7-roadmap.md 和 docs/operation-log.md 顶部。当前功能审查基线是 9d54346000c8668102305ce69342aa066896fd77。先实现 V7 P0-A：兼容接收 assistant_state schema-v1、发出 schema-v2，只新增严格限长的 knowledge_context.topic、outline[id,title] 和 focus_id；不得上传或落盘历史回答、引用、证据、sections、prompt_context 或模型原始输出。补一条五轮教学轨迹，覆盖“第三点展开、举例、换种说法、回到第一点”。稳定后更新文档、执行相关验证、提交并推送 main，再核验远端 CI。不要同时启动公开部署、写工具或更多模型 Provider。
```

## 11. 未验证项

- 真实 Kimi 的多轮质量、实时流式、延迟、429/超时恢复。
- private fresh/stale blind 与真实 Top-1 人工接受率。
- 公开只读 Assistant、LAN/反向代理暴露、鉴权和速率限制。
- 五轮教学旅程、SSE 无 final 恢复、混合意图硬约束保留尚未实现。
- 全局默认交接模板在预期位置未找到；本文按项目既有 V6 结构和要求字段生成。
