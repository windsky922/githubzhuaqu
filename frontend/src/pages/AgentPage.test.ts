import { describe, expect, it } from "vitest";
import { answerStatus } from "../components/StatusBadge";
import { answerConfidenceSemantics } from "../components/AgentWorkspace";
import { matchProjects } from "./AgentPage";

describe("项目匹配回答状态", () => {
  it("给出用户可理解的降级和拒答状态", () => {
    expect(answerStatus("llm", true).label).toBe("证据已校验");
    expect(answerStatus("fallback_rule").label).toBe("已切换为证据约束结论");
    expect(answerStatus("refusal").label).toBe("当前归档没有足够证据");
    expect(answerStatus("llm", false).label).toBe("模型回答未通过质量校验");
  });

  it("按引用去重候选并统计本轮证据", () => {
    const projects = matchProjects({
      citations: [{ full_name: "openai/example", html_url: "https://github.com/openai/example" }, { full_name: "openai/example" }, { full_name: "org/second" }],
      evidence: [{ full_name: "openai/example" }, { full_name: "openai/example" }, { full_name: "org/second" }],
    } as never);
    expect(projects).toEqual([
      expect.objectContaining({ full_name: "openai/example", evidenceCount: 2 }),
      expect.objectContaining({ full_name: "org/second", evidenceCount: 1 }),
    ]);
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
