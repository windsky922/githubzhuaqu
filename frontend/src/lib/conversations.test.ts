import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  HISTORY_TTL_MS, LEGACY_KEYS, MAX_CONVERSATIONS, MAX_TURNS, STORAGE_KEY,
  clearConversationHistory, isHistoryEnabled, loadConversations, saveConversations, setHistoryEnabled,
} from "./conversations";
import type { AssistantState, Conversation, RagAnswer } from "./types";

const now = Date.parse("2026-08-09T12:00:00.000Z");

function state(): AssistantState {
  return {
    schema_version: 1, revision: 2, goal: "学习 Agent", constraints: [],
    knowledge_context: { topic: "Agent 核心组成", outline: [{ id: "k1", title: "模型" }, { id: "k2", title: "工具" }], focus_id: "k2" },
    candidate_repository_ids: ["owner/agent"], primary_repository_id: "owner/agent",
    last_intent: "knowledge", pending_question: "",
    source_identity: { kind: "weekly_snapshot", source_id: "source:1", run_date: "2026-08-09", as_of: "2026-08-09" },
    mode: "hybrid", resumable: true,
  };
}

function answer(): RagAnswer {
  return {
    query: "q", answer: "允许保存的展示回答", answer_mode: "llm", fallback_reason: "",
    citations: [{ index: 1, full_name: "secret/citation", chunk_id: "secret-chunk", html_url: "" }],
    evidence: [{ chunk_id: "secret-evidence" } as never], recommendations: [],
    prompt_context: "secret-prompt", answer_quality: { passed: true }, assistant_mode: "knowledge",
    assistant_state: state(), contexts: [{ note: "secret-context" }], internal_payload: "secret-provider",
  };
}

function conversation(index = 0, updatedAt = new Date(now - index * 1000).toISOString()): Conversation {
  return {
    id: `conversation-${index}`, title: `对话 ${index}`, updatedAt,
    turns: [{ id: `turn-${index}`, question: `问题 ${index}`, createdAt: updatedAt, response: answer() }],
  };
}

describe("assistant conversation storage", () => {
  beforeEach(() => { localStorage.clear(); vi.restoreAllMocks(); });

  it("is disabled by default and writes no conversation data", () => {
    expect(isHistoryEnabled()).toBe(false);
    saveConversations([conversation()], undefined, now);
    expect(localStorage.getItem(STORAGE_KEY)).toBeNull();
  });

  it("stores only the approved display projection", () => {
    setHistoryEnabled(true);
    saveConversations([conversation()], true, now);
    const raw = localStorage.getItem(STORAGE_KEY) || "";
    expect(raw).toContain("允许保存的展示回答");
    expect(raw).toContain("owner/agent");
    expect(raw).toContain("Agent 核心组成");
    expect(raw).toContain('"schema_version":2');
    for (const forbidden of ["secret/citation", "secret-evidence", "secret-prompt", "secret-context", "secret-provider", "citations", "evidence", "prompt_context", "contexts", "internal_payload"])
      expect(raw).not.toContain(forbidden);
  });

  it("keeps records before 30 days and removes exact-expiry and future records", () => {
    setHistoryEnabled(true);
    const valid = conversation(1, new Date(now - HISTORY_TTL_MS + 1).toISOString());
    const expired = conversation(2, new Date(now - HISTORY_TTL_MS).toISOString());
    const future = conversation(3, new Date(now + 1).toISOString());
    saveConversations([expired, future, valid], true, now);
    const loaded = loadConversations(now);
    expect(loaded.map((item) => item.id)).toEqual([valid.id]);
  });

  it("removes expired turns inside a current conversation and ages out stored data", () => {
    setHistoryEnabled(true);
    const current = conversation(1, new Date(now).toISOString());
    current.turns = [
      { id: "expired", question: "过期轮次", createdAt: new Date(now - HISTORY_TTL_MS).toISOString() },
      { id: "valid", question: "有效轮次", createdAt: new Date(now - HISTORY_TTL_MS + 1).toISOString() },
    ];
    saveConversations([current], true, now);
    expect(loadConversations(now)[0].turns.map((turn) => turn.id)).toEqual(["valid"]);
    expect(loadConversations(now + HISTORY_TTL_MS)).toHaveLength(1);
    expect(loadConversations(now + HISTORY_TTL_MS)[0].turns).toHaveLength(0);
    expect(localStorage.getItem(STORAGE_KEY)).toBeNull();
  });

  it("keeps the newest 10 conversations and newest 20 turns", () => {
    setHistoryEnabled(true);
    const items = Array.from({ length: 12 }, (_, index) => conversation(index)).reverse();
    items[0].turns = Array.from({ length: 25 }, (_, index) => ({
      id: `many-${index}`, question: `轮次 ${index}`, createdAt: new Date(now - 5000 + index).toISOString(),
    }));
    saveConversations(items, true, now);
    const stored = JSON.parse(localStorage.getItem(STORAGE_KEY) || "{}").conversations;
    expect(stored).toHaveLength(MAX_CONVERSATIONS);
    expect(stored.map((item: { id: string }) => item.id)).toEqual(Array.from({ length: 10 }, (_, index) => `conversation-${index}`));
    const many = stored.find((item: { id: string }) => item.id === "conversation-11");
    expect(many).toBeUndefined();
    const projected = { ...conversation(0), turns: items[0].turns };
    saveConversations([projected], true, now);
    const turns = JSON.parse(localStorage.getItem(STORAGE_KEY) || "{}").conversations[0].turns;
    expect(turns).toHaveLength(MAX_TURNS);
    expect(turns[0].question).toBe("轮次 5");
    expect(turns[19].question).toBe("轮次 24");
  });

  it("clears old full-answer keys and never revives them", () => {
    for (const key of LEGACY_KEYS) localStorage.setItem(key, JSON.stringify([{ query: "旧问题", response: answer() }]));
    loadConversations(now);
    for (const key of LEGACY_KEYS) expect(localStorage.getItem(key)).toBeNull();
    expect(localStorage.getItem(STORAGE_KEY)).toBeNull();
  });

  it("supports clear and disabling without touching compare selection", () => {
    localStorage.setItem("github_weekly_project_compare_v1", '["owner/repo"]');
    setHistoryEnabled(true); saveConversations([conversation()], true, now);
    clearConversationHistory();
    expect(localStorage.getItem(STORAGE_KEY)).toBeNull();
    expect(localStorage.getItem("github_weekly_project_compare_v1")).toBe('["owner/repo"]');
    saveConversations([conversation()], true, now);
    setHistoryEnabled(false);
    expect(isHistoryEnabled()).toBe(false);
    expect(localStorage.getItem(STORAGE_KEY)).toBeNull();
  });

  it("persists single-conversation deletion", () => {
    setHistoryEnabled(true);
    const first = conversation(0); const second = conversation(1);
    saveConversations([first, second], true, now);
    saveConversations([second], true, now);
    expect(loadConversations(now).map((item) => item.id)).toEqual([second.id]);
  });

  it("fails safely for corrupted or unavailable storage", () => {
    setHistoryEnabled(true); localStorage.setItem(STORAGE_KEY, "not-json");
    expect(loadConversations(now)).toHaveLength(1);
    vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => { throw new DOMException("quota"); });
    expect(() => saveConversations([conversation()], true, now)).not.toThrow();
  });
});
