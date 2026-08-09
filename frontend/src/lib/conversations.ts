import type { AssistantState, Conversation, RagAnswer } from "./types";

export const STORAGE_KEY = "github_weekly_agent_assistant_conversations_v2";
export const HISTORY_ENABLED_KEY = "github_weekly_agent_assistant_history_enabled_v1";
export const LEGACY_KEYS = ["github_weekly_agent_match_conversations_v1", "github_weekly_agent_match_history"] as const;
export const HISTORY_TTL_MS = 30 * 24 * 60 * 60 * 1000;
export const MAX_CONVERSATIONS = 10;
export const MAX_TURNS = 20;

type StoredTurn = {
  id: string;
  question: string;
  answer: string;
  createdAt: string;
  assistantMode: string;
  repositoryIds: string[];
  assistantState?: AssistantState;
};

type StoredConversation = { id: string; title: string; updatedAt: string; turns: StoredTurn[] };

function bounded(value: unknown, length: number) {
  return typeof value === "string" ? value.trim().slice(0, length) : "";
}

function validDate(value: unknown, now: number) {
  if (typeof value !== "string") return "";
  const time = Date.parse(value);
  return Number.isFinite(time) && time <= now ? new Date(time).toISOString() : "";
}

function repositoryIds(value: unknown) {
  if (!Array.isArray(value)) return [];
  const result: string[] = [];
  for (const item of value) {
    const id = bounded(item, 200);
    if (/^[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+$/.test(id) && !result.includes(id)) result.push(id);
  }
  return result.slice(0, 10);
}

function assistantState(value: unknown): AssistantState | undefined {
  if (!value || typeof value !== "object" || Array.isArray(value)) return undefined;
  const state = value as Record<string, unknown>;
  const mode = state.mode === "fts5" || state.mode === "vector" ? state.mode : "hybrid";
  const source = state.source_identity && typeof state.source_identity === "object" && !Array.isArray(state.source_identity)
    ? state.source_identity as Record<string, unknown> : {};
  const constraints = Array.isArray(state.constraints) ? state.constraints.slice(0, 20).flatMap((item) => {
    if (!item || typeof item !== "object" || Array.isArray(item)) return [];
    const value = item as Record<string, unknown>;
    const constraintValue = typeof value.value === "string" || typeof value.value === "boolean"
      ? value.value : Array.isArray(value.value) ? value.value.filter((item): item is string => typeof item === "string").slice(0, 20).join(",") : "";
    return [{ field: bounded(value.field, 50), operator: bounded(value.operator, 20), value: constraintValue, hard: value.hard === true }];
  }) : [];
  const candidates = repositoryIds(state.candidate_repository_ids);
  const primary = bounded(state.primary_repository_id, 200);
  const goal = bounded(state.goal, 2000);
  const sourceIdentity = {
    kind: bounded(source.kind, 50), source_id: bounded(source.source_id, 200),
    run_date: bounded(source.run_date, 50), as_of: bounded(source.as_of, 50),
  };
  return {
    schema_version: 1,
    revision: Math.max(0, Math.min(Number.isInteger(state.revision) ? Number(state.revision) : 0, 1_000_000)),
    goal,
    constraints,
    candidate_repository_ids: candidates,
    primary_repository_id: candidates.includes(primary) ? primary : "",
    last_intent: bounded(state.last_intent, 50),
    pending_question: bounded(state.pending_question, 500),
    source_identity: sourceIdentity,
    mode,
    resumable: state.resumable === true && Boolean(goal && candidates.length && sourceIdentity.source_id && sourceIdentity.run_date),
  };
}

function projectTurn(turn: Conversation["turns"][number], now: number): StoredTurn | undefined {
  const question = bounded(turn.question, 4000);
  const createdAt = validDate(turn.createdAt, now);
  if (!question || !createdAt || now - Date.parse(createdAt) >= HISTORY_TTL_MS) return undefined;
  const response = turn.response;
  const ids = repositoryIds(response?.assistant_state?.candidate_repository_ids || response?.recommendations?.map((item) => item.full_name));
  return {
    id: bounded(turn.id, 100) || crypto.randomUUID(),
    question,
    answer: bounded(response?.answer, 20_000),
    createdAt,
    assistantMode: bounded(response?.assistant_mode, 50),
    repositoryIds: ids,
    ...(response?.assistant_state ? { assistantState: assistantState(response.assistant_state) } : {}),
  };
}

function hydrateTurn(turn: StoredTurn): Conversation["turns"][number] {
  const response: RagAnswer | undefined = turn.answer || turn.assistantState ? {
    query: turn.question,
    answer: turn.answer,
    answer_mode: "history_display",
    fallback_reason: "",
    citations: [], evidence: [], recommendations: [],
    answer_quality: { applicable: false },
    assistant_mode: turn.assistantMode,
    assistant_state: turn.assistantState,
  } : undefined;
  return { id: turn.id, question: turn.question, createdAt: turn.createdAt, ...(response ? { response } : {}) };
}

function normalizeConversation(value: unknown, now: number): StoredConversation | undefined {
  if (!value || typeof value !== "object" || Array.isArray(value)) return undefined;
  const item = value as Record<string, unknown>;
  const updatedAt = validDate(item.updatedAt, now);
  if (!updatedAt || now - Date.parse(updatedAt) >= HISTORY_TTL_MS) return undefined;
  const turns = Array.isArray(item.turns)
    ? item.turns.flatMap((turn) => {
      if (!turn || typeof turn !== "object" || Array.isArray(turn)) return [];
      const value = turn as Record<string, unknown>;
      const stored: StoredTurn = {
        id: bounded(value.id, 100) || crypto.randomUUID(),
        question: bounded(value.question, 4000),
        answer: bounded(value.answer, 20_000),
        createdAt: validDate(value.createdAt, now),
        assistantMode: bounded(value.assistantMode, 50),
        repositoryIds: repositoryIds(value.repositoryIds),
        ...(value.assistantState ? { assistantState: assistantState(value.assistantState) } : {}),
      };
      return stored.question && stored.createdAt && now - Date.parse(stored.createdAt) < HISTORY_TTL_MS ? [stored] : [];
    }).slice(-MAX_TURNS) : [];
  return {
    id: bounded(item.id, 100) || crypto.randomUUID(),
    title: bounded(item.title, 100) || "新对话",
    updatedAt,
    turns,
  };
}

function prune(conversations: StoredConversation[], now: number) {
  return conversations
    .flatMap((item) => normalizeConversation(item, now) || [])
    .sort((left, right) => Date.parse(right.updatedAt) - Date.parse(left.updatedAt))
    .slice(0, MAX_CONVERSATIONS);
}

function remove(key: string) { try { localStorage.removeItem(key); } catch { /* Browser storage is optional. */ } }

export function clearConversationHistory() {
  remove(STORAGE_KEY);
  for (const key of LEGACY_KEYS) remove(key);
}

export function isHistoryEnabled() {
  try { return localStorage.getItem(HISTORY_ENABLED_KEY) === "true"; } catch { return false; }
}

export function setHistoryEnabled(enabled: boolean) {
  try {
    if (enabled) localStorage.setItem(HISTORY_ENABLED_KEY, "true");
    else localStorage.removeItem(HISTORY_ENABLED_KEY);
  } catch { /* Keep the feature disabled when storage is unavailable. */ }
  if (!enabled) clearConversationHistory();
}

function createConversation(now = Date.now()): Conversation {
  return { id: crypto.randomUUID(), title: "新对话", updatedAt: new Date(now).toISOString(), turns: [] };
}

export function loadConversations(now = Date.now()): Conversation[] {
  for (const key of LEGACY_KEYS) remove(key);
  if (!isHistoryEnabled()) {
    remove(STORAGE_KEY);
    return [createConversation(now)];
  }
  try {
    const parsed = JSON.parse(localStorage.getItem(STORAGE_KEY) || "null") as Record<string, unknown> | null;
    const stored = parsed?.schema_version === 2 && Array.isArray(parsed.conversations) ? parsed.conversations : [];
    const normalized = prune(stored.flatMap((item) => normalizeConversation(item, now) || []), now);
    if (!normalized.length) {
      remove(STORAGE_KEY);
      return [createConversation(now)];
    }
    localStorage.setItem(STORAGE_KEY, JSON.stringify({ schema_version: 2, conversations: normalized }));
    return normalized.map((conversation) => ({ ...conversation, turns: conversation.turns.map(hydrateTurn) }));
  } catch {
    remove(STORAGE_KEY);
    return [createConversation(now)];
  }
}

export function saveConversations(conversations: Conversation[], enabled = isHistoryEnabled(), now = Date.now()) {
  if (!enabled) { remove(STORAGE_KEY); return; }
  try {
    const projected = conversations.map((conversation) => ({
      id: bounded(conversation.id, 100),
      title: bounded(conversation.title, 100),
      updatedAt: conversation.updatedAt,
      turns: conversation.turns.flatMap((turn) => projectTurn(turn, now) || []).slice(-MAX_TURNS),
    }));
    const normalized = prune(projected, now).filter((conversation) => conversation.turns.length > 0);
    if (!normalized.length) { remove(STORAGE_KEY); return; }
    localStorage.setItem(STORAGE_KEY, JSON.stringify({ schema_version: 2, conversations: normalized }));
  } catch { /* Keep the in-memory conversation when storage is unavailable. */ }
}

export function newConversation() { return createConversation(); }
