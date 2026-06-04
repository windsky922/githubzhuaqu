# 后端 API 说明

本文档记录当前后端 API 的最小可用设计。`/api/*` 继续作为兼容只读接口，`/v1/*` 用于任务调度、受控执行和后续管理端能力。

## 一、定位

当前项目已经具备 JSON 归档、SQLite 派生索引、GitHub Pages 前端和多通道推送。后端 API 的第一阶段目标是把这些能力整理成稳定入口，方便后续接入更完整的前端、数据库管理、用户订阅和个性化推荐。

设计边界：

1. JSON 归档仍然是事实来源。
2. SQLite 仍然是可重建的派生索引，不提交到 GitHub。
3. API 不读取、不返回任何密钥。
4. `/v1/runs/trigger` 只创建 planned 任务，真实执行必须走任务模型和受控执行入口。
5. `/v1/jobs/{job_id}/execute` 复用执行前检查并调用现有 job runner，不单独实现采集、Kimi 或推送逻辑。

## 二、本地启动

先安装依赖：

```powershell
py -m pip install -r requirements.txt
```

启动服务：

```powershell
py -m uvicorn src.api.app:app --reload
```

默认访问：

```text
http://127.0.0.1:8000/api/health
```

本地管理首页：

```text
http://127.0.0.1:8000/admin.html?api=1
```

根路径 `http://127.0.0.1:8000/` 会跳转到管理首页。`/v1/*` 路径是 JSON API，例如 `/v1/jobs?limit=50` 返回机器可读任务数据，不是 HTML 页面。

管理首页中的 RAG 区域会调用 `/v1/rag/ask`、`/v1/rag/retrieve` 和 `/v1/rag/vector-search`，用于查看问答结果、证据块、引用和 `prompt_context`；RAG 诊断会调用 `/v1/rag/diagnostics`，用于判断语料、证据块、embedding、解释历史和问答能力是否可用；RAG 质量概览会调用 `/v1/rag/quality-summary`，用于查看解释数量、质量分布、改进建议和低质量样本；RAG 回填区会调用 `/v1/rag/backfill-explanations`，先预览缺口项目，确认后再写入 SQLite。向量检索会在 `auto_build=true` 时自动构建本地 `local-hash-v1` 索引，也可以先手动运行 `py scripts\build_rag_embeddings.py`。

如果本地没有 `data/github_weekly.sqlite`，查询项目接口会从 `data/` 下的 JSON 归档自动重建 SQLite 派生索引。

## 三、接口

### `GET /api/health`

检查 API 是否可用，并返回本地归档目录和 SQLite 文件是否存在。

### `GET /api/projects`

查询历史入选项目。支持参数：

| 参数 | 说明 |
|---|---|
| `language` | 按主要语言筛选，例如 `Python`、`Java` |
| `category` | 按项目方向筛选，例如 `AI Agent`、`Developer Tools` |
| `profile` | 按 `config/profiles.json` 或示例 profile 筛选 |
| `source` | 按来源筛选，例如 `github_trending`、`github_search` |
| `risk` | `has` 表示有风险提示，`none` 表示无风险提示 |
| `quality_level` | `high`、`medium`、`low` 或 `unknown` |
| `min_quality` | 最低质量分，范围 0 到 100 |
| `trending_top` | 只看进入 GitHub Trending TopN 的项目 |
| `query` | 关键词搜索项目名、简介、方向和推荐理由 |
| `limit` | 返回数量，范围 1 到 200 |
| `sort` | `recent`、`position`、`score`、`star-growth`、`trending`、`quality` |

示例：

```text
/api/projects?profile=agent_development&source=github_trending&trending_top=10&limit=20
```

### `GET /api/projects/{owner}/{repo}`

查询单个项目的历史详情。该接口会按 `owner/repo` 聚合历史入选记录，并返回：

1. 最近一次入选日期和第一次入选日期。
2. 历史入选次数。
3. 累计新增 Star。
4. 最好 GitHub Trending 排名。
5. 推荐理由和趋势判断。
6. 历史来源、质量提示和风险提示。
7. 最近一次完整项目记录。
8. 相似历史项目列表。

示例：

```text
/api/projects/owner/agent
```

这个接口用于后续项目详情页、项目对比、相似项目推荐和个性化订阅解释。

### `GET /api/recommendations`

返回面向用户选择场景的推荐项目列表。它复用历史归档、SQLite 派生索引和 profile 过滤逻辑，但响应字段更适合推荐页直接展示。

支持参数：

| 参数 | 说明 |
|---|---|
| `profile` | 个性化方向，例如 `agent_development`、`python`、`java` |
| `language` | 主要语言，例如 `Python`、`Java`、`TypeScript` |
| `category` | 项目方向，例如 `AI Agent`、`Developer Tools`、`Backend` |
| `query` | 关键词，匹配项目名、简介、方向和推荐理由 |
| `limit` | 返回数量，范围 1 到 200 |
| `sort` | `score`、`trending`、`star-growth`、`quality`、`recent` 等 |

示例：

```text
/api/recommendations?profile=agent_development&language=Python&limit=20
```

返回内容包含：

1. `recommendations`：推荐项目数组。
2. `selection_summary`：本次推荐的筛选条件、命中数量、Trending 命中和首选项目说明。
3. `profile`、`language`、`category`、`query`：前端回显当前筛选条件。

对应的 v1 入口为：

```text
/v1/recommendations?profile=agent_development&limit=20
```

### `GET /api/runs`

返回公开运行记录，数据来源为 `docs/runs.json`。

### `GET /v1/database/summary`

返回 SQLite 派生索引的数据库概览，用于本地管理台、数据健康检查和后续 RAG 索引准备。该接口会返回：

1. `table_counts`：`runs`、`repositories`、`selections`、`jobs`、`job_events`、`subscriptions` 等表的记录数。
2. `latest_run` 和 `latest_job`：最近一次运行和最近一个任务。
3. `job_status_counts` 和 `subscription_status_counts`：任务状态和订阅状态分布。
4. `top_languages` 和 `top_categories`：当前归档中主要语言和项目方向分布。
5. `recent_events`：最近 10 条任务审计事件。
6. `rag_readiness`：后续构建文本索引或向量检索前的基础数据量提示。

该接口只读取本地 SQLite 统计摘要，不返回密钥、Webhook、请求头或完整原始载荷。

### `GET /v1/database/trends`

返回近 N 次运行的数据库趋势点，用于观察周报质量、数据变化和后续推荐特征。支持参数：

| 参数 | 说明 |
|---|---|
| `limit` | 返回最近运行数量，默认 20，最大 100 |

返回内容包括：

1. `points`：按时间升序排列的运行趋势点，包含入选数量、采集数量、新增 Star、Trending 命中率、Top10 命中数量、Kimi/降级/推送状态。
2. `summary`：聚合摘要，包含总入选数量、总新增 Star、平均 Trending 命中率、失败运行数、降级运行数和推送成功数。

该接口只做统计读取，不调用 GitHub、Kimi、Telegram 或任何外部服务。

### `GET /v1/database/facets`

返回数据库分面统计，用于前端筛选、个性化推荐和后续 RAG 索引建设。支持参数：

| 参数 | 说明 |
|---|---|
| `limit` | 每类分面最多返回数量，默认 20，最大 100 |

返回内容包括：

1. `languages`：按语言聚合项目数量、总 Star、总 Fork 和最近推送时间。
2. `categories`：按项目方向聚合入选次数、项目数、新增 Star、平均分和 Trending Top10 命中率。
3. `sources`：按来源聚合入选次数和项目数，例如 `github_trending`、`github_search`。
4. `quality_levels` 和 `risk_levels`：从入选项目载荷中提取质量等级和风险状态。
5. `subscriptions`：统计本地订阅的状态、profile、语言和方向分布。
6. `rag_readiness`：提示当前分面数据是否足够支撑个性化筛选和后续文本索引。

该接口只读取 SQLite 中的公开归档字段，不返回密钥、Webhook、请求头或完整原始载荷。

### `GET /v1/search`

读取 SQLite 派生的 `project_corpus` 语料表，按关键词搜索历史入选项目。当前优先使用 SQLite FTS5，FTS 不可用时自动回退到普通 SQL 文本匹配；不调用模型、不调用外部服务，后续可以平滑升级为向量检索或 RAG。

支持参数：

| 参数 | 说明 |
|---|---|
| `q` | 必填，搜索关键词，多个词用空格分隔 |
| `language` | 可选，按语言过滤 |
| `category` | 可选，按项目方向过滤 |
| `source` | 可选，按来源过滤，例如 `github_trending` |
| `limit` | 返回数量，默认 20，最大 100 |

返回内容包括：

1. `results`：搜索结果数组，包含项目名、链接、语言、方向、来源、命中片段、质量等级、Trending 排名和新增 Star。
2. `search_engine`：本次使用的搜索引擎，通常为 `fts5`，回退时为 `like`。
3. `summary`：本次搜索的命中数量、主要语言和主要方向。

示例：

```text
/v1/search?q=agent%20workflow&language=Python&limit=10
```

### `GET /v1/rag/corpus`

读取 SQLite 派生的 `project_corpus` 语料表，输出可直接进入 RAG 管道的文档列表。这个接口不会调用模型、不会生成 embedding、不会请求外部服务，只负责把历史项目语料整理成稳定的 `text + metadata + evidence` 数据契约，方便后续接入向量库、LangChain 或其他检索增强组件。

支持参数：

| 参数 | 说明 |
|---|---|
| `q` | 可选，关键词检索；传入后优先使用 SQLite FTS5，失败时回退普通文本匹配 |
| `language` | 可选，按语言过滤 |
| `category` | 可选，按项目方向过滤 |
| `source` | 可选，按来源过滤，例如 `github_trending` |
| `limit` | 返回文档数量，默认 20，最大 100 |

返回内容包括：

1. `documents`：RAG 文档数组，每条包含 `id`、`text`、`metadata` 和 `evidence`。
2. `metadata`：包含仓库全名、GitHub 链接、入选日期、语言、方向、来源、质量等级、Trending 排名和新增 Star。
3. `evidence`：从语料文本中抽取的证据片段，用于后续回答时引用或解释。
4. `retrieval`：本次读取使用的模式，可能是 `fts5`、`like` 或 `latest`。
5. `rag_readiness`：提示当前结果是否已经具备 embedding、检索器和 RAG 编排的基础条件。

示例：

```text
/v1/rag/corpus?q=agent%20workflow&language=Python&limit=10
```

该接口是数据库能力升级到 RAG 能力的第一层稳定出口。后续如果接入 embedding 或 LangChain，应优先复用这个接口的字段，而不是重新解析 Markdown 周报或原始 README。

### `GET /v1/rag/retrieve`

基于 SQLite `rag_chunks` 语料块执行 RAG 检索，返回短文本上下文、引用列表和可直接交给后续问答链的 `prompt_context`。这个接口仍然不调用模型、不生成 embedding、不请求外部服务，先用 SQLite FTS5 提供稳定的本地检索能力，后续可以替换或叠加向量检索。

支持参数：

| 参数 | 说明 |
|---|---|
| `q` | 必填，用户问题或检索关键词 |
| `language` | 可选，按语言过滤 |
| `category` | 可选，按项目方向过滤 |
| `source` | 可选，按来源过滤，例如 `github_trending` |
| `limit` | 返回上下文数量，默认 8，最大 30 |

返回内容包括：

1. `contexts`：召回的 RAG 短文本块，包含 `text`、`metadata`、`evidence` 和规则分。
2. `citations`：按上下文顺序生成的引用列表，包含项目名、GitHub 链接、入选日期和 chunk 编号。
3. `prompt_context`：拼接后的上下文文本，供后续 Kimi、OpenAI 或 LangChain 问答链直接使用。
4. `retrieval`：本次检索使用的模式，可能是 `fts5` 或 `like`。

示例：

```text
/v1/rag/retrieve?q=agent%20workflow&language=Python&limit=8
```

该接口是后续“项目知识库问答”和“基于证据的推荐解释”的核心入口。当前阶段只做本地证据召回，避免过早绑定某个向量库或模型供应商。

### `GET /v1/rag/vector-search`

基于本地 `rag_embeddings` 表执行向量检索，返回与用户问题最接近的 RAG 证据块。当前默认模型为确定性 `local-hash-v1`，用于打通向量索引表、构建命令和检索 API；它不调用外部模型、不需要密钥，后续可替换为真实 embedding 模型。

使用前先构建本地索引：

```powershell
py scripts\build_rag_embeddings.py
```

支持参数：

| 参数 | 说明 |
|---|---|
| `q` | 必填，用户问题或检索关键词 |
| `language` | 可选，按语言过滤 |
| `category` | 可选，按项目方向过滤 |
| `source` | 可选，按来源过滤，例如 `github_trending` |
| `limit` | 返回上下文数量，默认 8，最大 30 |
| `model` | 可选，默认 `local-hash-v1` |
| `auto_build` | 可选，为 `true` 且索引为空时自动构建本地索引 |

返回内容与 `/v1/rag/retrieve` 接近，包含 `contexts`、`citations`、`prompt_context` 和 `retrieval`。差异在于 `retrieval.mode` 为 `vector`，排序依据为本地向量相似度。

示例：

```text
/v1/rag/vector-search?q=agent%20workflow&language=Python&limit=8&auto_build=true
```

该接口是后续真正接入 embedding、向量库和 LangChain retriever 的预留层。当前实现只建设稳定数据边界，不改变周报采集、生成和推送流程。

### `GET /v1/rag/explain`

基于 `/v1/rag/retrieve` 或 `/v1/rag/vector-search` 的召回结果生成规则版 RAG 解释。该接口不调用外部模型，不请求 GitHub/Kimi/Telegram，只把已有证据块整理为“推荐解释、证据引用、风险提示、下一步动作”，用于后续接入模型总结、项目详情页解释和 LangChain 编排。

支持参数：

| 参数 | 说明 |
|---|---|
| `q` | 必填，用户问题或检索关键词 |
| `language` | 可选，按语言过滤 |
| `category` | 可选，按项目方向过滤 |
| `source` | 可选，按来源过滤，例如 `github_trending` |
| `limit` | 返回上下文数量，默认 8，最大 30 |
| `mode` | 可选，默认 `fts5`；传 `vector` 时走本地向量检索 |
| `model` | 可选，向量模式下默认 `local-hash-v1` |
| `auto_build` | 可选，向量模式下索引为空时自动构建本地索引 |

返回字段包含：

1. `contexts`：参与解释的 RAG 证据块。
2. `citations`：可引用的项目、日期和 chunk ID。
3. `prompt_context`：后续交给模型时可复用的上下文。
4. `explanation.answer`：规则版结论。
5. `explanation.why_recommended`：推荐依据。
6. `explanation.evidence`：裁剪后的证据摘要。
7. `explanation.risks`：证据缺口或人工复核提示。
8. `explanation.next_steps`：后续动作。

示例：

```text
/v1/rag/explain?q=agent%20workflow&language=Python&limit=8
/v1/rag/explain?q=agent%20workflow&mode=vector&auto_build=true
```

这是当前 RAG 从“召回证据”升级到“解释输出”的第一层接口。后续如果接入真实 LLM，应优先复用 `citations` 和 `prompt_context`，并要求模型按引用编号回答。

### `GET /v1/rag/ask`

面向前端和后续 Agent 编排的 RAG 问答入口。它复用 `/v1/rag/explain` 的检索、解释和 SQLite 解释历史写入能力，但返回结构更接近“可直接展示或交给下一步工具”的问答结果。

当前版本仍是本地规则版，不调用外部模型、不读取密钥。后续接入 Kimi、LangChain 或其他问答链时，应优先保持该接口的 `answer + citations + prompt_context + next_actions` 数据边界稳定。

支持参数与 `/v1/rag/explain` 一致：

| 参数 | 说明 |
|---|---|
| `q` | 必填，用户问题 |
| `language` | 可选，按语言过滤 |
| `category` | 可选，按项目方向过滤 |
| `source` | 可选，按来源过滤，例如 `github_trending` |
| `limit` | 返回上下文数量，默认 8，最大 30 |
| `mode` | 可选，默认 `fts5`；传 `vector` 时走本地向量检索 |
| `model` | 可选，向量模式下默认 `local-hash-v1` |
| `auto_build` | 可选，向量模式下索引为空时自动构建本地索引 |

返回字段包含：

1. `answer`：当前规则版回答。
2. `answer_model`：回答生成策略，当前为 `rule:rag-ask-v1`。
3. `citations`：回答引用的项目、日期和 chunk ID。
4. `evidence`：裁剪后的证据摘要。
5. `quality`：解释质量分与质量等级。
6. `prompt_context`：后续接入模型时可直接使用的上下文。
7. `next_actions`：建议的下一步核验或补库动作。
8. `source_explanation_id`：本次问答复用或写入的 RAG 解释编号。

示例：

```text
/v1/rag/ask?q=agent%20workflow&language=Python&limit=8
/v1/rag/ask?q=agent%20workflow&mode=vector&auto_build=true
```

### `GET /v1/rag/explanations`

查询已经写入 SQLite 的 RAG 解释历史。每次调用 `/v1/rag/explain` 都会把解释结果写入 `rag_explanations` 表，便于后续查看解释质量、比较 FTS 与向量模式、评估模型替换效果。

支持参数：

| 参数 | 说明 |
|---|---|
| `q` | 可选，按 query 或 answer 做模糊过滤 |
| `repo` | 可选，按解释覆盖的仓库过滤，格式为 `owner/name` |
| `limit` | 返回数量，默认 20，最大 100 |

返回字段包含 `query`、`repo`、`explanations`。每条解释包含 `explanation_id`、`query`、`mode`、`model`、`confidence`、`quality_score`、`quality_level`、`quality`、`answer`、`repositories`、`citations`、`explanation`、`retrieval` 和 `created_at`。

`quality` 是规则版质量评估，当前会统计证据块数量、引用数量、覆盖项目数量、解释依据数量、风险数量和是否包含 `prompt_context`。它用于判断解释是否足够可靠，不代表项目本身质量分。

示例：

```text
/v1/rag/explanations?limit=20
/v1/rag/explanations?q=agent
/v1/rag/explanations?repo=owner/agent
```

该接口只读取 SQLite 中的解释历史，不触发新的检索、不调用外部模型，也不包含密钥。

### `GET /v1/rag/quality-summary`

汇总 SQLite 中 RAG 解释历史的质量状态，用于判断当前 RAG 数据是否足够支撑模型总结、项目详情解释和后续 LangChain 编排。该接口只读 `rag_explanations`，不触发新检索。

支持参数：

| 参数 | 说明 |
|---|---|
| `limit` | 返回最近低质量样本和最近解释数量，默认 10，最大 50 |

返回字段包含：

1. `total_count`：解释历史总数。
2. `average_quality_score`：平均质量分。
3. `quality_levels`：高/中/低质量解释数量。
4. `confidence_levels`：解释置信度分布。
5. `modes`：FTS、向量等检索模式分布。
6. `recent_low_quality`：最近低质量解释样本。
7. `latest`：最近解释样本。
8. `recommendations`：下一步改进建议。

示例：

```text
/v1/rag/quality-summary?limit=10
```

### `GET /v1/rag/coverage`

检查历史项目的 RAG 覆盖缺口，用于判断哪些项目缺少证据块、embedding 或解释历史。该接口只读 SQLite，不触发外部请求，适合作为后续补库脚本、Agent 自动优化和管理页健康检查的数据源。

支持参数：

| 参数 | 说明 |
|---|---|
| `limit` | 返回缺口项目数量，默认 20，最大 100 |

返回字段包含：

1. `total_projects`：项目语料中覆盖的项目数量。
2. `healthy_project_count`：证据块、embedding 和解释历史均具备的项目数量。
3. `coverage_rate`：健康项目占比。
4. `gap_count`：存在 RAG 覆盖缺口的项目数量。
5. `gaps`：缺口项目列表，每项包含 `chunk_count`、`embedding_count`、`explanation_count`、`average_quality_score` 和 `gap_reasons`。
6. `recommendations`：下一步补库建议。

示例：

```text
/v1/rag/coverage?limit=20
```

可用 `scripts/backfill_rag_explanations.py` 按该接口的缺口结果批量生成规则版解释：

```text
python scripts/backfill_rag_explanations.py --dry-run
python scripts/backfill_rag_explanations.py --limit 10
```

### `GET /v1/rag/diagnostics`

返回数据库/RAG 的统一健康诊断。它组合 SQLite 表计数、RAG 质量摘要和覆盖缺口，不写入数据、不调用外部模型，适合本地管理页、GitHub Actions 或后续 Agent 自检使用。

支持参数：

| 参数 | 说明 |
|---|---|
| `limit` | 返回低质量样本和覆盖缺口数量，默认 10，最大 50 |

返回字段包含：

1. `status`：诊断状态，例如 `needs_corpus`、`needs_explanations`、`needs_maintenance`、`ready_for_text_rag` 或 `ready`。
2. `level`：健康等级，可能为 `low`、`medium` 或 `high`。
3. `signals`：布尔信号，包括是否已有语料、证据块、embedding、解释历史，以及是否可回答。
4. `table_counts`：核心 RAG 表记录数。
5. `quality`：解释历史数量、平均质量分和质量分布。
6. `coverage`：项目覆盖率、缺口数量和缺口样本。
7. `next_actions`：建议的下一步维护动作。

示例：

```text
/v1/rag/diagnostics?limit=10
```

### `POST /v1/rag/backfill-explanations`

按 `/v1/rag/coverage` 的缺口结果，为缺少解释历史的项目批量生成规则版 RAG 解释。该接口只使用本地 SQLite 和现有 RAG 检索逻辑，不调用外部模型、不请求 GitHub/Kimi/Telegram。

为避免误写数据库，接口默认 `dry_run=true`。如果请求中传入 `dry_run=false` 但没有同时传入 `confirm_execution=true`，后端会自动改回预览模式，并在 `safety_warnings` 中说明原因。

请求 JSON 支持字段：

| 字段 | 说明 |
|---|---|
| `limit` | 回填项目数量，默认 10，最大 100 |
| `rag_limit` | 每个项目解释时召回的证据块数量，默认 8，最大 30 |
| `mode` | 检索模式，支持 `fts5` 或 `vector` |
| `model` | 向量模式使用的 embedding 模型名，默认 `local-hash-v1` |
| `auto_build` | 向量模式缺少索引时是否自动构建本地索引 |
| `dry_run` | 是否只预览，不写入 SQLite；API 默认 `true` |
| `confirm_execution` | API 写库确认开关；只有 `dry_run=false` 且该字段为 `true` 才会创建解释历史 |
| `trigger_source` | 可选调用来源，默认 `rag_backfill_api` |
| `requested_by` | 可选调用者标识，默认 `api` |

返回字段包含：

1. `accepted`：请求是否被后端接受处理。
2. `dry_run`：本次实际执行模式。
3. `job_id`：本次回填任务编号，可用于查询任务详情和事件。
4. `safety_warnings`：安全降级提示。
5. `coverage_before`：回填前的覆盖概况。
6. `processed`：本次计划或创建的项目记录。

每次 API 调用都会写入一个 `kind=rag_backfill` 的任务记录。可以通过 `GET /v1/jobs?kind=rag_backfill` 查看最近回填任务，通过 `GET /v1/jobs/{job_id}/events` 查看 `rag_backfill_started` 和 `rag_backfill_completed` 等审计事件。脚本入口 `scripts/backfill_rag_explanations.py` 仍只执行补库逻辑，不额外写入任务审计。

示例：

```text
POST /v1/rag/backfill-explanations
{"limit": 3, "dry_run": true}

POST /v1/rag/backfill-explanations
{"limit": 3, "dry_run": false, "confirm_execution": true}
```

### `POST /v1/rag/backfill-plan`

创建一个 `kind=rag_backfill`、`status=planned` 的 RAG 回填计划任务，但不立即执行。请求字段与 `/v1/rag/backfill-explanations` 一致。接口会返回 `job_id`，后续可调用：

```text
GET /v1/job-execution-check?job_id=...
POST /v1/jobs/{job_id}/execute
```

执行时必须传入 `confirm_execution=true`。如果计划任务自身为 `dry_run=false`，创建计划时也必须传入 `confirm_execution=true`，否则后端会自动改为 `dry_run=true`，避免误写 SQLite。

### `POST /v1/rag/maintenance-plan`

检查 RAG 诊断状态与覆盖缺口，并按需创建 RAG 回填 planned 任务。该接口会先调用 `/v1/rag/diagnostics`；如果 `project_corpus` 或 `rag_chunks` 还没有准备好，只返回 `reason=rag_diagnostics_needs_corpus` 和诊断建议，不创建无效回填任务；如果 `gap_count` 小于 `min_gap_count`，只返回健康状态，不创建任务；如果已经存在相同参数的 active `rag_backfill` 任务，则返回 `duplicate_of`，避免重复补库。

返回结果会包含 `diagnostics`、`coverage`、`gap_count` 和 `min_gap_count`，方便 GitHub Actions、后台管理页或后续 Agent 判断下一步应先建语料、补向量，还是创建解释回填任务。

常用请求字段：

| 字段 | 说明 |
|---|---|
| `limit` | 本次计划回填项目数量，默认不超过缺口数和 10 |
| `coverage_limit` | 覆盖缺口检查数量，默认 100，最大 500 |
| `min_gap_count` | 至少发现多少缺口才创建任务，默认 1 |
| `dry_run` | 创建的任务是否只预览，默认 `true` |
| `confirm_execution` | 如果 `dry_run=false`，必须显式确认 |

本地脚本入口：

```text
python scripts/plan_rag_maintenance.py
python scripts/plan_rag_maintenance.py --limit 20 --coverage-limit 200
```

### `GET /v1/projects/{owner}/{repo}/rag`

返回单个项目的 RAG 聚合包，用于项目详情页、后续 Agent 工具调用和 LangChain/RAG 编排。该接口会读取项目详情、执行本地 RAG 检索，并合并该项目已经入库的解释历史，不调用外部模型、不请求 GitHub/Kimi/Telegram。

支持参数：

| 参数 | 说明 |
|---|---|
| `limit` | 证据块数量，默认 8，最大 30 |
| `explanation_limit` | 解释历史数量，默认 5，最大 50 |
| `mode` | 检索模式，默认 `fts5`；传 `vector` 时使用本地向量检索 |
| `model` | 向量模型名称，默认 `local-hash-v1` |
| `auto_build` | 向量检索时是否自动构建本地 embedding 索引 |

返回字段包含：

1. `project`：项目摘要，包含语言、方向、历史入选次数、新增 Star 和最好 Trending 排名。
2. `contexts`、`citations`、`prompt_context`：可直接交给后续问答链的证据与引用。
3. `explanations`：该项目已入库的 RAG 解释历史。
4. `explanation_summary`：该项目解释数量、平均质量分、质量等级分布和改进建议。

示例：

```text
/v1/projects/owner/agent/rag?limit=8&explanation_limit=5
/v1/projects/owner/agent/rag?mode=vector&auto_build=true
```

### `GET /v1/projects/{owner}/{repo}/similar`

基于单项目详情和 `project_corpus` 语料索引生成相似项目候选。该接口优先使用 SQLite FTS5 召回候选，再结合语言、方向、来源、关键词重合、Trending 排名和新增 Star 计算 `similarity_score`。

支持参数：

| 参数 | 说明 |
|---|---|
| `limit` | 返回相似候选数量，默认 10，最大 50 |

返回内容包括：

1. `source_project`：被查询项目的基础信息。
2. `similar_projects`：相似项目候选，包含 `similarity_score` 和 `similarity_reasons`。
3. `search_engine`：本次候选召回使用的检索引擎。
4. `selection_summary`：候选生成摘要。

示例：

```text
/v1/projects/owner/agent/similar?limit=10
```

该接口只读取本地公开归档数据，不调用外部模型或外部服务。它是后续 RAG、向量检索、项目对比和个性化推荐重排的前置候选层。

### `GET /v1/projects/compare`

对多个历史入选项目做结构化横向比较。该接口读取单项目详情聚合结果，返回统一对比矩阵和基础结论，用于后续对比页、RAG 解释和个性化推荐重排。

支持参数：

| 参数 | 说明 |
|---|---|
| `repos` | 必填，逗号分隔的仓库全名，例如 `owner/a,owner/b`，最多 8 个 |
| `profile` | 可选，当前个性化方向，例如 `agent_development`、`java`、`python` |
| `language` | 可选，当前优先语言，例如 `Python`、`Java` |
| `category` | 可选，当前优先方向，例如 `AI Agent`、`Backend` |
| `query` | 可选，当前关键词，例如 `agent`、`spring`、`rag` |

返回内容包括：

1. `projects`：每个项目的基础信息、历史热度、质量和风险摘要。
2. `matrix`：按指标展开的对比矩阵。
3. `best_by`：按累计新增 Star、最近新增 Star、质量分、Trending 排名等维度给出的领先项目。
4. `preference`：本次对比使用的个性化偏好上下文。
5. `recommendation`：规则版推荐结论，包含优先查看项目、推荐理由、注意事项、下一步动作和 `scoring_model`。没有偏好时为 `rule:v1`，传入 `profile`、`language`、`category` 或 `query` 后为 `rule:v2-preference`。
6. `missing`：未找到的项目。
7. `selection_summary`：本次对比摘要。

示例：

```text
/v1/projects/compare?repos=owner/agent,owner/agent-helper&profile=agent_development&language=Python
```

该接口只读公开归档数据，不调用外部服务，不写入任务或推送状态。

### `GET /api/profiles`

返回公开个性化方向，数据来源为 `docs/profiles.json`。

### `GET /api/weekly/latest`

返回最新 Markdown 周报正文、运行日期、周报页面路径和对应运行摘要。这个接口主要用于后续后台管理页、移动端入口或调试页面。

### `/v1` 订阅接口

订阅接口用于保存本地个性化偏好，后续精准推送和多用户订阅可以复用这个入口。当前订阅只保存筛选条件和通道名称，不保存 Token、Chat ID、Webhook 或请求头。

推送消息会使用这些订阅生成推荐入口：如果 SQLite 中存在启用订阅，Telegram、飞书和企业微信消息会追加最多 3 个 `recommendations.html` 个性化推荐链接。没有订阅时，消息仍只发送周报正文、项目筛选、运行状态和订阅配置页入口。

周报正文也会读取启用订阅生成“订阅推荐分区”。该分区只基于本期已经入选的项目做二次筛选，不改变采集、评分和入选逻辑。

当前支持：

1. `GET /v1/subscriptions`：查询订阅列表。
2. `POST /v1/subscriptions`：创建订阅。
3. `PATCH /v1/subscriptions/{subscription_id}`：更新订阅条件或启停状态。
4. `GET /v1/subscriptions/{subscription_id}/recommendations`：按订阅编号预览推荐结果。
5. `POST /v1/subscriptions/{subscription_id}/trigger`：把启用订阅转换成 planned 周报任务，默认 `dry_run=true`，不直接真实推送。

订阅字段包括：

| 字段 | 说明 |
|---|---|
| `name` | 订阅名称 |
| `status` | `enabled` 或 `disabled` |
| `profile` | 个性化方向 |
| `language` | 主要语言 |
| `category` | 项目方向 |
| `query` | 关键词 |
| `sort` | 推荐排序方式 |
| `limit` | 推荐数量 |
| `channels` | 推送通道名称，例如 `telegram`、`feishu`、`wecom` |

示例：

```text
POST /v1/subscriptions
```

```json
{
  "name": "Agent 开发订阅",
  "profile": "agent_development",
  "language": "Python",
  "channels": ["telegram"]
}
```

预览某个订阅的推荐结果：

```text
GET /v1/subscriptions/sub:xxxx/recommendations?limit=10
```

该接口会复用 `/v1/recommendations` 的筛选和排序逻辑，只把订阅保存的 profile、语言、方向、关键词和排序条件作为输入，不读取任何推送密钥。

按订阅生成计划任务：

```text
POST /v1/subscriptions/sub:xxxx/trigger
```

```json
{
  "dry_run": true,
  "requested_by": "subscriptions_page"
}
```

该接口只创建 planned 任务，不在 HTTP 请求里执行采集、生成或推送。订阅必须是 `enabled` 状态；如果传入 `dry_run=false`，仍需要 `confirm_delivery=true`，否则会自动降级为 `dry_run=true`。

### `/v1` 任务接口

`/v1` 是后端服务化入口，当前已经支持：

1. `GET /v1/jobs`：查询任务列表。
2. `GET /v1/job-execution-check?job_id=...`：检查 planned 任务是否可执行。
3. `GET /v1/jobs/{job_id}/events`：查询任务审计事件。
4. `POST /v1/runs/trigger`：创建 planned 周报任务，不直接执行。
5. `POST /v1/jobs/{job_id}/execute`：显式传入 `confirm_execution=true` 后，把检查通过的 planned 任务交给 job runner 执行。
6. `POST /v1/jobs/{job_id}/retry`：为 failed 任务创建新的 planned 重试任务。

执行接口仍然遵守任务请求中的 `dry_run` 和 `confirm_delivery`。如果任务允许真实推送，执行前需要确认 Telegram、飞书或微信等推送配置已经正确。

## 四、前端读取方式

当前 `docs/explorer.html` 已支持渐进式读取后端 API：

1. 在 `localhost`、`127.0.0.1` 或 `::1` 打开时，默认优先读取 `/api/projects` 和 `/api/profiles`。
2. 在任意环境中给 URL 增加 `api=1` 时，会尝试读取后端 API。
3. 给 URL 增加 `api=0` 时，会强制读取静态 `projects.json` 和 `profiles.json`。
4. API 不可用时会自动回退到静态 JSON，GitHub Pages 线上页面不受影响。

示例：

```text
explorer.html?api=1&profile=agent_development
explorer.html?api=0&profile=python
```

`docs/project.html` 使用同样的读取策略：

1. 默认通过 `project.html?repo=owner/name` 读取静态 `projects.json` 并在浏览器中聚合详情。
2. 在本地后端或 URL 带 `api=1` 时，优先读取 `/api/projects/{owner}/{repo}`。
3. API 模式下会额外调用 `/v1/projects/{owner}/{repo}/rag`，一次展示该项目相关的 RAG 证据块、引用、`prompt_context`、解释历史和解释质量摘要。
4. API 不可用时自动回退到静态 `projects.json`。

示例：

```text
project.html?repo=owner/agent
project.html?repo=owner/agent&api=1
```

`docs/recommendations.html` 是个性化推荐页：

1. 本地后端或 URL 带 `api=1` 时优先读取 `/v1/recommendations`。
2. GitHub Pages 静态模式下读取 `projects.json` 并在浏览器中完成基础筛选和排序。
3. 页面预留 Agent 开发、Python、Java、后端、前端、AI 工具等快捷方向，后续可以接入用户订阅数据库。

示例：

```text
recommendations.html?api=1&profile=agent_development
recommendations.html?api=0&language=Java&q=spring
```

`docs/subscriptions.html` 是订阅配置页：

1. 本地后端或 URL 带 `api=1` 时读取 `/v1/subscriptions`。
2. 支持创建订阅，并通过 `PATCH /v1/subscriptions/{subscription_id}` 启用或停用订阅。
3. 支持调用 `/v1/subscriptions/{subscription_id}/recommendations` 在当前页面预览该订阅命中的推荐项目。
4. 静态 GitHub Pages 模式只展示说明，不写入任何配置。

示例：

```text
subscriptions.html?api=1
subscriptions.html?api=1&profile=agent_development
```

## 五、后续扩展

下一阶段可以在这个 API 层继续扩展：

1. 项目详情页增强：继续补充跨周对比、更多趋势解释和项目收藏入口。
2. 订阅接口：保存用户选择的语言、方向、profile 和推送渠道。
3. 后台任务接口：触发采集、重建 SQLite、重新生成 Pages。
4. 数据库演进：从当前派生 SQLite 过渡到持久化服务数据库，但保留 JSON 归档作为可读审计源。
5. 前端演进：先让现有静态页面读取 API，再逐步迁移到更完整的前端工程。

