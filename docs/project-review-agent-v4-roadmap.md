# GitHub 项目研究 Agent V4 第一性原理对抗性审查与路线图

审查日期：2026 年 7 月 15 日

审查基线：`47bded04d344ed3a0dbe9070e045b437d2246c64`

远端状态：审查时 `main` 与 `origin/main` 一致；提交质量检查运行 `29410935146` 的核心质量、mock Playwright 和真实 FastAPI Playwright 三项 job 全部成功。

审查范围：公开归档、Ask/SSE、回答质量、硬约束、数据新鲜度、反馈闭环、管理边界、评估、CI、前端持久化和后端可维护性。

未审查边界：未读取 `tmp/`、`output/`、运行态 SQLite 或原始业务数据；未调用真实 Kimi、GitHub 项目采集或真实外发；未用真实用户流量证明推荐正确率。用户已确认历史归档数据库不存在真实用户信息、真实 token 或真实通知地址，本报告将其记录为用户提供的业务事实，不将其表述为独立内容取证结论。

## 一、结论先行

项目已经从“能返回项目卡片的原型”进入“有明确安全边界和确定性回归的工程系统”：公共归档最新 tree 已清理 SQLite，字段级投影、远端 attestation、无状态追问、管理写鉴权、SSE 完整缓冲和提交级三 job CI 都有当前实现与测试证据。

但系统仍没有证明其核心产品承诺：**面对未见过的真实中文需求和真实 GitHub 项目，能否理解用户要做什么，基于足够新鲜且作用域正确的证据，给出可复现、可纠错的首选。**

当前最危险的产品错觉是：

```text
CI 绿色 + answer_quality.passed=true + 合法引用编号
≠
回答相关、主张有证据、数据新鲜、首选正确
```

当前最危险的系统边界错觉是：

```text
源文件由 allowlist 选择 + push 后远端 attestation
≠
push 前最终 staged Git tree 已经是完整 allowlist
```

### 必要条件证据账本

| 核心必要条件 | 当前证据状态 | V4 判断 |
| --- | --- | --- |
| 最新公开归档不含数据库和运行态文件 | 已证实 | 最新 tree 已有远端 attestation；历史内容按用户确认不作真实泄露处置 |
| 发布前最终 Git tree 只能包含显式公共文件 | 被反证 | 发布器只重建 `docs/reports/data`，其他旧路径可保留；staged scan 不是完整 allowlist |
| 未校验 provider 草稿不进入 SSE | 已证实 | 当前实现先完整缓冲、校验后才发送 delta；V3 旧风险已修复 |
| `answer_quality.passed` 代表主张受证据支持 | 被反证 | `evidence_relevance`、`claim_support` 未评估，`data_freshness` 为 unknown |
| 硬约束在项目级作用域上可靠 | 部分证实 | 句子级固定集通过；setup/runtime、UI/inference、optional/required 等作用域未结构化 |
| 检索和推荐不会在 CI 中静默退化 | 未证实 | 两个核心评估 CLI 无阈值，部分测试只检查指标位于 `[0,1]` |
| Ask 能识别 search/explain/compare/learning 等回答类型 | 未证实 | 路由只有会话关系，没有独立 `answer_type` 和 `evidence_policy` |
| 数据水位足以支撑“最新/首选” | 未证实 | 无 source/corpus/embedding 三层水位和 stale 门禁 |
| 用户反馈能关联并纠正一次具体决策 | 未证实 | 反馈影响排序，但没有 query/decision 快照和版本链 |
| 管理数据和运行态全部受鉴权保护 | 部分证实 | 写接口有鉴权；若干管理 GET 仍可读反馈、订阅、通知和任务数据 |
| CI 能阻止失败提交进入 main | 未证实 | CI 在 push 后运行；main 无分支保护和 required checks |

### 本轮实际验证

- 前端 lint、11 项 Vitest、生产构建、Python 全量单元测试、12 项 mock Playwright、6 项真实 FastAPI Playwright和安全检查全部通过；`docs/app` 构建产物保持一致。
- 52 条固定项目匹配评估中，local-hash-v1 与 hybrid 均为 Recall@3/10 `0.9231`、MRR@10 `0.8878`、硬约束违反率 `0`；FTS5 的 Recall@3/10 与 MRR@10 均为 `0.0962`。
- 52 条固定推荐评估中，local-hash-v1 与 hybrid 均为 Top-1 `0.8654`、Recall@3 `0.9231`、MRR@10 `0.8878`、硬约束违反率 `0`；FTS5 的 Top-1、Recall@3 和 MRR@10 均为 `0.0962`。
- 60 条追问路由固定集全部通过；100 条约束解析和 60 条句子证据固定集全部通过，固定集 false eligibility 和硬约束违反率均为 `0`。
- 上述指标只属于当前公开 fixture 的可重复回归基线，不证明真实未见项目、真实 Kimi 或独立 blind 泛化。

## 二、眼下最没有把握的事情

### 真实未见需求下，“通过质量检查”的首选是否正确

【事实】`src/rag/answer_quality.py` 当前检查回答长度、引用编号是否存在、仓库名是否来自上下文、是否有 contexts，以及少量危险指令短语；返回值明确把 `evidence_relevance` 和 `claim_support` 设为 `not_evaluated`，把 `data_freshness` 设为 `unknown`。

【事实】项目匹配固定集只有 52 条需求和 8 个 fixture 仓库；追问固定集 60 条；真实 FastAPI Playwright 会清空 Kimi、GitHub 和通知凭据，使用临时 SQLite 与确定性 fixture。它不是“真实 Kimi + 真实 GitHub 数据”验证。

【推断】模型只要写出一个长度足够、提到已知仓库并附合法 `[1]` 的流畅答案，即使引用与主张无关，也可能得到 `passed=true`。如果检索语料过期或项目能力证据跨作用域混合，错误首选仍可能在 UI 中显示成“通过证据质量校验”。

现有证据无法回答真实错误率，因为开发者可见的固定 fixture、句子级分类和无真实 provider 的 E2E 主要证明确定性回归，不证明真实泛化。

最小补证动作：由未参与当前规则调参的人冻结一套不提交公开仓库的 blind pack，覆盖未见项目、真实 no-match、比较、解释、学习计划、setup/runtime、UI/inference、optional/required 和过期数据；逐条人工标注候选、硬约束、可支持主张和应否展示首选。首次运行只建立基线，不边跑边改标签。

## 三、最大的遗漏

### 公共归档只对白名单“输入”做选择，没有对白名单“最终 tree”做证明

目标要求是：公开 `weekly-archive` 的最终提交只能包含显式允许的公共投影。

【事实】`scripts/publish_archive_branch.py` 的 `_public_sources()` 只选择显式 docs 文件、`docs/weekly`、`docs/app`、全部 `reports/**/*.md` 和四类公共 JSON。

【事实】`_synchronize_archive_tree()` 只删除目标 worktree 中的 `docs/`、`reports/`、`data/`。归档分支根目录或其他旧目录不会被清理。

【事实】`_scan_staged_tree()` 会扫描完整 index，但路径级只拒绝匹配 `\.sqlite(?:-|$)` 的文件，并未验证每个 staged path 都属于公共 allowlist。`.sqlite3`、`.db`、`.db3`、`.env`、`.pem`、`.key`、`.log` 和未知根目录文件主要依赖 push 后的远端审计才发现。

【推断】若 `weekly-archive` 预先存在 `legacy/private.db`、根目录 `.env` 或未知目录，它可以绕过源选择并进入提交；远端 attestation 即使随后失败，文件也可能已经被 push 到公开分支。

这是当前最大的遗漏，因为它处于不可逆公开边界，且直接推翻“最终 tree 已由 allowlist 证明”的安全承诺。当前远端 latest tree 已知干净，因此这是未来发布绕过风险，不是对当前已公开敏感文件的断言。

最小修复动作：把公共路径、允许后缀和禁止后缀提取为单一、版本化 manifest；发布前要求 staged tree 的路径集合与本轮公共投影集合完全一致，任何额外路径 fail closed；push 后远端验证器复用同一 manifest。测试必须植入归档根目录和任意旧目录中的未知文件，证明它们在 push 前被删除或拒绝。

## 四、可能没有意识到的事实

### 1. 流式草稿已经修好，但“质量通过”仍主要是格式通过

【事实】`src/rag/answering.py` 已在发送 delta 前完整缓冲并调用质量检查；失败时只发送规则降级 final。V3 的“未校验草稿先展示”当前已修复。

【事实】主张支持、证据相关性和数据新鲜度仍未执行实际校验。

【推断】时序安全已经提高，但事实正确性没有因此自动提高。

### 2. 绿色 CI 不能阻止检索质量退化

【事实】`evaluate_project_match.py` 和 `evaluate_project_recommendations.py` 无冻结阈值；成功计算指标后，两个 `main()` 固定返回 0，不会因为 Recall、MRR 或 Top-1 低于质量下限而非零退出。项目匹配单测主要检查指标存在并落在 `[0,1]`，推荐评估只对硬约束违反率有强门禁。

【推断】Recall、MRR 或 Top-1 大幅下降，甚至系统保守地“什么都不推荐”，CI 仍可能全绿。

### 3. “真实 Playwright”不等于真实模型或真实生产环境

【事实】真实 E2E 的“真实”指真实 FastAPI、同源页面和临时 SQLite；启动器清空 Kimi、GitHub、Telegram 等业务凭据。

【推断】它适合 PR 级确定性回归，但不能证明真实 provider 的 SSE 分块、429、超时、非法 JSON、网关错误和模型行为。

### 4. 写接口有鉴权，不代表管理数据的读取安全

【事实】管理写路由复用 constant-time token 校验；但反馈、订阅、通知候选/投递、Agent 任务/运行、job 事件和部分开发上下文 GET 仍是无鉴权读取。反馈返回可包含 `note`。

【推断】若服务不再严格绑定到单用户 loopback，局域网、同机其他进程或错误代理配置可能读取运行态和用户态数据。

### 5. 一些 GET 并不是纯读

【事实】当前仍暴露的 legacy 兼容 GET Ask/SSE 可接收 `auto_build`；`rag_explain()` 会持久化解释，向量路径在 `auto_build=true` 时可构建 embedding。

【推断】浏览器预取、重试或匿名重复请求可能造成 CPU、磁盘写放大和 provenance 污染。

### 6. 系统已经会“学偏好”，但不能复盘为什么学错

【事实】项目反馈会形成最高约 `±40` 的 preference adjustment 并影响后续排序；反馈没有关联当时 query、route、候选顺序、eligibility、语料版本和最终首选的 decision ID。

【推断】一次误标可能长期影响不同问题，系统无法重放当时决策以判断是检索错、约束错、数据旧还是用户偏好变化。

### 7. 浏览器本地保存仍然是数据保留

【事实】React 工作台最多保存 10 个会话、每个 20 轮的完整问题和 `RagAnswer` 到 localStorage；旧管理工作台也保存最多 20 轮。管理 token 不持久化、下一轮不回传历史回答，这些边界仍成立。

【推断】共享电脑、同源 XSS、浏览器扩展或浏览器同步仍可能读取历史；本地保存不等于数据最小化。

### 8. 文档已经出现安全契约漂移

【事实】README 一处仍概括“`docs/reports/data` 会发布”，后文才说明显式投影；`docs/api.md` 仍把 delta 描述为“未通过质量闸门的生成草稿”，React 工作台也显示“正在生成草稿/等待证据质量校验”，均与当前后端“基础闸门通过后才发送 delta”冲突。

【推断】后续开发者可能按旧文档重新引入已修复风险，或错误理解归档边界。

### 9. 当前 allowlist 范围仍偏宽

【事实】`docs/app` 允许 `.map`，`reports/**/*.md` 全量递归发布，非 JSON 文件直接复制；内容正则不是通用脱敏器。

【推断】未来 source map、调试报告或事故 Markdown 可能公开内部路径、源码注释、查询样本和错误详情。

### 10. main 的 CI 是事后报警，不是合并门

【事实】远端 Actions 已启用且最新三 job 成功；GitHub API 返回 main 未配置分支保护。

【推断】失败提交仍可先进入 main，再由 CI 报警。当前这是已接受风险，但不能被描述成“CI 已阻止坏提交”。

## 五、对抗性场景

| 场景 | 当前可能行为 | 正确行为 |
| --- | --- | --- |
| 归档分支根目录遗留 `legacy/private.db` | 不属于 `docs/reports/data`，源同步不删除；可能先 push，后审计失败 | push 前 staged tree 与 manifest 精确相等；额外路径删除或 fail closed |
| 模型写出错误结论并附合法 `[1]` | `passed=true`，UI 可能展示首选 | 逐声明验证引用支持；不支持时不得成为正式首选 |
| 来源最新但 corpus/embedding 仍旧 | 只看到零散 `run_date`，`data_freshness=unknown` | 返回三层水位和 stale 原因，阻止无提示“最新/首选” |
| 用户说“比较第二和第三个项目” | 路由只决定 candidate scope，仍按普通搜索回答 | `answer_type=compare`，使用比较证据策略和结构化差异输出 |
| 安装可离线，但运行时调用云 API | 所有句子跨 scope 聚合，可能误合格或误拒绝 | 对同一 phase/surface/necessity 聚合，runtime blocker 优先 |
| 匿名请求读取反馈或订阅状态 | 管理 GET 可能直接返回运行态或 note | admin read 与 public read 分离，私有 GET 强制 token |
| 重复 GET Ask 并开启 auto_build | 可能持久化解释或重建 embedding | GET 严格纯读，写入只走鉴权 POST/计划任务 |
| 检索退化为零命中 | 核心指标脚本仍返回成功，CI 可能绿色 | 低于冻结阈值立即非零退出并阻断提交 |
| 真实 provider 返回异常分块或持续 429 | PR E2E 无法覆盖 | 独立 synthetic provider canary，脱敏、限额、非业务数据 |
| Pages tree 安全但资源路径错误 | 远端 tree audit 通过，用户页面仍 404 或缺资源 | 发布后关键 URL、content-type、资源加载和 app 启动 smoke |

## 六、整改优先级

### P0：先停止错误确定性和公开边界绕过

#### P0-14：最终 staged tree 统一 manifest

- **问题**：源 allowlist 不能证明最终 Git tree allowlist。
- **建议**：增加 schema-versioned 公共归档 manifest；选择器、staged tree 校验、测试和远端 attestation 共用；显式拒绝 `.sqlite/.sqlite3/.db/.db3/-wal/-shm/.env/.pem/.key/.log`，未知路径默认拒绝。
- **预期证据**：旧根目录/未知目录文件在 push 前被删除或失败；远端 tree 路径集合与本地 manifest attestation 一致。
- **影响**：高；**紧急性**：现在；**可逆性**：可逆。
- **最小验证**：临时归档分支植入 `legacy/private.db`、`.env` 和无害未知文件，断言不会执行 commit/push。

#### P0-15：把检索与推荐指标变成 CI 门禁

- **问题**：指标当前主要是报表，退化不一定失败。
- **建议**：建立版本化阈值 manifest；两个 evaluator 低于阈值时非零退出；CI 显式运行四套 evaluator 并记录 dataset hash、commit 与 JSON artifact。
- **预期证据**：故意把返回结果清空或打乱时 CI 失败；当前固定基线继续通过。
- **影响**：高；**紧急性**：现在；**可逆性**：可逆。
- **最小验证**：先锁定当前已接受固定基线，再加入一条必然失败的测试验证门禁有效；阈值只用于同版本数据集，不伪装成真实泛化指标。

#### P0-16：真实主张支持闸门

- **问题**：合法引用编号可包装错误或无关结论。
- **建议**：把质量结果拆为格式安全、硬约束、证据相关、主张支持和新鲜度；每条项目事实绑定 citation/chunk；`claim_support` 未评估或失败时不得标记完整质量通过，不得显示确认首选。
- **预期证据**：有合法 `[1]` 但引用不支持主张、引用反驳主张、跨项目引用和无来源比较结论全部 fail closed。
- **影响**：高；**紧急性**：现在；**可逆性**：可逆。
- **最小验证**：先用确定性 claim/citation fixture，不调用真实模型；保持 `meta → delta* → final` 契约和无状态追问。

#### P0-17：数据新鲜度门禁

- **问题**：系统无法证明“当前”证据水位。
- **建议**：增加 `source_latest_date`、`corpus_latest_date`、`embedding_latest_date`、`stale_days` 和统一 `as_of`；按周更 cadence 默认超过 8 天标记 stale，阈值可配置并在数据契约中声明。
- **预期证据**：来源新/索引旧、corpus 新/embedding 旧和全部过期均有不同诊断；stale 时 UI 明示，不能无提示称“最新”或展示确认首选。
- **影响**：高；**紧急性**：现在；**可逆性**：可逆。
- **最小验证**：只用临时 SQLite 和固定日期 fixture，不读取本机运行态数据库。

#### P0-18：项目级能力作用域

- **问题**：能力事实没有 phase、surface 和 necessity，跨句/跨 chunk 合并可能产生 false eligibility。
- **建议**：引入结构化 `CapabilityFact(capability, phase, surface, necessity, state, evidence_id)`；只在兼容 scope 内聚合，runtime、inference 和 required blocker 优先。
- **预期证据**：setup/runtime、UI/inference、optional/required、initial-download/steady-state、control-plane/data-plane 的项目级多句、多 chunk blind 集 false eligibility 为 0。
- **影响**：高；**紧急性**：近期；**可逆性**：可逆。
- **最小验证**：新增独立项目级 fixture，不修改 hybrid 权重、不允许 model_enrichment 决定 eligibility。

### P1：建立可学习、可复现的产品闭环

#### P1-1：顶层回答决策器

- 分离 `conversation_relation`、`answer_type`、`retrieval_scope`、`retrieval_query`、`resolved_user_request` 和 `evidence_policy`。
- `answer_type` 至少支持 `search/explain/compare/learning_plan/clarify/unsupported`；保持 POST 最小上下文，不新增服务端聊天会话。
- 先冻结 blind 意图集，再实现；比较请求必须生成结构化差异，不重新退化为普通搜索。

#### P1-2：私有查询级决策快照与反馈关联

- 使用 `decision_id` 保存结构化目标、路由、requirements、候选顺序、eligibility、规则/语料/embedding 版本、水位和是否展示首选。
- 反馈引用 `decision_id`，记录接受/拒绝原因；不保存完整 assistant 回答、prompt_context、query/note 原文到公共投影。
- 先确认私有持久化位置；不得回流 `weekly-archive`。

#### P1-3：管理读鉴权与 GET 纯读

- 将 public read 与 admin read 分层；反馈、订阅、通知、任务、job event 和开发上下文运行详情等私有 GET 复用管理 token。
- 当前仍暴露的 legacy 兼容 GET Ask/SSE 禁止 auto-build 和解释持久化；构建、回填和写解释只走受鉴权 POST/计划任务。
- 保持公开 Pages 静态投影和现有写接口确认门不变。

#### P1-4：独立 blind、provider canary 与 Pages smoke

- 固定集继续作为公开回归；blind pack 由独立标注者维护，不公开原文，只记录 hash 和聚合指标。
- 手动或定时运行 synthetic provider canary，覆盖超时、429、非法 JSON、跨 delta 注入和引用欺骗；不把真实网络接入普通 PR CI。
- 归档发布后验证关键 Pages URL、content-type、静态资源、最新周报入口和 React app 启动，并记录 archive commit SHA。

#### P1-5：浏览器数据最小化与不可信语料默认隔离

- 对话默认仅当前会话内存；持久化改为显式 opt-in、TTL 和一键清除，至少剥离 prompt_context、完整 evidence/citations 和内部诊断。
- 所有外部 README/HTML 默认标记为 untrusted，确定性规则用于清洗和分类，不以“是否命中少量注入短语”决定是否可信。

#### P1-6：修正文档和 UI 契约漂移

- README 统一改为“只发布 manifest 允许的公共投影”，删除整目录发布歧义。
- `docs/api.md` 将 delta 改为“已通过当前基础闸门的分段输出”，同时明确当前基础闸门不等于 claim support 或 freshness 通过。
- React 状态文案改为“已通过基础闸门，正在分段展示”，不得暗示仍在发送未校验草稿，也不得把基础闸门描述成完整事实校验。

### P2：扩大覆盖与可维护性

1. 保留 `ApiRepository` 外观契约，按 RAG、推荐、反馈、订阅通知和任务逐域提取 service；当前单文件约 8,219 行、约 97 个类方法，回归半径过大。
2. 从生产归档移除 `.map`；`reports/**/*.md` 改为显式周报/报告 manifest，不直接复制任意 Markdown。
3. 为真实 FastAPI Playwright 增加移动端关键流程；保持 mock 与 real 输出目录隔离。
4. 团队协作扩大后启用 PR、required checks 和 main 分支保护；在此之前继续诚实记录 CI 是 push 后报警。
5. 建立长期质量趋势：false eligibility、stale rate、fallback rate、clarification precision/recall、unsupported acceptance、decision replay consistency 和每请求成本。

## 七、建议实施顺序

```text
P0-14 最终归档 manifest
→ P0-15 评估阈值与 CI 门禁
→ P0-16 主张支持闸门
→ P0-17 数据新鲜度
→ P0-18 能力作用域
→ P1-1 顶层回答决策器
→ P1-2 决策快照与反馈
→ 管理读边界、provider/Pages 验证、浏览器最小化
→ repository 分域重构与分支保护
```

不能抢跑的工作：

- 不先调 hybrid 权重；没有冻结质量门禁时无法判断调优还是过拟合。
- 不先迁移 Responses API、Agents SDK 或引入服务端聊天会话；它们不能修复意图、证据、作用域和新鲜度问题。
- 不把真实 Kimi 接入普通 PR CI；先用确定性 fixture 和 synthetic provider canary。
- 不先建立反馈自动调权；没有 decision snapshot 时反馈不可复现。
- 不重写 `weekly-archive` 历史；用户已确认不存在真实信息，本路线图只修复未来发布边界。
- 不处理已知不可达损坏 loose object，除非另行制定备份优先的 Git 修复方案。

## 八、阶段验收标准

1. 公共归档本地 staged tree 和远端 latest tree 均与同一 manifest 一致，未知路径与禁止后缀为 0；根目录和旧目录遗留测试在 push 前失败或删除。
2. 四套 evaluator 在 CI 中显式运行；项目匹配和推荐低于同版本冻结阈值时非零退出。阈值来源标记为“当前固定 fixture 回归基线”，不称为真实准确率。
3. 有合法引用但主张不受支持的回答不得得到完整质量通过，不得发送 provider delta 或展示确认首选；POST 与 SSE final 继续等值。
4. Ask 和 diagnostics 返回三层数据水位、`stale_days` 与 `as_of`；超过默认 8 天时页面显示警告并限制“最新/首选”。8 天是按当前周更 cadence 选择的初始项目策略，需配置化。
5. 项目级作用域 blind 集的 false eligibility 和硬约束违反率为 0；其余 Top-1、Recall、澄清指标在首次独立 blind 基线后由用户确认阈值，不提前虚构达标线。
6. `answer_type` 至少覆盖搜索、解释、比较、学习计划、澄清和不支持；比较不会重新搜索全归档，unsupported 不展示项目首选。
7. 管理态/用户态 GET 未授权返回 401/403；GET Ask 不增加 explanation、embedding、job 或反馈行数。
8. 每条可学习反馈关联一个私有 `decision_id`，能重放当时结构化目标、候选、版本和水位；公共投影不包含该私有快照。
9. synthetic provider canary 和 Pages smoke 分开记录；前者证明协议/降级，后者证明用户侧页面可用，均不使用真实用户数据。
10. 完整前端、双 Playwright、Python、安全、四套评估、`git diff --check` 和 `docs/app` 一致性全部通过；远端三个 CI job 成功后才关闭阶段。

## 九、最终判断

应保留：显式公共投影方向、远端 attestation、SSE 完整缓冲、无状态追问、结构化 recommendations、管理写确认门、临时 SQLite E2E 和提交级三 job CI。

应暂停：把 `answer_quality.passed` 解释为事实正确，把固定 fixture 满分解释为真实泛化，把 source allowlist 解释为最终 tree allowlist，以及在没有新鲜度和 scope 证据时输出无警告“最新/首选”。

下一阶段最高优先级是 **P0-14 最终 staged tree manifest**。它是低成本、高信息量、可逆的安全修复，并能关闭当前公开发布边界中唯一被静态反证的绕过路径。随后立即把现有评估变成门禁，再推进主张支持、新鲜度和能力作用域。

项目当前最诚实的定位是：**具备较强确定性工程回归和公共归档治理的 GitHub 项目研究原型，但真实推荐正确性、作用域能力判断、新鲜度和反馈可学习性仍未建立独立证据。**

## 十、执行注意事项

1. 所有新增公共归档规则必须 fail closed，并由单一 manifest 驱动选择、staged tree 校验、测试和远端 attestation。
2. 保持 `/v1/rag/ask`、`/v1/rag/ask/stream` 现有字段与 `meta → delta* → final` 兼容；新增语义优先采用非破坏字段。
3. 保持无状态追问：不新增服务端聊天会话，不把历史 assistant 回答、citations、evidence 或 prompt_context 当作事实证据。
4. `model_enrichment` 只能补充理由和候选证据，不能决定硬约束通过或首选。
5. 新鲜度、claim support 和 match confidence 未校准时，继续输出 unknown/not_evaluated，不伪造 medium/high。
6. 查询级快照必须使用私有持久化；不得进入公共 JSON、Pages 或 `weekly-archive`。
7. 真实外发、历史改写、凭据轮换和 Git 对象修复仍需单独授权；不因本报告自动执行。
8. 先冻结基线与 blind hash，再修改规则；评估失败或指标下降时停止提交并定位原因。
9. 报告中的静态发现不等于已执行测试；本阶段的实际验证结果以提交前命令和远端 CI 为准。
