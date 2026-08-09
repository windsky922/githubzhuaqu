import { useEffect, useMemo, useRef, useState } from "react";
import { answerFromEvent, shouldUseApi, streamAssistantTurn } from "../lib/api";
import {
  clearConversationHistory, isHistoryEnabled, loadConversations, newConversation,
  saveConversations, setHistoryEnabled as persistHistoryEnabled,
} from "../lib/conversations";
import type { AskIntentContext, AssistantState, Conversation, RagAnswer } from "../lib/types";
import { AgentTopbar, AnswerSummary, ChatComposer, ConversationSidebar, type Candidate, ScrollToLatestButton, StreamDraft } from "../components/AgentWorkspace";

const examples = [
  "我想学习 AI Agent 开发方向的知识。",
  "推荐适合入门和实践的 AI Agent 项目",
  "重新搜索适合 Python 的项目",
];

export function matchProjects(answer?: RagAnswer): Candidate[] {
  return (answer?.recommendations || []).map((recommendation) => ({
    full_name: recommendation.full_name,
    html_url: `https://github.com/${recommendation.full_name}`,
    rag_reason: recommendation.reasons?.[0] || "基于本轮可审计排序进入候选。",
    evidenceCount: recommendation.evidence_chunk_ids?.length || 0,
    match_score: recommendation.match_score,
    matched_requirements: recommendation.matched_requirements,
    unmet_requirements: recommendation.unmet_requirements,
    unknown_requirements: recommendation.unknown_requirements,
    preferences: recommendation.preferences,
    eligibility: recommendation.eligibility,
    recommendation_rank: recommendation.rank,
    source_kind: recommendation.source_kind,
    source_date: recommendation.source_date,
    current_eligible: recommendation.current_eligible,
    source_notice: recommendation.source_notice,
  }));
}

export function followUpContext(answer: RagAnswer | undefined, previousQuestion: string): AskIntentContext | undefined {
  if (!answer) return undefined;
  const candidateIds = (answer.recommendations || []).map((item) => item.full_name).filter(Boolean).slice(0, 10);
  const primary = (answer.recommendations || []).find((item) => item.eligibility === "eligible" && item.current_eligible === true);
  const mode = answer.retrieval?.mode;
  const normalizedMode: AskIntentContext["mode"] = mode === "fts5" || mode === "vector" ? mode : "hybrid";
  const resumable = Boolean(candidateIds.length && !["clarification", "no_match", "refusal"].includes(answer.answer_mode));
  return {
    previous_user_goal: answer.resolved_query || previousQuestion,
    candidate_repository_ids: candidateIds,
    ...(answer.answer_quality?.passed === true && primary && (!answer.freshness_required || answer.freshness?.data_freshness === "fresh")
      ? { primary_repository_id: primary.full_name } : {}),
    mode: normalizedMode,
    resumable,
  };
}

export function assistantStateFromAnswer(answer?: RagAnswer): AssistantState | undefined {
  return answer?.assistant_state;
}

function history(conversations: Conversation[]) {
  return conversations.reduce<Record<string, Conversation[]>>((groups, conversation) => {
    const key = new Intl.DateTimeFormat("zh-CN", { month: "short", day: "numeric" }).format(new Date(conversation.updatedAt));
    (groups[key] ||= []).push(conversation);
    return groups;
  }, {});
}

export function AgentPage() {
  const [historyEnabled, setHistoryEnabled] = useState(isHistoryEnabled);
  const [conversations, setConversations] = useState<Conversation[]>(loadConversations);
  const [activeId, setActiveId] = useState(() => conversations[0]?.id || "");
  const [question, setQuestion] = useState("");
  const [draft, setDraft] = useState("");
  const [status, setStatus] = useState("输入问题，助手会区分通用教学与项目证据。");
  const [stage, setStage] = useState("正在准备回答");
  const [busy, setBusy] = useState(false);
  const [showLatest, setShowLatest] = useState(false);
  const controllerRef = useRef<AbortController | null>(null);
  const messagesRef = useRef<HTMLDivElement | null>(null);
  const messageEndRef = useRef<HTMLDivElement | null>(null);
  const apiEnabled = shouldUseApi();
  const active = conversations.find((item) => item.id === activeId) || conversations[0];
  const historyGroups = useMemo(() => history(conversations), [conversations]);

  useEffect(() => { saveConversations(conversations, historyEnabled); }, [conversations, historyEnabled]);
  useEffect(() => { if (busy && !showLatest) messageEndRef.current?.scrollIntoView({ behavior: "smooth", block: "end" }); }, [busy, draft, showLatest]);
  useEffect(() => {
    const node = messagesRef.current;
    if (!node) return;
    const handleScroll = () => setShowLatest(node.scrollHeight - node.scrollTop - node.clientHeight > 96);
    node.addEventListener("scroll", handleScroll);
    return () => node.removeEventListener("scroll", handleScroll);
  }, []);

  function createNewConversation() {
    const conversation = newConversation();
    setConversations((items) => [conversation, ...items].slice(0, 10));
    setActiveId(conversation.id); setQuestion(""); setDraft(""); setStatus("新对话已创建。");
  }
  function selectConversation(id: string) { setActiveId(id); setDraft(""); setShowLatest(false); }
  function deleteActiveConversation() {
    if (!active) return;
    const remaining = conversations.filter((item) => item.id !== active.id);
    const next = remaining.length ? remaining : [newConversation()];
    setConversations(next); setActiveId(next[0].id); setStatus("当前对话已删除。");
  }
  function clearAllConversations() {
    clearConversationHistory();
    const next = newConversation();
    setConversations([next]); setActiveId(next.id); setStatus("本机对话已全部清空。");
  }
  function toggleHistory(enabled: boolean) {
    persistHistoryEnabled(enabled); setHistoryEnabled(enabled);
    setStatus(enabled ? "本机历史已开启：最多保存 30 天、10 个会话、每会话 20 轮。" : "本机历史已关闭并删除。当前页面内容仅保留到刷新前。");
  }
  function scrollToLatest() { messageEndRef.current?.scrollIntoView({ behavior: "smooth", block: "end" }); setShowLatest(false); }

  async function submit(rawQuestion?: string, stateOverride?: AssistantState) {
    const nextQuestion = (rawQuestion || question).trim();
    if (!nextQuestion || busy || !active || !apiEnabled) return;
    const previousTurn = [...active.turns].reverse().find((turn) => turn.response?.assistant_state);
    const state = stateOverride ?? assistantStateFromAnswer(previousTurn?.response);
    const turnId = crypto.randomUUID(); const now = new Date().toISOString();
    setQuestion(""); setDraft(""); setBusy(true); setStage("正在识别意图并检索必要证据"); setStatus("助手处理中…");
    setConversations((items) => items.map((conversation) => conversation.id === active.id ? {
      ...conversation, title: conversation.turns.length ? conversation.title : nextQuestion.slice(0, 22), updatedAt: now,
      turns: [...conversation.turns, { id: turnId, question: nextQuestion, createdAt: now }].slice(-20),
    } : conversation));
    const controller = new AbortController(); controllerRef.current = controller;
    try {
      await streamAssistantTurn(nextQuestion, state, controller.signal, (event) => {
        if (event.event === "meta") { setStage("意图已识别，正在生成回答"); setStatus(`模式：${String(event.data.assistant_mode || "处理中")}`); }
        if (event.event === "delta") { setDraft((value) => value + String(event.data.text || "")); setStage("正在分段展示通用知识"); }
        if (event.event === "final") {
          const response = answerFromEvent(event.data);
          setConversations((items) => items.map((conversation) => conversation.id === active.id ? {
            ...conversation, updatedAt: new Date().toISOString(),
            turns: conversation.turns.map((turn) => turn.id === turnId ? { ...turn, response } : turn),
          } : conversation));
          setDraft(""); setStage("已生成正式结果");
          setStatus(`模式：${response.assistant_mode || "未知"} · 知识来源：${response.knowledge_basis || "未知"}`);
        }
        if (event.event === "error") { setStage("连接异常"); setStatus(String(event.data.message || "流式连接中断。")); }
      });
    } catch {
      if (!controller.signal.aborted) { setStage("请求失败"); setStatus("请求失败，请重试。"); }
    } finally { setBusy(false); controllerRef.current = null; }
  }

  const workspaceProps = {
    apiEnabled, conversations, activeId: active?.id, historyGroups, historyEnabled,
    onCreate: createNewConversation, onSelect: selectConversation, onHistoryChange: toggleHistory,
    onDelete: deleteActiveConversation, onClear: clearAllConversations,
  };
  return <main className="agent-page-shell"><section className="agent-page">
    <ConversationSidebar {...workspaceProps} />
    <section className="agent-workspace"><AgentTopbar {...workspaceProps} />
      <div className="messages" ref={messagesRef}><div className="message-stack">
        {!active?.turns.length ? <div className="welcome"><span className="agent-eyebrow">AI Agent 学习与项目研究导师</span><h1>你想学习什么，或研究哪个项目？</h1><p>通用知识由模型讲解；具体 GitHub 事实只使用本机归档证据。</p><div className="suggestions">{examples.map((example) => <button className="suggestion" type="button" key={example} disabled={!apiEnabled} onClick={() => void submit(example)}>{example}</button>)}</div></div> : null}
        {active?.turns.map((turn) => <div className="turn" key={turn.id}><span className="message-label">你的问题</span><div className="user-message">{turn.question}</div>{turn.response ? <div className="assistant-message"><span className="message-label">研究导师</span><AnswerSummary answer={turn.response} candidates={matchProjects(turn.response)} retryDisabled={busy || !apiEnabled} onRetry={(retryQuestion) => void submit(retryQuestion, assistantStateFromAnswer(turn.response))} /></div> : null}</div>)}
        {busy ? <StreamDraft draft={draft} stage={stage} /> : null}<div ref={messageEndRef} />
      </div></div>
      <ScrollToLatestButton visible={showLatest} onClick={scrollToLatest} />
      <ChatComposer value={question} status={apiEnabled ? status : "公开归档模式无法对话，请在本地 API 模式打开。"} busy={busy} apiEnabled={apiEnabled} onChange={setQuestion} onSubmit={() => void submit()} onStop={() => controllerRef.current?.abort()} />
    </section>
  </section></main>;
}
