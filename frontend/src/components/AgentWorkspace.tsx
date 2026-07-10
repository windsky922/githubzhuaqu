import * as Dialog from "@radix-ui/react-dialog";
import { ArrowDown, CheckCircle2, CircleStop, MessageSquareText, PanelLeft, Plus, Send, ShieldCheck, X } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import type { Conversation, Project, RagAnswer } from "../lib/types";
import { AnswerStatus } from "./StatusBadge";
import { CandidateProjectCard, PrimaryProjectCard } from "./ProjectCard";
import { EvidenceDrawer } from "./EvidenceDrawer";

export type Candidate = Project & { evidenceCount: number };

export function ConversationSidebar({ conversations, activeId, historyGroups, onCreate, onSelect, mobile = false }: { conversations: Conversation[]; activeId?: string; historyGroups: Record<string, Conversation[]>; onCreate: () => void; onSelect: (id: string) => void; mobile?: boolean }) {
  const [open, setOpen] = useState(false);
  const closeThen = (callback: () => void) => () => { callback(); if (mobile) setOpen(false); };
  const content = <><button className="button primary new-conversation" type="button" onClick={closeThen(onCreate)}><Plus size={16} />新对话</button><div className="conversation-list">{conversations.length ? Object.entries(historyGroups).map(([date, items]) => <div className="conversation-group" key={date}><span className="conversation-date">{date}</span>{items.map((conversation) => <button className={`conversation-item${conversation.id === activeId ? " active" : ""}`} type="button" key={conversation.id} onClick={closeThen(() => onSelect(conversation.id))} title={conversation.title}>{conversation.title || "新对话"}</button>)}</div>) : <p className="conversation-empty">尚无对话</p>}</div></>;
  if (!mobile) return <aside className="conversation-rail" aria-label="对话历史">{content}</aside>;
  return <Dialog.Root open={open} onOpenChange={setOpen}><Dialog.Trigger asChild><button className="icon-button session-menu" type="button" aria-label="打开对话历史" title="对话历史"><PanelLeft size={17} /></button></Dialog.Trigger><Dialog.Portal><Dialog.Overlay className="dialog-overlay" /><Dialog.Content className="mobile-nav-drawer sessions-drawer" aria-describedby={undefined}><div className="dialog-head"><Dialog.Title>对话</Dialog.Title><Dialog.Close className="icon-button" aria-label="关闭对话历史" title="关闭对话历史"><X size={17} /></Dialog.Close></div>{content}</Dialog.Content></Dialog.Portal></Dialog.Root>;
}

export function AgentTopbar({ apiEnabled, conversations, activeId, historyGroups, onCreate, onSelect }: { apiEnabled: boolean; conversations: Conversation[]; activeId?: string; historyGroups: Record<string, Conversation[]>; onCreate: () => void; onSelect: (id: string) => void }) {
  return <header className="agent-header"><div><span className="agent-eyebrow"><ShieldCheck size={14} />证据约束项目匹配</span><strong>告诉我你的需求</strong><p>每轮独立检索，只根据可引用的项目证据给出建议。</p></div><div className="agent-header-actions"><span className={`connection-status${apiEnabled ? " online" : ""}`}><i />{apiEnabled ? "可开始研究" : "需要本地 API"}</span><ConversationSidebar mobile conversations={conversations} activeId={activeId} historyGroups={historyGroups} onCreate={onCreate} onSelect={onSelect} /></div></header>;
}

export function ChatComposer({ value, status, busy, apiEnabled, onChange, onSubmit, onStop }: { value: string; status: string; busy: boolean; apiEnabled: boolean; onChange: (value: string) => void; onSubmit: () => void; onStop: () => void }) {
  const ref = useRef<HTMLTextAreaElement | null>(null);
  useEffect(() => { const node = ref.current; if (!node) return; node.style.height = "0"; node.style.height = `${Math.min(Math.max(node.scrollHeight, 54), 180)}px`; }, [value]);
  return <div className="composer-wrap"><form className="composer" onSubmit={(event) => { event.preventDefault(); onSubmit(); }}><textarea ref={ref} value={value} disabled={!apiEnabled || busy} placeholder={apiEnabled ? "例如：我需要一个可本地部署的多 Agent 自动化项目" : "请在本地 API 模式打开"} onChange={(event) => onChange(event.target.value)} onKeyDown={(event) => { if (event.key === "Enter" && !event.shiftKey) { event.preventDefault(); onSubmit(); } }} aria-label="输入项目需求" /><div className="composer-bottom"><span className="composer-status">{status}</span>{busy ? <button className="icon-button stop-button" type="button" onClick={onStop} aria-label="停止生成" title="停止生成"><CircleStop size={17} /></button> : <button className="icon-button send-button" type="submit" disabled={!apiEnabled || !value.trim()} aria-label="发送需求" title="发送需求"><Send size={17} /></button>}</div></form><span className="composer-hint">Enter 发送，Shift + Enter 换行</span></div>;
}

function reasonSummary(answer: RagAnswer) { return answer.answer.replace(/\[\d+\]/g, "").split(/\n+/).find((item) => item.trim()) || "已根据本轮召回证据形成项目建议。"; }
function friendlyFallback(reason: string) { if (/quality/i.test(reason)) return "模型输出与可引用证据不一致，已由证据约束结论替代。"; if (/not configured/i.test(reason)) return "模型服务不可用，已改用仅基于证据的结论。"; return "已按证据约束规则生成保守结论。"; }

export function AnswerSummary({ answer, candidates }: { answer: RagAnswer; candidates: Candidate[] }) {
  const [primary, ...rest] = candidates;
  return <section className="answer-summary"><div className="answer-meta"><AnswerStatus mode={answer.answer_mode} quality={answer.answer_quality?.passed} /><span className="badge">{answer.confidence || "未知"} 置信度</span></div>{primary ? <><div className="recommendation-title"><CheckCircle2 size={17} /><span>最匹配项目</span></div><PrimaryProjectCard project={primary} evidenceCount={primary.evidenceCount} /></> : null}<div className="answer-text"><p>{reasonSummary(answer)}</p></div><details className="expanded-analysis"><summary>展开完整分析</summary><div className="answer-text">{answer.answer.replace(/\[\d+\]/g, "").split(/\n+/).map((paragraph, index) => <p key={index}>{paragraph}</p>)}</div></details>{answer.fallback_reason ? <div className="answer-notice warn"><strong>已采用保守结论</strong><span>{friendlyFallback(answer.fallback_reason)}</span></div> : null}{answer.answer_quality?.passed === false ? <div className="answer-notice bad"><strong>质量校验未通过</strong><span>{(answer.answer_quality.issues || []).join("；") || "模型回答未通过证据质量闸门。"}</span></div> : null}{rest.length ? <div className="candidate-section"><div className="candidate-heading">其他可考虑项目</div><div className="project-grid">{rest.slice(0, 2).map((project) => <CandidateProjectCard key={project.full_name} project={project} evidenceCount={project.evidenceCount} />)}</div></div> : null}<EvidenceDrawer answer={answer} trigger={<button className="button evidence-trigger" type="button"><MessageSquareText size={15} />查看依据</button>} /></section>;
}

export function StreamDraft({ draft, stage }: { draft: string; stage: string }) { return <section className="assistant-message stream-draft"><span className="message-label">研究 Agent</span><span className="stream-stage"><i />{stage}</span>{draft ? <div className="answer-text draft">{draft}</div> : <div className="draft">正在分析本轮证据…</div>}</section>; }

export function ScrollToLatestButton({ visible, onClick }: { visible: boolean; onClick: () => void }) { return visible ? <button className="scroll-latest" type="button" onClick={onClick}><ArrowDown size={16} />回到最新消息</button> : null; }
