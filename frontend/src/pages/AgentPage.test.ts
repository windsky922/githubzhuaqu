import { describe, expect, it } from "vitest";
import { answerStatus } from "../components/StatusBadge";
import { answerConfidenceSemantics, selectPrimaryRecommendation } from "../components/AgentWorkspace";
import { eligibilityLabel } from "../components/ProjectCard";
import { matchProjects } from "./AgentPage";

describe("项目匹配回答状态", () => {
  it("给出用户可理解的降级和拒答状态", () => {
    expect(answerStatus("llm", true).label).toBe("证据已校验");
    expect(answerStatus("fallback_rule").label).toBe("已切换为证据约束结论");
    expect(answerStatus("refusal").label).toBe("当前归档没有足够证据");
    expect(answerStatus("llm", false).label).toBe("模型回答未通过质量校验");
  });

  it("只按后端 recommendations 组装候选，不让引用顺序决定首选", () => {
    const projects = matchProjects({
      recommendations: [
        { full_name: "org/second", rank: 1, match_score: 0.8, matched_requirements: ["语言=Python"], unmet_requirements: [], reasons: ["满足显式筛选"], citation_indexes: [2], evidence_chunk_ids: ["chunk:2"], eligibility: "eligible" },
        { full_name: "openai/example", rank: 2, match_score: 1, matched_requirements: [], unmet_requirements: ["语言=Python"], reasons: ["检索分更高但违反约束"], citation_indexes: [1], evidence_chunk_ids: ["chunk:1", "chunk:3"], eligibility: "rejected" },
      ],
      citations: [{ full_name: "openai/example" }, { full_name: "org/second" }],
      evidence: [{ full_name: "openai/example" }],
    } as never);
    expect(projects).toEqual([
      expect.objectContaining({ full_name: "org/second", evidenceCount: 1, eligibility: "eligible" }),
      expect.objectContaining({ full_name: "openai/example", evidenceCount: 2, eligibility: "rejected", unmet_requirements: ["语言=Python"] }),
    ]);
  });

  it("只有质量通过且第一项 eligible 时确认首选", () => {
    const eligible = { full_name: "org/eligible", evidenceCount: 1, eligibility: "eligible" } as never;
    const unknown = { full_name: "org/unknown", evidenceCount: 1, eligibility: "unknown" } as never;
    expect(selectPrimaryRecommendation({ answer_quality: { passed: true } } as never, [eligible])).toBe(eligible);
    expect(selectPrimaryRecommendation({ answer_quality: { passed: false } } as never, [eligible])).toBeUndefined();
    expect(selectPrimaryRecommendation({ answer_quality: { passed: true } } as never, [unknown, eligible])).toBeUndefined();
  });

  it("区分无法验证与明确违反约束", () => {
    expect(eligibilityLabel("unknown")).toBe("约束尚无法验证");
    expect(eligibilityLabel("rejected")).toBe("违反显式约束");
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
