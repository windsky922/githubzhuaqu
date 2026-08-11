# GitHub 项目研究导师 V7 对抗审查与路线图

审查日期：2026-08-11
工作目录：`C:\Users\Administrator\Documents\New project 3`
审查基线：`9d54346000c8668102305ce69342aa066896fd77`
核心目标：个人本机可以围绕 AI Agent 学习与 GitHub 项目研究进行自然、连续、可信的对话。

## 1. 结论先行

当前 Assistant V1 已经是一个边界清楚的只读领域助手，但还不能称为“流畅的完整 AI 助手”。它已经解决了候选不扩张、项目事实证据约束、模型失败降级、本机最小历史和旧 Ask 兼容；当前首要问题不再是继续添加功能，而是让教学对话真正连续并能从故障中恢复。

本轮没有发现新的发布安全 P0 或既有 V1 契约回归。按用户核心目标重新排序后，存在两个产品级 P0：

1. 知识型回答没有可供下一轮解析的结构化提纲，“把第三点展开”无法知道第三点是什么。
2. 纯教学链被项目 RAG 成功与否绑定；项目检索失败可阻断本来可回答的通用教学。

附件报告提出的独立 blind、`any_of/optional`、普通用户部署和 branch protection 均有价值，但不应按原顺序照搬。对个人本机使用，先修连续对话；公开部署延后，branch protection 保持暂不启用的既有决定。

## 2. 审查范围与证据边界

已审查：

- `src/assistant/`、`src/llm/` 与 Assistant API 编排。
- React 对话提交、本机历史白名单与 SSE 客户端。
- Assistant 单测、mock/真实 FastAPI E2E、固定 evaluator 与 CI 定义。
- README、API、架构、数据契约、V6 文档、操作日志及用户提供的每日审查报告。
- 一次确定性编排诊断：首轮“我想学习 AI Agent 开发方向的知识。”为 `knowledge`，下一轮“把第三点展开”为 `clarify`、`candidate_scope=none`。

未验证：

- 真实 Kimi 的延迟、流式分帧、限流、格式漂移和多轮回答质量。
- private fresh/stale blind pack 与真实 Top-1 人工接受率。
- 真实用户 5–10 轮任务完成率、公开部署、LAN/反向代理暴露和长期定时稳定性。
- 附件引用的远端运行 ID 本轮未能通过 `gh run view` 独立刷新；本文把它们标为附件证据，不扩大为本轮远端确认。

## 3. 目标、用户与关键任务

唯一主用户是本机个人开发者。V7 的完成标准不是“再多几个 Agent API”，而是用户可以完成以下主链：

```text
提出 AI Agent 学习问题
→ 得到分层讲解和可选项目证据
→ 用“第三点、继续、举例、换种说法”自然追问
→ 追加/撤销/析取约束
→ 比较上一轮候选
→ 模型、RAG 或 SSE 异常时可恢复
→ 明确知道回答来自模型常识还是项目证据
```

“完整 AI 助手”在本项目中的近期定义是完整的领域对话闭环，不等于通用闲聊、自动写操作、无限历史或多模型平台。

## 4. 当前系统与用户旅程

```text
React AgentPage
  → POST /v1/assistant/turn/stream
  → AssistantOrchestrator
      → 确定性/模型意图路由
      → contextual RAG（项目事实）
      → Kimi knowledge prompt（通用教学）
  → meta → delta* → final
  → 浏览器只回传最小 assistant_state
```

当前正向能力：

- Assistant 独立只读 repository，拒绝 `auto_build`，无工具写入和外发。
- 项目事实通过 RAG 证据、硬约束、claim 与 freshness 闸门。
- 上一轮项目候选追问限定 `previous_candidates`，显式 reset 才回全归档。
- Kimi 未配置或失败时明确降级，不伪造完整教程。
- 本机历史默认关闭；开启后仅保存白名单展示记录，30 天、10 会话、每会话 20 轮。

主链断点：

- `assistant_state` schema-v1 只有目标、约束、候选、首选、上一意图、待澄清问题和来源，不含上一教学回答的主题提纲或指代映射。
- 知识 Prompt 只接收当前问题；即使路由再次判为 `knowledge`，也不知道“第三点”指什么。
- `knowledge` 也先走项目检索；流式 RAG `error` 会直接结束，不再生成教学回答。
- 当前教学 SSE 在模型完整返回后才按字符切成 `delta`，不是模型实时流式。

## 5. 证据台账

| 类型 | 结论 | 主要证据 |
|---|---|---|
| 事实 | V1 已实现只读 Assistant、最小状态与项目候选续问 | `src/assistant/orchestrator.py`、`src/assistant/state.py`、`tests/test_assistant_orchestrator.py` |
| 事实 | 现有三轮 E2E 是“教学 → 候选选择 → 重置”，不是连续教学 | `e2e/agent.spec.ts`、`e2e-real/real-rag.spec.ts` |
| 事实 | “把第三点展开”确定性诊断落为 `clarify` | 本轮只读诊断，基线 `9d54346` |
| 事实 | knowledge 检索词会压缩为 `AI Agent` 加可识别语言 | `src/assistant/orchestrator.py` 的 `_rag_payload` |
| 事实 | SSE 客户端未强制要求收到 `final`；教学模型使用阻塞 `chat()` 后切块 | `frontend/src/lib/api.ts`、`src/assistant/orchestrator.py`、`src/llm/client.py` |
| 事实 | CI 运行六套固定 evaluator，AGENTS 原清单漏 capability scope | `.github/workflows/ci.yml`、`AGENTS.md` |
| 推断 | 5–10 轮教学会出现指代丢失、重复解释或不必要澄清 | 由 state/Prompt 输入边界推导，尚无真实用户数据 |
| 推断 | 公开部署现在会增加鉴权、额度与数据暴露面，不能直接解决本机对话连续性 | 当前无鉴权 Assistant 模型端点与 Pages 静态边界 |
| 待验证 | 推荐第一名是否真的适合用户 | 尚无独立 private blind 与人工 Top-1 判断 |
| 待验证 | 真实 Kimi 是否在本机稳定流式并保持知识边界 | 现有真实 E2E 使用确定性教学模型，不调用外网 |

## 6. 风险与失败链

### P0-1：知识型多轮缺少可解析的对话帧

- 失败链：首轮列出三点 → state 不保存提纲 → 用户说“第三点展开” → 路由和回答模型只有当前短句 → 澄清或泛化回答 → 对话失去连续性。
- 最小修复：兼容接收 schema-v1，发出 schema-v2；新增服务端生成、严格限长的 `knowledge_context={topic, outline:[{id,title}], focus_id}`。不保存上一回答正文、引用、证据或模型原始输出。
- 验收：支持“第三点展开、继续、举例、为什么、换种说法、回到第一点”；序号只能命中服务端上一轮 outline，客户端 state 仍按不可信输入校验。

### P0-2：教学主链错误依赖项目 RAG

- 失败链：用户问稳定概念 → 本地 snapshot/RAG 暂时不可用 → 流式 repository 发出 error → 编排直接结束 → Kimi 明明可用却没有教学回答。
- 附带风险：混合“学习 + 找项目”请求先命中 knowledge，原问题被重写为泛化检索词，可能丢失“必须离线、无需 API Key”等硬约束。
- 最小修复：教学回答独立执行；项目证据作为可选增强。纯教学 RAG 失败时仍返回 `model_general + limitations + final`；出现项目意图时，RAG 保留原始问题和已解析约束。
- 验收：fake repository 抛错时纯教学仍成功；具体项目请求继续 fail closed；混合意图的 hard requirements 不丢失。

### P1-1：SSE 截断恢复与真实首 token 流式缺失

- 失败链：HTTP 200 只收到 meta/delta 后 EOF → 客户端未检查 final → 页面留下无回答轮次 → 下一轮沿用更旧 state。
- 最小修复：客户端把“未收到 final”视为可恢复失败，使用同一请求体 POST fallback 或展示原问题重试；教学分支接入 `stream_chat()`，仍保持 `meta → delta* → final`。
- 验收：覆盖静默 EOF、partial delta 后断流、重复/畸形 final；未完成轮次不被当作成功。

### P1-2：通用教学的项目事实闸门过窄

- 失败链：模型输出框架名、GitHub URL、版本、Star、许可证或维护状态 → 不符合 `owner/repo` 正则却仍被标为 `model_general` → 具体项目事实绕过 RAG 证据门禁。
- 最小修复：教学输出结构化；检测仓库实体和时间敏感事实，命中时剥离、降级或转项目证据路径，不能只靠单一正则。
- 验收：命名框架、URL、空格 repo、版本/Star/license/current claim 对抗输出均不能作为无证据通用知识展示。

### P1-3：自然约束仍缺 `any_of`、optional 与撤销语义

- 失败链：“Python 或 TypeScript”“不要求本地部署”“取消离线要求” → 扁平 requirement 无法稳定表达 → 多余澄清或残留旧条件 → 用户感觉助手听不懂修改。
- 最小修复：requirement schema 增加 `group_id`、`logic=all_of|any_of`、`optional` 与显式撤销操作；前端编辑器同步。
- 验收：附件列出的四个自然表达直接形成正确结构，不发生硬约束漂移。

### P1-4：本机 readiness 与真实模型可用性没有目标级证据

- 失败链：实现 capability 被展示为可用 → 本机实际无模型、无 snapshot 或 stale → 用户只能在提交后看到降级 → 把“代码存在”误解为“现在可聊”。
- 最小修复：提供不泄露凭证的启动 preflight，分别报告 API、模型配置、snapshot/freshness、RAG 与只读模式；增加显式 opt-in 的真实 Kimi canary，CI 继续禁外网。
- 验收：ready/degraded/unavailable 与真实依赖一致；无模型、无 snapshot、stale 各有可恢复提示。

### P1-5：Top-1 缺独立 blind 与人工判断

- 失败链：固定 fixture 与实现共同演进 → CI 全绿 → 第一名仍可能不适合现实需求 → 用户基于错误首选投入时间。
- 最小修复：仓库外独立持有 fresh/stale private pack，分别冻结 snapshot；补真实 Top-1 人工接受判断。
- 验收：至少报告 Candidate Recall、Top-1 Acceptance、hard violation、route accuracy 与 answer-quality；未完成前不得宣称泛化。

### P2：后续而非当前前置

- 公开只读 Assistant：个人本机主用户暂不需要；若启动，必须先做鉴权/限流/额度与归档枚举威胁模型。
- main branch protection：单人开发阶段已决定暂不启用，保留为已接受治理风险；不得把 push 等同远端 CI 通过。
- 写工具、更多 Provider、服务端完整历史、通用闲聊：在流畅领域对话与 blind 质量达标前冻结。

## 7. 当前最没有把握、最大遗漏与隐蔽风险

最没有把握：真实 Kimi 在本机 5–10 轮教学、纠错、主题切换和故障恢复中的表现，以及真实 Top-1 是否比备选更适合用户。

最大遗漏：系统没有最小、结构化、可验证的“教学对话帧”。当前 localStorage 历史只是展示记录，不会成为模型上下文；这保护隐私，但也意味着自然指代没有来源。

容易被忽略的风险：

1. weekly 中 `kimi_used=true` 证明周报链调用过 Kimi，不证明 Assistant 对话链的真实模型可用性。
2. “真实 FastAPI E2E”使用临时 SQLite 和确定性教学模型，不等于真实 Kimi E2E。
3. `delta` 存在不等于真实流式；当前首 token 仍要等待完整模型回答。
4. CI 绿证明固定契约回归，不证明长对话任务完成或 Top-1 正确。
5. Pages 能展示归档，不等于公开页面可对话。

## 8. V7 实施顺序

1. P0-A：assistant_state schema-v2 教学对话帧与确定性指代解析。
2. P0-B：教学链与项目 RAG 解耦，保留混合意图完整约束。
3. P1-A：SSE final 强校验、断流恢复与真实模型流式。
4. P1-B：`model_general` 事实边界和 `any_of/optional/撤销`。
5. P1-C：本机 readiness、无模型/无 snapshot/stale 场景与 opt-in Kimi canary。
6. P1-D：5–8 轮旅程 fixture、private fresh/stale blind、Top-1 人工判断。

每个稳定阶段独立更新操作日志、执行相关验证、提交并推送 `main`；推送后单独核验远端 CI。

## 9. 测试与指标

新增最小矩阵：

- 五轮教学：列提纲 → 第三点展开 → 举例 → 换种说法 → 回到第一点。
- 混合意图：学习一个“必须完全离线、无需 API Key”的 Python Agent 项目。
- 约束表达：`Python 或 TypeScript`、`本地部署或 Docker`、`不要求本地部署`、`取消之前的离线要求`。
- 故障：RAG error、Kimi 未配置/超时/429、SSE 无 final、stale/no snapshot。
- 安全：无证据仓库事实、历史回答上传、禁止字段落盘、候选范围漂移继续为 0。

目标指标：

- 旅程任务完成率、指代解析成功率、澄清恢复率。
- 约束遗失率、候选范围漂移、无证据项目事实、禁止字段落盘均为 0。
- 首个 delta 延迟和 final 到达率单独记录，不用“有 delta”代替真实流式。
- blind 指标与固定 fixture 分开报告。

## 10. MVP 收敛与新基线

V7 只收敛领域助手主链：连续教学、可信项目研究、故障恢复和本机可用性。完成前不新增写工具、通知、订阅、管理 API、模型 Provider 或公开部署。

下一次增量审查从功能 SHA `9d54346000c8668102305ce69342aa066896fd77` 与提交本文件的文档 SHA 共同开始。V6 文档保留为历史取证，不再作为当前实施顺序。
