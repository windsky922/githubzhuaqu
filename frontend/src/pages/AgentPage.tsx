import { useEffect, useMemo, useRef, useState } from "react";
import { answerFromEvent, shouldUseApi, streamRagAsk } from "../lib/api";
import { loadConversations, newConversation, saveConversations } from "../lib/conversations";
import type { AskIntentContext, Conversation, RagAnswer } from "../lib/types";
import { AgentTopbar, AnswerSummary, ChatComposer, ConversationSidebar, type Candidate, ScrollToLatestButton, StreamDraft } from "../components/AgentWorkspace";

const examples = ["我需要一个适合本地部署的多 Agent 自动化项目", "团队想跟踪值得长期关注的 RAG 基础设施", "适合 Python 团队的 AI 编程工具有哪些？"];

export function matchProjects(answer?: RagAnswer): Candidate[] {
  return (answer?.recommendations || []).slice(0, 3).map((recommendation) => ({
    full_name: recommendation.full_name,
    html_url: `https://github.com/${recommendation.full_name}`,
    rag_reason: recommendation.reasons[0] || "基于本轮可审计排序进入候选。",
    evidenceCount: recommendation.evidence_chunk_ids.length,
    match_score: recommendation.match_score,
    matched_requirements: recommendation.matched_requirements,
    unmet_requirements: recommendation.unmet_requirements,
    unknown_requirements: recommendation.unknown_requirements,
    eligibility: recommendation.eligibility,
    recommendation_rank: recommendation.rank,
  }));
}

export function followUpContext(answer: RagAnswer | undefined, previousQuestion: string): AskIntentContext | undefined {
  if (!answer) return undefined;
  const candidateIds = (answer.recommendations || []).map((item) => item.full_name).filter(Boolean).slice(0, 10);
  const first = answer.recommendations?.[0];
  const mode = answer.retrieval?.mode;
  const normalizedMode: AskIntentContext["mode"] = mode === "fts5" || mode === "vector" ? mode : "hybrid";
  const resumable = Boolean(candidateIds.length && !["clarification", "no_match", "refusal"].includes(answer.answer_mode));
  return {
    previous_user_goal: answer.resolved_query || previousQuestion,
    candidate_repository_ids: candidateIds,
    ...(answer.answer_quality?.passed === true && first?.eligibility === "eligible"
      ? { primary_repository_id: first.full_name }
      : {}),
    mode: normalizedMode,
    resumable,
  };
}

function history(conversations: Conversation[]) { return conversations.reduce<Record<string, Conversation[]>>((groups, conversation) => { const key = new Intl.DateTimeFormat("zh-CN", { month: "short", day: "numeric" }).format(new Date(conversation.updatedAt)); (groups[key] ||= []).push(conversation); return groups; }, {}); }

export function AgentPage() {
  const [conversations, setConversations] = useState<Conversation[]>(loadConversations);
  const [activeId, setActiveId] = useState(() => conversations[0]?.id || "");
  const [question, setQuestion] = useState("");
  const [draft, setDraft] = useState("");
  const [status, setStatus] = useState("输入一句需求，Agent 会匹配当前归档中的项目。");
  const [stage, setStage] = useState("正在准备检索");
  const [busy, setBusy] = useState(false);
  const [showLatest, setShowLatest] = useState(false);
  const controllerRef = useRef<AbortController | null>(null);
  const messagesRef = useRef<HTMLDivElement | null>(null);
  const messageEndRef = useRef<HTMLDivElement | null>(null);
  const apiEnabled = shouldUseApi();
  const active = conversations.find((item) => item.id === activeId) || conversations[0];
  const historyGroups = useMemo(() => history(conversations), [conversations]);

  useEffect(() => { saveConversations(conversations); }, [conversations]);
  useEffect(() => { if (busy && !showLatest) messageEndRef.current?.scrollIntoView({ behavior: "smooth", block: "end" }); }, [busy, draft, showLatest]);
  useEffect(() => { const node = messagesRef.current; if (!node) return; const handleScroll = () => setShowLatest(node.scrollHeight - node.scrollTop - node.clientHeight > 96); node.addEventListener("scroll", handleScroll); return () => node.removeEventListener("scroll", handleScroll); }, []);

  function createNewConversation() { const conversation = newConversation(); setConversations((items) => [conversation, ...items].slice(0, 10)); setActiveId(conversation.id); setQuestion(""); setDraft(""); setStatus("新的项目匹配对话已创建。"); }
  function selectConversation(id: string) { setActiveId(id); setDraft(""); setShowLatest(false); }
  function scrollToLatest() { messageEndRef.current?.scrollIntoView({ behavior: "smooth", block: "end" }); setShowLatest(false); }

  async function submit(rawQuestion?: string) {
    const nextQuestion = (rawQuestion || question).trim(); if (!nextQuestion || busy || !active || !apiEnabled) return;
    const previousTurn = [...active.turns].reverse().find((turn) => turn.response);
    const context = previousTurn ? followUpContext(previousTurn.response, previousTurn.question) : undefined;
    const turnId = crypto.randomUUID(); const now = new Date().toISOString(); setQuestion(""); setDraft(""); setBusy(true); setStage("正在检索可引用的项目证据"); setStatus("检索中…");
    setConversations((items) => items.map((conversation) => conversation.id === active.id ? { ...conversation, title: conversation.turns.length ? conversation.title : nextQuestion.slice(0, 22), updatedAt: now, turns: [...conversation.turns, { id: turnId, question: nextQuestion, createdAt: now }] } : conversation));
    const controller = new AbortController(); controllerRef.current = controller;
    try { await streamRagAsk(nextQuestion, context, controller.signal, (event) => {
      if (event.event === "meta") { setStage("已召回证据，正在生成草稿"); setStatus("证据已召回"); }
      if (event.event === "delta") { setDraft((value) => value + String(event.data.text || "")); setStage("已通过当前基础闸门，正在分段展示"); setStatus("主张与证据校验已通过。"); }
      if (event.event === "final") { const response = answerFromEvent(event.data); setConversations((items) => items.map((conversation) => conversation.id === active.id ? { ...conversation, updatedAt: new Date().toISOString(), turns: conversation.turns.map((turn) => turn.id === turnId ? { ...turn, response } : turn) } : conversation)); setDraft(""); setStage("已生成正式结论"); setStatus(response.answer_mode === "clarification" ? "需要补充需求后再检索。" : response.answer_mode === "no_match" ? "当前硬约束下没有匹配项目。" : response.answer_mode === "llm" && response.answer_quality?.passed !== false ? "回答已通过证据质量校验。" : "已返回证据约束结论。"); }
      if (event.event === "error") { setStage("连接异常"); setStatus(String(event.data.message || "流式连接中断。")); }
    }); } catch (error) { if (!controller.signal.aborted) { setStage("请求失败"); setStatus(`请求失败：${error instanceof Error ? error.message : "未知错误"}`); } } finally { controllerRef.current = null; setBusy(false); }
  }

  return <main className="agent-page-shell"><section className="agent-page"><ConversationSidebar conversations={conversations} activeId={active?.id} historyGroups={historyGroups} onCreate={createNewConversation} onSelect={selectConversation} /><section className="agent-workspace"><AgentTopbar apiEnabled={apiEnabled} conversations={conversations} activeId={active?.id} historyGroups={historyGroups} onCreate={createNewConversation} onSelect={selectConversation} /><div className="messages" ref={messagesRef}><div className="message-stack">{!active?.turns.length ? <div className="welcome"><span className="agent-eyebrow">项目研究 Agent</span><h1>描述你要解决的问题。</h1><p>我会从本轮召回的证据中，找出最匹配的 GitHub 项目。</p><div className="suggestions">{examples.map((example) => <button className="suggestion" type="button" key={example} disabled={!apiEnabled} onClick={() => void submit(example)}>{example}</button>)}</div></div> : null}{active?.turns.map((turn) => <div className="turn" key={turn.id}><span className="message-label">你的需求</span><div className="user-message">{turn.question}</div>{turn.response ? <div className="assistant-message"><span className="message-label">研究 Agent</span><AnswerSummary answer={turn.response} candidates={matchProjects(turn.response)} /></div> : null}</div>)}{busy ? <StreamDraft draft={draft} stage={stage} /> : null}<div ref={messageEndRef} /></div></div><ScrollToLatestButton visible={showLatest} onClick={scrollToLatest} /><ChatComposer value={question} status={apiEnabled ? status : "公开归档模式无法进行项目匹配，请在本地 API 模式打开。"} busy={busy} apiEnabled={apiEnabled} onChange={setQuestion} onSubmit={() => void submit()} onStop={() => controllerRef.current?.abort()} /></section></section></main>;
}
