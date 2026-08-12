# Private blind RAG 与 Top-1 人工验收准备

## 1. 目标与边界

这套流程验证未见需求下的项目检索与首选质量。它与仓库内固定 fixture、push/PR CI 完全分开：private pack、冻结 snapshot、baseline、人审清单、policy 和最终验收报告都必须位于仓库外，也不得上传为公开 CI artifact。

仓库只提供 runner、验收检查器和合成测试。缺少真实 fresh/stale pack、独立人审或冻结 policy 时，P1-D 仍是 `not_verified`；固定 fixture 或合成测试全绿不能替代真实 blind 证据。

## 2. 冻结输入

每个 cohort 使用独立的 schema-v2 JSONL pack 和独立 weekly snapshot：

- `fresh` pack 的 `source-freshness` 样本必须标注 `data_freshness=fresh`。
- `stale` pack 的 `source-freshness` 样本必须标注 `data_freshness=stale`。
- 每个 pack 至少 20 条，统一 `evaluation_date`，`id` 和规范化查询唯一。
- `request` 只允许 `q` 与可选 `context`。`mode=hybrid`、`model=local-hash-v1`、`limit=3`、`auto_build=true` 由 runner 固定，pack 不能覆盖。
- pack 必须覆盖既有固定类别；Recall@3、候选资格和 answer-quality 标签各自至少覆盖 25% 样本。

运行前还要冻结一个仓库外 policy JSON：

```json
{
  "schema_version": 1,
  "kind": "blind_rag_acceptance_policy",
  "policy_id": "p1-d-private-v1",
  "status": "frozen",
  "frozen_at": "2026-08-12T08:00:00+08:00",
  "thresholds": {
    "minimum_candidate_recall": 0.9,
    "minimum_data_freshness_accuracy": 0.9,
    "minimum_top_1_acceptance": 0.8,
    "minimum_top_1_coverage": 0.5,
    "minimum_route_accuracy": 0.9,
    "minimum_answer_quality": 0.9,
    "maximum_hard_constraint_violation": 0.0
  }
}
```

上面的数值只是格式示例，不是项目已批准的真实门槛。实际 policy 必须由验收责任人在查看模型结果和人审结论前冻结；检查器会拒绝晚于人审冻结时间的 policy。

## 3. 分别运行 fresh 与 stale baseline

```powershell
python scripts\evaluate_blind_rag.py `
  --cohort fresh `
  --blind-pack C:\private-blind\fresh.jsonl `
  --snapshot-root C:\private-blind\fresh-snapshot `
  --policy C:\private-blind\policy.json `
  --output C:\private-blind\fresh-baseline.json `
  --judgment-template C:\private-blind\fresh-judgments.json

python scripts\evaluate_blind_rag.py `
  --cohort stale `
  --blind-pack C:\private-blind\stale.jsonl `
  --snapshot-root C:\private-blind\stale-snapshot `
  --policy C:\private-blind\policy.json `
  --output C:\private-blind\stale-baseline.json `
  --judgment-template C:\private-blind\stale-judgments.json
```

runner 会：

- 对 pack、snapshot 事实 JSON、冻结 policy 和执行源码清单生成 SHA-256；执行前后复核外部输入未变。baseline 记录真实开始时间，且 policy 必须已先冻结。
- 在临时 SQLite 上运行 contextual normal 与 SSE 主链。
- 清空外部凭证，并阻断 runner 进程内受控 Python socket/DNS 连接路径；这些路径的联网尝试固定失败为 `blind_network_disabled`。这不是 OS 级物理断网，也不覆盖任意子进程或原生库。
- 报告 schema-v4 cohort、聚合指标、精确 numerator/denominator、Top-1 coverage 和人审 subject commitment，不输出题目、标签、回答、仓库级失败或路径。
- 用独占创建写 baseline 和可选人审模板，不覆盖已有文件。

## 4. 独立人工 Top-1 判断

`--judgment-template` 是仓库外私有工作文件。独立审查者使用 `case_id` 关联 private pack，在冻结 snapshot 中检查当前首选及其证据，然后：

- 有首选时把 `judgment` 改为 `accept` 或 `reject`。
- 无首选时只能填写 `not_applicable`。
- 不允许 `pending`、`abstain`、缺项、重复 case 或额外 case。
- 完成后设置 `status=frozen`、`reviewer_count>=1`、带时区的 `frozen_at`，并填写审查者集合的 SHA-256 commitment；不在报告中公开审查者身份。

机器只能验证清单完整、hash 绑定和声明的流程字段，不能证明审查者事实上独立，也不能证明五份外部 JSON 不是同一操作者自行构造。独立角色、预提交和盲评执行仍需仓库外治理证据。

## 5. 汇总自检

```powershell
python scripts\check_blind_rag_acceptance.py `
  --fresh-baseline C:\private-blind\fresh-baseline.json `
  --stale-baseline C:\private-blind\stale-baseline.json `
  --fresh-judgments C:\private-blind\fresh-judgments.json `
  --stale-judgments C:\private-blind\stale-judgments.json `
  --policy C:\private-blind\policy.json `
  --output C:\private-blind\policy-check.json
```

检查器要求 fresh/stale pack 与 snapshot hash 分别不同、runner hash 相同，并验证每个人审 subject 与实际 Top-1 commitment 一致；各指标必须有与 case 数一致或不超过 case 数的精确 numerator/denominator，freshness 也是冻结 policy 的硬门禁。最终单独报告 Candidate Recall、Top-1 Acceptance、Top-1 coverage、hard violation、route accuracy、answer-quality 和 freshness accuracy。

当前检查器输出固定为 `accepted=false`、`verification_level=self_attested` 和 `independent_evidence_verified=false`。`policy_passed=true` 只表示这些自声明外部文件在结构上自洽且达到冻结门槛；在外部持有人/审查者的预提交或签名证明未另行核验前，不得改写为“独立 blind 已验收”。

退出语义：

- `0`：自声明证据结构完整，且指标达到冻结 policy；仍不代表独立验收。
- `1`：证据完整，但至少一项指标未达到冻结 policy。
- `2`：输入无效、证据缺失、零分母、人审未完成、hash 不一致或输出不可安全创建。

任何退出码都不能单独写成 blind 已验收；退出 `0` 仅表示 `policy_passed=true`，且只适用于报告中绑定的 pack、snapshot、runner 和 policy，不外推到其他数据或真实 Kimi 对话质量。
