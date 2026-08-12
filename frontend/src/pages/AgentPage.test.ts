import { describe, expect, it } from "vitest";
import { answerStatus } from "../components/StatusBadge";
import { answerConfidenceSemantics, constraintRetryQuery, readinessPresentation, selectPrimaryRecommendation } from "../components/AgentWorkspace";
import { eligibilityLabel } from "../components/ProjectCard";
import { contextualAskBody } from "../lib/api";
import type { AssistantReadiness } from "../lib/types";
import { followUpContext, matchProjects } from "./AgentPage";

describe("项目匹配回答状态", () => {
  it("maps readiness to dependency-backed connection status", () => {
    const degraded: AssistantReadiness = {
      schema_version: 1,
      status: "degraded",
      summary: "Project evidence is available.",
      capabilities: { can_chat: true, knowledge_available: false, project_available: true, current_project_available: true },
      components: {},
      issues: [{ component: "model", code: "model_not_configured", message: "Model missing.", recovery: "Configure model." }],
    };
    expect(readinessPresentation(true, degraded).label).toBe("助手部分可用");
    expect(readinessPresentation(true, degraded).detail).toContain("Configure model");
    expect(readinessPresentation(true, null).label).toBe("本机 API 不可达");
    expect(readinessPresentation(false, null).label).toBe("需要本地 API");
  });

  it("给出用户可理解的降级和拒答状态", () => {
    expect(answerStatus("llm", true).label).toBe("证据已校验");
    expect(answerStatus("fallback_rule").label).toBe("已切换为证据约束结论");
    expect(answerStatus("refusal").label).toBe("当前归档没有足够证据");
    expect(answerStatus("llm", false).label).toBe("模型回答未通过质量校验");
  });

  it("把编辑后的硬约束和偏好转换为可重试查询", () => {
    const requirements = [
      { field: "language", operator: "eq", value: "Python", hard: true },
      { field: "hosting_mode", operator: "eq", value: "self_hosted", hard: false },
      { field: "language", operator: "not_eq", value: "Java", hard: false },
    ];
    expect(constraintRetryQuery(requirements)).toBe("使用这些条件重新搜索：必须满足语言=Python；偏好部署方式=本地部署；语言最好不是Java");
    expect(constraintRetryQuery(requirements, true)).toBe("使用这些条件重新搜索：偏好语言=Python；偏好部署方式=本地部署；语言最好不是Java");
    expect(constraintRetryQuery([])).toBe("重新搜索并给出当前最匹配的项目");
  });

  it("重试查询保留任一组和可选条件语义", () => {
    const requirements = [
      { field: "language", operator: "eq", value: "Python", hard: true, group_id: "g1", logic: "any_of", optional: false },
      { field: "language", operator: "eq", value: "TypeScript", hard: true, group_id: "g1", logic: "any_of", optional: false },
      { field: "hosting_mode", operator: "contains", value: "self_hosted", hard: false, group_id: "g2", logic: "all_of", optional: true },
    ] as const;
    expect(constraintRetryQuery(requirements as never)).toBe("使用这些条件重新搜索：必须满足语言=Python或语言=TypeScript；不要求部署方式=本地部署");
    expect(constraintRetryQuery(requirements as never, true)).toBe("使用这些条件重新搜索：偏好语言=Python或语言=TypeScript；不要求部署方式=本地部署");
  });

  it("只按后端 recommendations 组装候选，不让引用顺序决定首选", () => {
    const projects = matchProjects({
      recommendations: [
        { full_name: "org/second", rank: 1, match_score: 0.8, matched_requirements: ["语言=Python"], unmet_requirements: [], unknown_requirements: [], reasons: ["满足显式筛选"], citation_indexes: [2], evidence_chunk_ids: ["chunk:2"], eligibility: "eligible" },
        { full_name: "openai/example", rank: 2, match_score: 1, matched_requirements: [], unmet_requirements: ["语言=Python"], unknown_requirements: [], reasons: ["检索分更高但违反约束"], citation_indexes: [1], evidence_chunk_ids: ["chunk:1", "chunk:3"], eligibility: "rejected" },
      ],
      citations: [{ full_name: "openai/example" }, { full_name: "org/second" }],
      evidence: [{ full_name: "openai/example" }],
    } as never);
    expect(projects).toEqual([
      expect.objectContaining({ full_name: "org/second", evidenceCount: 1, eligibility: "eligible" }),
      expect.objectContaining({ full_name: "openai/example", evidenceCount: 2, eligibility: "rejected", unmet_requirements: ["语言=Python"] }),
    ]);
  });

  it("只有质量与新鲜度通过且存在当前 eligible 候选时确认首选", () => {
    const eligible = { full_name: "org/eligible", evidenceCount: 1, eligibility: "eligible", current_eligible: true } as never;
    const unknown = { full_name: "org/unknown", evidenceCount: 1, eligibility: "unknown" } as never;
    expect(selectPrimaryRecommendation({ answer_quality: { passed: true, data_freshness: "fresh" } } as never, [eligible])).toBe(eligible);
    expect(selectPrimaryRecommendation({ answer_quality: { passed: false } } as never, [eligible])).toBeUndefined();
    expect(selectPrimaryRecommendation({ freshness_required: true, answer_quality: { passed: true, data_freshness: "stale" } } as never, [eligible])).toBeUndefined();
    expect(selectPrimaryRecommendation({ freshness_required: false, answer_quality: { passed: true, data_freshness: "stale" } } as never, [eligible])).toBe(eligible);
    const historical = { full_name: "org/history", evidenceCount: 1, eligibility: "eligible", current_eligible: false } as never;
    const fourth = { full_name: "org/fourth", evidenceCount: 1, eligibility: "eligible", current_eligible: true } as never;
    expect(selectPrimaryRecommendation({ answer_quality: { passed: true } } as never, [unknown, historical, eligible, fourth])).toBe(eligible);
  });

  it("历史候选可展示但绝不成为当前首选", () => {
    const historical = { full_name: "org/history", evidenceCount: 1, eligibility: "eligible", current_eligible: false, source_kind: "local_archive_sqlite" } as never;
    expect(selectPrimaryRecommendation({ answer_quality: { passed: true, data_freshness: "stale" } } as never, [historical])).toBeUndefined();
  });

  it("区分无法验证与明确违反约束", () => {
    expect(eligibilityLabel("unknown")).toBe("约束尚无法验证");
    expect(eligibilityLabel("rejected")).toBe("违反显式约束");
  });

  it("为追问只提交最小用户意图上下文，不提交历史模型回答或证据", () => {
    const answer = {
      answer: "历史模型回答不得发送",
      answer_mode: "llm",
      answer_quality: { passed: true },
      resolved_query: "找适合 Python 团队的项目",
      retrieval: { mode: "hybrid" },
      citations: [{ chunk_id: "secret-citation" }],
      evidence: [{ quote: "secret-evidence" }],
      prompt_context: "secret-prompt-context",
      input_route: { requirements: [{ field: "language", operator: "eq", value: "Python", hard: true }] },
      recommendations: [
        { full_name: "org/history", eligibility: "eligible", current_eligible: false },
        { full_name: "org/repo", eligibility: "eligible", current_eligible: true },
        { full_name: "org/other", eligibility: "unknown" },
      ],
    } as never;
    const context = followUpContext(answer, "原始问题");
    const body = contextualAskBody("继续", context);
    expect(body.context).toEqual({
      previous_user_goal: "找适合 Python 团队的项目",
      candidate_repository_ids: ["org/history", "org/repo", "org/other"],
      primary_repository_id: "org/repo",
      requirements: [{ field: "language", operator: "eq", value: "Python", hard: true }],
      mode: "hybrid",
      resumable: true,
    });
    const serialized = JSON.stringify(body);
    expect(serialized).not.toContain("历史模型回答不得发送");
    expect(serialized).not.toContain("secret-citation");
    expect(serialized).not.toContain("secret-evidence");
    expect(serialized).not.toContain("secret-prompt-context");
  });

  it("澄清和无匹配轮不可继续，也不确认首选", () => {
    expect(answerStatus("clarification", false).label).toBe("需要补充需求");
    expect(answerStatus("no_match", false).label).toBe("硬约束下无匹配");
    const context = followUpContext({
      answer_mode: "clarification",
      recommendations: [{ full_name: "org/repo", eligibility: "eligible" }],
    } as never, "继续");
    expect(context?.resumable).toBe(false);
    expect(selectPrimaryRecommendation({ answer_mode: "clarification", answer_quality: { passed: true } } as never, [{ full_name: "org/repo", evidenceCount: 1, eligibility: "eligible" } as never])).toBeUndefined();
  });

  it("把兼容 confidence 显示为证据覆盖并标记匹配未校准", () => {
    const semantics = answerConfidenceSemantics({
      confidence: "high",
      evidence_coverage: "high",
      match_confidence: "unknown",
    });
    expect(semantics.coverageLabel).toBe("证据覆盖：高");
    expect(semantics.matchLabel).toBe("匹配把握：尚未校准");
    expect(Object.values(semantics).join(" ")).not.toContain("置信度");
  });
});
