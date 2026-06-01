# 操作日志

本文件记录 Codex 对本仓库执行的文档审查和项目规划操作。

## 2026-06-01 追加：RAG 维护计划自动创建回填任务

### 1. 开发目的
RAG 回填已经支持 planned 任务执行，但仍需要人工判断是否存在覆盖缺口。为了把“覆盖缺口检测 -> 创建补库任务 -> 执行补库”串成维护闭环，本次新增 RAG 维护计划入口，自动按覆盖缺口决定是否创建回填任务。

### 2. 修改内容
1. 新增 `POST /v1/rag/maintenance-plan`，先检查 RAG 覆盖缺口，再按需创建 `rag_backfill` planned 任务。
2. 如果缺口数低于阈值，接口只返回健康状态，不创建任务。
3. 如果已存在相同参数的 active `rag_backfill` 任务，接口返回 `duplicate_of`，避免重复补库。
4. 新增 `scripts/plan_rag_maintenance.py`，用于本地或后续 GitHub Actions 调度时创建维护计划。
5. 更新 README、API 文档、数据契约和后端测试。

### 3. 验证
已运行 `python -m unittest discover -q`、`python scripts\security_check.py` 和 `git diff --check`。

## 2026-06-01 追加：RAG 回填支持 planned 任务执行

### 1. 开发目的
RAG 回填已经能写入任务审计，但仍主要是即时 API 动作。为了把数据库补库纳入统一任务模型，本次新增 RAG 回填计划任务入口，并让本地 job runner 能执行 `rag_backfill` 任务。

### 2. 修改内容
1. 新增 `POST /v1/rag/backfill-plan`，用于创建 `kind=rag_backfill`、`status=planned` 的计划任务。
2. `/v1/job-execution-check` 支持检查 `rag_backfill` 任务，真实写库仍要求 `confirm_execution=true`。
3. `/v1/jobs/{job_id}/execute` 可执行 planned RAG 回填任务，并写入 runner 事件和精简执行结果。
4. `scripts/run_planned_job.py` 扩展为通用 planned 任务执行入口，当前支持周报任务和 RAG 回填任务。
5. 更新 README、API 文档、数据契约和后端测试。

### 3. 验证
已运行 `python -m unittest discover -q`、`python scripts\security_check.py` 和 `git diff --check`。

## 2026-06-01 追加：RAG 回填接入任务审计

### 1. 开发目的
RAG 回填已经具备脚本、后端 API 和管理页入口，但每次补库动作还没有进入任务审计体系。为了让数据库维护能力可追踪、可复盘，并为后续 Agent 自动补库预留统一任务模型，本次把 RAG 回填 API 接入 `jobs` 与 `job_events`。

### 2. 修改内容
1. `POST /v1/rag/backfill-explanations` 每次调用都会创建 `kind=rag_backfill` 的任务记录。
2. 回填开始、完成和失败会写入 `job_events`，可通过 `/v1/jobs/{job_id}/events` 查询。
3. `/v1/jobs` 的 `kind` 筛选支持 `rag_backfill`。
4. 回填响应新增 `job_id` 和精简任务结果，便于前端或 Agent 继续追踪。
5. 更新 README、API 文档、数据契约和后端测试。

### 3. 验证
已运行 `python -m unittest discover -q`、`python scripts\security_check.py` 和 `git diff --check`。

## 2026-06-01 追加：管理首页接入 RAG 解释回填

### 1. 开发目的
后端已经提供受控 RAG 解释回填接口，但用户仍需要手动调用 API 或脚本。为了让数据库补库能力进入本地管理闭环，本次把回填入口接入 `admin.html`，支持先预览再确认写入。

### 2. 修改内容
1. `admin.html` 新增 RAG 回填数量输入、预览按钮、确认写入复选框和执行按钮。
2. 新增 `setupRagBackfill`、`runRagBackfill` 和 `ragBackfillHtml`。
3. 前端调用 `POST /v1/rag/backfill-explanations`，默认预览；执行写库前必须勾选“确认写入 SQLite”。
4. 回填完成后刷新数据库/RAG 概览，便于查看解释历史覆盖变化。
5. 更新 README、API 文档和页面构建测试。

### 3. 验证
已运行 `python -m unittest discover -q`、`python scripts\security_check.py`、`git diff --check` 和 `docs/admin.html` 结构校验。浏览器直接打开本地页面时被客户端策略拦截，未继续绕过。

## 2026-06-01 追加：新增 RAG 解释回填 API

### 1. 开发目的
RAG 解释回填已经有脚本入口，但后端和后续管理页、Agent 工具调用还不能直接复用同一能力。本次把回填逻辑下沉到 `ApiRepository`，并增加受控 API 入口，让数据库补库从“脚本能力”升级为“后端能力”。

### 2. 修改内容
1. 新增 `ApiRepository.backfill_rag_explanations`，作为脚本和 API 的共用回填逻辑。
2. 新增 `POST /v1/rag/backfill-explanations`。
3. API 默认 `dry_run=true`；如果未传入 `confirm_execution=true`，即使请求 `dry_run=false` 也会自动改回预览模式。
4. `scripts/backfill_rag_explanations.py` 改为复用后端仓库层，减少重复逻辑。
5. 更新 API 文档、README 和单元测试。

### 3. 验证
已运行 `python -m unittest discover -q`、`python scripts\security_check.py` 和 `git diff --check`。

## 2026-06-01 追加：新增 RAG 解释回填脚本

### 1. 开发目的
RAG 覆盖缺口接口已经能找出缺少解释历史的项目，但还需要一个可执行的补库入口。本次新增回填脚本，把“发现缺口”推进到“批量生成规则版解释并写入 SQLite”，继续补齐数据库与 RAG 核心闭环。

### 2. 修改内容
1. 新增 `scripts/backfill_rag_explanations.py`。
2. 脚本读取 RAG 覆盖缺口，优先选择 `explanation_count=0` 的项目。
3. 支持 `--dry-run` 预览、`--limit` 控制数量、`--mode vector` 和 `--auto-build`。
4. 执行模式会调用现有 `rag_explain`，生成规则版解释并写入 `rag_explanations`。
5. 更新 README、API 文档和脚本测试。

### 3. 验证
已运行 `python -m unittest discover -q`、`python scripts\security_check.py` 和 `git diff --check`。

## 2026-06-01 追加：新增 RAG 覆盖缺口接口

### 1. 开发目的
当前 RAG 已经具备语料、证据块、embedding、解释历史和项目级聚合能力，但还缺少“哪些项目没有被 RAG 充分覆盖”的健康检查入口。本次新增覆盖缺口接口，用于后续补库脚本、Agent 自动优化和管理页健康检查。

### 2. 修改内容
1. 新增 `GET /v1/rag/coverage`。
2. 后端统计项目语料、证据块、embedding 和解释历史覆盖情况。
3. 返回缺口项目列表，包含证据块数量、embedding 数量、解释数量、平均质量分和缺口原因。
4. 返回整体覆盖率、健康项目数量和补库建议。
5. 更新 README、API 文档和后端测试。

### 3. 验证
已运行 `python -m unittest discover -q`、`python scripts\security_check.py` 和 `git diff --check`。首次测试发现覆盖建议可能为空，已补充默认建议后复测通过。

## 2026-06-01 追加：项目详情页改用单项目 RAG 聚合接口

### 1. 开发目的
后端已经提供 `/v1/projects/{owner}/{repo}/rag`，但项目详情页仍分别调用 RAG 检索和解释历史接口。为了减少前端拼装逻辑，并让后续 Agent/RAG 编排复用统一数据包，本次把项目详情页切换到单项目 RAG 聚合接口。

### 2. 修改内容
1. `project.html` 的 `loadProjectRag` 改为读取 `/v1/projects/{owner}/{repo}/rag?limit=6&explanation_limit=5`。
2. 移除项目详情页中不再需要的前端 RAG 查询拼装逻辑。
3. 保留“RAG 证据”和“RAG 解释历史”展示，但数据来源改为聚合接口。
4. 更新 README、API 文档和页面构建测试。

### 3. 验证
已运行 `python scripts\build_pages.py`、`python -m unittest discover -q`、`python scripts\security_check.py` 和 `git diff --check`。

## 2026-06-01 追加：新增单项目 RAG 聚合接口

### 1. 开发目的
项目详情页和后续 Agent/RAG 编排需要同时读取项目摘要、证据块、引用、解释历史和解释质量。如果继续由前端分别调用多个接口，后续接入 LangChain 或工具调用会重复拼装数据。本次新增单项目 RAG 聚合接口，把项目级 RAG 数据收束成稳定后端能力。

### 2. 修改内容
1. 新增 `GET /v1/projects/{owner}/{repo}/rag`。
2. `ApiRepository.project_rag_bundle` 聚合项目摘要、RAG 检索结果、引用、`prompt_context`、项目解释历史和项目级解释质量摘要。
3. 支持 `mode=fts5` 和 `mode=vector`，向量模式继续复用本地 `local-hash-v1` 能力。
4. `/v1/health` 能力声明新增 `rag_project_bundle`。
5. 更新 README、API 文档和后端测试。

### 3. 验证
已运行 `python -m unittest discover -q`、`python scripts\security_check.py` 和 `git diff --check`。

## 2026-06-01 追加：项目详情页展示 RAG 解释历史

### 1. 开发目的
后端已经支持按项目过滤 RAG 解释历史，但项目详情页仍只展示证据块。为了让单个项目的“证据、解释、质量”形成闭环，本次把项目级解释历史接入 `project.html`。

### 2. 修改内容
1. `project.html` 在 API 模式下读取 `/v1/rag/explanations?repo=owner/name&limit=5`。
2. 项目详情页新增“RAG 解释历史”区域，展示问题、检索模式、质量等级、质量分、引用数量和解释答案。
3. 静态模式保留提示，不触发本地后端专属查询。
4. 更新 README 和页面构建测试。

### 3. 验证
已运行 `python scripts\build_pages.py`、`python -m unittest discover -q`、`python scripts\security_check.py` 和 `git diff --check`。

## 2026-06-01 追加：RAG 解释历史支持按项目过滤

### 1. 开发目的
RAG 解释已经能写入 SQLite 并做质量汇总，但项目详情、后续前端管理页和 LangChain/RAG 编排还缺少“某个项目关联了哪些历史解释”的查询入口。本次把解释历史和具体仓库关联起来，继续补齐数据库与 RAG 的核心闭环。

### 2. 修改内容
1. `/v1/rag/explanations` 新增 `repo=owner/name` 过滤参数。
2. `ApiRepository.rag_explanations` 支持同时按问题关键词和覆盖仓库过滤。
3. `/v1/health` 能力声明新增 `rag_project_explanations`。
4. 更新 README、API 文档和后端测试。

### 3. 验证
已运行 `python -m unittest discover -q`、`python scripts\security_check.py` 和 `git diff --check`。

## 2026-05-30 追加：管理首页接入 RAG 质量概览

### 1. 开发目的
后端已经提供 RAG 质量概览接口，但管理首页还没有可视入口。为了让数据库和 RAG 能力更容易被检查，本次把质量统计接入 `admin.html`，让用户不用直接看 JSON 也能判断解释质量、低质量样本和下一步优化重点。

### 2. 修改内容
1. `admin.html` 的“数据库与语料”区域新增 RAG 质量概览展示容器。
2. API 模式读取 `/v1/rag/quality-summary?limit=5`。
3. 展示解释总数、平均质量分、最高/最低质量分、质量分布、改进建议和最近低质量解释。
4. 静态模式提示需要启动本地后端或添加 `api=1`。
5. 更新 README、API 文档和页面构建测试。

### 3. 验证
已运行 `python scripts\build_pages.py`、`python -m unittest discover -q`、`python scripts\security_check.py` 和 `git diff --check`。

## 2026-05-30 追加：新增 RAG 质量概览接口

### 1. 开发目的
RAG 解释已经有质量分和历史入库，但还缺少聚合视角。后续管理页、自动优化和模型替换评估需要快速知道当前解释整体质量如何、低质量样本有哪些、应该优先补语料还是调整检索模式。

### 2. 修改内容
1. 新增 `GET /v1/rag/quality-summary`。
2. 后端汇总 `rag_explanations` 的总数、平均质量分、最高/最低质量分、质量等级分布、置信度分布和检索模式分布。
3. 返回最近低质量解释和最近解释样本，方便后续管理页定位问题。
4. 返回规则版 `recommendations`，提示下一步应补充语料、对比 FTS/向量检索或接入模型总结。
5. 更新 README、API 文档和后端测试。

### 3. 验证
已运行 `python -m unittest discover -q`、`python scripts/security_check.py` 和 `git diff --check`。

## 2026-05-30 追加：新增 RAG 解释质量评估

### 1. 开发目的
RAG 解释结果已经能够写入 SQLite，但后续要判断解释是否可靠、是否需要补语料或替换 embedding，不能只看文本答案。本次为每条解释增加规则版质量评估，让数据库能直接记录证据覆盖和引用完整度。

### 2. 修改内容
1. `rag_explanations` 新增 `quality_score`、`quality_level` 和 `quality_json` 字段。
2. `initialize` 会为旧版本地 SQLite 自动补齐质量字段，避免旧库升级时报错。
3. `/v1/rag/explain` 响应新增 `quality`，统计证据块、引用、覆盖项目、解释依据、风险数量和 `prompt_context`。
4. `/v1/rag/explanations` 返回历史解释的质量分和质量等级。
5. 更新 README、API 文档、数据契约和测试。

### 3. 验证
待运行 `python -m unittest discover -q`、`python scripts/security_check.py` 和 `git diff --check`。

## 2026-05-30 追加：RAG 解释结果写入 SQLite

### 1. 开发目的
RAG 解释接口已经能把证据块整理成推荐解释，但如果解释结果不入库，后续无法追踪“某次问题召回了什么、解释质量如何、FTS 与向量模式差异在哪里”。本次继续优先建设数据库和 RAG 核心能力，把解释结果变成可查询、可复用、可评估的数据资产。

### 2. 修改内容
1. SQLite 新增 `rag_explanations` 表，保存解释 ID、query、过滤条件、检索模式、模型、命中数量、置信度、答案、引用和完整解释 JSON。
2. `/v1/rag/explain` 每次生成解释后会写入或更新 `rag_explanations`。
3. 新增 `GET /v1/rag/explanations`，用于查询历史解释结果。
4. 数据库概览新增 `rag_explanations` 表计数和 `ready_for_explanation_history` 状态。
5. 更新 README、API 文档、数据契约和测试。

### 3. 验证
待运行 `python -m unittest discover -q`、`python scripts/security_check.py` 和 `git diff --check`。

## 2026-05-30 追加：新增 RAG 解释层接口

### 1. 开发目的
当前数据库和 RAG 已经能输出语料、证据块和本地向量检索结果，但还缺少面向产品功能的解释层。后续项目详情、推荐理由、问答和 LangChain 编排都需要一个稳定的“证据到解释”接口，因此本次优先建设后端核心能力，而不是继续优化末端页面样式。

### 2. 修改内容
1. 新增 `GET /v1/rag/explain`，支持 `fts5` 和 `vector` 两种模式。
2. 新增 `repository.rag_explain`，复用已有 `/v1/rag/retrieve` 与 `/v1/rag/vector-search` 的召回结果。
3. 新增规则版解释结构，包含 `answer`、`why_recommended`、`evidence`、`risks`、`next_steps` 和 `coverage`。
4. `/v1/health` 新增 `rag_explain` 能力标识。
5. 更新 README、API 文档和后端测试。

### 3. 验证
待运行 `python -m unittest discover -q`、`python scripts/security_check.py` 和 `git diff --check`。

## 2026-05-29 追加：项目详情页接入 RAG 证据

### 1. 开发目的
RAG 检索已经有后端 API 和管理首页入口，但单个项目详情页还不能直接展示“为什么这个项目值得看”的证据块。本次把项目详情页接到 `/v1/rag/retrieve`，让用户在查看某个仓库时直接看到可引用的历史语料。

### 2. 修改内容
1. `project.html` 在本地后端或 `api=1` 模式下读取项目详情后，会额外调用 `/v1/rag/retrieve`。
2. 项目详情页新增“RAG 证据”模块，展示召回摘要、证据块、引用 ID 和可展开的 `prompt_context`。
3. 静态 GitHub Pages 模式继续只读取 `projects.json`，不调用后端，也不会阻塞页面渲染。
4. 更新 README、API 文档和页面构建测试，记录详情页的 RAG 读取策略。

### 3. 验证
待运行 `python scripts/build_pages.py`、`python -m unittest discover -q`、`python scripts/security_check.py` 和 `git diff --check`。

## 2026-05-29 追加：管理首页新增 RAG 检索入口

### 1. 开发目的

数据库和 RAG 后端已经具备语料、证据块和本地向量检索接口，但用户还需要一个网页入口直接查看召回结果。本次把 RAG 检索放进本地管理首页，先实现必要前端入口，不做复杂前端工程化。

### 2. 修改内容

1. `admin.html` 的“数据库与语料”区域新增 RAG 问题输入、检索方式选择和语言过滤。
2. 支持调用 `/v1/rag/retrieve` 做 FTS 证据检索。
3. 支持调用 `/v1/rag/vector-search` 做本地向量检索，并在需要时通过 `auto_build=true` 自动构建本地索引。
4. 页面会展示召回证据块、引用 chunk、项目详情链接和 `Prompt Context`。
5. README、API 文档和页面构建测试已同步更新。

### 3. 边界说明

该入口只在本地后端或 `api=1` 模式下启用；静态 GitHub Pages 仍只展示归档入口。页面不保存问题、不调用外部模型、不读取密钥，只复用已有后端 RAG API。

## 2026-05-29 追加：新增本地 RAG embedding 索引

### 1. 开发目的

RAG 已经具备项目级语料和短文本块检索，但后续要接入向量库、LangChain retriever 或真实 embedding 模型，还需要先把“向量索引表、构建命令、向量检索 API”这条链路打通。本次优先建设本地可验证底座，不引入外部模型依赖。

### 2. 修改内容

1. SQLite 新增 `rag_embeddings` 表，保存从 `rag_chunks` 派生的本地 embedding 向量。
2. 新增 `src/rag/embeddings.py`，提供确定性 `local-hash-v1` 向量生成、归一化和相似度计算。
3. 新增 `scripts/build_rag_embeddings.py`，可手动构建本地 RAG embedding 索引。
4. 新增 `GET /v1/rag/vector-search`，支持按问题、语言、方向和来源做本地向量检索。
5. 数据库概览增加 embedding 计数和 `ready_for_vector_search` 状态。
6. README、API 文档、v1 规划、数据契约和测试已同步更新。

### 3. 边界说明

当前 `local-hash-v1` 只用于打通数据表和 API 契约，不代表最终推荐质量。它不调用外部模型、不需要密钥、不改变周报主流程。后续可以替换为真实 embedding 模型或向量数据库，同时保持 `/v1/rag/vector-search` 的响应结构稳定。

## 2026-05-29 追加：新增 RAG 短文本块检索

### 1. 开发目的

上一步已经提供 `/v1/rag/corpus`，但它输出的是项目级语料。真正接入 RAG、embedding 或 LangChain 时，需要更短、更稳定、可引用的证据块。本次优先升级数据库层和 RAG 检索层，继续避免过早绑定外部模型或复杂框架。

### 2. 修改内容

1. SQLite 新增 `rag_chunks` 和 `rag_chunks_fts`，从 `project_corpus` 自动拆分短文本块。
2. JSON 归档导入和 SQLite 自动重建时会同步重建 RAG chunk 索引。
3. 新增 `GET /v1/rag/retrieve`，支持按关键词、语言、方向和来源召回 RAG 证据块。
4. 检索结果返回 `contexts`、`citations` 和 `prompt_context`，后续可以直接接入问答模型或 LangChain retriever。
5. 数据库概览增加 chunk 计数和 `ready_for_chunk_retrieval` 状态。
6. README、API 文档、v1 规划、数据契约和测试已同步更新。

### 3. 边界说明

本次仍然不调用外部模型、不生成 embedding、不写入用户隐私，也不改变周报主流程。当前实现是 RAG 的本地证据召回层；下一步可以在此基础上增加可选的 embedding 构建命令和向量检索表。

## 2026-05-29 追加：新增 RAG 语料输出接口

### 1. 开发目的

当前项目已经具备 SQLite 派生索引和 `project_corpus` 文本语料，但后续接入 embedding、向量库或 LangChain 时，还需要一个稳定的数据出口。本次优先补齐 RAG 底座，而不是继续优化末端页面交互。

### 2. 修改内容

1. 新增 `GET /v1/rag/corpus`，从 SQLite `project_corpus` 输出 RAG-ready 文档。
2. 每条文档包含 `text`、`metadata` 和 `evidence`，后续可以直接进入 embedding 或检索器。
3. 支持 `q`、`language`、`category`、`source` 和 `limit` 参数；有关键词时优先使用 FTS5，失败时回退普通文本匹配，没有关键词时返回最新语料。
4. `/v1/health` 新增 `rag_corpus` 能力标识。
5. README、后端 API 文档和后端测试已同步更新。

### 3. 边界说明

本次只建设数据库到 RAG 的稳定语料出口，不新增外部模型调用、不生成 embedding、不保存用户隐私，也不改变周报采集、评分、推送和订阅任务执行链路。下一步可以在这个接口之上构建向量索引、RAG 问答和项目知识库检索。

## 2026-05-28 追加：任务执行器接收订阅筛选上下文

### 1. 开发目的

订阅已经能生成 planned 周报任务，但执行器此前主要使用 `profile` 和回看天数。为了让订阅中的语言、方向、关键词和数量真正影响后续任务执行，本次把订阅筛选上下文接入 job runner。

### 2. 修改内容

1. `src/job_runner.py` 执行任务时会把 `language`、`category`、`query` 和 `limit` 转换为临时环境变量。
2. `src/settings.py` 会读取这些运行时变量，并合并到 `preferred_languages`、`search_languages`、`preferred_topics` 和 `search_topics`。
3. 任务执行结果新增 `request_context`，记录本次任务使用的 profile、语言、方向、关键词、数量和订阅编号。
4. 新增测试覆盖运行时偏好合并和 job runner 环境变量传递。

### 3. 边界说明

本次只让任务级筛选条件进入既有采集和评分配置，不改动密钥配置、不绕过 dry-run 保护，也不新增外部服务调用。`sort` 暂时保留在任务上下文里，后续可用于定向周报内部排序。

## 2026-05-28 追加：订阅生成 planned 周报任务

### 1. 开发目的

订阅页已经能保存 Java、Python、Agent 开发等偏好，但还没有进入任务执行链路。为了让个性化订阅真正成为后续定向周报和定向推送的入口，本次新增“按订阅生成计划任务”能力。

### 2. 修改内容

1. 新增 `POST /v1/subscriptions/{subscription_id}/trigger`。
2. 接口会读取启用订阅的 profile、语言、方向、关键词、排序和数量，转换成 planned 周报任务。
3. 订阅列表新增“生成任务”按钮，生成后跳转到任务详情页继续人工确认。
4. 生成任务默认 `dry_run=true`，不会直接真实推送。
5. 如果订阅未启用或不存在，接口会返回 blockers，不创建任务。
6. API 文档、README、前端构建测试和后端路由测试已同步更新。

### 3. 边界说明

本次只打通订阅到任务模型的受控入口，不绕过 job runner，不绕过 `confirm_execution`，也不保存任何密钥。真实推送仍依赖后续任务执行确认和环境变量/GitHub Actions Secrets。

## 2026-05-28 追加：订阅配置页接入个性化方向快捷选择

### 1. 开发目的

项目已经具备订阅配置、个性化推荐和多渠道推送入口，但订阅页仍需要手动填写 `profile`、语言和关键词。为了让 Java、Python、Agent 开发等方向真正成为可用的精准推送入口，本次把公开个性化画像接入订阅配置页。

### 2. 修改内容

1. `docs/subscriptions.html` 新增个性化方向快捷按钮区域，由 `profiles.json` 动态生成。
2. 点击方向按钮后自动填充订阅名称、profile、主要语言和关键词。
3. 快捷选择会同步到 URL 参数，方便分享或复现当前订阅输入。
4. `profiles.json` 读取失败时使用内置备用方向，保证本地后端和静态页面都能展示基本入口。
5. README 和页面构建测试已同步更新。

### 3. 边界说明

本次只优化订阅创建入口，不保存任何密钥，不触发真实推送，也不新增用户登录系统。后续可以继续把订阅配置接入更完整的任务执行器、RAG 重排和多渠道精准推送。

## 2026-05-28 追加：项目对比页接入个性化方向快捷选择

### 1. 开发目的

项目对比页已经支持手动输入 `profile`、`language`、`category` 和 `q` 做个性化加权，但真实使用时用户更需要直接选择 Java、Python、Agent 开发等方向。本次把公开个性化画像接入对比页，让对比功能更接近“选择当前需求后比较项目”的核心使用方式。

### 2. 修改内容

1. `docs/compare.html` 新增个性化方向快捷按钮区域，由 `profiles.json` 动态生成。
2. 点击方向按钮后会自动填入方向、语言和关键词，并在已有至少两个仓库时立即重新对比。
3. 当 `profiles.json` 不可读取时，页面会使用内置的最小备用方向，保证静态页面仍可操作。
4. 静态 GitHub Pages 模式和本地后端 API 模式共用同一套偏好参数。
5. README 和页面构建测试已同步更新，避免后续重构时丢失该入口。

### 3. 边界说明

本次只做前端入口和确定性偏好传参，不新增数据库写入、外部模型调用或推送逻辑。后续可以把这些快捷选择继续接入订阅数据库、RAG 重排和多用户个性化推荐。

## 2026-05-27 追加：项目对比推荐支持个性化加权

### 1. 开发目的

项目对比页已经能给出规则版推荐结论，但不同用户当前目标不同，例如 Java、Python、Agent 开发或后端方向。本次把用户偏好接入对比评分，让同一组项目能根据当前需求重新排序。

### 2. 修改内容

1. `/v1/projects/compare` 和 `/api/projects/compare` 新增 `profile`、`language`、`category`、`query` 可选参数。
2. 响应新增 `preference` 字段，记录本次对比使用的偏好上下文。
3. 推荐结论在存在偏好时使用 `rule:v2-preference`，对语言匹配和关键词命中加权。
4. `docs/compare.html` 新增方向、语言、分类和关键词输入框，并把偏好同步到 URL。
5. 静态 GitHub Pages 模式也支持相同的偏好加权逻辑。
6. README、API 文档和测试已同步更新。

### 3. 边界说明

当前仍是确定性规则评分，不调用外部模型。后续可以把 `preference` 作为 RAG 检索、Embedding 重排和 Kimi 解释生成的稳定输入。

## 2026-05-26 追加：项目对比页新增推荐结论

### 1. 开发目的

项目对比页已经能展示矩阵和领先指标，但用户仍需要自己判断“先看哪个”。本次新增规则版推荐结论，让对比页直接给出优先查看项目、推荐理由、注意事项和下一步动作，为后续接入 Kimi、RAG 或 LangChain 解释层留下稳定字段。

### 2. 修改内容

1. `/v1/projects/compare` 和 `/api/projects/compare` 新增 `recommendation` 字段。
2. `recommendation` 包含 `primary_project`、`score`、`reasons`、`cautions`、`next_actions` 和 `scoring_model`。
3. 规则评分综合累计新增 Star、最近新增 Star、质量分、历史入选次数、Trending 排名和风险提示数量。
4. `docs/compare.html` 新增“推荐结论”区块，静态模式和后端 API 模式保持一致。
5. README、API 文档和测试已同步更新。

### 3. 边界说明

当前推荐结论是确定性规则，不调用外部模型，不替代人工判断。后续可以把该字段扩展为模型解释、用户偏好权重、RAG 证据引用和多场景推荐。

## 2026-05-26 追加：串联项目对比入口

### 1. 开发目的

项目对比页已经可以单独访问，但如果用户仍需要手动拼 `repos=` 参数，功能链路不够顺畅。本次把对比入口接入筛选页、个性化推荐页和项目详情页，让用户从正在浏览的项目直接进入横向对比。

### 2. 修改内容

1. `docs/explorer.html` 的项目列表操作区新增“对比”入口。
2. `docs/recommendations.html` 的推荐卡片新增“加入对比”入口。
3. `docs/project.html` 的详情面板新增“与相似项目对比”入口。
4. 相似项目列表从只跳 GitHub 改为同时提供项目详情、GitHub 和“与当前项目对比”。
5. 页面构建测试补充对比入口断言，避免后续页面重构时丢失关键入口。

### 3. 边界说明

本次只串联已有只读数据和已有对比接口，不新增采集、推送、外部模型调用或写入型后端能力。下一步可以继续把对比结果接入模型解释或用户偏好权重。

## 2026-05-26 追加：新增项目对比页

### 1. 开发目的

项目对比 API 已经完成，但用户需要在网页里直接查看多个项目的横向差异。本次新增项目对比页，把后端对比能力做成可见入口，也让 GitHub Pages 静态模式继续可用。

### 2. 修改内容

1. 新增 `docs/compare.html`，由 `scripts/build_pages.py` 生成。
2. 页面支持 `compare.html?repos=owner/a,owner/b`，可输入逗号或换行分隔的仓库全名。
3. 本地后端或 `api=1` 模式优先读取 `/v1/projects/compare`。
4. 静态模式读取 `projects.json` 并在前端聚合对比数据。
5. 页面展示项目数量、领先项目、对比摘要、对比矩阵、项目卡片和未找到项目。
6. 周报首页、README 和页面构建测试已补充对比页入口。

### 3. 边界说明

该页面只读公开归档和本地后端只读接口，不触发采集、任务执行或推送。它是后续 RAG 解释、项目筛选决策和个性化推荐重排的前端基础。

## 2026-05-25 追加：新增项目对比接口

### 1. 开发目的

相似项目候选已经能找到可横向参考的项目，但用户还需要快速判断“哪个更值得看”。本次新增项目对比接口，把多个仓库的历史热度、质量、风险和基础属性整理成统一结构，为后续前端对比页、RAG 解释和个性化推荐重排打基础。

### 2. 修改内容

1. 后端新增 `GET /v1/projects/compare?repos=owner/a,owner/b`。
2. 兼容新增 `GET /api/projects/compare?repos=owner/a,owner/b`。
3. 支持一次传入最多 8 个 `owner/repo`，自动去重并返回缺失项目列表。
4. 响应包含 `projects`、`matrix`、`best_by` 和 `selection_summary`。
5. 对比指标包含语言、方向、历史入选次数、累计新增 Star、最近新增 Star、最好 Trending 排名、最新质量分、风险提示数量和质量提示数量。
6. `/v1/health` 新增 `project_compare` 能力标识。

### 3. 边界说明

该接口只读取公开归档和本地 SQLite 派生索引，不调用外部模型或推送服务。当前只做结构化对比和基础结论，后续可以接入前端对比页、用户偏好权重、Embedding 重排和模型生成解释。

## 2026-05-21 追加：项目详情页接入后端相似项目候选

### 1. 开发目的

相似项目候选接口已经完成，但如果只能通过 JSON 查看，无法直接服务日常使用。为了让核心能力可见，本次把该接口接入项目详情页，让用户打开单个项目时就能看到后端召回的相似项目和推荐原因。

### 2. 修改内容

1. `project.html` 在本地后端或 `api=1` 模式下读取 `/api/projects/{owner}/{repo}/similar?limit=8`。
2. 页面优先展示后端返回的相似项目候选，静态 GitHub Pages 模式继续使用原有本地启发式相似项目。
3. 相似项目展示新增相似度分和 `similarity_reasons`，说明同语言、同方向、来源重合、关键词重合和热度信号。
4. 保留接口失败回退，不影响项目详情页基础信息展示。
5. 补充页面构建测试，避免后续构建时丢失该入口。

### 3. 边界说明

该页面只读取公开归档和本地后端只读接口，不触发采集、推送或外部模型调用。当前目标是让 RAG 前置候选能力可见，后续再接入项目对比、用户反馈和模型生成解释。

## 2026-05-21 追加：新增相似项目候选接口

### 1. 开发目的

项目已经具备 FTS5 语料搜索能力，但后续 RAG、个性化推荐和项目对比不能只停留在关键词搜索。需要先提供一个稳定的“相似项目候选召回”接口，把同语言、同方向、同来源、关键词重合和历史热度综合起来，为后续向量检索和模型总结提供候选池。

### 2. 修改内容

1. 后端新增 `GET /v1/projects/{owner}/{repo}/similar`，支持 `limit` 参数。
2. 兼容新增 `GET /api/projects/{owner}/{repo}/similar`。
3. 接口会读取项目详情，自动构造检索词，优先通过 SQLite FTS5 语料索引召回候选。
4. 候选排序综合基础搜索分、同语言、同方向、同来源、关键词重合、Trending 排名和新增 Star。
5. 响应新增 `similarity_score` 和 `similarity_reasons`，便于前端解释为什么相似。
6. `/v1/health` 新增 `project_similarity` 能力标识。

### 3. 边界说明

该能力只读取本地 SQLite 和公开归档字段，不调用 Kimi、GitHub、Embedding、Telegram 或任何外部服务。当前是 RAG 前置候选层，不做最终语义总结；后续可以在该接口之后接入 Embedding、向量库、LangChain 或模型重排。

## 2026-05-20 追加：项目语料搜索升级为 FTS5

### 1. 开发目的

`/v1/search` 已经具备基础语料搜索能力，但普通 `LIKE` 匹配在数据量扩大后会变慢，也难以作为 RAG 前置检索层。为了提升搜索质量和后续扩展空间，本次把语料搜索升级为 SQLite FTS5，同时保留普通匹配回退。

### 2. 修改内容

1. SQLite 新增 `project_corpus_fts` 虚拟表，作为 `project_corpus` 的全文检索索引。
2. 重建项目语料时同步重建 FTS5 索引。
3. `/v1/search` 优先使用 FTS5 `MATCH` 和 `bm25` 排序；FTS 不可用或查询异常时自动回退到原有 LIKE 搜索。
4. 搜索响应新增 `search_engine` 字段，用于确认本次使用 `fts5` 还是 `like`。
5. 数据库概览增加 FTS 记录数和文本索引准备度。
6. 补充 SQLite、API、数据契约和迁移校验测试。

### 3. 边界说明

FTS5 索引只来自公开归档语料，不调用外部模型，不保存密钥。该能力仍属于本地检索层，尚未接入 Embedding、向量库或 LangChain。

## 2026-05-20 追加：管理台接入数据库和语料搜索

### 1. 开发目的

数据库概览、趋势、分面和语料搜索接口已经具备，但用户如果只打开本地管理台，仍然看不到这些后端能力。为了让后端和数据库建设能被直接验证，本次把管理首页接入这些核心接口。

### 2. 修改内容

1. `admin.html` 新增“数据库与语料”区域。
2. 本地 API 模式下读取 `/v1/database/summary`、`/v1/database/facets` 和 `/v1/database/trends`。
3. 页面展示仓库记录、入选记录、语料记录、订阅记录、主要语言、方向、来源和趋势摘要。
4. 页面新增语料搜索表单，调用 `/v1/search` 搜索历史入选项目。
5. 静态模式下保留提示，不写入数据、不调用后端。
6. 补充页面构建测试，固定管理台数据库和搜索入口。

### 3. 边界说明

该页面只在本地后端或 `api=1` 模式下读取数据库接口。搜索和统计只使用 SQLite 公开归档字段，不调用外部模型，不读取密钥。

## 2026-05-20 追加：新增项目语料搜索接口

### 1. 开发目的

项目后续要进入数据库、RAG 和个性化推荐阶段，不能只依赖项目列表过滤。需要先把项目描述、README 摘要、推荐理由、语言、方向和来源整理成统一语料，并提供一个不依赖外部模型的本地搜索入口，作为后续 FTS、向量检索和 LangChain 编排的地基。

### 2. 修改内容

1. SQLite 新增 `project_corpus` 派生表，保存历史入选项目的公开搜索语料。
2. JSON 归档导入 SQLite 时自动重建 `project_corpus`，已有数据库在首次访问 API 时也会补建空缺语料。
3. 后端新增 `GET /v1/search`，支持 `q`、`language`、`category`、`source` 和 `limit` 参数。
4. `/v1/health` 新增 `project_search` 能力标识。
5. 数据库概览和分面接口补充语料表数量与文本搜索准备度。
6. 补充 API、SQLite、数据契约和迁移校验测试。

### 3. 边界说明

当前搜索只读取 SQLite 中的公开归档字段，不调用 GitHub、Kimi、Telegram、Embedding 或任何外部模型，也不保存密钥。`project_corpus` 是派生表，可由 `data/selected` 重新构建。

## 2026-05-19 追加：新增数据库分面统计接口

### 1. 开发目的

数据库趋势接口已经能回答“最近运行表现如何”，但后续前端筛选、个性化推荐和 RAG 索引还需要回答“当前项目库由哪些语言、方向、来源和质量层级组成”。本次新增数据库分面统计接口，把 SQLite 中的公开归档数据整理成可直接用于筛选器、图表和推荐特征的结构。

### 2. 修改内容

1. 后端新增 `GET /v1/database/facets`，支持 `limit` 参数控制每类分面返回数量。
2. 接口返回语言、项目方向、来源、质量等级、风险状态和订阅偏好分布。
3. 语言分面包含项目数、总 Star、总 Fork 和最近推送时间；方向分面包含入选次数、项目数、新增 Star、平均分和 Trending Top10 命中率。
4. `/v1/health` 新增 `database_facets` 能力标识。
5. 补充 API、路由和文档测试，固定接口结构。

### 3. 边界说明

该接口只读取 SQLite 中的公开归档字段，不调用 GitHub、Kimi、Telegram 或任何外部服务，也不返回密钥、Webhook、请求头或完整原始载荷。它是后续前端仪表盘、精准推荐和 RAG 语料健康检查的基础能力。

## 2026-05-19 追加：新增数据库趋势接口

### 1. 开发目的

数据库概览接口已经能回答“当前有多少数据”，但后续 RAG、推荐排序和前端图表还需要回答“数据如何变化”。本次新增数据库趋势接口，用近 N 次运行的结构化指标作为后续分析基础。

### 2. 修改内容

1. 后端新增 `GET /v1/database/trends`，支持 `limit` 参数。
2. 接口按运行日期输出采集数量、入选数量、新增 Star、Trending 命中率、Trending Top10 命中数、Kimi/降级/推送状态。
3. 返回 `summary` 聚合总入选数量、总新增 Star、平均 Trending 命中率、失败运行数、降级运行数和推送成功数。
4. `/v1/health` 新增 `database_trends` 能力标识。
5. 补充 API 和路由测试，固定趋势接口结构。

### 3. 边界说明

该接口只读取 SQLite，不调用 GitHub、Kimi、Telegram 或任何外部服务。它为后续图表、推荐特征和 RAG 数据健康检查服务，不代表已经接入向量数据库或 LangChain。

## 2026-05-19 追加：新增数据库概览接口

### 1. 开发目的

项目后续重点转向数据库和 RAG 能力，需要先有一个稳定的数据库健康入口。当前 SQLite 已保存运行、项目、入选、任务、审计事件和订阅数据，但前端和后续索引器缺少统一概览接口。本次新增数据库概览能力。

### 2. 修改内容

1. 后端新增 `GET /v1/database/summary`。
2. 接口返回核心表记录数、最近运行、最近任务、任务状态分布和订阅状态分布。
3. 接口返回主要语言、项目方向、最近审计事件和 `rag_readiness`。
4. `/v1/health` 新增 `database_summary` 能力标识。
5. 补充 API 和路由测试，固定数据库概览返回结构。

### 3. 边界说明

该接口只读取 SQLite 统计摘要，不返回密钥、Webhook、请求头或完整原始载荷。`rag_readiness` 只是基础数据量提示，不代表已经启用向量数据库、LangChain 或外部模型。

## 2026-05-18 追加：任务执行器写入审计事件

### 1. 开发目的

任务闭环已经支持从页面或 API 创建、检查和执行 planned 任务，但如果任务由脚本或 GitHub Actions 直接调用 `run_planned_job.py`，审计事件主要依赖外层 API。为了让执行链路更稳定，本次把事件写入下沉到本地任务执行器内部。

### 2. 修改内容

1. `src/job_runner.py` 在任务进入 running 时写入 `runner_started` 事件。
2. 任务成功或业务失败后写入 `runner_finished` 事件，并保存结果摘要。
3. 执行器抛出异常时写入 `runner_failed` 事件，并保存错误摘要。
4. 补充 job runner 测试，覆盖成功和异常两条执行路径的事件写入。
5. 更新 v1 API 规划文档和 README，记录任务审计能力和后续数据库/RAG 建设方向。

### 3. 边界说明

事件只保存任务编号、状态、时间、执行摘要和错误摘要，不保存任何密钥、Webhook 或请求头。该能力不改变任务执行权限规则，也不绕过 `dry_run` 和 `confirm_delivery` 保护。

## 2026-05-18 追加：订阅配置页支持推荐预览

### 1. 开发目的

订阅推荐预览接口已经具备，但用户仍需要手动拼接 API 才能查看某条订阅会命中哪些项目。为了让订阅配置真正成为可操作的前端入口，本次把推荐预览直接接入 `subscriptions.html`。

### 2. 修改内容

1. 订阅列表中新增“预览推荐”按钮。
2. 点击后调用 `/v1/subscriptions/{subscription_id}/recommendations?limit=5`。
3. 在当前订阅卡片内展示筛选摘要、项目名称、简介、语言、方向、新增 Star 和 Trending 排名。
4. 预览项目名称链接到 `project.html?repo=owner/name`，方便继续查看项目详情。
5. 补充页面构建测试，固定推荐预览按钮、接口调用和详情页链接入口。

### 3. 边界说明

该页面预览只在本地 API 模式下工作，静态 GitHub Pages 模式仍不写入订阅配置。预览接口只读取公开归档和订阅偏好字段，不读取任何推送密钥。

## 2026-05-18 追加：订阅推荐新增后端预览接口

### 1. 开发目的

订阅配置已经能够进入推送链接和周报正文，但还缺少一个直接按订阅编号查看匹配项目的后端入口。为了让后续 Telegram、微信、飞书和前端订阅页复用同一套精准推荐逻辑，本次新增订阅推荐预览接口。

### 2. 修改内容

1. 后端新增 `GET /v1/subscriptions/{subscription_id}/recommendations`。
2. 接口读取订阅保存的 profile、language、category、query、sort 和 limit，并复用现有 `/v1/recommendations` 过滤逻辑。
3. 返回内容包含订阅基础信息、筛选摘要和推荐项目列表，方便前端直接展示或调试推送结果。
4. `/v1/health` 新增 `subscription_recommendations` 能力标识。
5. 补充 API 测试，覆盖仓储层和 FastAPI 路由。

### 3. 边界说明

该接口只读取订阅表中的公开偏好字段，不读取、不返回、不保存任何 Token、Chat ID 或 Webhook。订阅不存在时返回空推荐和明确提示，不影响已有订阅配置、周报生成和推送流程。

## 2026-05-18 追加：周报正文新增订阅推荐分区

### 1. 开发目的

订阅配置已经能保存偏好并进入推送消息，但周报正文仍是统一列表。为了让订阅真正参与内容生成，本次让周报在生成阶段按启用订阅拆分推荐分区，例如 Agent 开发、Java、Python 等方向可以在正文中直接看到匹配项目。

### 2. 修改内容

1. 报告生成完成后读取本地 SQLite 中启用状态的订阅配置。
2. 根据订阅的 profile、language、category、query 从本期入选项目中筛选匹配项目。
3. 在周报正文追加“订阅推荐分区”，每个订阅最多展示 5 个匹配项目。
4. 订阅分区同时适用于 Kimi 周报和规则版降级周报。
5. 补充 reporter 测试，固定订阅分区输出和过滤逻辑。

### 3. 边界说明

该能力只读取本地 `subscriptions` 表的公开偏好字段，不读取密钥，不改变采集、评分和入选逻辑。没有启用订阅或没有 SQLite 时，周报内容保持原有结构。

## 2026-05-18 追加：推送消息接入订阅推荐入口

### 1. 开发目的

订阅配置已经可以保存用户偏好，但还没有进入真实推送链路。为了让订阅成为后续精准推送的核心输入，本次把订阅配置页和启用订阅的推荐链接接入 Telegram、飞书和企业微信消息。

### 2. 修改内容

1. 推送消息新增“订阅配置”链接，方便手机端直接进入订阅入口。
2. 如果本地 SQLite 中存在启用状态的订阅，推送消息会附加最多 3 个订阅推荐链接。
3. 订阅推荐链接指向 `recommendations.html`，并自动携带 profile、language、category、query 和 sort 参数。
4. 飞书和企业微信消息复用同一套 Markdown 链接内容，避免多通道格式不一致。
5. 补充发送层测试，覆盖订阅推荐链接和链接消息内容。

### 3. 边界说明

推送层只读取 `subscriptions` 表中的公开偏好字段，不读取、不发送、不保存任何 Token、Chat ID 或 Webhook。没有订阅或没有 SQLite 时，推送消息仍按原有周报、项目筛选、运行状态入口发送。

## 2026-05-18 追加：新增本地订阅配置能力

### 1. 开发目的

个性化推荐页已经能按 Java、Python、Agent 开发等条件筛选项目，但这些条件还只是临时 URL 参数。为了给后续精准推送、数据库化用户配置和多渠道订阅留下入口，本次新增本地订阅配置能力。

### 2. 修改内容

1. SQLite 新增 `subscriptions` 表，保存订阅名称、状态、profile、语言、方向、关键词、排序、数量和通道名称。
2. 后端新增 `/v1/subscriptions` 查询和创建接口，以及 `/v1/subscriptions/{subscription_id}` 更新接口。
3. 新增 `subscriptions.html`，支持本地 API 模式下创建、查看、启用和停用订阅。
4. 推荐页、首页、API 文档和 v1 规划文档增加订阅入口说明。
5. 补充 API、页面构建和 SQLite schema 合约测试。

### 3. 边界说明

订阅配置只保存通道名称，不保存 Telegram Token、Chat ID、Webhook 或任何密钥。GitHub Pages 静态模式不写入订阅，只有本地后端模式才允许创建和更新。

## 2026-05-18 追加：新增个性化推荐接口和页面

### 1. 开发目的

项目已经具备历史项目归档、筛选页、详情页和本地管理后台，但用户仍需要按 Java、Python、Agent 开发、后端等方向快速得到推荐项目。本次新增轻量级个性化推荐能力，把已有 profile、语言、方向和关键词筛选封装成独立入口，优先推进核心功能，而不是只做页面细节优化。

### 2. 修改内容

1. 后端新增 `/api/recommendations` 和 `/v1/recommendations`，复用现有项目索引和 profile 过滤逻辑。
2. 推荐接口返回 `recommendations` 和 `selection_summary`，便于前端直接展示筛选依据。
3. 新增 `recommendations.html`，支持本地 API 模式和 GitHub Pages 静态回退模式。
4. 推荐页预留 Agent 开发、Python、Java、后端、前端、AI 工具等快捷方向，后续可继续接入更复杂的用户订阅和数据库配置。
5. 更新 API 文档和页面构建测试，固定推荐接口与推荐页入口。

### 3. 边界说明

本次不新增外部请求，不读取密钥，不改变现有周报采集和推送流程。推荐结果来自已经归档的项目数据，后续可在此基础上扩展用户选择、订阅保存和多渠道精准推送。

## 2026-05-18 追加：项目详情页新增推荐理由和趋势判断

### 1. 开发目的

项目详情页已经能展示历史入选、Star 增长、Trending 排名和相似项目，但还缺少直接解释“为什么推荐”和“趋势是否继续走强”的结论。本次补齐项目分析层，让用户打开项目详情后能更快判断项目价值。

### 2. 修改内容

1. 后端 `project_detail` 聚合历史记录中的 `selection_reasons`。
2. 后端新增 `trend_summary`，输出历史入选次数、累计新增 Star、最近入选日期、最好 Trending 排名和最近热度变化。
3. 静态 `project.html` 回退模式同步生成推荐理由和趋势判断。
4. 项目详情页新增“推荐理由”和“趋势判断”两个区域。
5. 补充 API 测试和页面构建测试，固定新增字段和页面文案。

### 3. 边界说明

该功能只基于已有归档数据做聚合，不新增外部请求，不读取密钥，也不改变项目筛选规则。

## 2026-05-18 追加：本地后端挂载管理首页静态页面

### 1. 开发目的

用户启动本地 FastAPI 后访问 `/v1/jobs?limit=50` 看到的是 JSON 数据，这是 API 的正常行为；但访问 `/admin.html?api=1` 返回 404，说明本地后端还没有挂载 `docs/` 静态页面。本次修复本地后端入口，让用户能直接从 `127.0.0.1:8000` 打开管理后台。

### 2. 修改内容

1. FastAPI 启动时挂载仓库 `docs/` 目录，提供 `admin.html`、`jobs.html`、`project.html` 等静态页面。
2. 新增根路径 `/` 跳转到 `/admin.html?api=1`。
3. 保持 `/v1/*` 路径为 JSON API，不改变现有接口语义。
4. 补充 API 路由测试，确认 `/admin.html?api=1` 返回 HTML，`/` 返回跳转。
5. 更新 API 文档，说明 JSON API 和 HTML 管理页的区别。

### 3. 边界说明

`/v1/jobs?limit=50` 返回 JSON 是正确设计，用于前端和程序读取；用户要看网页界面应打开 `/admin.html?api=1`。

## 2026-05-17 追加：本地管理首页新增核心工作流面板

### 1. 开发目的

管理首页已经具备任务概览和最近任务结果，但用户仍需要在多个入口之间判断下一步。本次新增核心工作流面板，把最近周报、Top 项目、失败任务和待执行任务聚合到同一区域，减少后台操作路径。

### 2. 修改内容

1. `admin.html` 新增“核心工作流”区域。
2. 展示最近周报入口，附带入选项目数和候选项目数。
3. 展示 Top 项目入口，链接到项目详情页。
4. 展示失败任务入口，直接进入对应任务详情页处理。
5. 展示待执行任务入口，直接进入对应任务详情页做执行前检查。
6. 所有数据继续来自 `projects.json`、`runs.json` 和任务数据，不新增后端接口。
7. 补充页面构建测试，固定核心工作流区域和入口函数。

### 3. 边界说明

该面板只做导航和状态聚合，不自动执行任务，也不读取任何密钥。执行、重试和真实推送仍必须经过已有按钮和后端安全规则。

## 2026-05-17 追加：本地管理首页新增最近任务结果视图

### 1. 开发目的

管理首页已经能查看、创建和处理任务，但用户仍需要进入任务详情页才能快速判断最近一次任务是否成功、是否有错误、下一步该做什么。本次在数据概览区域新增最近任务结果视图，让后台首页直接具备基础判断能力。

### 2. 修改内容

1. `admin.html` 新增“最近任务结果”区域。
2. 从任务数据中按完成时间、提交时间和运行日期选出最新任务。
3. 展示任务编号、状态、完成时间、周报链接、错误信息和下一步建议。
4. 根据任务状态生成建议：失败任务提示重试，待执行任务提示执行前检查，运行中任务提示等待或查看详情，成功任务提示打开周报。
5. 对任务状态补充可读的颜色样式，提升后台判断效率。
6. 补充页面构建测试，固定最近任务结果视图和建议字段。

### 3. 边界说明

该视图只读取已有任务数据，不新增后端接口，也不自动执行任务。真实执行、重试和推送仍必须走已有按钮和后端安全规则。

## 2026-05-17 追加：本地管理首页任务工作台接入操作按钮

### 1. 开发目的

管理首页已经能看到任务工作台和实时任务列表，但处理 planned 或 failed 任务仍需要跳转到任务详情页。为了让后台首页更接近完整工作台，本次把执行前检查、确认执行和失败重试接入到任务工作台卡片中，同时保持用户确认和 API 模式限制。

### 2. 修改内容

1. `admin.html` 的任务工作台每条任务新增“执行前检查”“确认执行”“重试”按钮。
2. 执行前检查调用 `/v1/job-execution-check?job_id=...`。
3. planned 任务确认执行调用 `POST /v1/jobs/{job_id}/execute`，并传入 `confirm_execution=true`。
4. failed 任务重试调用 `POST /v1/jobs/{job_id}/retry`，并固定写入 `requested_by=admin_page`。
5. 静态 GitHub Pages 模式下操作按钮禁用，只保留查看能力。
6. 操作完成后重新读取任务概览和任务工作台，方便看到状态变化。
7. 补充页面构建测试，固定管理首页的三个任务操作入口和 API 路径。

### 3. 边界说明

管理首页仍不绕过执行前检查，也不自动执行真实推送。确认执行前会触发浏览器确认，后端仍按既有安全规则阻止不满足条件的任务。

## 2026-05-17 追加：本地管理首页任务工作台接入实时 API

### 1. 开发目的

管理首页的任务工作台已经能集中查看重点任务，但此前只读取静态 `jobs.json`。当本地后端正在运行时，用户仍需要等待重新构建 Pages 才能看到最新 planned、running 或 failed 任务。本次让管理首页在 API 模式下优先读取实时任务接口，提升后台操作的即时性。

### 2. 修改内容

1. `admin.html` 的概览和任务工作台改为复用统一任务数据源。
2. 本地后端或 `api=1` 模式下优先读取 `/v1/jobs?limit=200`。
3. API 读取失败时自动回退到静态 `jobs.json`，避免页面空白。
4. 静态 GitHub Pages 模式继续只读取 `jobs.json`，不依赖常驻后端。
5. 任务工作台的重点、失败、待执行、运行中和全部筛选逻辑保持不变。
6. 补充页面构建测试，固定 API 优先读取与静态回退路径。

### 3. 边界说明

本次只增强任务数据读取来源，不新增任务执行动作。真实执行、重试和执行前检查仍在任务详情页完成，并继续要求用户确认。

## 2026-05-17 追加：本地管理首页新增任务工作台

### 1. 开发目的

管理首页已经能看到概览并创建 planned 任务，但处理异常任务仍需要进入任务状态页筛选。为了让首页更像后台工作台，本次新增任务工作台，直接展示重点任务并支持快速筛选。

### 2. 修改内容

1. `admin.html` 新增“任务工作台”区域。
2. 工作台读取 `jobs.json`，不依赖新后端接口。
3. 支持重点、失败、待执行、运行中和全部任务筛选。
4. 重点视图聚合 `failed`、`planned` 和 `running` 任务。
5. 每条任务展示任务编号、状态、方向和提交时间。
6. 任务编号链接到 `job.html?job=...`，便于继续查看详情或执行操作。
7. 补充页面构建测试，固定筛选按钮和渲染函数。

### 3. 边界说明

工作台只展示和跳转，不直接执行任务。执行前检查、确认执行和重试仍在单任务详情页中完成。

## 2026-05-17 追加：本地管理首页接入任务创建表单

### 1. 开发目的

管理首页已经能查看系统概览，但创建新周报任务仍需要进入任务状态页。为了让后台首页具备最小控制能力，本次在管理首页接入 planned 周报任务创建表单。

### 2. 修改内容

1. `admin.html` 新增“创建 planned 周报任务”表单。
2. 支持填写个性化方向、回看天数、来源、dry_run 和确认真实推送。
3. API 模式下调用 `POST /v1/runs/trigger`。
4. 请求固定写入 `trigger_source=admin_page` 和 `requested_by=local-admin`。
5. 创建成功后给出任务详情页链接，方便继续执行前检查、确认执行或重试。
6. 静态 Pages 模式下按钮禁用，不触发任何后端请求。
7. 补充页面构建测试，固定表单字段、触发接口和审计字段。

### 3. 边界说明

该表单只创建 planned 任务，不直接执行采集、生成或推送。真实执行仍需要进入任务详情页确认。

## 2026-05-17 追加：本地管理首页新增数据概览

### 1. 开发目的

本地管理首页已经聚合核心入口，但打开后还需要分别进入多个页面才能判断当前系统状态。为了提升后台可用性，本次在管理首页新增数据概览，直接展示最新运行、项目数量、失败任务和待执行任务。

### 2. 修改内容

1. `admin.html` 新增“数据概览”区域。
2. 页面读取 `projects.json`、`runs.json` 和 `jobs.json`。
3. 展示项目总数、最新运行日期、失败任务数和待执行任务数。
4. 自动生成最新周报、运行面板、失败任务处理和待执行任务查看入口。
5. 保持静态 Pages 可用，不依赖常驻后端。
6. 补充页面构建测试，固定数据源、指标名称和快捷入口。

### 3. 边界说明

该功能只读公开归档数据，不触发任务执行或推送。真实任务处理仍进入 `job.html` 后由用户确认。

## 2026-05-17 追加：新增本地管理首页

### 1. 开发目的

项目已经有项目筛选、运行状态、任务状态和单任务控制台，但入口分散。为了更接近完整后台，本次新增本地管理首页，把核心页面和后端健康检查集中到一个入口。

### 2. 修改内容

1. 新增 `docs/admin.html`，作为本地管理首页。
2. 页面聚合项目、运行、任务三个核心入口。
3. 静态 GitHub Pages 模式下显示只读入口和静态数据说明。
4. 本地后端或 `api=1` 模式下读取 `/v1/health`。
5. 展示后端能力开关和归档健康摘要。
6. 周报归档首页增加“本地管理首页”入口。
7. 补充页面构建测试，固定管理页生成和健康检查路径。

### 3. 边界说明

该页面只做入口聚合和健康检查，不直接执行任务。任务执行、重试和审计仍在 `jobs.html` 与 `job.html` 中完成。

## 2026-05-17 追加：任务详情页接入单任务控制台

### 1. 开发目的

任务详情页已经能查看任务请求、执行结果和审计事件，但还不能直接处理当前任务。为了减少在任务列表和接口文档之间来回切换，本次把执行前检查、确认执行和失败重试集中接入单个任务详情页。

### 2. 修改内容

1. `job.html` 新增“任务操作”区域。
2. 支持在 API 模式下对当前任务调用 `/v1/job-execution-check?job_id=...`。
3. 支持对 `planned` 任务调用 `POST /v1/jobs/{job_id}/execute`，并传入 `confirm_execution=true`。
4. 支持对 `failed` 任务调用 `POST /v1/jobs/{job_id}/retry`，并写入 `requested_by=job_detail_page`。
5. 操作完成后刷新任务详情和事件时间线，方便看到状态变化和审计记录。
6. 静态 Pages 模式下按钮禁用，只保留查看能力。
7. 补充页面构建测试，固定单任务操作入口和 API 路径。

### 3. 边界说明

该页面仍然依赖本地后端或 `api=1` 模式执行操作。公开 GitHub Pages 默认不触发后端，不会误执行任务或推送消息。

## 2026-05-17 追加：新增任务详情页和审计事件时间线

### 1. 开发目的

任务系统已经具备创建、执行、失败重试和事件记录能力，但用户查看单个任务时仍只能看列表摘要。为了让任务管理更接近可用后台，本次新增任务详情页，集中展示任务请求、执行结果、错误信息和审计事件。

### 2. 修改内容

1. 新增 `docs/job.html`，作为单个任务详情页。
2. `docs/jobs.html` 的任务编号改为可点击链接，进入 `job.html?job=...`。
3. 详情页在本地后端或 `api=1` 模式下读取 `/v1/jobs/{job_id}`。
4. 详情页在 API 模式下读取 `/v1/jobs/{job_id}/events?limit=200` 并展示审计事件时间线。
5. 静态 GitHub Pages 模式下从 `jobs.json` 读取任务基础信息，事件区提示需要本地后端。
6. 补充页面构建测试，固定任务详情页、事件接口路径和任务页跳转入口。

### 3. 边界说明

该页面只做查询和展示，不执行任务、不重试任务、不读取任何密钥。后续可以继续把任务详情页扩展成后台工作台的一部分。


## 2026-05-16 追加：任务状态页接入失败任务重试按钮

### 1. 开发目的

后端已经具备 `POST /v1/jobs/{job_id}/retry`，但用户仍需要手动调用接口才能重试 failed 任务。为了让“前端管理页 -> 后端任务模型 -> 本地执行器”的闭环更完整，本次把失败任务重试入口接入 `jobs.html`，让失败任务可以在本地 API 模式下直接创建新的 planned 重试任务。

### 2. 修改内容

1. `jobs.html` 的任务行新增“重试”按钮。
2. 该按钮只在本地后端或 `api=1` 模式下，并且任务状态为 `failed` 时启用。
3. 点击重试前会触发浏览器确认，随后调用 `POST /v1/jobs/{job_id}/retry`。
4. 页面固定写入 `requested_by=jobs_page`，便于后续审计任务来源。
5. 页面展示重试结果、命中的已有任务、阻止原因和新任务状态。
6. 重试请求完成后自动刷新任务列表，便于查看新 planned 任务。
7. 补充页面构建测试，固定重试按钮、重试 API 路径和审计字段。

### 3. 边界说明

该按钮只负责创建 planned 重试任务，不直接运行采集、生成或推送。真实执行仍由 `/v1/jobs/{job_id}/execute`、本地 job runner 或后续 worker 接管。

## 2026-05-16 追加：新增失败任务重试 API

### 1. 开发目的

任务系统已经具备任务创建、受控执行和审计事件，但 failed 任务还缺少标准重试入口。为了避免人工重复构造任务参数，本次新增失败任务重试能力，让后续前端管理页和自动恢复策略可以基于同一套任务模型创建新的 planned 重试任务。

### 2. 修改内容

1. 新增 `POST /v1/jobs/{job_id}/retry`。
2. 只有 `status=failed` 且 `kind=weekly_report` 的任务允许重试。
3. 重试会复用原任务 request，并追加 `trigger_source=retry`、`requested_by` 和 `retry_of`。
4. 如果已存在相同 active 任务，则返回已有任务，不重复创建。
5. 重试过程写入 `retry_requested`、`retry_blocked`、`retry_duplicate_ignored`、`retry_created` 和新任务 `job_created` 事件。
6. 补充 repository 和 FastAPI 路由测试，覆盖重试成功和非 failed 任务被阻止。

### 3. 边界说明

该接口只创建新的 planned 任务，不直接执行。真实执行仍走 `/v1/jobs/{job_id}/execute` 或 job runner，继续遵守 `dry_run` 和 `confirm_delivery` 规则。

## 2026-05-15 追加：新增任务审计事件表和事件查询 API

### 1. 开发目的

任务系统已经可以创建、检查和执行 planned 任务，但缺少可查询的过程记录。为了支撑后续失败重试、后台管理页、用户审查和问题排查，本次新增任务审计事件能力，记录任务从创建到执行结束的关键动作。

### 2. 修改内容

1. SQLite schema 新增 `job_events` 表，保存 `event_id`、`job_id`、`event_type`、`status`、`actor`、`created_at`、`message` 和脱敏 payload。
2. 新增 `insert_job_event()`，统一写入任务事件。
3. `/v1/runs/trigger` 在创建任务或命中重复任务时写入事件。
4. `/v1/jobs/{job_id}/execute` 在收到执行请求、阻止执行、开始执行和执行结束时写入事件。
5. 新增 `GET /v1/jobs/{job_id}/events`，用于查询单个任务的审计事件。
6. 补充 API、SQLite 和数据契约测试，固定事件表结构和查询入口。

### 3. 边界说明

事件 payload 只记录审计摘要，不记录 Token、Chat ID、Webhook、请求头或原始密钥配置。当前事件表仍属于可重建本地 SQLite 派生索引，后续可迁移到持久化数据库。

## 2026-05-15 追加：任务状态页接入受控执行按钮

### 1. 开发目的

后端已经具备 `POST /v1/jobs/{job_id}/execute` 受控执行入口，但用户仍需要手动调用接口。为了完成“前端 -> 后端 -> 数据库 -> runner”的最小闭环，本次把执行入口接入任务状态页，让本地后端模式下的 planned 任务可以从页面发起执行。

### 2. 修改内容

1. `jobs.html` 的任务行新增“确认执行”按钮。
2. 该按钮只在本地后端或 `api=1` 模式下，并且任务状态为 `planned` 时启用。
3. 点击执行前会触发浏览器确认，随后向 `/v1/jobs/{job_id}/execute` 发送 `confirm_execution=true`。
4. 页面展示执行接口返回的接受状态、任务状态、阻止原因和提示信息。
5. 执行后自动刷新任务列表，便于查看任务从 planned 推进后的状态。
6. 补充页面构建测试，固定执行按钮、确认参数和执行 API 路径。

### 3. 边界说明

该按钮仍然依赖本地后端和现有 job runner，不会在 GitHub Pages 静态页面中直接运行任务。真实推送仍由任务请求中的 `dry_run` 和 `confirm_delivery` 控制。

## 2026-05-15 追加：新增受控任务执行 API

### 1. 开发目的

任务系统已经具备 planned 创建、重复防护、执行前检查和本地 job runner，但后端 API 还不能把一个已检查通过的任务交给执行器。为了推进核心后端能力，本次新增受控执行入口，让后续前端管理页、脚本或本地服务可以通过同一套任务模型执行 planned 周报任务。

### 2. 修改内容

1. 新增 `POST /v1/jobs/{job_id}/execute`。
2. 执行前强制复用 `/v1/job-execution-check` 的判断结果。
3. 请求必须显式传入 `confirm_execution=true`，否则只返回阻止原因，不执行任务。
4. 检查不通过的任务不会交给 runner，包括已完成任务、缺失任务和不满足真实推送确认的任务。
5. 检查通过后调用 `src.job_runner.run_planned_job()`，由现有执行器负责状态推进和结果写回。
6. 补充 repository 和 FastAPI 路由测试，避免后续改动绕过确认逻辑。

### 3. 边界说明

该接口是本地后端和后续管理端的核心执行入口，不用于公开 GitHub Pages 静态页面。真实推送仍受任务请求中的 `dry_run` 和 `confirm_delivery` 控制。

## 2026-05-15 追加：任务状态页接入执行前检查按钮

### 1. 开发目的

任务执行前检查接口已经可以判断 planned 任务是否可被本地执行器消费，但用户仍需要手动调用 API。为了让任务管理页形成更完整的闭环，本次把检查能力接入 `jobs.html`，让每条任务都可以在页面中查看是否可执行、阻止原因、提示信息和下一步命令。

### 2. 修改内容

1. `jobs.html` 的任务行新增“执行前检查”按钮。
2. 按钮在本地后端或 `api=1` 模式下调用 `/v1/job-execution-check?job_id=...`。
3. GitHub Pages 静态模式下不会调用后端，只提示需要本地后端或 `api=1`。
4. 检查结果显示可执行状态、阻止原因、提示信息和 `next_command`。
5. 补充页面构建测试，固定执行前检查入口不会被后续改动移除。

### 3. 边界说明

本次只做执行前检查，不在浏览器页面里直接执行任务。真实执行仍由 `scripts/run_planned_job.py`、GitHub Actions 或后续受控 worker 处理。

## 2026-05-15 追加：新增任务执行前检查接口

### 1. 开发目的

planned 任务已经具备创建、去重和本地执行器消费能力，但前端或调度器在执行前还缺少统一检查入口。为了避免把不可执行、已完成或缺少确认的任务交给执行器，本次增加只读执行前检查接口。

### 2. 本次修改

1. 新增 `/v1/job-execution-check?job_id=...`，用于判断单个任务是否可被 `scripts/run_planned_job.py` 消费。
2. `ApiRepository.job_execution_check()` 返回 `executable`、`blockers`、`warnings` 和建议执行命令。
3. 检查规则要求任务必须是 `weekly_report` 且状态为 `planned`。
4. 如果 `dry_run=false` 但没有 `confirm_delivery=true`，执行前检查会阻止执行。
5. 补充 API 和 FastAPI 路由测试，覆盖 planned、历史完成任务和缺失任务。

### 3. 设计边界

本次只做执行前检查，不在 HTTP 请求中执行 job runner，不暴露任何密钥配置状态。真实执行仍通过脚本、GitHub Actions 或后续受控 worker 完成。

## 2026-05-15 追加：planned 任务创建增加重复防护

### 1. 开发目的

任务状态页已经可以创建 planned 任务，但如果用户多次点击按钮，或多个入口提交同一组参数，可能在 `jobs` 表里产生重复的 planned 任务。为了让后续前端和 worker 更稳定，本次在后端任务创建入口增加 active 任务去重。

### 2. 本次修改

1. `/v1/runs/trigger` 创建任务前会检查已有 `planned` 或 `running` 周报任务。
2. 去重依据为 `profile`、`sources`、`dry_run`、`confirm_delivery` 和 `days_back`，不受 `requested_by` 或 `trigger_source` 影响。
3. 如果命中重复任务，接口返回已有 `job_id`，并设置 `planned_job_created=false` 和 `duplicate_of`。
4. 补充 API 测试，覆盖重复提交不会创建第二个 planned 任务。
5. `/v1` API 规划文档补充重复任务防护说明。

### 3. 设计边界

本次只拦截 active 状态的重复任务。已经完成或失败的历史任务不会阻止新任务创建，避免影响后续按周重新运行和人工重试。

## 2026-05-15 追加：任务状态页新增 planned 任务创建表单

### 1. 开发目的

后端已经具备受控创建 planned 任务的能力，但用户仍需要通过接口文档或脚本才能创建任务。为了让后续前端管理页有一个最小可用入口，本次在任务状态页增加创建任务表单，同时继续保持“只创建 planned，不直接执行”的安全边界。

### 2. 本次修改

1. `jobs.html` 新增 planned 任务创建表单，支持填写 profile、回看天数、来源、dry_run 和确认推送。
2. 表单只在本地后端或 `api=1` 模式下启用，静态 GitHub Pages 默认只能查看任务。
3. 提交时调用 `/v1/runs/trigger`，写入 `trigger_source=jobs_page` 和 `requested_by=local-ui`。
4. 创建成功后自动筛选 planned 任务并刷新任务列表。
5. 补充页面构建测试，固定表单、受控触发接口和审计字段。

### 3. 设计边界

本次不在页面中执行 job runner，也不绕过 `confirm_delivery` 规则。真实执行仍需要由 `scripts/run_planned_job.py`、GitHub Actions 或后续受控 worker 消费 planned 任务。

## 2026-05-15 追加：任务触发入口增加推送确认和审计字段

### 1. 开发目的

项目已经具备 planned 任务、job runner 和 GitHub Actions 手动触发能力，但 `/v1/runs/trigger` 的语义仍容易被理解成“HTTP 直接执行任务”。为了给后续前端管理页和真实任务触发按钮打基础，本次先明确触发边界：接口只创建计划任务，真实执行仍由 job runner 完成。

### 2. 本次修改

1. `/v1/runs/trigger` 的任务请求新增 `trigger_source`、`requested_by`、`requested_dry_run`、`confirm_delivery`、`delivery_allowed` 和 `safety_warnings`。
2. 如果请求传入 `dry_run=false` 但没有 `confirm_delivery=true`，系统会自动改为 `dry_run=true`，防止误推送。
3. 返回结果新增 `planned_job_created`、`http_execution_supported` 和 `execution_path`，明确当前不会在 HTTP 请求中直接执行长任务。
4. `scripts/create_planned_job.py` 写入触发来源和触发人，GitHub Actions 场景默认记录 `github_actions` 与 `GITHUB_ACTOR`。
5. README、数据契约和 `/v1` API 规划文档补充受控推送规则。

### 3. 设计边界

本次不增加前端“立即执行”按钮，也不让 API 请求直接跑采集和推送。后续要开放前端触发时，还需要补鉴权、重复任务控制、审计查看和失败重试策略。

## 2026-05-15 追加：任务状态页接入后端任务查询

### 1. 开发目的

`/v1/jobs` 已经支持按状态、类型、profile 和关键词查询任务，但 GitHub Pages 的任务状态页仍只读取静态 `jobs.json`。为了让本地后端、未来前端和静态页面使用一致的任务查询语义，本次把任务页改成“后端 API 优先、静态 JSON 回退”的加载方式。

### 2. 本次修改

1. `jobs.html` 在本地或 `api=1` 时优先读取 `/v1/jobs?limit=200`。
2. GitHub Pages 环境继续自动回退到 `jobs.json`，不影响公开归档查看。
3. 任务页 URL 保留 `api=1/api=0`，关键词参数统一输出为 `q`，同时兼容旧的 `query`。
4. profile 筛选改为精确匹配，与 `/v1/jobs?profile=...` 保持一致。
5. 补充页面构建测试，固定 API 回退、URL 参数和 profile 匹配行为。

### 3. 设计边界

本次只让任务页读取后端查询入口，不增加页面上的真实任务触发按钮。后续如果要开放前端触发，需要先完成鉴权、触发权限、审计日志和任务防重复策略。

## 2026-05-15 追加：增强任务 API 查询过滤

### 1. 开发目的

任务状态页面已经能查看公开任务，但后续前端管理页、后台面板和个性化任务调度都需要直接从后端按条件查询任务。为了避免前端重复过滤逻辑，本次把任务筛选能力下沉到 `/v1/jobs` 对应的 repository 层。

### 2. 本次修改

1. `/v1/jobs` 新增 `status`、`kind`、`profile`、`query` 和 `limit` 查询参数。
2. `ApiRepository.jobs()` 支持复用同一套过滤逻辑，兼容 SQLite jobs 表和公开 runs 回退数据。
3. 补充 API 单元测试，覆盖 planned 预览任务、succeeded 历史任务和 FastAPI 路由过滤。
4. `/v1` API 规划文档补充任务查询参数说明。

### 3. 设计边界

本次只增强只读查询能力，不新增 HTTP 直接执行任务，也不暴露密钥、请求头或原始运行环境信息。真实任务触发仍通过现有 planned job 和 job runner 路径推进。

## 2026-05-15 追加：新增任务状态页面

### 1. 开发目的

任务执行器和 GitHub Actions 已经可以写入 `jobs` 表，但用户还缺少一个无需连接 API 或 SQLite 的可视化入口。为了让任务调度能力能在 GitHub Pages 上直接检查，本次增加公开任务状态 JSON 和页面。

### 2. 本次修改

1. `scripts/build_pages.py` 新增 `docs/jobs.json` 和 `docs/jobs.html` 输出。
2. `jobs.json` 优先读取 SQLite `jobs` 表；如果 SQLite 不存在，则从公开运行记录生成历史任务视图。
3. `jobs.html` 支持按状态、类型、profile 和关键词筛选任务。
4. README 和数据契约文档补充任务状态入口说明。
5. 补充页面构建和公开 JSON 契约测试。

### 3. 设计边界

本次只做公开状态查看，不提供前端触发任务按钮，也不暴露任何密钥、请求头或原始异常堆栈。后续可以在管理端或后端 API 中增加受控触发入口。

## 2026-05-11 追加：GitHub Actions 接入任务执行器

### 1. 开发目的

本地任务执行器已经可以消费 `planned` 任务，但还不能通过 GitHub 网页参数化触发。为了让项目从“定时脚本”继续演进为“可调度的后端任务系统”，需要把 weekly workflow 改造成任务创建和任务执行两段式流程。

### 2. 本次修改

1. weekly workflow 的 `workflow_dispatch` 新增 `profile`、`days_back`、`skip_main_delivery` 和 `send_link` 输入。
2. 新增 `scripts/create_planned_job.py`，负责在 Actions 中创建 planned 任务并写入 `.weekly-job.json`。
3. `scripts/run_planned_job.py` 支持 `--job-file`，可读取刚创建的任务编号并执行指定任务。
4. weekly workflow 从直接运行 `python main.py` 改为先创建任务，再执行任务，后续仍构建 Pages、发布 `weekly-archive` 并推送周报链接。
5. 补充 workflow 和任务脚本测试，防止后续改动破坏手动触发入口。

### 3. 设计边界

本次没有引入常驻服务，也没有让 HTTP 请求直接执行采集任务。GitHub Actions 只是当前阶段的任务执行环境；后续仍可以把相同的 job runner 接入 FastAPI 管理端、前端按钮或独立 worker。

## 2026-05-11 追加：接入本地任务执行器

### 1. 开发目的

`jobs` 表已经可以保存 `planned` 任务，但还缺少把计划任务推进为真实执行结果的最小执行器。为了后续接 GitHub Actions 手动触发、常驻 worker 或管理后台，需要先完成本地可测试的任务执行闭环。

### 2. 本次修改

1. 新增 `src/job_runner.py`，负责读取 `planned` 任务、标记 `running`、调用 `run_weekly_report()`，并写回 `succeeded` 或 `failed`。
2. 新增 `scripts/run_planned_job.py`，可执行最早的 planned 任务，也可通过 `--job-id` 指定任务。
3. `/v1/runs/trigger` 的请求保留 `profile`、`sources`、`dry_run`，并新增 `days_back`。
4. `dry_run=true` 时任务执行器会跳过 Telegram 推送，避免本地验证误发消息。
5. README 和 `/v1` API 文档补充任务执行器说明。

### 3. 设计边界

本次仍不在 HTTP 请求生命周期里执行采集任务，也不引入 Redis、Celery 或常驻进程。当前完成的是最小本地执行器，下一步再决定由 GitHub Actions、后台服务或前端管理页触发它。

## 2026-05-11 追加：增加持久化 job 任务表

### 1. 开发目的

`/v1/jobs` 原本只把 `docs/runs.json` 临时映射为任务视图，`/v1/runs/trigger` 也只返回预览，不会留下任务记录。为了后续接入后台 worker、状态轮询和真实手动触发，需要先把任务模型落到 SQLite 派生索引中。

### 2. 本次修改

1. SQLite schema 新增 `jobs` 表和任务状态查询索引。
2. JSON 归档导入 SQLite 时，会把历史 `data/runs/*.json` 同步为 `run:YYYY-MM-DD` 任务。
3. `/v1/jobs` 和 `/v1/jobs/{job_id}` 改为优先读取持久化任务表。
4. `/v1/runs/trigger` 会写入 `preview:*` 的 `planned` 任务记录，但仍不执行真实采集。
5. 补充 SQLite、API 和数据契约测试，固定任务表结构。

### 3. 设计边界

本次只建立任务状态底座，不启动后台 worker，也不在 HTTP 请求中执行长任务。下一步会把 `run_weekly_report()` 接入任务执行器，让任务状态从 `planned` 推进到 `running`、`succeeded` 或 `failed`。

## 2026-05-11 追加：封装周报主流程 use case

### 1. 开发目的

`main.py` 原本直接承载采集、评分、生成、归档、推送和运行摘要写入。这样 CLI 可以运行，但后续 `/v1/runs/trigger`、后台 worker 和任务状态模型无法复用主流程。根据核心功能优先路线，需要先把主链路封装成可调用 use case。

### 2. 本次修改

1. 新增 `src/weekly_run.py`，提供 `run_weekly_report()`。
2. `main.py` 改为轻量 CLI 包装，只负责调用 use case、打印结果和返回退出码。
3. 补充 `tests/test_weekly_run.py`，覆盖环境参数解析、观测指标计算和 CLI 委托行为。
4. 更新 `docs/v1-api-plan.md`，标记主流程 use case 封装已完成。

### 3. 设计边界

本次不改变周报主链路行为，不新增真实后台 worker，也不让 `/v1/runs/trigger` 立即执行长任务。下一步才接持久化 job 表和任务执行器。

## 2026-05-11 追加：新增 `/v1` 后端核心接口骨架

### 1. 开发目的

根据核心功能优先路线，开始把现有只读 API 演进为后端服务化入口。当前先补 `/v1/*` 查询接口、任务视图和触发预检，为后续封装主流程 use case、持久化 job 表和 worker 做准备。

### 2. 本次修改

1. `/v1/health` 返回服务状态和能力开关。
2. `/v1/projects`、`/v1/projects/{owner}/{repo}`、`/v1/runs`、`/v1/reports/latest` 复用现有只读归档查询能力。
3. `/v1/jobs` 和 `/v1/jobs/{job_id}` 把历史运行记录映射为最小任务视图。
4. `/v1/runs/trigger` 当前只返回任务计划预览，不直接执行采集、Kimi 生成或推送。
5. 新增 `docs/v1-api-plan.md` 记录接口契约和后续演进路径。

### 3. 设计边界

本次不启动真实后台任务，不新增外部服务，不改变 GitHub Actions 周报主链路。真实执行能力需要等主流程 use case 和持久化 job 表完成后再接入。

## 2026-05-11 追加：核心功能优先建设路线

### 1. 开发目的

根据 `deep-research-report (4).md` 的后端化和 Agent 化建议，重新收敛后续建设方向。后续不再优先消耗在页面细节和末端体验优化上，而是先补齐后端服务化、数据层、Agent/RAG 和任务调度等核心能力。

### 2. 本次修改

1. 新增 `docs/core-development-plan.md`。
2. 明确 P0 到 P5 的建设优先级：主链路稳定、后端服务化、数据层升级、Agent/RAG、异步任务、前端体验。
3. 明确推荐技术栈引入顺序：FastAPI、SQLite、PostgreSQL、Redis、pgvector、APScheduler、Celery、前端框架。
4. README 增加核心建设路线文档入口。

### 3. 设计边界

本次只调整建设路径和文档方向，不改动采集、生成、推送和归档运行逻辑。

## 2026-05-09 追加：增加 workflow 防回归测试

### 1. 开发目的

weekly workflow 已经改为发布到 `weekly-archive`，但刚刚出现过 YAML 冒号导致 Actions 无法解析的问题。需要把关键约束纳入本地测试，避免后续修改 workflow 时再次破坏手动触发和归档分支发布。

### 2. 本次修改

1. 新增 `tests/test_workflows.py`。
2. 检查 weekly workflow 保留 `workflow_dispatch` 和 `ARCHIVE_BRANCH: weekly-archive`。
3. 检查 workflow 不再直接执行 `git commit -m` 或裸 `git push` 推进 `main`。
4. 检查带 `--message` 的命令不再使用容易触发 YAML 冒号解析问题的单行写法。
5. 测试归档发布脚本只复制 `docs/`、`reports/` 和 `data/`，不复制 README 等代码文档文件。

### 3. 设计边界

本次只增加本地测试，不触发远端 Actions，也不实际创建或推送归档分支。

## 2026-05-09 追加：修复 weekly workflow YAML 语法

### 1. 问题原因

`weekly.yml` 中发布归档分支的 `run:` 单行命令包含提交信息 `chore: ...`。YAML 普通字符串中出现冒号加空格会被解析为键值结构，导致 GitHub Actions 报告 workflow 语法无效。

### 2. 本次修改

1. 将两个发布归档分支的 `run:` 命令改为 YAML 折叠块。
2. 保留原提交信息，不改变归档分支发布逻辑。

### 3. 影响

修复后 GitHub 才能正确识别 `workflow_dispatch`，页面右上角会恢复 `Run workflow` 按钮。

## 2026-05-09 追加：将自动归档分离到 weekly-archive 分支

### 1. 问题原因

GitHub Actions 原本会把每周生成的 `reports/`、`data/` 和 `docs/` 直接提交到 `main`。如果本地正在开发，远端 `main` 会被自动推进，导致本地提交经常需要 fetch、rebase，并且生成文件容易出现冲突。

### 2. 本次修改

1. 新增 `scripts/publish_archive_branch.py`，专门把生成文件发布到 `weekly-archive` 分支。
2. 调整 `.github/workflows/weekly.yml`，运行前从 `weekly-archive` 恢复历史 `data/` 和 `reports/`，运行后把 `docs/`、`reports/` 和 `data/` 发布到 `weekly-archive`。
3. `main` 不再由 weekly workflow 自动提交归档文件，后续主要用于代码、配置和文档开发。
4. README 和 setup 文档补充 GitHub Pages 来源应切换为 `weekly-archive / docs`。

### 3. 需要手动处理

首次合并后，需要在 GitHub 仓库 `Settings -> Pages` 中把 Branch 从 `main` 改为 `weekly-archive`，Folder 保持 `/docs`。第一次 workflow 成功运行后才会创建该分支。

## 2026-05-09 追加：减少 feed.xml 重复冲突

### 1. 问题原因

`docs/feed.xml` 的 `lastBuildDate` 原本使用当前构建时间，每次运行页面构建都会变化。GitHub Actions 自动归档也会更新该文件，导致本地提交经常在 rebase 时遇到无业务意义的冲突。

### 2. 本次修改

1. 将 RSS `lastBuildDate` 改为使用最新周报日期。
2. 没有周报时使用固定的 Unix epoch 时间，避免空归档构建产生动态差异。
3. 补充页面构建测试，锁定稳定的 `lastBuildDate` 输出。

### 3. 设计边界

本次只减少生成文件冲突，不改变周报内容、归档结构和推送流程。后续仍建议把 Actions 自动归档迁移到独立分支。

## 2026-05-09 追加：项目筛选页名称进入站内详情

### 1. 问题原因

项目筛选页主表里的项目名称原本直接链接到 GitHub 仓库主页，用户容易认为点击项目名就能进入站内详情页，但实际会跳出到 GitHub。

### 2. 本次修改

1. 将项目筛选页主表的项目名称改为链接到 `project.html?repo=owner/name`。
2. GitHub 仓库完整链接继续保留在展开详情中的“完整链接”区域。
3. 补充页面生成测试，确保项目名称继续作为站内详情页入口。

### 3. 设计边界

本次只调整前端跳转入口，不改变采集、评分、归档和数据结构。

## 2026-05-09 追加：修复项目详情页无参数加载状态

### 1. 问题原因

直接访问 `project.html` 时 URL 中没有 `repo=owner/name` 参数，详情页入口函数会同步抛出“缺少 repo 参数”。旧代码在同步抛错后没有进入 Promise 的 `.catch()`，所以页面保留初始“加载中”状态。

### 2. 本次修改

1. 将详情页初始化改为 `Promise.resolve().then(loadDetail)`，保证同步错误也会进入统一错误处理。
2. 缺少 `repo` 参数时提示用户从项目筛选页点击具体项目进入。
3. 补充页面生成测试，防止后续改动再次让无参数页面卡住。

### 3. 设计边界

本次只修复前端入口错误处理，不改变项目详情 API、归档数据和筛选逻辑。

## 2026-05-09 追加：项目详情页历史趋势

### 1. 开发目的

项目详情页已经能展示历史入选记录，但用户还需要快速判断项目热度和质量是否持续变化。本次在详情页增加轻量趋势视图。

### 2. 本次修改

1. `docs/project.html` 新增“历史趋势”模块。
2. 使用现有历史入选记录展示每期新增 Star 和质量分。
3. 趋势视图使用纯 HTML/CSS 条形展示，不引入图表库。
4. README、API 文档和页面构建测试同步更新。

### 3. 设计边界

本次只增强详情页展示，不改变采集、评分、归档和 API 数据结构。

## 2026-05-09 追加：项目详情前端页

### 1. 开发目的

项目详情 API 已经可用，但用户还缺少可视化入口。本次新增单项目详情页，把列表筛选、只读 API 和静态 JSON 归档连接起来。

### 2. 本次修改

1. 新增 `docs/project.html`，支持 `project.html?repo=owner/name`。
2. 项目筛选页的每个项目行增加“详情页”入口。
3. 详情页展示历史入选次数、首次和最近入选日期、累计新增 Star、最好 Trending 排名、质量提示、风险提示、历史入选记录和相似项目。
4. 详情页在本地后端或 `api=1` 模式下优先读取 `/api/projects/{owner}/{repo}`，失败后自动回退到 `projects.json`。
5. README、API 文档和页面构建测试同步更新。

### 3. 设计边界

本次仍保持静态页面优先，不引入前端框架，不改变数据归档格式。后端 API 只是渐进增强入口。

## 2026-05-09 追加：修复 API 路由测试依赖

### 1. 问题原因

GitHub Actions 中 `fastapi.testclient.TestClient` 会通过 Starlette 依赖 `httpx`。当前依赖文件只声明了 FastAPI 和 Uvicorn，导致 CI 环境安装 FastAPI 后仍缺少 `httpx`，从而在 `python -m unittest` 阶段报错。

### 2. 本次修改

1. 在 `requirements.txt` 中补充 `httpx`。
2. API 路由测试的跳过条件同时检查 FastAPI 和 `httpx`。
3. 保留仓库访问层测试，确保没有完整 API 测试依赖时仍能验证只读归档逻辑。

### 3. 设计边界

本次只修复测试依赖和 CI 稳定性，不改变 API 行为、采集逻辑、数据库结构或推送逻辑。

## 2026-05-09 追加：项目详情 API

### 1. 开发目的

只读后端已经具备项目列表查询能力。为了给后续项目详情页、相似项目推荐、个性化订阅解释和数据库化前端打基础，本次新增单项目详情聚合接口。

### 2. 本次修改

1. 新增 `/api/projects/{owner}/{repo}` 接口。
2. 按项目全名聚合历史入选记录、首次入选日期、最近入选日期、入选次数、累计新增 Star 和最好 Trending 排名。
3. 聚合历史来源、质量提示、风险提示和最近一次质量等级。
4. 返回相似历史项目列表，方便后续前端做详情页推荐。
5. 补充 API 文档、README 和测试覆盖。

### 3. 设计边界

该接口仍然只读取 JSON 归档和 SQLite 派生索引，不触发采集、不调用模型、不推送消息，也不读取任何密钥。

## 2026-05-09 追加：操作日志倒序排列规则

### 1. 调整原因

为了方便阅读和回看最新开发动作，操作日志改为倒序排列，最新操作放在文件最上面。

### 2. 后续规则

以后每次更新 `docs/operation-log.md` 时，新日志都追加到顶部，而不是放到文件末尾。若同一天有多条记录，后发生的操作放在更靠上的位置。

### 3. 影响范围

本次只调整操作日志的排列方式，不改变项目代码、数据契约、采集逻辑或推送逻辑。

## 2026-05-09 追加：项目筛选页接入只读 API

### 1. 开发目的

只读后端 API 已经具备历史项目、运行记录、个性化方向和最新周报接口。本次把项目筛选页改成渐进式接入后端 API，让前端、后端和 SQLite 派生索引开始形成闭环，同时继续保留 GitHub Pages 的纯静态可用性。

### 2. 本次修改

1. `docs/explorer.html` 在本地后端环境下优先读取 `/api/projects` 和 `/api/profiles`。
2. URL 带 `api=1` 时强制尝试后端 API，带 `api=0` 时强制使用静态 JSON。
3. API 不可用时自动回退到 `projects.json` 和 `profiles.json`，避免影响 GitHub Pages。
4. 页面会显示当前数据来源，便于判断正在使用“后端 API”还是“静态 JSON”。
5. `docs/api.md` 和 README 补充前端读取方式说明。

### 3. 设计边界

本次没有引入前端框架，也没有改变现有静态页面的数据契约。后端 API 作为增强入口存在，静态 JSON 仍然是线上 Pages 的默认稳定读取方式。

## 2026-05-09 追加：只读后端 API 骨架

### 1. 开发目的

项目已经具备 GitHub Trending 优先采集、周报生成、GitHub Pages、运行状态面板、个性化方向和 SQLite 派生索引。为了后续快速建设完整前端、数据库管理、用户订阅和个性化推荐，本次先补齐最小后端 API 层。

### 2. 本次修改

1. 新增 `src/api/repository.py`，封装历史项目、运行记录、个性化方向和最新周报的只读访问能力。
2. 新增 `src/api/app.py`，提供 FastAPI 路由：`/api/health`、`/api/projects`、`/api/runs`、`/api/profiles`、`/api/weekly/latest`。
3. 新增 `docs/api.md`，说明本地启动方式、接口参数和后续扩展方向。
4. README 和 Pages 首页增加后端 API 文档入口。
5. 新增 API 测试，FastAPI 未安装时本地路由测试会跳过，但归档访问层测试仍会执行。

### 3. 设计边界

API 当前只读，不触发采集、不调用 Kimi、不推送 Telegram，也不读取任何密钥。JSON 归档仍然是事实来源，SQLite 只作为可重建派生索引。这个边界可以避免当前阶段过早引入复杂服务，同时给后续完整前端和数据库演进留出接口空间。

## 2026-05-07 追加：运行指标与数据契约稳定化

### 1. 开发目的

外部研究文档建议下一阶段优先提升一致性、可验证性和可观测性。当前项目已经能生成周报、Pages 和推送链接，但运行摘要中缺少标准化指标，后续很难持续判断 Trending 保底、README 摘要、GitHub 查询和持续热门项目占比是否健康。

### 2. 本次实现

更新：

```text
docs/data-contracts.md
docs/operation-log.md
main.py
scripts/build_pages.py
src/models.py
src/trends.py
tests/test_data_contracts.py
tests/test_trends.py
```

调整内容：

1. `RunSummary` 新增 `schema_version`。
2. 运行摘要新增采集查询数量、成功数量和成功率。
3. 运行摘要新增 README 抓取率。
4. 运行摘要新增 Trending Top10 可用数量、入选数量和命中率。
5. 运行摘要新增已推送项目入选占比，用于观察持续热门项目。
6. 趋势摘要新增 `schema_version`、Trending Top10 入选数量和 Trending 入选比例。
7. `docs/runs.json` 公开输出这些指标，方便前端、SQLite 和外部脚本复用。
8. 测试覆盖趋势摘要和公共运行 JSON 的数据契约。

### 3. 设计边界

本次只增加可观测指标，不改变推荐逻辑。已推送项目仍然不会被硬过滤，只在评分中降权；这样可以避免把本周仍然热门的项目从周报中错误排除。

## 2026-05-07 追加：推送消息增加项目筛选入口

### 1. 问题来源

前端质量信号改动落在 `explorer.html`，但 Telegram 推送仍只发送 `weekly/YYYY-MM-DD.html` 周报正文链接。用户从手机端打开推送后只能看到周报正文，看不到项目筛选页新增的质量筛选、质量排序和质量信号详情。

### 2. 本次实现

更新：

```text
README.md
docs/data-contracts.md
docs/operation-log.md
docs/setup.md
main.py
scripts/build_pages.py
scripts/send_report_link.py
src/models.py
src/sender.py
tests/test_data_contracts.py
tests/test_send_report_link.py
tests/test_sender.py
```

调整内容：

1. 推送消息同时包含“周报正文”和“项目筛选”两个入口。
2. 周报正文继续指向 `weekly/YYYY-MM-DD.html`。
3. 项目筛选指向 `explorer.html?date=YYYY-MM-DD`。
4. Telegram 使用 HTML 超链接；飞书和企业微信 Webhook 消息同步使用双入口。
5. 运行摘要新增 `telegram_explorer_url`，公开 `docs/runs.json` 也输出该字段。
6. 测试覆盖双链接消息、运行摘要写回和公共 JSON 数据契约。

### 3. 设计边界

本次不改变周报生成内容，也不把完整 Markdown 推送到手机端。推送消息保持短链接形式，只增加一个筛选页入口，方便用户在阅读周报之外继续按方向、语言、质量和风险查看项目。

---

## 2026-05-07 追加：前端质量信号可视化

### 1. 开发目的

前端此前已经读取质量字段，但主要藏在详情页的项目指标文本中，用户不容易直接感知变化。本次把质量信号提升为筛选、排序、表格列和详情块，方便在 GitHub Pages 中直接查看项目质量状态。

### 2. 本次实现

更新：

```text
docs/operation-log.md
scripts/build_pages.py
tests/test_build_pages.py
```

调整内容：

1. 项目筛选页新增“质量”筛选项，支持按高质量、中等质量、低质量和未知过滤。
2. 排序方式新增“质量分”。
3. 项目表格新增“质量”列，直接展示质量等级和质量分。
4. 详情面板新增“质量信号”块，展示质量扣分项。
5. 筛选概览新增平均质量分，便于快速判断当前筛选结果整体质量。
6. 页面构建测试补充质量筛选、质量信号和质量排序的断言。

### 3. 设计边界

本次只增强静态 Pages 前端展示，不改变主采集、评分、报告生成和 Telegram 推送逻辑。质量判断仍来自归档数据中的 `quality_score`、`quality_level` 和 `quality_flags`。

---

## 2026-05-07 追加：GitHub 采集错误分类与限流可观测性

### 1. 开发目的

前一阶段已经补齐运行指标，但 GitHub API 失败仍主要以字符串记录。这样在 Actions 中出现限流、认证失败、仓库不存在或 GitHub 服务异常时，只能靠人工阅读错误文本判断原因，不利于后续稳定运行和告警。

### 2. 本次实现

更新：

```text
docs/data-contracts.md
docs/operation-log.md
src/collector.py
tests/test_collector.py
```

调整内容：

1. GitHub JSON、README 和 Trending HTML 请求统一抛出结构化 `GitHubRequestError`。
2. 采集统计 `collector_stats` 新增 `stage`、`error_kind`、`status_code`、`retry_after`、`rate_limit_remaining` 和 `rate_limit_reset`。
3. 支持识别主限流、二级限流、认证失败、仓库不存在、GitHub 服务错误和普通运行时错误。
4. 部分 Trending 仓库详情抓取失败时，仍保留成功项目，同时把部分失败原因写入统计。
5. 测试覆盖 GitHub 主限流、二级限流和查询失败统计字段。

### 3. 设计边界

本次只增强错误分类和运行可观测性，不新增自动等待重试，也不改变采集排序逻辑。后续如果 Actions 中频繁出现 `rate_limited` 或 `secondary_rate_limited`，再按运行数据决定是否增加退避重试、降低查询数量或拆分采集时间窗口。

---

## 2026-05-07 追加：历史归档查询增强

### 1. 开发目的

项目已经具备 SQLite 派生索引和基础历史查询能力。为了给后续前端数据库页、个性化推荐和项目回看留接口，本次把近期新增的质量信号和 Trending 信号接入归档查询。

### 2. 本次实现

更新：

```text
docs/archive-query.md
docs/operation-log.md
scripts/query_archive.py
tests/test_query_archive.py
```

调整内容：

1. `scripts/query_archive.py` 新增 `--quality-level`、`--min-quality` 和 `--trending-top`。
2. 查询结果新增 `quality_score`、`quality_level` 和 `quality_flags`。
3. 新增 `--sort` 参数，支持按最新、评分、新增 Star、Trending 排名和质量分排序。
4. 表格输出新增质量分列，方便在终端直接筛选高质量项目。
5. 测试覆盖质量分、Trending TopN 和质量排序。

### 3. 设计边界

本次只增强本地归档查询，不改变采集、评分、周报生成和推送逻辑。质量字段来自已经归档的 `data/selected/*.json`，SQLite 仍然是可重建索引，后续前端或 API 可以复用同一套查询参数。

---

## 2026-05-07 追加：运行状态面板

### 1. 开发目的

项目已经把运行指标写入 `runs.json`，但目前只能直接阅读 JSON，不方便在手机或 Pages 页面中快速判断本周是否降级、是否推送成功、采集是否完整。为了补齐前端可观测入口，本次新增静态运行状态面板。

### 2. 本次实现

更新：

```text
README.md
docs/operation-log.md
scripts/build_pages.py
tests/test_build_pages.py
```

调整内容：

1. `scripts/build_pages.py` 新增 `docs/runs.html` 生成逻辑。
2. `runs.html` 直接读取 `runs.json`，不请求任何密钥或私有接口。
3. 页面支持按关键词、运行状态、Kimi/规则版、Telegram 状态和排序方式筛选。
4. 页面展示采集成功率、Trending Top10 命中率、README 抓取率、Kimi 状态、Telegram 状态和周报/筛选入口。
5. 首页和 README 增加运行状态面板入口。

### 3. 设计边界

本次只增加静态前端展示，不改变主流程、采集策略、推送策略和数据契约。后续如果引入真正数据库后台或 API，可以让该页面继续复用 `runs.json`，也可以平滑切换到只读接口。

---

## 2026-05-07 追加：运行状态面板接入采集异常摘要

### 1. 开发目的

采集器已经能识别 GitHub 主限流、二级限流、认证失败、仓库不存在和服务端错误，但此前这些信息主要留在原始运行摘要中。为了让手机端和 Pages 页面可以直接判断采集不完整的原因，本次把脱敏后的采集异常摘要接入公开运行数据和运行状态面板。

### 2. 本次实现

更新：

```text
docs/data-contracts.md
docs/operation-log.md
scripts/build_pages.py
tests/test_build_pages.py
tests/test_data_contracts.py
```

调整内容：

1. `docs/runs.json` 新增 `collector_failed_count`、`collector_error_kinds` 和 `collector_error_summary`。
2. `collector_error_summary` 只保留公开可展示的摘要字段，不输出密钥、请求头或原始堆栈。
3. `runs.html` 新增采集异常筛选项和采集异常列。
4. 运行状态概览新增采集异常次数，便于判断近期是否经常触发 GitHub 限流。
5. 测试同步覆盖公开 JSON 字段、运行状态面板脚本和限流错误摘要。

### 3. 设计边界

本次只展示异常原因，不新增自动重试和等待策略。后续如果运行数据表明 `rate_limited` 或 `secondary_rate_limited` 频繁出现，再基于统计结果调整查询数量、引入退避重试或拆分采集任务。

---

## 2026-05-07 追加：推送消息增加运行状态入口

### 1. 开发目的

手机端推送已经包含周报正文和项目筛选入口，但运行状态面板上线后，用户仍需要手动打开 Pages 才能判断本次是否降级、是否推送成功、是否遇到 GitHub 限流。为了让手机端直接完成阅读、筛选和诊断，本次把 `runs.html` 加入统一推送消息。

### 2. 本次实现

更新：

```text
README.md
docs/data-contracts.md
docs/operation-log.md
main.py
scripts/build_pages.py
scripts/send_report_link.py
src/models.py
src/sender.py
tests/test_build_pages.py
tests/test_data_contracts.py
tests/test_send_report_link.py
tests/test_sender.py
```

调整内容：

1. `src/sender.py` 新增 `runs_url(settings)`。
2. Telegram、飞书和企业微信推送消息统一包含周报正文、项目筛选和运行状态三个入口。
3. 主流程和补推脚本会把 `telegram_runs_url` 写入运行摘要。
4. `docs/runs.json` 公开输出 `telegram_runs_url`，方便前端和外部工具复用。
5. 测试覆盖 URL 生成、三入口消息、补推写回和公开数据契约。

### 3. 设计边界

本次只改变推送消息入口，不改变采集、评分、周报生成和多渠道发送机制。运行状态入口是公开 Pages 页面，不包含 Token、Chat ID、Webhook 或任何密钥。

---

## 2026-05-07 追加：个性化方向可视化页面

### 1. 开发目的

项目已经支持 `profiles.json` 个性化方向配置，但用户需要直接查看 JSON 才能知道当前有哪些方向。为了让 Java、Python、Agent 开发、学习型项目和开发者工具等方向更容易被使用，本次新增公开的个性化方向页面。

### 2. 本次实现

更新：

```text
README.md
docs/operation-log.md
scripts/build_pages.py
tests/test_build_pages.py
```

调整内容：

1. `scripts/build_pages.py` 新增 `docs/profiles.html` 生成逻辑。
2. `profiles.html` 直接读取公开 `profiles.json`，展示方向名称、学习目标、语言和主题。
3. 每个方向提供“查看匹配项目”和“主题筛选”入口，跳转到 `explorer.html?profile=...`。
4. 首页和 README 增加个性化方向页入口。
5. 测试覆盖页面生成、入口链接和公开 profile 数据读取。

### 3. 设计边界

本次只展示公开 profile 配置，不读取 API Key、Token、Chat ID、Webhook 或任何用户私有配置。后续如果接入真正前端和数据库，该页面可以升级为用户偏好选择入口。

---

## 2026-05-06 追加：仓库质量信号

### 1. 开发目的

当前热点筛选已经以 Trending 和新增 Star 为核心，但仍需要区分“热度高”和“信息完整、便于学习或复用”的差异。本次新增轻量质量信号，用于补充判断 README、简介、许可证、主题标签、社区复用和维护连续性等维度。

### 2. 本次实现

更新：

```text
README.md
docs/data-contracts.md
docs/future-plan.md
docs/operation-log.md
main.py
prompts/weekly_report.md
scripts/build_pages.py
src/models.py
src/processor.py
src/quality.py
src/reporter.py
tests/test_build_pages.py
tests/test_data_contracts.py
tests/test_processor.py
tests/test_quality.py
```

调整内容：

1. 新增 `src/quality.py`。
2. `Repository` 新增 `quality_flags`、`quality_score` 和 `quality_level`。
3. 质量信号覆盖 README 摘要、仓库简介、许可证、主题标签、社区复用信号和近期维护时间。
4. 质量分以小权重接入综合评分，不改变 GitHub Trending 第一优先级。
5. 规则版周报新增“质量信号”字段。
6. Kimi 提示词要求参考质量字段解释项目成熟度和信息完整度。
7. `docs/projects.json` 公开输出质量字段，供后续前端、数据库和个性化推荐复用。
8. 探索页详情的项目指标新增质量分展示。

### 3. 设计边界

质量信号是启发式判断，不代表项目一定成熟或可靠。它只用于排序辅助、周报解释和前端展示。后续如果需要更准确的质量判断，可以继续接入 Release 活跃度、提交频率、Issue 响应时间、依赖文件完整度和异常 Star 增长提示。

---

## 2026-05-06 追加：历史归档查询说明页

### 1. 开发目的

历史查询 CLI 已经可用，但入口主要面向开发者。为了让后续前端、数据库和个性化能力有更清楚的文档入口，本次补充 GitHub Pages 可访问的查询说明页。

### 2. 本次实现

更新：

```text
README.md
docs/archive-query.md
docs/operation-log.md
scripts/build_pages.py
tests/test_build_pages.py
```

调整内容：

1. 新增 `docs/archive-query.md`。
2. 说明历史查询的使用场景、常用命令、安全边界和后续扩展方向。
3. GitHub Pages 首页增加“历史归档查询说明”入口。
4. README 的 SQLite 派生索引部分补充说明页引用。
5. 页面构建测试覆盖新增入口。

### 3. 设计边界

该页面是静态说明文档，不引入新的运行依赖。后续如果建设数据库页面或前端后台，可以把这里的命令示例演进为页面筛选项和 API 查询参数。

---

## 2026-05-06 追加：历史归档查询脚本

### 1. 开发目的

前端和数据库已经进入规划阶段，但当前不适合立刻引入完整后台服务。本次先补齐命令行历史查询入口，让 SQLite 派生索引真正可用，为后续后台 API、复杂前端筛选和个性化订阅打基础。

### 2. 本次实现

更新：

```text
README.md
docs/data-contracts.md
docs/operation-log.md
scripts/query_archive.py
tests/test_query_archive.py
```

调整内容：

1. 新增 `scripts/query_archive.py`。
2. 支持按语言、方向、profile、来源、风险提示和关键词查询历史项目。
3. 支持 `--refresh` 在查询前从 JSON 归档同步 SQLite。
4. 支持 `table` 和 `json` 两种输出格式。
5. 新增测试覆盖语言、来源、关键词、profile、风险和表格输出。

### 3. 设计边界

该脚本只读取 JSON 归档、SQLite 派生索引和公开 profile 配置，不读取密钥，不发送外部请求，也不改变主流程。未来如果建设后端 API，可以直接复用其中的筛选条件和输出字段。

---

## 2026-05-06 追加：探索页相似项目推荐

### 1. 开发目的

项目详情已经能展示 README 摘要和推荐理由，但用户还需要在同一方向内横向比较类似仓库。本次在静态探索页中加入相似历史项目推荐，为后续个性化推荐、数据库查询和复杂前端框架迁移预留入口。

### 2. 本次实现

更新：

```text
README.md
docs/explorer.html
docs/operation-log.md
tests/test_build_pages.py
```

调整内容：

1. `docs/explorer.html` 的项目详情新增“相似项目”区域。
2. 相似度暂按语言、方向、来源和项目关键词重合度计算，不依赖新接口或新数据库。
3. 每个项目最多展示 3 个相似历史项目，并显示项目链接、语言、方向和新增 Star。
4. 页面仍然只消费 `projects.json`，后续可把当前相似度函数迁移到前端框架、SQLite 查询或服务端推荐模块。

### 3. 设计边界

当前相似项目推荐是轻量启发式匹配，用于提升浏览效率，不作为最终推荐模型。未来接入数据库后，可以把同语言、同主题、同 profile 和用户点击反馈纳入更稳定的相似度计算。

---

## 2026-05-06 追加：个性化方向快捷视图

### 1. 开发目的

筛选页已有 profile 下拉框，但移动端和频繁切换场景下不够直观。本次增加快捷视图按钮，让用户可以一键切换 Java、Python、Agent 开发等方向，同时继续复用公开 `profiles.json`。

### 2. 本次实现

更新：

```text
README.md
docs/operation-log.md
scripts/build_pages.py
tests/test_build_pages.py
```

调整内容：

1. `docs/explorer.html` 新增 `profileShortcuts` 区域。
2. 页面根据 `profiles.json` 自动生成“全部方向”和各 profile 快捷按钮。
3. 点击快捷按钮会同步更新 profile 筛选条件、表格结果和 URL 查询参数。
4. 当前仍为静态页面实现，不新增前端构建步骤。

### 3. 设计边界

快捷按钮只消费公开 profile 数据，不硬编码业务方向。未来升级到复杂前端框架时，可以直接复用 `profiles.json` 和当前 URL 参数约定。

---

## 2026-05-06 追加：历史项目详情展开

### 1. 开发目的

当前历史项目筛选页已经能按语言、profile、来源和风险筛选，但用户仍需要打开周报或仓库才能理解项目价值。本次在静态筛选页中加入详情展开能力，提升浏览效率，同时继续保留未来升级复杂前端框架的空间。

### 2. 本次实现

更新：

```text
README.md
docs/data-contracts.md
docs/future-plan.md
docs/operation-log.md
scripts/build_pages.py
tests/test_build_pages.py
tests/test_data_contracts.py
```

调整内容：

1. `docs/projects.json` 新增 `readme_summary` 字段。
2. `docs/explorer.html` 每个项目新增“详情”按钮。
3. 展开详情后展示 README 精简摘要、推荐理由、风险提示、项目指标、来源和完整链接。
4. `docs/future-plan.md` 新增前端扩展边界，明确未来可升级到复杂框架，但当前仍以公共 JSON 契约为核心。

### 3. 设计边界

本次没有引入前端构建工具。所有交互仍在静态页面内完成，数据继续来自 `projects.json`、`profiles.json` 和 `runs.json`，为后续框架化迁移保留清晰接口。

---

## 2026-05-06 追加：安全分与风险等级

### 1. 开发目的

此前项目只保存风险提示文本，前端和后续个性化推荐难以排序或筛选风险强弱。本次新增基础安全分和风险等级，为后续安全检查功能、前端筛选和推送摘要提供结构化字段。

### 2. 本次实现

更新：

```text
README.md
docs/data-contracts.md
docs/operation-log.md
scripts/build_pages.py
src/models.py
src/security.py
tests/test_build_pages.py
tests/test_data_contracts.py
tests/test_security.py
```

调整内容：

1. `Repository` 新增 `security_score` 和 `security_level`。
2. `apply_security_flags` 会同步计算安全分和风险等级。
3. 风险等级分为 `low`、`medium`、`high`。
4. 不同风险提示按严重程度扣分，例如恶意软件、钓鱼、窃取类风险扣分更高。
5. `docs/projects.json` 输出安全分和风险等级。
6. `docs/explorer.html` 在风险列展示风险等级和安全分。

### 3. 设计边界

该评分是启发式基础检查，不代表完整安全审计。它用于排序、提醒和后续筛选，不应作为是否可以直接运行外部项目的唯一依据。

---

## 2026-05-06 追加：公开个性化方向数据

### 1. 开发目的

用户希望后续可以通过 Java、Python、Agent 开发等选项精准推送项目。当前 profile 已经能影响采集和评分，但前端缺少稳定公开数据入口。本次新增 `profiles.json`，让 GitHub Pages 和后续前端可以直接读取个性化方向。

### 2. 本次实现

更新：

```text
README.md
docs/data-contracts.md
docs/operation-log.md
scripts/build_pages.py
tests/test_build_pages.py
tests/test_data_contracts.py
```

调整内容：

1. `scripts/build_pages.py` 生成 `docs/profiles.json`。
2. GitHub Pages 首页新增 `profiles.json` 入口。
3. `docs/explorer.html` 新增“个性化方向”筛选项。
4. 筛选页会读取 `profiles.json`，按 profile 的偏好语言和主题关键词过滤历史项目。
5. URL 参数新增 `profile`，方便分享某个个性化方向视图。
6. 契约测试覆盖 `profiles.json` 的公开字段集合。

### 3. 安全边界

`profiles.json` 只公开 profile 名称、显示标签、学习目标、偏好语言和主题关键词，不公开评分权重、私有配置、密钥或用户身份信息。

---

## 2026-05-06 追加：推送通道配置检查

### 1. 开发目的

飞书和企业微信 Webhook 已经支持真实发送，但如果 `DELIVERY_CHANNELS` 启用了通道却没有配置对应 Secret，用户只能在运行后从日志里发现跳过。本次新增独立检查脚本，让配置问题可以提前暴露。

### 2. 本次实现

更新：

```text
.github/workflows/secrets-check.yml
README.md
docs/operation-log.md
docs/setup.md
scripts/check_delivery_channels.py
tests/test_delivery_channel_check.py
```

调整内容：

1. 新增 `scripts/check_delivery_channels.py`。
2. 默认模式只打印 Telegram、飞书、企业微信通道配置状态，不发送真实消息。
3. `--strict` 模式会在启用通道缺少配置或出现不支持通道时返回失败。
4. Secrets 配置检查 workflow 新增推送通道配置检查步骤。
5. 测试覆盖 Telegram 完整配置、飞书缺失 Webhook、企业微信双变量名和不支持通道。

### 3. 安全边界

检查脚本只判断环境变量是否存在，不打印变量值，不发送消息，也不访问外部 Webhook。真实连通性仍由后续发送流程负责。

---

## 2026-05-06 追加：飞书与企业微信 Webhook 推送

### 1. 开发目的

上一阶段已经把推送状态抽象为多通道结果。本次继续补齐飞书和企业微信 Webhook 发送能力，让周报链接可以直接推送到更多移动端协作工具。

### 2. 本次实现

更新：

```text
.env.example
.github/workflows/weekly.yml
README.md
docs/data-contracts.md
docs/operation-log.md
docs/setup.md
src/sender.py
tests/test_sender.py
```

调整内容：

1. `DELIVERY_CHANNELS` 支持 `telegram`、`feishu`、`wechat`。
2. `lark` 会归一为 `feishu`，`wecom`、`weixin` 会归一为 `wechat`。
3. 新增 `FEISHU_WEBHOOK_URL`，用于飞书机器人 Webhook。
4. 新增 `WECHAT_WEBHOOK_URL` 和 `WECOM_WEBHOOK_URL`，用于企业微信机器人 Webhook。
5. 飞书发送交互卡片，企业微信发送 Markdown 消息，内容都只包含周报标题和 GitHub Pages 阅读链接。
6. 未配置 Webhook 的通道会记录为跳过，不影响周报生成、归档和其他通道发送。

### 3. 安全边界

Webhook 地址只从环境变量或 GitHub Actions Secrets 读取，不写入代码和示例值。错误摘要会做字段收敛，只记录平台返回的状态码和简短消息，不记录完整 Webhook 地址。

---

## 2026-05-06 追加：多推送通道入口

### 1. 开发目的

当前实际推送通道是 Telegram。为了后续接入微信、飞书或邮件，本次先把推送结果抽象为通道状态列表，保持现有 Telegram 行为不变，同时让运行摘要和公共 JSON 能记录多通道状态。

### 2. 本次实现

更新：

```text
main.py
src/models.py
src/sender.py
scripts/send_report_link.py
scripts/build_pages.py
tests/test_sender.py
tests/test_send_report_link.py
tests/test_build_pages.py
tests/test_data_contracts.py
.env.example
README.md
docs/data-contracts.md
docs/operation-log.md
```

调整内容：

1. 新增 `DeliveryResult`，记录通道名称、发送状态、错误摘要和是否跳过。
2. 新增 `DELIVERY_CHANNELS` 配置入口，默认 `telegram`。
3. 当前仅 Telegram 会真实发送；`feishu`、`wechat` 会记录为预留通道未实现，不会发送请求。
4. 运行摘要新增 `delivery_results` 字段。
5. `docs/runs.json` 公开输出 `delivery_results`，方便后续前端和外部自动化读取。
6. 保留 `telegram_sent`、`telegram_error`、`telegram_report_url` 旧字段，避免破坏现有 workflow 和页面逻辑。

### 3. 设计边界

本次不提前实现微信、飞书具体 API，也不新增密钥字段。后续接入时再按实际平台要求增加环境变量和发送函数，仍然不能把 Webhook、Token 或 Chat ID 写入代码和文档示例。

---

## 2026-05-06 追加：RSS 订阅输出

### 1. 开发目的

项目已经支持 Telegram 推送和 GitHub Pages 阅读，但还缺少面向阅读器和自动化工具的订阅入口。本次新增 RSS 输出，让用户可以订阅每周周报更新，也为后续微信、飞书、邮件等渠道提供轻量监听来源。

### 2. 本次实现

更新：

```text
.github/workflows/weekly.yml
scripts/build_pages.py
tests/test_build_pages.py
README.md
docs/data-contracts.md
docs/operation-log.md
```

新增产物：

```text
docs/feed.xml
```

调整内容：

1. `scripts/build_pages.py` 在生成 Pages 时同步生成 RSS 2.0 文件。
2. RSS 条目按周报日期倒序生成，最多保留最近 20 篇。
3. 条目链接优先使用运行摘要中的公开 Pages 基础地址。
4. RSS 描述包含入选数量、采集数量、生成方式、Telegram 状态和趋势摘要。
5. workflow 归档提交范围加入 `docs/feed.xml`。
6. 测试验证 RSS 文件生成、标题、周报链接和摘要内容。

### 3. 设计边界

RSS 只发布公开摘要，不包含密钥、用户隐私、原始错误堆栈或未脱敏配置。它是订阅入口，不替代 Telegram 推送和 GitHub Pages 阅读页。

---

## 2026-05-06 追加：可分享筛选视图

### 1. 开发目的

项目筛选页已经可以读取 `projects.json` 做基础筛选，但筛选状态不能复现。为了让后续 Telegram、微信、飞书和浏览器书签能够指向同一个筛选视图，本次补充 URL 状态同步和结果概览。

### 2. 本次实现

更新：

```text
scripts/build_pages.py
tests/test_build_pages.py
README.md
docs/data-contracts.md
docs/operation-log.md
```

调整内容：

1. `docs/explorer.html` 新增日期筛选。
2. 新增筛选结果概览，展示新增 Star、Trending 项目数、风险提示数和主语言/方向。
3. 筛选条件会同步到 URL 查询参数。
4. 打开带查询参数的链接时会自动恢复筛选状态。
5. 新增“复制链接”按钮，方便分享当前筛选视图。
6. 测试覆盖日期控件、分享按钮、URL 状态恢复、URL 更新和结果概览函数存在性。

### 3. 设计边界

本次仍保持无框架静态页面。URL 参数只保存公开筛选条件，不写入隐私信息或密钥。

---

## 2026-05-03 追加：轻量项目筛选页

### 1. 开发目的

公共 JSON 已经具备稳定字段，下一步需要给未来前端和用户浏览提供一个最小可用入口。本次不引入前端框架，只在现有 GitHub Pages 构建流程中生成静态 HTML 页面。

### 2. 本次实现

更新：

```text
scripts/build_pages.py
tests/test_build_pages.py
.github/workflows/weekly.yml
README.md
docs/data-contracts.md
docs/roadmap.md
docs/future-plan.md
```

新增产物：

```text
docs/explorer.html
```

调整内容：

1. `scripts/build_pages.py` 新增 `docs/explorer.html` 生成逻辑。
2. 筛选页直接读取 `docs/projects.json`。
3. 支持关键词、语言、方向、来源、风险提示筛选。
4. 支持按最新入选、新增 Star、Trending 排名、综合分和累计 Star 排序。
5. GitHub Pages 首页新增“项目筛选页”入口。
6. workflow 归档提交范围加入 `docs/explorer.html`。
7. 测试验证筛选页会生成，并包含核心控件和 `projects.json` 数据入口。

### 3. 设计边界

本次没有引入 Astro、React、Vue 或 SSR。页面只是最小可用的静态筛选入口，后续如果交互需求继续增加，再基于公共 JSON 和数据契约评估前端工程化。

---

## 2026-05-03 追加：公共数据契约测试

### 1. 开发目的

公共 JSON 和 SQLite 已经成为后续前端、多渠道推送、订阅和趋势分析的基础。如果字段被无意删除或重命名，下游功能会出现隐蔽问题。本次补充数据契约测试和中文说明文档。

### 2. 本次实现

更新：

```text
scripts/build_pages.py
tests/test_build_pages.py
tests/test_data_contracts.py
docs/data-contracts.md
docs/roadmap.md
docs/future-plan.md
```

调整内容：

1. 新增 `tests/test_data_contracts.py`，固定 `docs/projects.json` 的项目字段集合。
2. 固定 `docs/runs.json` 的运行摘要字段集合。
3. 固定 SQLite 关键表字段集合。
4. 新增 `docs/data-contracts.md`，用中文说明公共 JSON、SQLite 表和修改字段时的要求。
5. GitHub Pages 首页文档入口新增“数据契约说明”。

### 3. 设计边界

契约测试只锁定当前对外稳定字段，不阻止后续新增能力。未来如果确实要新增、删除或重命名字段，应同步更新契约测试、中文文档和所有下游消费逻辑。

---

## 2026-05-03 追加：主流程 SQLite 同步

### 1. 开发目的

上一阶段已经建立 SQLite schema、迁移脚本和校验脚本。本次继续把 SQLite 作为派生索引接入主流程，让每次运行在写入 JSON 归档后自动更新数据库，同时仍保持 JSON 为事实来源。

### 2. 本次实现

更新：

```text
main.py
scripts/send_report_link.py
src/archive.py
src/models.py
tests/test_archive.py
tests/test_send_report_link.py
README.md
docs/roadmap.md
docs/future-plan.md
```

调整内容：

1. `RunSummary` 新增 `sqlite_index_path` 和 `sqlite_error` 字段。
2. `src/archive.py` 新增 `sync_sqlite_index`，会从现有 JSON 归档同步到 SQLite。
3. 主流程在 `write_run_summary` 后自动同步 SQLite；同步失败不会阻断周报生成。
4. `scripts/send_report_link.py` 在 Telegram 状态写回后再次同步 SQLite，保证数据库中的发送状态和最终 JSON 一致。
5. 新增 `SQLITE_INDEX_PATH` 环境变量，用于自定义 SQLite 路径。
6. 新增 `SKIP_SQLITE_INDEX` 环境变量，用于跳过 SQLite 同步。
7. 新增测试覆盖归档同步和发送脚本写回 SQLite 状态字段。

### 3. 设计边界

SQLite 仍是可重建派生索引，不是唯一事实来源。主流程不从 SQLite 读取数据；即使 SQLite 同步失败，报告、归档、Pages 和 Telegram 链路仍继续工作。

---

## 2026-05-03 追加：SQLite 派生索引基础版本

### 1. 开发目的

后续前端筛选、历史趋势查询和个性化反馈都需要更稳定的数据底座。当前 JSON 归档仍然适合作为可读事实来源，但跨周查询和一致性校验会逐步变复杂。因此本次先建立 SQLite 派生索引的最小基础，不改变主流程读取路径。

### 2. 本次实现

更新：

```text
.gitignore
README.md
docs/roadmap.md
docs/future-plan.md
src/storage/schema.sql
src/storage/sqlite_store.py
scripts/migrate_json_to_sqlite.py
scripts/verify_migration.py
tests/test_storage_sqlite.py
```

新增表：

```text
runs
repositories
selections
trend_summaries
sent_repositories
star_history
migration_meta
```

调整内容：

1. 新增 SQLite schema，覆盖运行摘要、仓库、入选记录、趋势摘要、已推送状态和 Star 历史。
2. 新增 `scripts/migrate_json_to_sqlite.py`，可将现有 `data/` JSON 归档导入 `data/github_weekly.sqlite`。
3. 新增 `scripts/verify_migration.py`，校验 SQLite 表计数和 JSON 归档基础计数是否一致。
4. 新增测试验证导入、幂等性、计数一致性和表名保护。
5. `.gitignore` 排除 `data/*.sqlite`、`data/*.sqlite-shm`、`data/*.sqlite-wal`，避免提交派生数据库。

### 3. 设计边界

SQLite 当前只是可重建的派生索引，JSON 仍然是事实来源。主流程尚未接入双写，也没有从 SQLite 读取数据。后续可以在本基础上小步加入主流程双写，再逐步让前端或分析脚本消费 SQLite。

---

## 2026-05-03 追加：公共 JSON 导出

### 1. 开发目的

根据路线图，后续前端、RSS、微信、飞书和外部订阅都需要稳定的数据入口。如果直接读取 Markdown 页面，后续会增加解析成本。因此本次先在现有 Pages 构建流程中导出公开 JSON。

### 2. 本次实现

更新：

```text
.github/workflows/weekly.yml
scripts/build_pages.py
tests/test_build_pages.py
README.md
docs/roadmap.md
docs/future-plan.md
```

新增产物：

```text
docs/projects.json
docs/runs.json
```

调整内容：

1. `scripts/build_pages.py` 会在生成 `docs/index.md` 和 `docs/projects.md` 的同时生成公共 JSON。
2. `projects.json` 汇总历次入选项目的公开摘要字段，包括项目名、链接、语言、方向、来源、Trending 排名、新增 Star、推荐理由和风险提示。
3. `runs.json` 汇总历次运行摘要的公开字段，包括运行日期、入选数量、采集数量、Kimi/降级状态、Telegram 状态和趋势要点。
4. workflow 的两处归档提交都加入 `docs/projects.json` 和 `docs/runs.json`。
5. 新增测试验证公共 JSON 的 schema 版本、数量、项目链接、运行状态和空数据兜底。

### 3. 设计边界

公共 JSON 只导出适合公开展示的摘要字段，不导出密钥、用户隐私、原始错误堆栈或未脱敏配置。SQLite 仍未引入，后续数据库可以从这些公开 JSON 和原始 `data/` 工件继续演进。

---

## 2026-05-03 追加：重复入选项目的新颖度策略

### 1. 开发目的

用户要求周报必须保持“每周最火爆项目”的完整性，因此不能简单过滤已经推送过的仓库。但如果同一批项目连续多周入选，周报会降低新鲜感。本次实现轻量的新颖度惩罚和说明机制。

### 2. 本次实现

更新：

```text
main.py
src/processor.py
config/interests.example.json
tests/test_processor.py
README.md
docs/roadmap.md
docs/future-plan.md
```

调整内容：

1. `process_repositories` 新增可选参数 `previously_sent_names`，旧调用保持兼容。
2. 主流程把 `sent_repos.json` 中的已推送仓库集合传入排序阶段。
3. 新增 `novelty_penalty_weight` 配置，默认 `0.08`，用于轻微降低非 Trending 前十的重复项目分数。
4. GitHub Trending 前十项目不受该惩罚，避免破坏 Trending 优先级和前十保护策略。
5. 重复入选项目会增加推荐理由：“此前已经推送过，本次因仍然具备热点信号继续保留观察。”
6. 新增测试覆盖重复项目不被过滤、非 Trending 重复项目被轻量降权、Trending 前十重复项目仍保持优先。

### 3. 设计边界

本次没有引入按日期窗口的复杂去重，也不删除历史推送状态。后续如果需要更精细的长期体验，可基于 `first_sent_at`、最近推送日期和反馈数据做动态惩罚。

---

## 2026-05-03 追加：吸收研究报告并修复发布状态一致性

### 1. 开发目的

用户提供 `deep-research-report.md` 后，确认后续方向应从“更复杂的抓取器”转向“可复盘、可订阅、可个性化的开源情报系统”。本次先吸收其中适合当前阶段的路线建议，并修复 Pages 页面可能显示旧 Telegram 状态的问题。

### 2. 本次实现

更新：

```text
.github/workflows/weekly.yml
scripts/send_report_link.py
tests/test_send_report_link.py
docs/roadmap.md
docs/future-plan.md
```

调整内容：

1. `scripts/send_report_link.py` 在写回 `data/runs/YYYY-MM-DD.json` 的 Telegram 状态后，会重新构建 GitHub Pages 页面。
2. workflow 的“提交推送状态”步骤同时提交 `docs/index.md`、`docs/projects.md` 和 `docs/weekly`，避免页面状态停留在推送前。
3. 新增测试，验证 Telegram 状态写回后重建页面时，首页会展示“已推送”。
4. 重写 `docs/roadmap.md`，将路线明确为“模块化单体 + SQLite 双写 + 公共 JSON + 中期轻量前端 + 个性化反馈”。
5. 更新 `docs/future-plan.md` 的优先级，把 Pages 状态一致性、重复入选新颖度、SQLite 双写和公共 JSON 提到更靠前的位置。

### 3. 设计边界

本次没有直接引入数据库、前端框架或新外部服务。SQLite、GraphQL、公共 JSON 和前端增强只进入路线图，后续按小步提交逐项实现。

---

## 2026-04-30 追加：代码审查问题修复

### 1. 开发目的

根据最新代码审查结果，修复四类问题：已推送状态影响热点完整性、Kimi 格式小错误导致整份降级、README 摘要字段不清晰、旧架构文档仍保留 `created` 查询示例。

### 2. 本次实现

更新：

```text
main.py
src/models.py
src/collector.py
src/reporter.py
tests/test_collector.py
tests/test_reporter.py
docs/project-architecture.md
```

调整内容：

1. 周报候选池不再因 `sent_repos.json` 过滤历史已推送项目，避免遗漏持续热门项目。
2. 运行摘要新增 `previously_sent_selected_count`，记录本期入选项目中有多少曾经推送过。
3. 删除不再使用的 `filter_unsent_repositories`，避免后续误以为主流程仍会过滤已推送仓库。
4. Kimi 输出进入质量检查前，会自动补齐项目完整链接、来源、Trending 排名和风险提示，减少可修复格式问题导致的降级。
5. `Repository` 新增 `readme_summary` 字段，继续保留 `readme_excerpt` 兼容历史数据。
6. README 规则摘要增加 bullet-only README 的兜底提取。
7. `docs/project-architecture.md` 将旧 `created:>=...` 示例改为当前 `Trending + pushed` 策略。

### 3. 设计边界

本次没有引入数据库或新框架。`sent_repos.json` 仍用于记录推送状态，但不再影响周报候选池；Kimi 修复器只做结构化元数据补齐，不改写模型正文。

---

## 2026-04-30 追加：外部项目 README 精炼摘要

### 1. 开发目的

用户说明需要保留本仓库 README 的完整状态，真正需要精简的是周报中来自外部项目的 README 内容。此前系统会截取外部项目 README 前段文本，容易把过长说明复制进周报页面。

### 2. 本次实现

更新：

```text
src/collector.py
tests/test_collector.py
README.md
```

调整内容：

1. 恢复本仓库 README 的完整版本。
2. 外部项目 README 进入周报前先清理徽章、图片、代码块、表格、安装命令和目录噪声。
3. `readme_excerpt` 改为保存 2-3 句、约 300 字以内的精炼摘要。
4. 规则版周报中原来的“README 摘要”位置会直接使用该精炼摘要，不再展示长篇 README 原文。

### 3. 设计边界

当前摘要是规则型提取，不调用额外模型，避免增加成本和失败点。后续如果 Kimi 稳定，可再让模型基于该精炼摘要做更自然的中文改写。

---

## 2026-04-30 追加：Kimi 过载重试与降级原因修正

### 1. 问题原因

真实运行时 Kimi 返回 `429 engine_overloaded_error`，表示模型服务过载。旧代码没有针对这类临时错误等待重试，而是第一次请求失败后直接回退到规则版周报。

### 2. 本次实现

更新：

```text
src/reporter.py
tests/test_reporter.py
README.md
docs/setup.md
```

调整内容：

1. Telegram 允许继续推送规则版周报链接，保证用户能收到兜底结果。
2. Kimi 返回 `429`、`500`、`502`、`503`、`504`、`engine_overloaded` 或网络临时错误时，会先自动重试。
3. 新增 `KIMI_MAX_RETRIES`，默认重试 `2` 次。
4. 新增 `KIMI_RETRY_SECONDS`，默认每次等待 `20` 秒。
5. 多次重试仍失败时，才会生成规则版周报，并在运行摘要的 `report_error` 中记录完整失败原因。

### 3. 设计结论

本次问题的直接原因不是配置错误，而是 Kimi 服务端过载。后续通过自动重试减少偶发过载导致的降级；如果多次重试后仍失败，说明外部模型服务持续不可用，系统仍会保留规则版周报作为兜底。

---

## 2026-04-30 追加：个性化匹配原因

### 1. 开发目的

用户希望后续不仅能选择 Java、Python、Agent 开发等方向，还能精准推送符合当前需求的项目。本次在已有 profile 选择能力上增加“匹配原因”，让推荐结果可以解释为什么某个项目适合当前选择。

### 2. 本次实现

更新：

```text
src/personalization.py
src/processor.py
tests/test_personalization.py
tests/test_processor.py
README.md
docs/setup.md
```

调整内容：

1. profile 应用后会生成轻量的 `profile_match_rules`。
2. 评分阶段根据仓库语言、topic、名称和简介判断命中哪些个性化方向。
3. 入选项目的 `selection_reasons` 会追加类似“匹配当前个性化方向：Java 后端与工程实践、Agent 开发。”的说明。
4. 该字段会进入 `data/selected/YYYY-MM-DD.json`，可供 Kimi 周报、规则版周报和后续前端筛选复用。

### 3. 设计边界

本次仍不新增前端或数据库。匹配逻辑保持轻量，先以 profile 的语言和主题关键词为依据，后续如果真实周报中误判较多，再扩展更细的规则。

### 4. 追加修正

运行真实周报后发现，子串匹配可能让 `java` 误命中 `JavaScript`。已将 profile 主题匹配调整为词项匹配，并新增测试覆盖，避免语言和主题出现明显误判。
---

## 2026-04-30 追加：个性化 profile 最小版本

### 1. 开发目的

用户希望后续可以通过选择 Java、Python、Agent 开发等选项，精准推送符合当前需求的项目。本次先实现配置层的最小版本，避免提前引入复杂前端或数据库。

### 2. 本次实现

更新：

```text
config/profiles.example.json
src/personalization.py
src/settings.py
tests/test_personalization.py
tests/test_settings.py
README.md
docs/setup.md
.github/workflows/weekly.yml
```

调整内容：

1. 新增 `config/profiles.example.json`，提供 `java`、`python`、`agent_development`、`learning`、`developer_tools` 五类示例方向。
2. 新增 `src/personalization.py`，支持把多个 profile 叠加到基础兴趣配置中。
3. 支持 `INTEREST_PROFILE=java,agent_development` 这种多选形式，为后续前端选择器预留入口。
4. `src/settings.py` 在加载 `config/interests.json` 或 example 后自动应用 profile。
5. GitHub Actions 支持从仓库变量读取 `INTEREST_PROFILE`。
6. README 更新为当前真实项目能力说明。

### 3. 设计边界

本次只做个性化配置入口，不新增数据库、不新增登录系统、不新增复杂前端。profile 中只允许保存兴趣方向、语言、主题、搜索补充项和评分权重，不应写入任何密钥。

---

## 2026-04-30 追加：前端、数据库与个性化分析规划提前

### 1. 开发目的

用户希望后期项目可以构建前端和数据库，同时希望个性化分析提上日程。本次先不直接开工复杂工程，而是把成熟度判断、触发条件、预留目录、分支策略和最终成品展望写入未来规划。

### 2. 本次实现

更新：

```text
docs/future-plan.md
```

新增规划：

1. 前端建设计划。
2. 数据库建设计划。
3. 个性化分析计划。
4. 多分支开发策略。
5. 最终成品展望。
6. 继续推进前需要解决的问题。

### 3. 判断结论

当前前端和数据库还不适合立即完整开发。更合理的路径是先稳定数据结构和周报质量，再做 GitHub Pages 轻量筛选，等历史数据足够后再引入 SQLite 和更完整的前端。个性化分析已经有 `config/interests.json` 基础，可以优先推进 profile 配置设计。

---

## 2026-04-30 追加：Kimi 质量失败自动重试

### 1. 开发目的

此前 Kimi 生成的周报只要未通过质量检查，就会直接回退到规则周报。这样虽然稳定，但会让一些可修复的问题也变成降级版本。本次增加一次自动重试机会，减少可避免的降级周报。

### 2. 本次实现

更新：

```text
src/reporter.py
tests/test_reporter.py
```

调整内容：

1. 首次 Kimi 输出未通过质量检查时，记录质量错误。
2. 第二次请求 Kimi 时，把质量错误作为 `quality_retry_feedback` 传入。
3. 重试指令要求 Kimi 只使用本次输入项目，并修复质量检查问题。
4. 如果第二次仍不合格，才回退到规则周报。
5. 内容安全过滤失败仍保留原有逻辑：必要时去掉 README 摘要后再试。

### 3. 设计边界

该重试只执行一次，避免外部 API 不稳定时无限重试。所有失败原因仍会写入运行摘要的 `report_error`，便于后续排查。

---

## 2026-04-30 追加：周报固定结构检查

### 1. 开发目的

未来计划中提到需要把周报拆成固定结构，减少模型自由发挥。提示词已经要求 Kimi 输出五个核心部分，但代码层还没有验证这些章节是否真的存在。

### 2. 本次实现

更新：

```text
src/report_checks.py
tests/test_report_checks.py
```

新增检查：

1. 本周总体趋势。
2. 热点项目总览。
3. 重点项目分析。
4. 最适合用户学习的项目。
5. 本周结论。

为了兼容已有表达，部分章节允许近义标题，例如“本周趋势”“热门项目总览”“最适合关注的项目”。

### 3. 设计边界

该检查只用于 Kimi 周报质量校验。若 Kimi 输出缺少核心结构，主流程会回退到规则周报，避免生成结构混乱的报告。

---

## 2026-04-30 追加：报告非入选项目链接检查

### 1. 开发目的

未来计划中提到需要检查周报是否包含非入选项目。Kimi 生成周报时可能额外推荐未进入本期筛选结果的 GitHub 仓库，这会削弱 Trending 优先和个性化筛选的约束。

### 2. 本次实现

更新：

```text
src/report_checks.py
tests/test_report_checks.py
```

新增检查：

1. 从周报中提取 `https://github.com/owner/repo` 形式的仓库链接。
2. 与本期入选仓库 `full_name` 对比。
3. 如果出现非入选仓库链接，返回质量错误。
4. Kimi 周报质量检查失败时，主流程会回退到规则周报。

### 3. 设计边界

该检查只针对 GitHub 仓库链接，不限制普通网页、文档链接或 GitHub Pages 周报链接。它用于保证本期周报严格围绕筛选后的项目集合展开。

---

## 2026-04-30 追加：Open Issue 风险提示

### 1. 开发目的

未来计划中提到需要为入选仓库增加 Issue 风险提示。当前 GitHub 仓库详情已经包含 `open_issues_count`，可以先做一条保守规则：当 Open Issue 数量明显偏高时，在周报风险提示中标记“需要人工检查维护响应”。

### 2. 本次实现

更新：

```text
src/security.py
tests/test_security.py
```

新增规则：

```text
open_issues_count >= 100
并且 open_issues_count / stargazers_count >= 0.2
```

满足条件时，`security_flags` 会加入：

```text
Open Issue 数量相对较高，建议复用前人工检查维护响应和问题质量。
```

### 3. 设计边界

该规则只做风险提示，不把项目判定为不可用，也不影响当前排序。Issue 多可能代表项目活跃，也可能代表维护压力较大，因此周报中只提示人工复核。

---

## 2026-04-30 追加：保留脱敏字段名

### 1. 开发目的

通用密钥赋值脱敏应该保留 `api_key=`、`password:` 等字段名，只替换后面的疑似密钥值。这样既能避免敏感字符串进入归档，也能让报告读者知道原文位置存在一个被脱敏的配置字段。

### 2. 本次实现

更新：

```text
src/security.py
tests/test_security.py
```

调整内容：

1. 将明确 token 形态和通用赋值形态分开处理。
2. GitHub token、Telegram bot token 仍整体替换为 `[已脱敏疑似密钥]`。
3. `api_key=...`、`password: ...` 等赋值形态保留键名和分隔符，只替换值。
4. 测试增加对字段名保留行为的断言。

### 3. 使用效果

示例：

```text
api_key=[已脱敏疑似密钥]
password: [已脱敏疑似密钥]
```

---

## 2026-04-30 追加：通用密钥赋值脱敏

### 1. 开发目的

此前运行时脱敏已经覆盖 GitHub token 和 Telegram bot token 的明确格式，但第三方 README 中还可能出现 `api_key=...`、`password: ...`、`chat_id=...` 这类通用密钥赋值。为了和 `scripts/security_check.py` 的扫描策略保持一致，本次扩展运行时脱敏规则。

### 2. 本次实现

更新：

```text
src/security.py
tests/test_security.py
```

新增脱敏匹配范围：

1. `api_key` 或 `api-key`
2. `token`
3. `secret`
4. `password`
5. `chat_id` 或 `chat-id`

### 3. 设计边界

通用赋值规则只替换疑似密钥值，不阻止周报生成。它用于减少第三方内容归档风险，项目自身源码和手写文档仍由 `scripts/security_check.py` 阻断硬编码密钥。

---

## 2026-04-30 追加：报告生成层最终脱敏

### 1. 开发目的

采集层已经会对第三方仓库简介和 README 摘要做脱敏，但报告生成层仍需要最后一道保护，防止手工构造的数据、测试数据或模型输出绕过采集边界，把疑似密钥写入 Markdown 周报。

### 2. 本次实现

更新：

```text
src/reporter.py
tests/test_reporter.py
```

调整内容：

1. `normalize_report_markdown` 会先执行 `redact_sensitive_text`，再做链接和语言规范化。
2. `fallback_report` 返回前会做最终脱敏。
3. `_repository_payload` 会在发给 Kimi 前对 `description` 和 `readme_excerpt` 再次脱敏。
4. 新增测试覆盖报告归一化脱敏和 Kimi payload 脱敏。

### 3. 安全边界

该保护是“最后兜底”，不能替代采集层脱敏和仓库密钥扫描。未来如果报告中增加更多来自第三方的文本字段，应继续复用 `redact_sensitive_text`。

---

## 2026-04-30 追加：第三方内容入库前脱敏

### 1. 开发目的

周报会保存第三方仓库简介和 README 摘要。即使这些内容不是本项目自己的密钥，也不应该把疑似 token 原样写入 `reports/`、`data/selected/` 或 GitHub Pages 周报中。本次在采集边界增加脱敏，降低归档第三方敏感字符串的风险。

### 2. 本次实现

更新：

```text
src/security.py
src/collector.py
tests/test_security.py
tests/test_collector.py
```

新增：

```text
redact_sensitive_text
```

处理范围：

1. GitHub token 形态字符串。
2. Telegram bot token 形态字符串。
3. GitHub 仓库简介进入系统时脱敏。
4. README 摘要进入系统时脱敏。

### 3. 设计边界

该能力用于减少第三方内容归档风险，不改变安全扫描脚本的职责。后续如果接入更多服务，可以继续扩展 `redact_sensitive_text` 的模式列表。

---

## 2026-04-30 追加：排除生成周报目录的密钥误报

### 1. 开发目的

`docs/weekly/` 是由 `reports/` 同步生成的 GitHub Pages 周报目录，里面可能包含第三方仓库 README 摘要。安全检查的目标是保护本项目源码、配置和手写文档中不要硬编码密钥，不应把第三方生成内容误判为本项目自身泄漏。

### 2. 本次实现

更新：

```text
scripts/security_check.py
tests/test_security_check.py
```

调整内容：

1. 新增 `EXCLUDED_PATH_PREFIXES`，当前只排除 `docs/weekly/`。
2. 保留 `docs/setup.md`、`docs/operation-log.md` 等手写文档扫描。
3. 新增测试确认 `docs/weekly/` 中的疑似 token 会被跳过。
4. 新增测试确认普通 `docs/` 文档仍会被扫描。

### 3. 安全边界

该调整只处理误报来源，不降低对项目源码、workflow、配置、提示词和手写文档的检查强度。生成周报仍然会长期归档，因此后续可以考虑在报告生成阶段对 README 摘要做更保守的脱敏处理。

---

## 2026-04-30 追加：安全检查 allowlist 收紧

### 1. 开发目的

项目要求不能在代码中硬编码 API Key、Token、Chat ID 或任何密钥。原安全检查会对包含 `os.getenv(` 的整行直接放行，这在正常读取环境变量时没有问题，但如果有人写入带真实密钥的默认值，例如 `os.getenv("TOKEN", "真实 token")`，就可能被漏检。

### 2. 本次实现

更新：

```text
scripts/security_check.py
tests/test_security_check.py
```

调整内容：

1. allowlist 不再整行跳过所有规则。
2. 对 GitHub token 和 Telegram bot token 这类具有明确格式的密钥，始终执行检测。
3. 仍然允许 GitHub Actions Secrets 引用和环境变量示例通过通用配置检查，避免误报正常配置。
4. 新增测试覆盖 `os.getenv` 默认值中藏入 GitHub token 的情况。

### 3. 安全边界

该检查只能发现常见格式和明显硬编码的密钥，不能替代 GitHub Secret Scanning 或人工审查。后续如果接入更多外部服务，需要继续补充对应 token 格式规则。

---

## 2026-04-30 追加：推送短消息结构预留

### 1. 开发目的

当前只需要 Telegram 推送，但后续可能接入微信、飞书或邮件。为了避免以后把 Telegram 的 HTML 文案复制到其他渠道，本次在不创建复杂 `channels/` 框架的前提下，先抽出统一的短消息结构。

### 2. 本次实现

更新：

```text
src/sender.py
tests/test_sender.py
```

新增：

```text
DeliveryMessage
build_delivery_message
```

字段说明：

1. `title`：周报标题。
2. `url`：GitHub Pages 周报链接。
3. `text`：纯文本消息，适合后续微信、飞书或邮件复用。
4. `html_text`：HTML 消息，当前 Telegram 使用它来发送可点击超链接。

### 3. 架构边界

本次没有提前创建 `src/channels/` 目录，也没有加入微信、飞书或邮件依赖。只有当第二个真实推送渠道接入时，再把各渠道发送函数拆出独立模块。

---

## 2026-04-30 追加：GitHub Pages 内部链接修复

### 1. 开发目的

Telegram 已改为推送 GitHub Pages 的 `.html` 周报页面，但归档首页中仍使用 `weekly/YYYY-MM-DD.md` 作为周报入口。为了让手机端和 Pages 页面内的跳转路径保持一致，本次将页面导航链接统一改为最终网页地址。

### 2. 本次实现

更新：

```text
scripts/build_pages.py
tests/test_build_pages.py
```

调整内容：

1. 周报归档首页中的最新周报链接改为 `weekly/YYYY-MM-DD.html`。
2. 全部周报列表中的历史周报链接改为 `weekly/YYYY-MM-DD.html`。
3. 首页中的项目文档导航改为 `.html` 链接，适配 GitHub Pages 最终渲染页面。
4. 历史项目索引的返回链接改为 `index.html`。
5. 修复历史项目索引在暂无项目时的表格列数，避免表格结构不完整。

### 3. 验证方式

新增单元测试覆盖：

1. 首页是否输出 `.html` 周报链接。
2. 文档导航是否输出 `.html` 链接。
3. 暂无项目时，历史项目索引表格是否仍保持完整列数。

---

## 2026-04-30 追加：运行摘要记录 Telegram 周报链接

### 1. 开发目的

Telegram 改为推送 GitHub Pages 周报链接后，需要在运行摘要中记录实际发送的链接，方便从 GitHub 仓库直接排查本次推送是否指向正确页面。

### 2. 本次实现

更新：

```text
src/models.py
main.py
scripts/send_report_link.py
tests/test_send_report_link.py
```

新增运行摘要字段：

```text
telegram_report_url
```

该字段记录本次发送到 Telegram 的 GitHub Pages 周报页面地址，例如：

```text
https://windsky922.github.io/githubzhuaqu/weekly/YYYY-MM-DD.html
```

### 3. 使用价值

后续排查 Telegram 推送时，可以直接打开 `data/runs/YYYY-MM-DD.json`，确认：

1. `telegram_sent` 是否为 `true`。
2. `telegram_error` 是否为空。
3. `telegram_report_url` 是否是预期的周报页面。

---

## 2026-04-29 追加：Telegram 链接发送顺序调整

### 1. 问题来源

Telegram 已经改为推送 GitHub Pages 周报链接，但原流程是在 `main.py` 内生成报告后立即发送 Telegram。此时 `scripts/build_pages.py` 还没有生成 `docs/weekly/YYYY-MM-DD.md`，GitHub Actions 也还没有把页面提交到仓库，因此用户点击链接时可能遇到页面尚未发布的问题。

### 2. 本次调整

更新：

```text
main.py
scripts/send_report_link.py
.github/workflows/weekly.yml
tests/test_send_report_link.py
```

新的 Actions 顺序：

```text
python main.py（跳过 Telegram）
python scripts/build_pages.py
提交 reports/data/docs 归档
python scripts/send_report_link.py（发送 Pages 链接）
提交 data/runs 和 data/state 中的推送状态
```

### 3. 设计边界

1. 本地运行 `python main.py` 默认仍可直接尝试发送 Telegram，保持兼容。
2. GitHub Actions 中通过 `SKIP_TELEGRAM_SEND=true` 跳过主流程内发送，改由归档提交后的独立脚本发送。
3. 如果 Telegram 未配置或发送失败，脚本会记录状态，但不阻断已经完成的周报归档。

---

## 2026-04-29 追加：Pages 历史项目索引提交范围修复

### 1. 问题来源

复核 workflow 时发现，`scripts/build_pages.py` 会生成：

```text
docs/projects.md
```

但 `.github/workflows/weekly.yml` 的自动提交范围只包含 `docs/index.md` 和 `docs/weekly`，没有包含 `docs/projects.md`。这会导致 GitHub Actions 运行后，历史项目索引可能没有随最新数据一起提交。

### 2. 本次修复

更新：

```text
.github/workflows/weekly.yml
```

将 `docs/projects.md` 加入自动提交范围，确保每次周报生成后，GitHub Pages 首页、周报页面和历史项目索引都能同步刷新。

---

## 2026-04-29 追加：Trending 入选保底与 Telegram 超链接修复

### 1. 问题现象

用户反馈真实运行后仍然没有把 GitHub Trending 放在足够重要的位置，希望 Trending 周榜前 10 的项目至少有 7 个进入热点项目周报。同时 Telegram 推送中的周报地址不能直接点击，需要以超链接形式发送。

### 2. 原因判断

仅依赖评分权重仍可能让高 Star、高增长的 Search API 项目挤掉 Trending Top 10 项目。另一个隐藏原因是历史去重会在排序前过滤已推送项目，如果某个 Trending Top 10 项目之前发过，它会被挡在周报外。

Telegram 侧的问题是当前消息只发送纯文本地址，而且默认生成的是 `.md` 地址；GitHub Pages 更适合使用 `.html` 页面地址。

### 3. 本次实现

更新：

```text
src/processor.py
src/state.py
src/sender.py
config/interests.example.json
tests/test_processor.py
tests/test_state.py
tests/test_sender.py
docs/setup.md
docs/future-plan.md
```

具体变化：

1. `process_repositories` 新增 Trending Top 10 保底选择逻辑。
2. 默认 `min_trending_top10_projects` 为 `7`，即 Trending 前 10 中至少 7 个进入周报；如果可用项目不足 7 个，则保留实际可用数量。
3. `filter_unsent_repositories` 对 Trending Top 10 项目放行，避免历史去重挡掉本周真正热门项目。
4. Telegram 消息改为 HTML 超链接：`打开本周周报`。
5. 周报链接从 GitHub Pages 的 `.md` 地址改为 `.html` 地址，更适合浏览器直接打开。

### 4. 设计边界

该规则只保护 Trending 周榜前 10，不取消其他 Search API 辅助项目。周报剩余名额仍按综合评分补齐，继续保留垂直方向和个性化调整空间。

---

## 2026-04-29 追加：Telegram 改为推送周报链接

### 1. 用户要求

用户希望 Telegram 中直接推送 GitHub Actions 运行后由 Kimi 生成并归档到 GitHub Pages 的周报链接，而不是推送完整 Markdown 正文，方便在手机上阅读。同时需要为后续接入微信、飞书等渠道预留入口。

### 2. 本次实现

更新：

```text
src/sender.py
src/settings.py
tests/test_sender.py
.env.example
docs/setup.md
docs/future-plan.md
```

具体变化：

1. `send_report` 不再把完整 Markdown 拆分发送到 Telegram。
2. 新增 `build_report_message`，统一构建短版推送消息。
3. 新增 `report_url`，用于生成周报公开访问链接。
4. 新增 `REPORT_BASE_URL` 配置，适配自定义域名、自定义 Pages 路径或未来其他展示入口。
5. 如果未配置 `REPORT_BASE_URL`，GitHub Actions 中会根据 `GITHUB_REPOSITORY` 自动推导 GitHub Pages 链接。

默认链接格式：

```text
https://<owner>.github.io/<repo>/weekly/YYYY-MM-DD.md
```

### 3. 后续渠道预留

当前仍保持 Telegram 单渠道，不提前创建复杂的 `channels` 框架。后续接入微信、飞书时，可以复用 `build_report_message` 和 `report_url`，只新增对应渠道的发送函数即可。

---

## 2026-04-29 追加：报告质量校验增强

### 1. 开发目的

当前采集和排序已经把 GitHub Trending 作为第一热度信号。为了避免 Kimi 周报漏掉关键字段，本轮增强报告质量校验，让模型输出必须体现项目来源、Trending 排名和风险提示。

### 2. 本次实现

更新：

```text
src/report_checks.py
src/reporter.py
tests/test_report_checks.py
```

校验规则：

1. 如果项目包含 `sources`，报告中需要出现对应来源，例如 `GitHub Trending` 或 `GitHub Search`。
2. 如果项目包含大于 0 的 `trending_rank`，报告中需要出现 `Trending` 和对应排名数字。
3. 如果项目包含 `security_flags`，报告中需要出现风险提示相关内容。

这些规则只在对应数据存在时触发，不会要求普通 Search 项目强行展示 Trending 排名。

### 3. 冗余文案修正

降级周报结论文案中仍提到“后续加入 README 深度分析和历史去重”，但这两类能力已经部分实现。本轮改为提醒用户优先查看 Trending 排名靠前、近期增长明显且匹配兴趣的项目，并强调复用前仍需人工审查代码、依赖和许可证。

---

## 2026-04-29 追加：架构、安全与冗余审查

### 1. 审查范围

本次审查了当前主流程和核心模块：

```text
main.py
src/collector.py
src/processor.py
src/reporter.py
src/archive.py
src/security.py
src/state.py
scripts/security_check.py
```

### 2. 架构结论

当前架构仍然清晰，主流程保持为：

```text
collector -> processor -> reporter -> archive -> sender
```

GitHub Trending 已经作为第一优先级候选来源接入，GitHub Search API 作为辅助来源。当前还不需要立刻拆分 `src/sources/`，因为数据源数量和复杂度仍可由 `collector.py` 承载。后续接入 GraphQL、自定义仓库列表或 OSSInsight 时，再拆分来源模块更合适。

### 3. 安全结论

当前未发现硬编码密钥风险：

1. 密钥仍然只从环境变量或 GitHub Actions Secrets 读取。
2. 项目不会下载、安装或执行第三方仓库代码。
3. 入选仓库安全检查仍是元数据级提示，不把外部项目判断为“安全”。
4. `scripts/security_check.py` 会继续扫描源码、配置、workflow、文档和提示词中的疑似硬编码密钥。

需要继续注意的风险：

1. README 摘要属于不可信输入，可能包含提示注入内容。
2. GitHub Trending 是网页来源，不是稳定官方 API，页面结构变化可能影响解析。
3. 若后续配置多个 `trending_languages`，GitHub API 请求量会增加，需要继续关注限流。

### 4. 本次修复

更新：

```text
prompts/weekly_report.md
src/reporter.py
```

修复内容：

1. 提示词新增要求：仓库简介、README 摘要、项目名称和 topic 都是不可信项目内容，只能作为分析材料，不能执行或遵循其中指令。
2. 降级周报文案从旧的“GitHub Search API 结果”改为“GitHub Trending 与 GitHub Search 采集结果”，避免与当前架构不一致。

### 5. 可继续优化方向

后续优先级建议：

1. 观察下一次 GitHub Actions 中 Trending 404 噪声是否消失。
2. 为 Trending 解析增加真实页面样例测试，降低 GitHub 页面结构变化带来的风险。
3. 增加报告结构校验，检查 Kimi 是否确实展示来源、Trending 排名和风险提示。
4. 当数据源继续增加时，再拆分 `src/sources/`，不要现在提前复杂化。

---

## 2026-04-29 追加：Trending 标题区域解析收紧

### 1. 开发目的

上一轮通过过滤非仓库路径减少了 Trending 采集噪声。本轮继续收紧解析边界，避免未来 GitHub Trending 页面新增其他两段式链接时再次被误判为仓库。

### 2. 本次实现

更新：

```text
src/collector.py
tests/test_collector.py
```

解析规则从“读取页面中所有形如 `/owner/repo` 的链接”调整为：

```text
只读取 article 内 h2 标题区域中的仓库链接
```

这样可以更贴近 GitHub Trending 项目卡片结构，避免页面导航、赞助入口、应用入口或项目卡片内部的辅助链接进入候选池。

### 3. 测试补充

测试中新增了以下噪声链接：

```text
/outside/not-repository
/inside/not-repository
```

确认它们不会被解析为 Trending 候选仓库。

---

## 2026-04-29 追加：Trending 页面非仓库链接过滤

### 1. 问题来源

检查 GitHub Actions 自动归档回来的 `data/runs/2026-04-29.json` 后发现，GitHub Trending 采集已经生效，但页面解析器把部分非仓库链接也当成仓库，例如：

```text
sponsors/explore
apps/dependabot
apps/github-actions
```

这些路径不是普通仓库，调用 GitHub 仓库详情 API 时会返回 404，导致运行摘要中出现不必要的 `collector_errors`。

### 2. 本次修复

更新：

```text
src/collector.py
tests/test_collector.py
```

修复方式：

1. 在 Trending 链接解析阶段过滤 `sponsors`、`apps`、`users`、`settings` 等非仓库路径前缀。
2. 保留真实仓库路径解析逻辑，不改变 Trending 优先级和评分逻辑。
3. 增加单元测试，确保 `sponsors/explore` 和 `apps/dependabot` 不会进入 Trending 仓库候选列表。

### 3. 预期效果

下一次 GitHub Actions 运行时，Trending 来源的 404 噪声应明显减少。若 GitHub 页面结构继续变化，后续再考虑把解析规则收紧到 Trending 项目卡片区域。

---

## 2026-04-29 追加：Trending 信号展示增强

### 1. 开发目的

上一轮已经把 GitHub Trending 周榜作为第一优先级候选来源。本轮继续补齐可见性：让周报、趋势摘要和 GitHub Pages 历史项目索引都能直接看到项目来源与 Trending 排名，方便判断排序是否符合“Trending 优先”的设计。

### 2. 本次实现

更新：

```text
prompts/weekly_report.md
src/reporter.py
src/trends.py
scripts/build_pages.py
tests/test_reporter.py
tests/test_trends.py
tests/test_build_pages.py
```

具体变化：

1. Kimi 提示词要求优先解释 `trending_rank`，并说明 `sources` 来源。
2. 降级周报的项目总览新增“来源”和“Trending 排名”。
3. 重点项目分析新增“热度来源”。
4. 趋势摘要新增 `trending_project_count` 和 `top_trending`。
5. GitHub Pages 历史项目索引新增“来源”和“Trending 排名”列。

### 3. 设计边界

本次只增强展示与摘要，不改变采集排序逻辑。排序逻辑仍由上一轮的 `score_weights` 控制，后续可以通过 `config/interests.json` 调整权重。

---

## 2026-04-29 追加：GitHub Trending 第一优先级采集

### 1. 用户要求

用户明确希望以 GitHub Trending 作为热点考核的第一指标，其余信号作为辅助，同时保留垂直方向配置，方便后续做个性化调整。

### 2. 架构判断

本次没有提前拆出新的 `src/sources/` 目录，而是在现有 `src/collector.py` 中接入 Trending。原因是当前只有两个来源：GitHub Trending 和 GitHub Search API，直接在采集层扩展更简洁；等后续接入 GraphQL、自定义仓库列表或更多来源时，再拆分来源模块。

当前数据源定位：

1. GitHub Trending 周榜：第一优先级候选来源。
2. GitHub Search API：辅助候选来源，主要用于补充垂直方向和 Trending 遗漏项目。
3. 后续预留：GraphQL 细粒度热度、用户自定义关注仓库。

### 3. 本次实现

更新：

```text
src/models.py
src/collector.py
src/processor.py
config/interests.example.json
tests/test_collector.py
tests/test_processor.py
docs/architecture.md
docs/future-plan.md
docs/setup.md
```

新增仓库字段：

1. `sources`：记录项目来自 `github_trending`、`github_search` 或多个来源。
2. `trending_rank`：记录项目在 GitHub Trending 周榜中的排名。
3. `trending_period`：当前为 `weekly`。
4. `source_priority`：用于保留来源优先级，Trending 高于 Search。

采集流程调整为：

```text
GitHub Trending weekly
-> GitHub Search API 辅助查询
-> 去重并合并来源信号
-> 过滤最近一周活跃项目
-> 综合评分排序
```

### 4. 评分调整

当前默认评分权重：

1. `trending`：45%。
2. `star_growth`：25%。
3. `topic`：15%。
4. `freshness`：10%。
5. `community`：5%。

其中 `community` 由总 Star 和 Fork 共同构成。该设计把 Trending 作为第一指标，同时保留新增 Star、垂直方向匹配、近期活跃和社区基础信号。

### 5. 个性化预留

`config/interests.example.json` 新增：

1. `enable_github_trending`：是否启用 Trending。
2. `trending_languages`：额外采集指定语言的 Trending 榜。
3. `trending_max_repositories`：限制每个 Trending 榜补齐详情的项目数。
4. `search_topics`：Search API 的 topic 补充方向。
5. `search_languages`：Search API 的语言补充方向。
6. `score_weights`：综合评分权重。

后续用户可以通过 `config/interests.json` 调整这些字段，不需要改主流程代码。

---

## 2026-04-29 追加：历史项目索引

### 1. 开发目的

继续增强 GitHub Pages 浏览能力，让用户不只按周报日期回看，也能在一个页面中查看历次入选项目。

### 2. 本次实现

`scripts/build_pages.py` 新增生成：

```text
docs/projects.md
```

该页面从以下目录读取数据：

```text
data/selected/
```

并生成历史项目表格，包含：

1. 日期。
2. 项目名称。
3. 方向。
4. 语言。
5. Star。
6. 新增 Star。
7. 风险提示数量。
8. 完整 GitHub 链接。

### 3. 首页入口

`docs/index.md` 的项目文档区域新增：

```text
历史项目索引
```

### 4. 设计边界

本次仍保持 Markdown 页面，不引入前端框架。后续如果历史项目明显增多，再考虑按语言、方向、日期生成更细的分组页面。

---

## 2026-04-29 追加：历史周报趋势摘要

### 1. 开发目的

继续增强 GitHub Pages 的浏览效率，让“全部周报”列表不仅显示日期和推送状态，也能快速看出每期的主要语言、主要方向和新增 Star。

### 2. 本次实现

更新：

```text
scripts/build_pages.py
tests/test_build_pages.py
```

`docs/index.md` 的每条历史周报记录会在存在趋势数据时追加：

1. 主语言。
2. 主方向。
3. 累计新增 Star。

### 3. 数据来源

该信息来自：

```text
data/trends/YYYY-MM-DD.json
```

如果历史周报没有趋势数据，则保持原有简洁格式。

---

## 2026-04-29 追加：GitHub Pages 首页摘要增强

### 1. 开发目的

继续第四阶段质量与可观测性增强，让 GitHub Pages 首页不只显示周报列表，也能快速看到最新运行状态和趋势要点。

### 2. 本次实现

更新：

```text
scripts/build_pages.py
tests/test_build_pages.py
```

首页新增：

1. 最新运行摘要。
2. 入选项目数。
3. 采集候选数。
4. 生成方式。
5. Telegram 推送状态。
6. 采集错误数量。
7. 最新趋势要点。

### 3. 数据来源

首页读取：

```text
data/runs/YYYY-MM-DD.json
data/trends/YYYY-MM-DD.json
```

### 4. 设计边界

本次仍保持 GitHub Pages 为轻量 Markdown，不引入前端框架。后续当历史周报数量增加后，再考虑筛选、项目卡片和趋势可视化。

---

## 2026-04-29 追加：采集分项统计

### 1. 开发目的

继续第四阶段质量与可观测性增强。此前运行摘要只记录 `collector_errors`，无法清楚看到每条 GitHub Search 查询的成功、失败和返回数量。

### 2. 本次实现

`collect_repositories` 现在返回：

```text
repositories
queries
errors
stats
```

运行摘要新增字段：

```text
collector_stats
```

每条统计包含：

1. `query`：查询条件。
2. `status`：`success` 或 `failed`。
3. `count`：返回仓库数量。
4. `error`：失败原因。

### 3. 价值

后续可以从 `data/runs/YYYY-MM-DD.json` 直接判断：

1. 哪些查询成功。
2. 哪些查询失败。
3. 每条查询贡献了多少候选仓库。
4. 是否存在 GitHub API 限流、网络异常或查询语法问题。

该结构也为后续 GitHub Trending、GraphQL API 等多数据源扩展预留了统计入口。

---

## 2026-04-29 追加：报告质量检查

### 1. 开发目的

继续第四阶段质量与可观测性增强，降低 Kimi 输出缺项、链接格式错误或语言翻译不当的概率。

### 2. 本次实现

新增：

```text
src/report_checks.py
tests/test_report_checks.py
```

当前检查范围：

1. 报告中不能出现“蟒蛇”这类不合适的技术语言翻译。
2. 每个入选项目的完整仓库名必须出现在报告中。
3. 每个入选项目的 GitHub 链接必须以完整 URL 的 Markdown 链接形式出现。

### 3. 主流程变化

Kimi 输出会先经过：

```text
normalize_report_markdown
check_report_quality
```

如果质量检查失败，程序会记录 `report_error`，并回退到规则周报，避免把结构不完整的模型输出推送给用户。

### 4. 后续空间

后续可以继续增强：

1. 检查报告是否包含非入选项目。
2. 对结构问题增加 Kimi 自动重试，而不是直接回退。
3. 检查每个项目是否包含入选原因和风险提示。

---

## 2026-04-29 追加：入选原因记录

### 1. 开发目的

继续第四阶段质量与可观测性增强，增加每个入选项目的解释字段，让用户知道项目为什么进入周报。

### 2. 本次实现

`Repository` 新增字段：

```text
selection_reasons
```

`src/processor.py` 会根据以下信号生成入选原因：

1. 新增 Star。
2. 当前累计 Star。
3. 主题、语言或名称与关注方向匹配。
4. 最近一周仍有更新或维护活动。

### 3. 报告变化

降级版周报在重点项目分析中新增：

```text
入选原因
```

Kimi 提示词也已更新，要求优先使用 `selection_reasons` 解释项目为什么值得关注，并结合 `security_flags` 保持谨慎表述。

### 4. 归档变化

`data/selected/YYYY-MM-DD.json` 会保存每个项目的 `selection_reasons` 字段，为后续报告质量检查和页面展示提供基础数据。

---

## 2026-04-29 追加：入选仓库安全风险提示

### 1. 开发目的

在项目自身密钥扫描之后，继续增加入选仓库的安全风险提示能力。该能力用于提醒用户关注潜在风险，不对第三方项目做安全背书。

### 2. 本次实现

新增：

```text
src/security.py
tests/test_security.py
```

`Repository` 新增字段：

```text
security_flags
```

主流程在抓取 README 后，对最终入选仓库执行：

```text
apply_security_flags(selected)
```

### 3. 当前检查范围

当前只做元数据级检查：

1. 缺少许可证。
2. 仓库已归档。
3. 仓库是 fork。
4. 名称、简介、主题或 README 摘要中包含明显风险关键词，例如空投、赠送、破解、窃取、恶意软件、钓鱼。

### 4. 报告变化

降级版周报的重点项目分析中新增：

```text
风险提示
```

Kimi 周报生成也会收到 `security_flags` 字段，可用于生成更谨慎的项目说明。

### 5. 安全边界

本功能不会执行第三方仓库代码，不会下载或运行项目依赖，也不会把项目判定为安全。风险提示只作为人工复核线索。

---

## 2026-04-29 追加：安全检查基础版本

### 1. 用户要求

用户要求在未来规划中加入安全性检查功能，用于检查项目是否存在安全风险，同时对当前工作方式做安全保护。

### 2. 当前安全状态检查

已检查：

1. GitHub CLI 当前未登录，本机没有继续保留 CLI 登录态。
2. 当前进程环境中未发现 `TOKEN`、`KEY`、`SECRET`、`CHAT_ID` 等密钥类环境变量名。
3. 本次操作不读取、不输出任何真实密钥值。

### 3. 本次实现

新增：

```text
scripts/security_check.py
tests/test_security_check.py
```

能力：

1. 扫描源码、配置、workflow、文档和提示词中的疑似硬编码密钥。
2. 检测 GitHub token、Telegram Bot Token、通用 key/token/secret/password/chat_id 赋值。
3. 允许 GitHub Actions Secrets 引用和 `os.getenv` 这类安全读取方式。
4. 排除 `data/` 和 `reports/`，避免把第三方 README 或生成报告误判为项目自身密钥。

### 4. 工作流接入

`.github/workflows/weekly.yml` 新增步骤：

```text
python scripts/security_check.py
```

该步骤在单元测试前运行。如果发现疑似硬编码密钥，工作流会失败，阻止继续生成和提交归档。

### 5. 未来规划更新

`docs/future-plan.md` 新增“安全风险检查”阶段，后续会扩展到入选仓库风险提示，例如可疑关键词、异常 Star 增长、许可证缺失和维护风险。

---

## 2026-04-29 追加：未来更新规划

### 1. 规划目的

当前前三阶段已经完成，项目具备稳定的采集、筛选、Kimi 周报、Telegram 推送、归档、GitHub Pages 和 Codex 技能能力。

为了避免后续开发直接堆到主流程中，本次补充长期更新路线和架构边界。

### 2. 新增文档

新增：

```text
docs/future-plan.md
```

该文档规划：

1. 数据质量增强。
2. 多数据源采集。
3. 报告质量增强。
4. 推送渠道扩展。
5. 展示页面增强。
6. 长期状态和 SQLite 评估。
7. 短期、中期、长期优先级。
8. 暂不建议做的事项。

### 3. 同步更新

已更新：

1. `docs/roadmap.md`：增加第四阶段和第五阶段。
2. `docs/architecture.md`：增加后续扩展边界。
3. `docs/index.md`：增加未来更新规划入口。

### 4. 设计结论

后续不应提前重构为复杂框架。当前主流程保持稳定，只有当某类能力开始包含多个实现或明显变复杂时，再拆出 `sources`、`quality`、`report_checks`、`channels`、`storage` 等模块。

---

## 2026-04-29 追加：Codex 技能封装

### 1. 开发目的

路线图第三阶段最后一项是“在项目流程稳定后，再封装真正可用的 Codex 技能”。当前采集、筛选、Kimi 周报、Telegram 推送、归档和 GitHub Actions 已完成多次真实运行验证，因此开始封装技能。

### 2. 本次实现

新增技能目录：

```text
skills/github-weekly-agent/
```

核心文件：

```text
skills/github-weekly-agent/SKILL.md
```

技能内容覆盖：

1. 项目维护约束。
2. 主流程。
3. 目录职责。
4. 采集与排序修改规范。
5. 周报生成修改规范。
6. 归档和 GitHub Pages 修改规范。
7. GitHub Actions 修改规范。
8. 本地验证和真实链路验证方式。

### 3. 简洁性处理

本次只创建必要的技能说明，不增加脚本、模板或资产，避免重复维护已有项目代码。

### 4. 路线图更新

`docs/roadmap.md` 中第三阶段 Codex 技能封装标记为已完成。

---

## 2026-04-29 追加：Kimi 内容过滤降级修复

### 1. 问题现象

用户在 GitHub 网页手动触发工作流后，工作流本身运行成功，但生成的是降级版周报。

运行摘要显示：

```text
"kimi_used": false
"fallback_used": true
"report_error": "Kimi API error 400: ... high risk ... content_filter"
```

### 2. 原因判断

这次不是超时，也不是 Secrets 未配置。Kimi API 返回了内容过滤错误，说明请求中的提示词或项目数据被判定为高风险。

最可能的触发源是某个入选仓库的 README 摘要包含模型安全策略不接受的原文内容。

### 3. 修复动作

已在 `src/reporter.py` 中增加安全重试：

1. 第一次仍使用完整项目数据，包括 README 摘要。
2. 如果 Kimi 返回 `content_filter` 或 `high risk`，自动重试一次。
3. 重试时移除 `readme_excerpt`，只保留仓库名称、简介、语言、Star、Fork、链接、分类、趋势摘要等结构化信息。
4. 如果重试成功，则不再生成降级版周报。
5. 如果重试仍失败，才保留原有降级逻辑，避免整个工作流中断。

### 4. 说明

外部模型 API 仍可能因为服务不可用、限流或更严格的安全策略失败，因此无法绝对保证永远不出现降级版。但本次修复已经针对当前真实失败原因做了兜底，能显著降低因 README 原文触发内容过滤而降级的概率。

### 5. 测试补充

已增加测试：当第一次 Kimi 调用返回 `content_filter high risk` 时，程序会自动以不包含 README 摘要的 payload 重试，并在重试成功时返回 Kimi 周报。

---

## 2026-04-29 追加：GitHub Actions Node 24 兼容更新

### 1. 触发原因

GitHub Actions 运行时提示 `actions/checkout@v4` 和 `actions/setup-python@v5` 仍运行在 Node.js 20。GitHub 已提示 Node.js 20 actions 将被弃用。

### 2. 官方版本确认

已确认官方 action 新版本：

1. `actions/checkout@v6`：支持 Node 24。
2. `actions/setup-python@v6`：支持 Node 24。

### 3. 本次调整

已更新：

```text
.github/workflows/weekly.yml
```

调整内容：

```text
actions/checkout@v4 -> actions/checkout@v6
actions/setup-python@v5 -> actions/setup-python@v6
```

### 4. 预期效果

后续每周周报工作流不再触发 Node.js 20 action 弃用警告。

---

## 2026-04-29 追加：GitHub Actions 真实运行复测

### 1. 复测结果

已通过 GitHub CLI 手动触发每周周报工作流：

```text
https://github.com/windsky922/githubzhuaqu/actions/runs/25087537033
```

运行结论：成功。

关键结果：

1. `collected_count`: 210
2. `selected_count`: 10
3. `collector_errors`: []
4. `readme_fetched_count`: 10
5. `telegram_sent`: true
6. `raw_repositories_path`: `data/raw/2026-04-29.json`
7. `selected_repositories_path`: `data/selected/2026-04-29.json`
8. `trend_summary_path`: `data/trends/2026-04-29.json`

### 2. 发现的问题

本次 Kimi 调用超时，运行摘要记录：

```text
"report_error": "The read operation timed out"
```

因此本次周报使用降级模板生成，但主流程、Telegram 推送和归档均成功。

### 3. 修复动作

已将 Kimi 请求超时时间从固定 60 秒调整为可配置项：

```text
KIMI_TIMEOUT_SECONDS
```

默认值为：

```text
120
```

同时更新 `.env.example` 和 `docs/setup.md`。

---

## 2026-04-29 追加：配置说明补充

### 1. 补充原因

代码已经支持优先读取 `config/interests.json`，但配置文档中还没有说明该文件的用途和提交方式。

### 2. 本次更新

已更新：

```text
docs/setup.md
```

新增内容：

1. `config/interests.json` 的读取优先级。
2. `preferred_topics`、`preferred_languages`、`exclude_keywords`、`max_projects`、`min_stars` 的用途。
3. 如果希望 GitHub Actions 使用自定义兴趣配置，需要将 `config/interests.json` 提交到仓库。
4. `config/interests.json` 不应包含任何 API Key、Token 或 Chat ID。

### 3. 处理结论

本次不把 `config/interests.json` 加入 `.gitignore`。原因是该文件不是密钥文件，并且 GitHub Actions 需要从仓库读取它才能使用自定义偏好。

---

## 2026-04-29 追加：代码审查问题修复

### 1. 修复范围

根据阶段性代码审查的下一步建议，本次继续处理数据质量和可观测性问题。

### 2. 采集查询修正

已从 `src/collector.py` 中移除：

```text
created:>=... stars:>10
```

当前采集查询只围绕最近一周 `pushed` 活跃项目展开，避免候选池继续偏向“本周新创建项目”。

### 3. 部分采集失败记录

`collect_repositories` 现在会返回：

```text
repositories
queries
errors
```

如果部分 GitHub 查询失败但仍有其他查询成功，程序会继续生成周报，同时把错误写入运行摘要：

```text
collector_errors
```

这样后续可以从 `data/runs/YYYY-MM-DD.json` 判断采集是否完整。

### 4. 自定义兴趣配置

`src/settings.py` 新增用户配置优先级：

1. 优先读取 `config/interests.json`。
2. 如果不存在，再读取 `config/interests.example.json`。

这样用户可以维护自己的兴趣配置，不需要直接修改示例文件。

### 5. 归档职责明确

本次将原始候选数据和最终入选数据拆开：

1. `data/raw/YYYY-MM-DD.json`：保存本次 GitHub API 采集到的原始候选仓库。
2. `data/selected/YYYY-MM-DD.json`：保存最终入选周报的仓库。

`.github/workflows/weekly.yml` 的自动提交范围也已加入：

```text
data/selected
```

### 6. 测试补充

新增和更新测试：

1. 采集查询不再包含 `created` 条件。
2. 部分采集失败会返回错误列表。
3. `config/interests.json` 优先于示例配置。
4. `data/raw` 和 `data/selected` 写入不同路径。

---

## 2026-04-29 追加：阶段性代码审查记录

### 1. 审查目的

在趋势总结功能提交后，对当前代码进行阶段性审查，确认已经实现的能力、仍存在的风险点，以及下一步开发优先级。

本次审查范围包括：

1. `main.py`
2. `src/collector.py`
3. `src/processor.py`
4. `src/reporter.py`
5. `src/settings.py`
6. `src/state.py`
7. `src/trends.py`
8. `.github/workflows/weekly.yml`
9. 现有测试文件

### 2. 已确认实现的能力

当前项目已经实现：

1. GitHub 近期活跃仓库采集。
2. 仓库去重、过滤、评分和排序。
3. 新增 Star 历史记录与评分加权。
4. README 摘要抓取。
5. Kimi 中文周报生成。
6. Kimi 不可用时生成降级版 Markdown 周报。
7. Telegram 手机推送。
8. Telegram 不可用时保留归档。
9. 周报、原始数据、运行摘要和趋势总结归档。
10. GitHub Actions 定时运行、手动触发和自动提交归档。
11. GitHub Pages 周报归档页面。
12. 单元测试覆盖核心采集、处理、报告、状态和趋势逻辑。

本地验证结果：

```text
py -m unittest
```

结果：20 个测试全部通过。

### 3. 本次审查发现

#### 问题 1：仍保留 `created` 查询，可能继续偏向“新建项目”

位置：

```text
src/collector.py:27
```

说明：

用户已经明确要求关注“一周内最火爆的项目”，而不是“这一周新创建的项目”。当前仍保留：

```text
created:>=... stars:>10
```

该查询会额外引入新建项目。虽然后续会经过活跃时间过滤，但它仍可能影响候选池来源。

建议：

1. 下一步移除该查询；或
2. 将其作为低权重补充来源，并在运行摘要中标明。

#### 问题 2：部分 GitHub 查询失败不会进入运行摘要

位置：

```text
src/collector.py:83-90
```

说明：

当前逻辑只有在所有查询都失败时才抛出错误。如果部分查询失败、部分成功，错误会被内部收集但不会写入 `data/runs/YYYY-MM-DD.json`。

影响：

1. 周报可能正常生成，但采集结果不完整。
2. 后续无法从运行摘要中判断是否发生 GitHub API 限流、网络异常或查询语法问题。

建议：

将部分查询失败记录写入 `RunSummary`，例如新增：

```text
collector_errors
```

#### 问题 3：只读取 example 配置，不利于自定义兴趣配置

位置：

```text
src/settings.py:49
```

说明：

当前 `load_settings` 固定读取：

```text
config/interests.example.json
```

这会让示例配置承担真实配置职责，不利于用户长期维护自己的兴趣偏好。

建议：

优先读取：

```text
config/interests.json
```

如果不存在，再回退到：

```text
config/interests.example.json
```

#### 问题 4：`data/raw` 实际写入的是筛选后项目

位置：

```text
main.py:41
```

说明：

当前调用：

```text
write_raw_repositories(selected, settings)
```

写入的是最终入选项目，而不是原始采集结果。`raw` 命名容易误导后续调试。

建议：

二选一处理：

1. 如果要保留真正原始采集结果，应写入 `collected`。
2. 如果只想保留入选项目，应将函数或目录命名调整为 `selected`。

### 4. 下一步建议

下一步优先处理：

1. 修正采集查询，移除或弱化 `created` 查询。
2. 增强运行摘要，记录部分采集失败。
3. 增加 `config/interests.json` 用户配置优先级。
4. 明确 `data/raw` 与入选项目归档的命名和职责。

这些改动属于数据质量和可观测性增强，不需要推翻现有架构。

---

## 2026-04-28 追加：第三阶段趋势总结

### 1. 开发目的

继续第三阶段产品化输出，增加数据驱动的趋势总结，减少周报趋势部分依赖模型自由发挥。

### 2. 本次实现

新增模块：

```text
src/trends.py
```

该模块根据本期入选仓库生成：

1. 入选项目总数。
2. 累计新增 Star。
3. 主要语言分布。
4. 项目方向分布。
5. 新增 Star 最高的项目列表。
6. 可直接写入周报的趋势要点。

### 3. 归档文件

新增归档路径：

```text
data/trends/YYYY-MM-DD.json
```

运行摘要新增字段：

```text
trend_summary_path
```

### 4. 报告生成变化

Kimi 生成周报时会收到 `trend_summary`。如果本地未配置 Kimi，降级版周报也会在“本周趋势”部分展示趋势要点。

### 5. 工作流变化

`.github/workflows/weekly.yml` 自动提交范围增加：

```text
data/trends
```

### 6. 本地验证

已补充测试：

1. `tests/test_trends.py`
2. `tests/test_reporter.py` 中的趋势要点展示断言

---

## 2026-04-28 追加：提高新增 Star 权重与完整链接显示

### 1. 用户要求

用户要求：

1. 将新增 Star 作为重要筛选依据。
2. 链接部分应显示完整链接，而不是只显示 `GitHub`。

### 2. 评分调整

已将综合评分权重调整为：

1. Star 增量：40%
2. 总 Star：25%
3. 兴趣主题匹配：20%
4. 活跃时间新鲜度：10%
5. Fork：5%

同时排序时增加明确的兜底顺序：

```text
score -> star_growth -> stargazers_count
```

这样新增 Star 会成为判断“本周最火爆”的主要依据。

### 3. 链接显示调整

周报中的 GitHub 链接统一显示为完整 URL，并保持可点击：

```text
[https://github.com/owner/repo](https://github.com/owner/repo)
```

报告清洗逻辑也会把模型生成的短文本链接：

```text
[GitHub](https://github.com/owner/repo)
```

转换为完整 URL 文本链接。

### 4. 本地验证

已补充测试，覆盖：

1. 新增 Star 对排序的优先影响。
2. 原始 GitHub URL 转换为完整 URL 文本链接。
3. `[GitHub](...)` 链接转换为完整 URL 文本链接。

已执行：

```text
py -m unittest
py -m compileall main.py src tests scripts
```

验证结果：通过。

### 5. 当前页面重新生成

已重新执行：

```text
py main.py
py scripts/build_pages.py
```

当前 `2026-04-28` 周报已按新增 Star 高权重重新排序，前两项为：

1. `NousResearch/hermes-agent`，新增 Star 25。
2. `affaan-m/everything-claude-code`，新增 Star 10。

报告和 Pages 页面中的链接均显示完整 URL。

---

## 2026-04-28 追加：修正“本周最火爆”定义与 Kimi 降级原因

### 1. 用户纠正

用户指出：项目应当是一周内最火爆的项目，而不是生成时间或创建时间在一周之内的项目。

这是正确的。本项目的采集逻辑应以“最近一周活跃且热度高”为主，不能只看 `created_at`。

### 2. 采集逻辑修正

已将主查询从 `created:>=...` 改为 `pushed:>=...`：

```text
pushed:>=YYYY-MM-DD stars:>N
topic:ai pushed:>=YYYY-MM-DD stars:>N
topic:agent pushed:>=YYYY-MM-DD stars:>10
topic:llm pushed:>=YYYY-MM-DD stars:>10
topic:automation pushed:>=YYYY-MM-DD stars:>10
language:Python pushed:>=YYYY-MM-DD stars:>N
language:TypeScript pushed:>=YYYY-MM-DD stars:>N
created:>=YYYY-MM-DD stars:>10
```

其中 `created` 查询只作为补充，用于捕捉本周新出现且增长较快的项目。

### 3. 过滤逻辑修正

`Repository` 新增字段：

```text
pushed_at
```

处理阶段不再要求 `created_at >= since_date`，改为要求：

```text
pushed_at 或 updated_at >= since_date
```

这样老项目只要本周仍然活跃且热度高，也可以进入周报。

### 4. Kimi 降级原因判断

本次页面显示“ Kimi API 未启用或调用失败”的直接原因是：为了修正页面，我在本地执行了：

```text
py main.py
```

当前本地环境没有配置：

```text
KIMI_API_KEY
KIMI_MODEL
```

因此程序按设计生成降级版 Markdown 周报，并在 `data/runs/2026-04-28.json` 中记录：

```text
"kimi_used": false
"fallback_used": true
"report_error": "Kimi API 未配置"
```

这不是 GitHub Actions Secrets 失效。之前 GitHub Actions 自动归档提交 `3767552` 中的运行摘要显示：

```text
"kimi_used": true
"fallback_used": false
"telegram_sent": true
```

说明在 GitHub Actions 环境中，Kimi Secrets 曾经正常生效。

### 5. 当前页面重新生成

已重新执行：

```text
py main.py
py scripts/build_pages.py
```

当前 `2026-04-28` 页面已经按最近一周活跃项目重新生成。由于本地未配置 Kimi 和 Telegram，本次页面为降级版，且不会写入已推送状态。

### 6. 校验结果

已确认：

1. `data/raw/2026-04-28.json` 中所有入选项目的 `pushed_at` 或 `updated_at` 都不早于 `2026-04-21`。
2. 报告中没有“蟒蛇”。
3. 热门项目总览中的 GitHub 链接为 Markdown 超链接。

### 7. 本地验证

已执行：

```text
py -m unittest
py -m compileall main.py src tests scripts
```

验证结果：通过。

---

## 2026-04-28 追加：周报页面内容与链接格式修正

### 1. 用户反馈

用户反馈 GitHub Pages 中生成的周报页面存在以下问题：

1. 需要确保页面内容属于本周范围。
2. “主要语言”中不能出现“蟒蛇”这类中文直译，应保留 `Python` 等技术语言英文名称。
3. 热门项目总览中的 GitHub 链接应为可点击超链接。
4. 修改后需要检查代码是否存在冗余或明显问题。

### 2. 本次修正

采集范围修正：

1. 移除 `pushed:>=...` 查询，避免历史老项目仅因本周更新而进入“本周创建项目”周报。
2. 在处理阶段增加 `created_at >= since_date` 二次校验，即使 GitHub Search 查询变化，也不会让非本周创建项目进入周报。

报告格式修正：

1. Kimi 输出和降级报告都会经过 `normalize_report_markdown` 清洗。
2. 将“蟒蛇”统一替换为 `Python`。
3. 将 GitHub 原始 URL 转为 Markdown 超链接。
4. 已经是 Markdown 格式的链接不会重复包装。
5. 降级版周报中的 README 摘要截断展示，避免页面过长影响阅读。

提示词修正：

1. 要求技术语言名称保留官方英文名称。
2. 要求只分析用户数据提供的本周创建项目。
3. 要求热点项目总览中的链接列使用 Markdown 超链接格式。

### 3. 当前页面重新生成

已重新执行：

```text
py main.py
py scripts/build_pages.py
```

说明：本地环境没有 Kimi 和 Telegram 密钥，因此本次重新生成的 `2026-04-28` 页面为降级版周报，且不会写入已推送状态。GitHub Actions 后续正式运行时仍会读取仓库 Secrets 并使用 Kimi 与 Telegram。

### 4. 校验结果

已确认：

1. `reports/2026-04-28.md` 和 `docs/weekly/2026-04-28.md` 中没有“蟒蛇”。
2. 热门项目总览中的 GitHub 链接已为 `[GitHub](...)` Markdown 超链接。
3. `data/raw/2026-04-28.json` 中所有入选项目的 `created_at` 都不早于 `2026-04-21`。

### 5. 本地验证

已执行：

```text
py -m unittest
py -m compileall main.py src tests scripts
```

验证结果：通过。

---

## 2026-04-28 追加：第三阶段 GitHub Pages 周报归档页面

### 1. 开发目的

进入第三阶段产品化输出后，优先实现轻量的周报归档页面，让生成的周报可以通过 GitHub Pages 直接浏览。

### 2. 本次实现

新增脚本：

```text
scripts/build_pages.py
```

该脚本负责：

1. 读取 `reports/` 下的周报。
2. 读取 `data/runs/` 下的运行摘要。
3. 生成 `docs/index.md` 周报归档首页。
4. 将周报同步到 `docs/weekly/YYYY-MM-DD.md`。

### 3. 工作流变化

`.github/workflows/weekly.yml` 新增步骤：

```text
python scripts/build_pages.py
```

自动提交范围新增：

```text
docs/index.md
docs/weekly
```

### 4. 本次生成文件

```text
docs/index.md
docs/weekly/2026-04-28.md
```

### 5. GitHub Pages 启用方式

在 GitHub 仓库中进入：

```text
Settings -> Pages
```

设置：

```text
Source: Deploy from a branch
Branch: main
Folder: /docs
```

### 6. 本地验证

已执行：

```text
py scripts/build_pages.py
py -m unittest
py -m compileall main.py src tests scripts
```

验证结果：通过。

---

## 2026-04-28 追加：第二阶段 Star 增量评分

### 1. 开发目的

补齐第二阶段数据质量增强中的历史热度能力。单纯按总 Star 排序容易长期偏向大型老项目；加入 Star 增量后，可以更好发现近期增长明显的项目。

### 2. 本次实现

新增状态文件：

```text
data/state/star_history.json
```

该文件记录：

1. 仓库完整名称。
2. 仓库链接。
3. 最近一次采集到的 Star 数。
4. 最近一次采集日期。

### 3. 评分变化

`Repository` 新增字段：

```text
star_growth
```

计算方式：

```text
star_growth = 当前 Star - 历史 Star
```

如果没有历史记录，则增长值为 0。

当前评分权重：

1. 总 Star：35%
2. Fork：15%
3. 兴趣主题匹配：25%
4. Star 增量：15%
5. 创建时间新鲜度：10%

### 4. 主流程变化

主流程会在处理仓库前读取 Star 历史，在完成本次归档时写入最新 Star 历史。

运行摘要新增字段：

1. `star_history_updated_count`
2. `star_history_path`

### 5. 初始状态写入

由于 `2026-04-28` 已经有一次成功完整运行，本次使用 `data/raw/2026-04-28.json` 初始化 `data/state/star_history.json`，为下一次运行提供增量基线。

### 6. 本地验证

已执行：

```text
py -m unittest
py -m compileall main.py src tests
```

验证结果：通过。

---

## 2026-04-28 追加：第二阶段 README 摘要抓取

### 1. 开发目的

提升周报内容质量。仅依赖仓库名称和简介时，Kimi 对项目定位容易过于粗略；加入 README 摘要后，可以让周报更准确地说明项目用途、特性和学习价值。

### 2. 实现范围

本次实现保持简洁，不增加新依赖，不引入复杂缓存或数据库。

新增能力：

1. 对最终入选周报的仓库抓取 README。
2. 清洗 README 中的多余空白。
3. 每个仓库只保留前 2000 个字符作为摘要。
4. 单个 README 获取失败时跳过，不影响整体运行。
5. Kimi 提示词要求优先参考 README 摘要。
6. 降级版周报也会展示 README 摘要。

### 3. 主流程变化

新的处理顺序：

```text
collect_repositories
-> load_sent_repository_names
-> filter_unsent_repositories
-> process_repositories
-> enrich_repositories_with_readmes
-> generate_report
-> send_report
-> write_sent_repositories
```

### 4. 运行摘要变化

`data/runs/YYYY-MM-DD.json` 新增字段：

```text
readme_fetched_count
```

该字段记录本次成功获取 README 摘要的入选仓库数量。

### 5. 本地验证

已执行：

```text
py -m unittest
py -m compileall main.py src tests
```

验证结果：通过。

---

## 2026-04-28 追加：第二阶段已推送仓库状态记录

### 1. 开发目的

进入第二阶段数据质量增强后，优先实现最小且必要的历史状态能力，避免同一仓库在后续周报中被重复推送。

### 2. 本次实现

新增模块：

```text
src/state.py
```

该模块负责：

1. 读取 `data/state/sent_repos.json`。
2. 过滤已经成功推送过的仓库。
3. Telegram 推送成功后写入新的已推送仓库。
4. 兼容旧的字符串数组格式和新的对象数组格式。

### 3. 主流程变化

新的处理顺序：

```text
collect_repositories
-> load_sent_repository_names
-> filter_unsent_repositories
-> process_repositories
-> generate_report
-> send_report
-> write_sent_repositories
```

状态写入条件：

1. Telegram 推送成功。
2. 本次筛选出的新仓库列表不为空。

如果 Kimi 不可用，仍可使用降级版周报；如果 Telegram 不可用或发送失败，则不会写入已推送状态，避免遗漏后续真实推送。

### 4. 运行摘要变化

`data/runs/YYYY-MM-DD.json` 新增字段：

1. `skipped_sent_count`：本次采集结果中被历史推送状态跳过的仓库数。
2. `state_path`：本次成功写入的状态文件路径。

### 5. 工作流变化

`.github/workflows/weekly.yml` 的自动提交范围增加：

```text
data/state
```

这样 GitHub Actions 生成的已推送状态会和周报、原始数据、运行摘要一起提交回仓库。

### 6. 本地验证

已执行：

```text
py -m unittest
py -m compileall main.py src tests
```

验证结果：通过。

### 7. 初始状态写入

由于 `2026-04-28` 的完整工作流已经确认 Telegram 推送成功，本次同步创建：

```text
data/state/sent_repos.json
```

该文件使用 `data/raw/2026-04-28.json` 中的 10 个已推送仓库初始化，避免下一次运行重复推送同一批项目。

---

## 2026-04-28 追加：完整周报工作流验证

### 1. 验证目的

在用户完成 GitHub Secrets 配置后，对完整自动化链路进行验证，确认从 GitHub Actions 到周报归档、Kimi 生成和 Telegram 推送的流程可以正常运行。

验证链路：

```text
GitHub Actions
-> python -m unittest
-> python main.py
-> GitHub 项目采集
-> Kimi 中文周报生成
-> reports/ 与 data/ 归档
-> Telegram 推送
-> Actions 自动提交归档文件
```

### 2. 临时触发方式

为避免等待每周定时任务，临时给 `.github/workflows/weekly.yml` 增加了仅用于测试的 `push` 触发器。

测试完成后已移除该临时触发器，正式工作流保留：

1. `workflow_dispatch` 手动触发。
2. 每周一 UTC 00:00 的定时触发。

### 3. 第一次完整流程测试

运行链接：

```text
https://github.com/windsky922/githubzhuaqu/actions/runs/25031865017
```

运行结论：成功。

归档结果：

1. `reports/2026-04-28.md`
2. `data/raw/2026-04-28.json`
3. `data/runs/2026-04-28.json`

本次结果显示 Telegram 推送成功，但 Kimi 周报生成使用了降级报告。为便于后续定位，随后在运行摘要中增加了 `report_error` 字段，并增强了 Kimi 响应内容提取逻辑。

### 4. 第二次完整流程测试

运行链接：

```text
https://github.com/windsky922/githubzhuaqu/actions/runs/25031996992
```

运行结论：成功。

关键结果：

1. `collected_count`: 165
2. `selected_count`: 10
3. `kimi_used`: true
4. `fallback_used`: false
5. `telegram_sent`: true
6. `report_path`: `reports/2026-04-28.md`
7. `run_summary_path`: `data/runs/2026-04-28.json`

说明：第二次完整流程已经确认 Kimi 正常生成中文周报，Telegram 正常推送，Actions 自动归档提交正常执行。

### 5. 本次代码与文档调整

1. `src/models.py`：为运行摘要增加 `report_error` 字段。
2. `src/reporter.py`：让 Kimi 生成失败时返回明确错误原因，并兼容更多响应内容结构。
3. `main.py`：写入 `report_error`，便于从 `data/runs/` 追踪模型生成问题。
4. `tests/test_reporter.py`：增加 Kimi 响应内容提取测试。
5. `.github/workflows/weekly.yml`：移除测试用 `push` 触发器。
6. `docs/operation-log.md`：记录完整工作流验证过程和结果。

### 6. 当前结论

Secrets 配置已经通过完整链路验证。当前项目已具备按周自动抓取 GitHub 热点项目、生成中文周报、推送到 Telegram、归档运行结果并自动提交到 GitHub 的基础能力。

---

## 2026-04-27 追加：GitHub Secrets 配置测试

### 1. 测试方式

新增检查工作流：

```text
.github/workflows/secrets-check.yml
```

该工作流通过 GitHub Actions 读取仓库 Secrets，并验证：

1. `GH_SEARCH_TOKEN` 是否存在并可访问 GitHub API。
2. `KIMI_API_KEY`、`KIMI_BASE_URL`、`KIMI_MODEL` 是否存在并可调用 Kimi API。
3. `TELEGRAM_BOT_TOKEN`、`TELEGRAM_CHAT_ID` 是否存在并可发送 Telegram 测试消息。

### 2. 初始测试结果

运行结论：失败。

已确认：

1. 所有必要 Secrets 都能被 GitHub Actions 读取到。
2. `GH_SEARCH_TOKEN` 验证通过，GitHub API 剩余额度正常。

失败点：

```text
Kimi API 返回 HTTP 400。
```

### 3. 失败原因

GitHub Actions 日志显示：

```text
invalid temperature: only 1 is allowed for this model
```

说明当前配置的 Kimi 模型只允许 `temperature=1`。

### 4. 修复动作

已将以下位置的 `temperature` 改为 `1`：

1. `src/reporter.py`
2. `.github/workflows/secrets-check.yml`

### 5. 最终测试结果

最终运行结果：成功。

已确认：

1. `GH_SEARCH_TOKEN` 已配置，并通过 GitHub API 验证。
2. `KIMI_API_KEY` 已配置。
3. `KIMI_BASE_URL` 已配置。
4. `KIMI_MODEL` 已配置。
5. Kimi API 可以连通并返回 `choices`。
6. `TELEGRAM_BOT_TOKEN` 已配置。
7. `TELEGRAM_CHAT_ID` 已配置。
8. Telegram 测试消息发送成功。

GitHub Actions 成功运行链接：

```text
https://github.com/windsky922/githubzhuaqu/actions/runs/24992511910
```

说明：本次 Kimi 轻量测试请求返回内容为空，但 HTTP 调用成功并返回了有效 `choices` 字段，因此判断为 API 配置可用。正式周报生成流程会使用完整提示词和项目数据调用 Kimi。

---

## 2026-04-27 追加：文档中文化

### 1. 用户要求

用户要求项目中所有文档使用中文书写，将英文写成的部分重新用中文表达。

### 2. 本次处理范围

本次已将以下文档性文件中的英文说明改写为中文：

1. `AGENTS.md`
2. `docs/architecture.md`
3. `docs/setup.md`
4. `docs/roadmap.md`
5. `prompts/weekly_report.md`
6. `.env.example`
7. `requirements.txt`
8. `.github/workflows/weekly.yml` 中面向用户显示的工作流名称和步骤名称

### 3. 保留内容

以下内容属于技术名词、命令、路径、环境变量名或 GitHub Actions 语法，保持原样：

1. `GitHub Weekly Agent`
2. `GitHub Actions`
3. `Telegram`
4. `Kimi API`
5. `python main.py`
6. `GH_SEARCH_TOKEN` 等环境变量名
7. `.github/workflows/weekly.yml` 中的工作流关键字

---

## 2026-04-27 追加：第一阶段 MVP 开发

### 1. 开发范围

严格按照收敛后的 MVP 架构开发，未创建暂缓的 `skills/`、Web Dashboard、SQLite 或复杂插件系统。

本次实现内容：

1. `AGENTS.md` 项目级 Agent 开发规则。
2. `prompts/weekly_report.md` 独立周报提示词。
3. `main.py` 主流程编排。
4. `src/collector.py` GitHub Search API 采集。
5. `src/processor.py` 去重、过滤、评分和排序。
6. `src/reporter.py` Kimi 生成和 fallback 基础报告。
7. `src/sender.py` Telegram 分段推送。
8. `src/archive.py` Markdown、原始数据和运行摘要归档。
9. `src/settings.py` 环境变量和兴趣配置读取。
10. `src/utils.py` 日期、分段和通用辅助函数。
11. `.github/workflows/weekly.yml` 定时和手动触发工作流。
12. `tests/` 最小单元测试。

### 2. 简洁性处理

1. 暂不增加外部依赖，`requirements.txt` 保持标准库实现。
2. 暂不拆分 HTTP clients，避免 MVP 过度抽象。
3. 暂不创建 Skill 目录，等工作流稳定后再产品化。
4. 每个模块只负责一个主要职责。

### 3. 本地验证

已执行：

```text
py -m unittest discover -v
py -m compileall main.py src tests
py main.py
```

验证结果：

1. 3 个单元测试通过。
2. Python 编译检查通过。
3. 端到端运行成功生成报告。
4. 本地未配置 Telegram，程序按设计输出 `Telegram is not configured`，未阻断归档流程。

本地验证生成的临时报告和运行数据不作为源码提交。

---

## 2026-04-27 追加：基于 pi-mono 的重新架构审查

### 1. 学习参考项目

参考链接：

```text
https://github.com/badlogic/pi-mono
```

重点学习内容：

1. `pi-mono` 是围绕 AI Agent 构建的 monorepo，包含统一 LLM API、Agent runtime、coding agent、TUI、Web UI、Slack bot 和 vLLM pods 管理工具。
2. `pi-coding-agent` 的核心思想是最小核心、工具扩展、Prompt Templates、Skills、AGENTS.md、Sessions 和 Extensions。
3. 对本项目最有价值的是项目级 Agent 规则、提示词模板外置、运行历史记录、可扩展但不过度复杂的模块边界。

### 2. 审查新版架构文档

输入文件：

```text
D:\liulanqixiazai\github-weekly-agent-rearchitecture-from-pi-mono.md
```

结论：

1. 新版架构方向正确，适合作为原架构的升级版。
2. `AGENTS.md` 和 `prompts/weekly_report.md` 应纳入第一阶段。
3. `data/` 历史记录设计应保留，但要区分不可变运行摘要和可变去重状态。
4. `skills/` 目录只应作为后续预留说明，MVP 阶段不建议创建空 Skill 文件，避免增加无实际用途的维护面。
5. GitHub Actions 自动提交必须加入防循环、并发控制和变更检测。

### 3. 本次新增文档

输出文件：

```text
docs/pi-mono-rearchitecture-review.md
```

该文档记录：

1. 从 `pi-mono` 学到的可采纳设计。
2. 新版架构中建议保留的部分。
3. 需要收敛或延后的部分。
4. 面向“代码简洁完整”的最终开发建议。

---

## 2026-04-27

### 1. 读取原始文档

输入文件：

```text
D:\liulanqixiazai\github-weekly-agent-architecture.md
```

处理结果：

1. 首次读取时终端中文显示为乱码。
2. 使用显式 UTF-8 重新读取后，确认文档内容完整可读。
3. 已完成对项目目标、用户需求、模块设计、技术选型、MVP 和验收标准的审查。

### 2. 审查架构

结论：

1. 原架构总体清晰，不需要推翻重建。
2. 需要补强热点定义、GitHub Actions 自提交、防循环、Telegram 分段、运行摘要和模块边界。
3. 推荐采用“原始架构 + 工程化增强”的架构。

输出文件：

```text
docs/architecture-review.md
```

### 3. 生成优化后的项目文档

新增完整架构文档，覆盖：

1. 项目定位。
2. 推荐架构。
3. 数据流。
4. MVP 范围。
5. 推荐目录结构。
6. 模块职责。
7. 搜索策略。
8. 推荐评分。
9. 周报格式。
10. Telegram 推送策略。
11. 运行归档。
12. GitHub Actions 要求。
13. 安全要求。
14. 迭代路线。

输出文件：

```text
docs/project-architecture.md
```

### 4. 建立仓库入口文档

新增 `README.md`，用于说明当前仓库状态、文档索引、项目目标、技术路线和第一阶段范围。

### 5. 当前阶段未执行的事项

按照用户要求，本阶段暂不开发项目代码，因此没有创建 Python 源码、GitHub Actions workflow、依赖文件或运行脚本。

后续如果进入开发阶段，再按 `docs/project-architecture.md` 中的开发顺序实施。

---

