import { beforeEach, describe, expect, it } from "vitest";
import { loadConversations, saveConversations } from "./conversations";

describe("conversation storage", () => {
  beforeEach(() => localStorage.clear());

  it("migrates valid legacy history once", () => {
    localStorage.setItem("github_weekly_agent_match_history", JSON.stringify([{ query: "找 Agent 项目", answer: "候选项目" }]));

    const conversations = loadConversations();

    expect(conversations).toHaveLength(1);
    expect(conversations[0].turns[0].question).toBe("找 Agent 项目");
    expect(localStorage.getItem("github_weekly_agent_match_conversations_v1")).not.toBeNull();
  });

  it("limits persisted conversations and turns", () => {
    const conversations = Array.from({ length: 12 }, (_, index) => ({
      id: String(index), title: String(index), updatedAt: new Date().toISOString(),
      turns: Array.from({ length: 25 }, (_, turn) => ({ id: `${index}-${turn}`, question: "q", createdAt: new Date().toISOString() })),
    }));

    saveConversations(conversations);
    const stored = JSON.parse(localStorage.getItem("github_weekly_agent_match_conversations_v1") || "[]");
    expect(stored).toHaveLength(10);
    expect(stored[0].turns).toHaveLength(20);
  });
});
