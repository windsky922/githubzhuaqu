import { useEffect, useMemo, useRef, useState } from "react";
import { CircleStop, Plus, Send, ShieldCheck } from "lucide-react";
import { answerFromEvent, shouldUseApi, streamRagAsk } from "../lib/api";
import { loadConversations, newConversation, saveConversations } from "../lib/conversations";
import type { Conversation, RagAnswer } from "../lib/types";
import { EvidenceDrawer } from "../components/EvidenceDrawer";
import { ProjectCard } from "../components/ProjectCard";
import { StatusBadge } from "../components/StatusBadge";

const examples = ["哪些 Agent workflow 项目适合本地开发和自动化？", "我想找可以继续跟踪的 RAG 基础设施项目。", "适合 Python 团队的 AI 编程工具有哪些？"];

function compactProjects(answer?: RagAnswer) {
  const seen = new Map<string, { full_name: string; html_url?: string; run_date?: string }>();
  (answer?.citations || []).forEach((citation) => {
    if (citation.full_name) seen.set(citation.full_name, { full_name: citation.full_name, html_url: citation.html_url, run_date: citation.run_date });
  });
  return [...seen.values()].slice(0, 3);
}

export function AgentPage() {
  const [conversations, setConversations] = useState<Conversation[]>(loadConversations);
  const [activeId, setActiveId] = useState(() => conversations[0]?.id || "");
  const [question, setQuestion] = useState("");
  const [draft, setDraft] = useState("");
  const [status, setStatus] = useState("输入你的需求，Agent 会从当前项目证据中匹配候选。");
  const [busy, setBusy] = useState(false);
  const controllerRef = useRef<AbortController | null>(null);
  const messageEndRef = useRef<HTMLDivElement | null>(null);
  const apiEnabled = shouldUseApi();
  const active = conversations.find((item) => item.id === activeId) || conversations[0];

  useEffect(() => { saveConversations(conversations); }, [conversations]);
  useEffect(() => { if (busy) messageEndRef.current?.scrollIntoView({ behavior: "smooth", block: "end" }); }, [busy, draft]);

  const historyGroups = useMemo(() => conversations.reduce<Record<string, Conversation[]>>((groups, conversation) => {
    const key = new Intl.DateTimeFormat("zh-CN", { month: "short", day: "numeric" }).format(new Date(conversation.updatedAt));
    (groups[key] ||= []).push(conversation);
    return groups;
  }, {}), [conversations]);

  function createNewConversation() {
    const conversation = newConversation();
    setConversations((items) => [conversation, ...items].slice(0, 10));
    setActiveId(conversation.id);
    setQuestion("");
    setDraft("");
    setStatus("新的项目匹配对话已创建。");
  }

  async function submit(rawQuestion?: string) {
    const nextQuestion = (rawQuestion || question).trim();
    if (!nextQuestion || busy || !active || !apiEnabled) return;
    const turnId = crypto.randomUUID();
    const now = new Date().toISOString();
    setQuestion("");
    setDraft("");
    setBusy(true);
    setStatus("正在检索可引用项目证据…");
    setConversations((items) => items.map((conversation) => conversation.id === active.id ? {
      ...conversation,
      title: conversation.turns.length ? conversation.title : nextQuestion.slice(0, 22),
      updatedAt: now,
      turns: [...conversation.turns, { id: turnId, question: nextQuestion, createdAt: now }],
    } : conversation));
    const controller = new AbortController();
    controllerRef.current = controller;
    try {
      await streamRagAsk(nextQuestion, controller.signal, (event) => {
        if (event.event === "meta") setStatus("已召回证据，正在生成草稿…");
        if (event.event === "delta") {
          setDraft((value) => value + String(event.data.text || ""));
          setStatus("草稿生成中，等待证据质量校验…");
        }
        if (event.event === "final") {
          const response = answerFromEvent(event.data);
          setConversations((items) => items.map((conversation) => conversation.id === active.id ? {
            ...conversation,
            updatedAt: new Date().toISOString(),
            turns: conversation.turns.map((turn) => turn.id === turnId ? { ...turn, response } : turn),
          } : conversation));
          setDraft("");
          setStatus(response.answer_mode === "llm" ? "回答已通过证据质量校验。" : "已返回证据约束结果，请注意回答状态。 ");
        }
        if (event.event === "error") setStatus(String(event.data.message || "流式连接中断。"));
      });
    } catch (error) {
      if (!controller.signal.aborted) setStatus(`请求失败：${error instanceof Error ? error.message : "未知错误"}`);
    } finally {
      controllerRef.current = null;
      setBusy(false);
    }
  }

  return (
    <main className="page">
      <section className="agent-page">
        <aside className="conversation-rail">
          <button className="button primary" type="button" onClick={createNewConversation}><Plus size={16} />新对话</button>
          <div className="conversation-list">
            {Object.entries(historyGroups).map(([date, items]) => <div key={date}><p className="conversation-date">{date}</p>{items.map((conversation) => <button className={`conversation-item${conversation.id === active?.id ? " active" : ""}`} type="button" key={conversation.id} onClick={() => setActiveId(conversation.id)}>{conversation.title}</button>)}</div>)}
          </div>
        </aside>
        <section className="agent-workspace">
          <header className="agent-header">
            <div><strong>项目匹配</strong><span>只基于本轮召回证据形成结论</span></div>
            <span className="mode-pill"><ShieldCheck size={13} />证据约束</span>
          </header>
          <div className="messages">
            <div className="message-stack">
              {!active?.turns.length ? <div className="welcome"><h2>描述你现在想解决的问题。</h2><p>我会从当前归档中筛出最匹配的 GitHub 项目，并把依据留在每轮回答里。</p><div className="suggestions">{examples.map((example) => <button className="suggestion" type="button" key={example} onClick={() => void submit(example)}>{example}</button>)}</div></div> : null}
              {active?.turns.map((turn) => <div className="turn" key={turn.id}>
                <span className="message-label">你的需求</span><div className="user-message">{turn.question}</div>
                {turn.response ? <div className="assistant-message"><span className="message-label">研究 Agent</span><div className="answer-meta"><StatusBadge mode={turn.response.answer_mode} quality={turn.response.answer_quality?.passed} /><span className="badge">{turn.response.confidence} 置信度</span></div><div className="answer-text">{turn.response.answer}</div>{turn.response.fallback_reason ? <span className="badge warn">降级原因：{turn.response.fallback_reason}</span> : null}{turn.response.answer_quality?.passed === false ? <span className="badge bad">质量问题：{(turn.response.answer_quality.issues || []).join("；") || "未通过"}</span> : null}<div className="project-grid">{compactProjects(turn.response).map((project) => <ProjectCard key={project.full_name} project={project} />)}</div><EvidenceDrawer answer={turn.response} trigger={<button className="button evidence-trigger" type="button">查看证据</button>} /></div> : null}
              </div>)}
              {busy ? <div className="assistant-message"><span className="message-label">研究 Agent</span>{draft ? <div className="answer-text draft">{draft}</div> : <div className="draft">正在分析…</div>}</div> : null}
              <div ref={messageEndRef} />
            </div>
          </div>
          <div className="composer-wrap"><form className="composer" onSubmit={(event) => { event.preventDefault(); void submit(); }}><textarea value={question} disabled={!apiEnabled || busy} placeholder={apiEnabled ? "例如：我需要一个适合本地运行的多 Agent 自动化项目" : "请在本地 API 模式打开"} onChange={(event) => setQuestion(event.target.value)} onKeyDown={(event) => { if (event.key === "Enter" && !event.shiftKey) { event.preventDefault(); void submit(); } }} /><div className="composer-bottom"><span className="composer-status">{apiEnabled ? status : "公开归档模式无法进行项目匹配，请在本地 API 模式打开。"}</span>{busy ? <button className="button" type="button" onClick={() => controllerRef.current?.abort()}><CircleStop size={15} />停止</button> : <button className="button primary" type="submit" disabled={!apiEnabled || !question.trim()}><Send size={15} />发送</button>}</div></form></div>
        </section>
      </section>
    </main>
  );
}
