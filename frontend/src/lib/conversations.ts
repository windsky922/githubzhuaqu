import type { Conversation, RagAnswer } from "./types";

const STORAGE_KEY = "github_weekly_agent_match_conversations_v1";
const LEGACY_KEY = "github_weekly_agent_match_history";

function createConversation(): Conversation {
  return { id: crypto.randomUUID(), title: "新项目匹配", updatedAt: new Date().toISOString(), turns: [] };
}

export function loadConversations(): Conversation[] {
  try {
    const stored = JSON.parse(localStorage.getItem(STORAGE_KEY) || "null");
    if (Array.isArray(stored) && stored.length) return stored.slice(0, 10);
    const legacy = JSON.parse(localStorage.getItem(LEGACY_KEY) || "null");
    if (Array.isArray(legacy) && legacy.length) {
      const conversation = createConversation();
      conversation.title = "历史项目匹配";
      conversation.turns = legacy.slice(-20).map((item: Record<string, unknown>) => ({
        id: crypto.randomUUID(),
        question: String(item.query || item.question || "历史问题"),
        createdAt: String(item.created_at || item.createdAt || conversation.updatedAt),
        response: item.response || item.answer ? (item.response || item) as RagAnswer : undefined,
      }));
      saveConversations([conversation]);
      return [conversation];
    }
  } catch { /* Ignore corrupted browser-only history. */ }
  return [createConversation()];
}

export function saveConversations(conversations: Conversation[]) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(conversations.slice(0, 10).map((conversation) => ({ ...conversation, turns: conversation.turns.slice(-20) }))));
}

export function newConversation() {
  return createConversation();
}
