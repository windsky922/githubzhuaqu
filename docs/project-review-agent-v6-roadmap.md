# GitHub 项目研究 Agent V6 只读增量完整审查

审查日期：2026-08-02  
审查方式：只读代码、文档、配置、固定测试、GitHub 元数据与 Actions 失败日志；未读取 `tmp/`、`output/`、运行态 SQLite、原始历史 blob 或真实用户内容。  
审查基线：`d638dae32d20bf73a0153576e45adbef38c89d64`（`main` 与 `origin/main` 一致）

## 1. 审查基线

- 上次审查基线：`bb1e249`（V5 文档基线）。本次共检查其后的 9 个提交；最新产品改动为 `d638dae feat: prefer soft project constraints`。
- 当前 `HEAD`：`d638dae32d20bf73a0153576e45adbef38c89d64`。本地仅有用户未跟踪的 `output/`、`tmp/`，未触碰。
- GitHub：无开放 PR、无开放 Issue；远端另有未合并的 `codex/archive-query` 分支。`main` 未启用分支保护。
- 当前 HEAD 的 Actions「提交质量检查」运行 `30737083119` 已失败。最近 weekly 成功运行 `30733405312` 于 2026-08-02 05:05 UTC 完成，`weekly-archive` HEAD 为 `47cb50ab`。

## 2. 本次更新概述

本次主要把 Ask 从“自然语言条件默认硬约束”改为“默认偏好、明确强制词才硬约束”，并增加本机历史 SQLite/JSON 回退与来源标识。前端可显示偏好、历史来源和非当前首选状态。

事实：解析器、候选排序、Ask/SSE 响应、React 卡片和文档均有对应改动。推断：产品方向正确，但两个主链缺口使当前变更尚未达到可发布状态。

## 3. 产品定位与核心用户任务

定位应收缩为：**有证据和来源日期的 GitHub 项目研究/筛选内部工具**，不是成熟的通用项目选择产品。

核心任务是“描述需求 → 获得最多 3 个可解释候选 → 查看证据、日期和限制 → 比较/进入详情 → 选择项目”。采集、订阅、任务、反馈和模型增强是辅助能力；它们不能阻断该任务。

## 4. 产品完成度审查

|能力|事实|结论|
|---|---|---|
|本机历史检索|SQLite 不可读会回退 JSON；候选标记历史来源|部分可用|
|偏好展示|`preferences[]` 已在卡片显示|可用，但历史验证缺口影响可信度|
|明确硬冲突淘汰|非只读路径有 verifier；只读历史路径跳过 verifier|主链不完整|
|当前推荐|fresh verified snapshot 才可 `current_eligible`|安全边界合理|
|比较和详情|已有路由、对比选择和项目详情页|代码存在；未进行真实用户验证|
|反馈/订阅/任务|有 API、表和管理页面|辅助链，未证明真实闭环|

普通用户在正确启动本地 API 且历史语料可读时，能发起一次候选检索；但不能可靠依赖历史证据完成“硬条件项目选择”。静态 Pages 不能执行 Ask，且启动/模式差异仍是可用性门槛。

## 5. 完整用户旅程审查

1. 用户须使用带 API 的本地服务，静态归档模式会禁用项目匹配；此限制在界面有提示，但从 Pages 到 API 的切换不是一键完成。
2. 新需求解析为偏好或硬约束，正常 API 路径会检索、验证、返回卡片和证据。
3. 本机历史模式能召回候选，但 `Repository._contextual_explained()` 在 `local_read_only` 时令 `requirement_verification={}`，失去条件证据判定。
4. 前端不会把历史候选标为当前首选；这一点与产品要求一致。
5. 对比、详情、浏览器本地对话历史均存在；反馈是否被真实用户使用、订阅是否实际发送，未取得生产证据。

## 6. 约束体系审查

必须保留在主链：生产快照显式来源、freshness attestation、证据引用、主张绑定/极性/作用域校验、明确硬冲突淘汰、历史非当前标识、写操作鉴权与确认。

应软化：语言、部署、成本、离线、外部 API、许可证和 `multi_agent` 的自然语言提及；现实现已采用此策略，只有“必须、仅、不得、排除、不能接受、只要、必须满足”等短语级强制词设为 `hard=true`。

应移出核心检索主链：planned job、解释回填、质量趋势、订阅派发、开发上下文索引与模型增强。它们应降级为后台/管理能力，不能决定普通 Ask 是否返回候选。

## 7. 约束是否过多的最终判断

**生产可信度约束不多；实现约束叠加过多。** 之前的“unknown 即 clarification”已修正。但本机只读模式把“不写库”错误扩大成“不做内存核验”，使本应保留的硬冲突淘汰也消失。问题不是证据要求本身，而是把写入限制与读取/推理限制混为一体。

## 8. 核心文档一致性检查

P1 文档漂移：`docs/data-contracts.md:9` 声明 freshness 为 30 天，`docs/data-contracts.md:29` 仍声明默认阈值为 8 天。README、API 文档顶部已描述 local mode，但数据契约可使下游实现采用错误阈值。

文档正确地区分了历史候选与当前结论，也未把固定 fixture 表述为泛化质量证明。未验证项：生产部署、真实用户体验、独立 blind 评估、分支保护实际执行。

## 9. 实现与调用链验证

- `src/rag/follow_up_router.py:251-467`：短语级解析和 `multi_agent` 字段已接入；默认 `hard=false` 的代码与产品目标一致。
- `src/rag/project_recommendations.py:92-134`：`eligibility` 只由 hard evaluation 决定，偏好参与排序；结构正确。
- `src/rag/answering.py:335-351`：仅全部候选明确 `rejected` 才 `no_match`；结构正确。
- `src/api/repository.py:1065-1084`：SQLite 只读失败时 JSON 回退；但临时改写共享 `self.root`，并发请求可能读到错误根目录。
- `src/api/repository.py:1781-1787`：本机历史模式跳过 verifier；这是 P0。
- `src/api/repository.py:1945-1967` 和 `frontend/src/pages/AgentPage.tsx:36-43`：历史候选不会成为当前首选；符合要求。

## 10. 测试与评估真实性

本轮实际通过：

- `python -m unittest tests.test_contextual_ask tests.test_p1_data_trust tests.test_rag_freshness tests.test_data_contracts -q`
- `npm.cmd run lint`
- `npm.cmd run test`（3 文件、12 测试）
- `git diff --check` 与 `git diff --exit-code -- docs/app`

远端全量 Python CI 未通过。运行 `30737083119` 的 `test_constraint_parsing_eval`、`test_follow_up_eval` 和 `test_follow_up_router` 仍将默认条件断言为 `hard=true`，与新语义冲突。定向测试通过不能替代全量 CI。

缺失或未证明：历史模式对“已有证据满足/明确冲突淘汰”的端到端测试、fresh+history 混合排序、并发 JSON 回退、真实用户选择闭环、独立 blind pack 完整 RAG 主链、Top-1 人工标注。

## 11. 工作流与部署状态

- weekly：最近一次手动运行成功；其前三次手动运行及 2026-07-27 schedule 运行失败。成功一次不能证明持续稳定。
- CI：当前 main 已失败，分支保护又不存在，失败提交仍可留在 main。
- 生产：没有 `GITHUB_WEEKLY_SNAPSHOT_ROOT` 时 fail closed，安全策略正确；本机必须设置 `GITHUB_WEEKLY_DATA_MODE=local` 才可用历史数据。
- 未查阅真实密钥、真实模型或真实通知；Token 是否正确轮换、外发是否可控，不能据此确认。

## 12. 当前最没有把握的事情

历史数据库中的项目证据是否足以支持真实需求，及其检索排序是否帮助用户选到合适项目。固定 fixture 和局部测试只能证明规则回归，不能证明这一点。

## 13. 当前最大的产品遗漏

缺少一个可靠的“历史证据核验但绝不写历史库”的适配层。没有它，双源策略只是“能找出旧项目”，不是“能基于旧项目证据做受控选择”。

## 14. 用户可能没有意识到的风险

1. 历史候选的“待核实”不等于不适合；但当前实现也不能显示哪些条件已由历史证据确认。
2. `self.root` 的临时替换会在并发 FastAPI 请求中造成跨请求数据根串扰。
3. 未保护的 main 允许 CI 失败提交继续成为部署/审查基线。
4. 浏览器 localStorage 对话只是客户端记录，不是可审计或可迁移的会话历史。

## 15. 风险严重度

### P0-1：历史只读模式跳过条件核验

- 风险描述：`local_read_only` 使 `requirement_verification` 固定为空。
- 产品影响：明确“不得依赖外部 API”等冲突不能在历史候选上淘汰；已存在证据也不能标为满足。
- 触发条件：设置 `GITHUB_WEEKLY_DATA_MODE=local` 且使用历史 SQLite/JSON。
- 后果：错误展示、无意义 unknown、产品主链仍像“无法操作”。
- 证据：`src/api/repository.py:1781-1787`；verifier 为读取证据的独立逻辑 `src/rag/constraint_verifier.py:88`。
- 建议修改：给 verifier 传入只读连接/上下文，禁止持久化但保留内存判定；JSON 走同一 `CapabilityFact` 适配层。
- 建议测试：历史 SQLite、历史 JSON 各验证“满足、unknown、明确冲突”；确认无 DB 写入。
- 验收：历史候选可出现 `matched/unmet/unknown`；明确硬冲突为 `rejected`；历史候选仍永不 `current_eligible`。
- 分类：正确性、产品可用性、过度约束。

### P0-2：main CI 已失败且无分支保护

- 风险描述：偏好语义变更未同步固定评估和路由测试，当前 main 的质量门已红。
- 产品影响：后续改动缺少可信回归基线，错误可以直接进入 main。
- 触发条件：推送 `d638dae`。
- 后果：CI 不能作为发布或审查证据；新旧约束语义并存。
- 证据：Actions `30737083119`；失败测试 `tests/test_constraint_parsing_eval.py:11`、`tests/test_follow_up_eval.py:12`、`tests/test_follow_up_router.py:135`；main protection API 返回 404 `Branch not protected`。
- 建议修改：先更新 fixture、期望指标与阈值说明，再恢复全量 CI；随后为 main 启用必需 checks。
- 建议测试：故意把默认偏好改回 hard，确保 evaluator/CI 非零退出；显式强制词必须仍为 hard。
- 验收：全量 CI 三 job 通过；main 只接受所需检查成功的更新。
- 分类：正确性、工程治理。

### P1-1：freshness 契约自相矛盾

- 风险描述：同一数据契约同时写 30 天和 8 天。
- 产品影响：客户端、运维和后续代码可能采用不同 freshness 口径。
- 触发条件：任何依照文档重建或集成 Ask 的工作。
- 后果：历史/当前标签和拒答行为不可预测。
- 证据：`docs/data-contracts.md:9`、`:29`。
- 建议修改：保留一个常量来源并在文档引用它；删除旧 8 天叙述。
- 建议测试：文档契约测试断言唯一 30 天口径。
- 验收：README、API、架构、数据契约和代码均为 30 天。
- 分类：正确性、文档治理。

### P1-2：JSON 历史回退修改共享仓库根

- 风险描述：`_merge_history_contexts()` 暂时写入 `self.root` 后再恢复。
- 产品影响：多请求下可能把 A 请求的检索指向 B 的历史根。
- 触发条件：并发请求且 SQLite 回退 JSON。
- 后果：来源混淆、候选错配，甚至跨数据根泄露可见内容。
- 证据：`src/api/repository.py:1076-1083`。
- 建议修改：把 `root` 作为 `_local_json_rag_retrieve` 显式参数，禁止修改实例共享状态。
- 建议测试：两个临时根并发 JSON 检索，断言来源与候选不串扰。
- 验收：无任何请求路径改写 `self.root`。
- 分类：正确性、安全边界。

## 16. 可执行修改建议

1. 先修 P0-1：抽出只读 evidence verifier；不要因为禁止写 SQLite 而跳过判断。
2. 立即修 P0-2：更新固定评估样本和测试预期，执行完整 CI；再启用 main required checks。
3. 修 P1-1/P1-2：统一 30 天常量和文档；移除共享状态根切换。
4. 将首页入口改成明确的两条路径：`当前 verified 快照` 与 `本机历史参考`，给出可复制启动命令和可恢复错误说明。

## 17. 建议测试

- local SQLite / JSON：硬冲突、已验证满足、unknown、无写入。
- fresh verified 与 historical verified/unknown 混合排序，最多三个候选。
- 30/31 天、三层日期不一致、无 attestation。
- 并发 JSON fallback。
- Playwright：普通用户在本地模式完成“输入 → 候选 → 证据 → 对比 → 详情”。
- CI：偏好与明确强制词的 fixture/evaluator 不可同时漂移。

## 18. MVP 收敛建议

保留：双源只读检索、硬/软条件、证据抽屉、来源/日期、详情、对比。  
延后：任务编排、解释回填、质量趋势、订阅派发、开发上下文索引。  
冻结：任何未能证明为普通用户选择项目提供直接价值的管理 API。  
不要新增更多约束开关；让用户继续用自然语言“必须/不得”表达强制条件。

## 19. 下一步优先级

1. P0-1 历史只读核验适配层。
2. P0-2 修复全量 CI 与 main 保护。
3. P1-1 freshness 单一事实来源。
4. P1-2 并发安全 JSON fallback。
5. MVP 用户旅程真实 E2E 与独立 blind 评估。

整改顺序遵循：产品主链错误 → 用户无法完成任务 → 过度约束 → 数据可信度 → 推荐质量 → 工作流可靠性 → 安全/隐私 → 工程治理 → 文档优化。

## 20. 本次新审查基线

下一次增量审查基线为：`d638dae32d20bf73a0153576e45adbef38c89d64`。在 P0-1、P0-2 未关闭前，不应把本项目称为成熟产品或将当前 CI / 固定 fixture 当作发布质量证明。

## 证据边界

事实来自当前工作树、定向本地测试、GitHub 元数据和失败日志。产品成熟度、用户价值和风险排序属于基于这些事实的工程推断。未执行真实采集、Kimi、Telegram、生产部署、真实用户研究或独立 blind 评估；这些事项均未被表述为已验证。
