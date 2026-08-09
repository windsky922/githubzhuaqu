import * as Dialog from "@radix-ui/react-dialog";
import { ArrowDown, CheckCircle2, CircleStop, MessageSquareText, PanelLeft, Plus, Send, ShieldCheck, Trash2, X } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import type { Conversation, Project, RagAnswer } from "../lib/types";
import { AnswerStatus } from "./StatusBadge";
import { CandidateProjectCard, PrimaryProjectCard } from "./ProjectCard";
import { EvidenceDrawer } from "./EvidenceDrawer";

export type Candidate = Project & { evidenceCount: number };

export function selectPrimaryRecommendation(answer: RagAnswer, candidates: Candidate[]) {
  return !["clarification", "no_match"].includes(answer.answer_mode)
    && answer.answer_quality?.passed === true
    && (!answer.freshness_required || answer.answer_quality?.data_freshness === "fresh")
    ? candidates.find((candidate) => candidate.eligibility === "eligible" && candidate.current_eligible === true)
    : undefined;
}

type ConversationControls = { historyEnabled: boolean; onHistoryChange: (enabled: boolean) => void; onDelete: () => void; onClear: () => void };

export function ConversationSidebar({ conversations, activeId, historyGroups, onCreate, onSelect, historyEnabled, onHistoryChange, onDelete, onClear, mobile = false }: { conversations: Conversation[]; activeId?: string; historyGroups: Record<string, Conversation[]>; onCreate: () => void; onSelect: (id: string) => void; mobile?: boolean } & ConversationControls) {
  const [open, setOpen] = useState(false);
  const closeThen = (callback: () => void) => () => { callback(); if (mobile) setOpen(false); };
  const content = <><button className="button primary new-conversation" type="button" onClick={closeThen(onCreate)}><Plus size={16} />新对话</button><div className="history-controls"><label className="history-toggle"><input type="checkbox" checked={historyEnabled} onChange={(event) => onHistoryChange(event.target.checked)} /><span>本机保存 30 天</span></label><div><button className="button" type="button" onClick={closeThen(onDelete)}><Trash2 size={14} />删除当前</button><button className="button" type="button" onClick={closeThen(onClear)}>全部清空</button></div><small>默认关闭；最多 10 个会话，每会话 20 轮。</small></div><div className="conversation-list">{conversations.length ? Object.entries(historyGroups).map(([date, items]) => <div className="conversation-group" key={date}><span className="conversation-date">{date}</span>{items.map((conversation) => <button className={`conversation-item${conversation.id === activeId ? " active" : ""}`} type="button" key={conversation.id} onClick={closeThen(() => onSelect(conversation.id))} title={conversation.title}>{conversation.title || "新对话"}</button>)}</div>) : <p className="conversation-empty">尚无对话</p>}</div></>;
  if (!mobile) return <aside className="conversation-rail" aria-label="对话历史">{content}</aside>;
  return <Dialog.Root open={open} onOpenChange={setOpen}><Dialog.Trigger asChild><button className="icon-button session-menu" type="button" aria-label="打开对话历史" title="对话历史"><PanelLeft size={17} /></button></Dialog.Trigger><Dialog.Portal><Dialog.Overlay className="dialog-overlay" /><Dialog.Content className="mobile-nav-drawer sessions-drawer" aria-describedby={undefined}><div className="dialog-head"><Dialog.Title>对话</Dialog.Title><Dialog.Close className="icon-button" aria-label="关闭对话历史" title="关闭对话历史"><X size={17} /></Dialog.Close></div>{content}</Dialog.Content></Dialog.Portal></Dialog.Root>;
}

export function AgentTopbar({ apiEnabled, conversations, activeId, historyGroups, onCreate, onSelect, historyEnabled, onHistoryChange, onDelete, onClear }: { apiEnabled: boolean; conversations: Conversation[]; activeId?: string; historyGroups: Record<string, Conversation[]>; onCreate: () => void; onSelect: (id: string) => void } & ConversationControls) {
  return <header className="agent-header"><div><span className="agent-eyebrow"><ShieldCheck size={14} />AI Agent 学习与项目研究导师</span><strong>告诉我你想学习或研究什么</strong><p>通用教学与可核验项目事实分开标注。</p></div><div className="agent-header-actions"><span className={`connection-status${apiEnabled ? " online" : ""}`}><i />{apiEnabled ? "助手已连接" : "需要本地 API"}</span><ConversationSidebar mobile conversations={conversations} activeId={activeId} historyGroups={historyGroups} onCreate={onCreate} onSelect={onSelect} historyEnabled={historyEnabled} onHistoryChange={onHistoryChange} onDelete={onDelete} onClear={onClear} /></div></header>;
}

export function ChatComposer({ value, status, busy, apiEnabled, onChange, onSubmit, onStop }: { value: string; status: string; busy: boolean; apiEnabled: boolean; onChange: (value: string) => void; onSubmit: () => void; onStop: () => void }) {
  const ref = useRef<HTMLTextAreaElement | null>(null);
  useEffect(() => { const node = ref.current; if (!node) return; node.style.height = "0"; node.style.height = `${Math.min(Math.max(node.scrollHeight, 54), 180)}px`; }, [value]);
  return <div className="composer-wrap"><form className="composer" onSubmit={(event) => { event.preventDefault(); onSubmit(); }}><textarea ref={ref} value={value} disabled={!apiEnabled || busy} placeholder={apiEnabled ? "例如：我需要一个可本地部署的多 Agent 自动化项目" : "请在本地 API 模式打开"} onChange={(event) => onChange(event.target.value)} onKeyDown={(event) => { if (event.key === "Enter" && !event.shiftKey) { event.preventDefault(); onSubmit(); } }} aria-label="输入项目需求" /><div className="composer-bottom"><span className="composer-status">{status}</span>{busy ? <button className="icon-button stop-button" type="button" onClick={onStop} aria-label="停止生成" title="停止生成"><CircleStop size={17} /></button> : <button className="icon-button send-button" type="submit" disabled={!apiEnabled || !value.trim()} aria-label="发送需求" title="发送需求"><Send size={17} /></button>}</div></form><span className="composer-hint">Enter 发送，Shift + Enter 换行</span></div>;
}

function reasonSummary(answer: RagAnswer) { return answer.answer.replace(/\[\d+\]/g, "").split(/\n+/).find((item) => item.trim()) || "已根据本轮召回证据形成项目建议。"; }
function friendlyFallback(reason: string) { if (/quality/i.test(reason)) return "模型输出与可引用证据不一致，已由证据约束结论替代。"; if (/not configured/i.test(reason)) return "模型服务不可用，已改用仅基于证据的结论。"; return "已按证据约束规则生成保守结论。"; }
export function answerConfidenceSemantics(answer: Pick<RagAnswer, "confidence" | "evidence_coverage" | "match_confidence">) {
  const coverage = answer.evidence_coverage || answer.confidence || "unknown";
  const coverageLabel = ({ low: "低", medium: "中", high: "高" } as Record<string, string>)[coverage] || "未知";
  return { coverageLabel: `证据覆盖：${coverageLabel}`, matchLabel: "匹配把握：尚未校准" };
}

type EditableRequirement = NonNullable<NonNullable<RagAnswer["input_route"]>["requirements"]>[number];

const requirementFieldLabels: Record<string, string> = {
  language: "语言",
  license: "许可证",
  hosting_mode: "部署方式",
  multi_agent: "多 Agent",
  offline_capable: "离线运行",
  network_required: "需要联网",
  external_api_required: "外部模型 API",
  api_key_required: "API Key",
  cost: "成本",
};

const requirementValueLabels: Record<string, string> = {
  self_hosted: "本地部署",
  cloud_hosted: "云端部署",
  free: "免费",
  paid: "付费",
  true: "是",
  false: "否",
};

function requirementLabel(requirement: EditableRequirement) {
  const field = requirementFieldLabels[requirement.field] || requirement.field;
  const value = requirementValueLabels[String(requirement.value)] || String(requirement.value);
  return `${field}${requirement.operator === "not_eq" ? "不等于" : "="}${value}`;
}

function requirementClause(requirement: EditableRequirement) {
  const field = requirementFieldLabels[requirement.field] || requirement.field;
  const value = requirementValueLabels[String(requirement.value)] || String(requirement.value);
  if (requirement.operator === "not_eq") return requirement.hard ? `不得满足${field}=${value}` : `${field}最好不是${value}`;
  return requirement.hard ? `必须满足${field}=${value}` : `偏好${field}=${value}`;
}

export function constraintRetryQuery(requirements: EditableRequirement[], relaxHard = false) {
  const normalized = requirements.map((requirement) => relaxHard ? { ...requirement, hard: false } : requirement);
  return normalized.length ? `使用这些条件重新搜索：${normalized.map(requirementClause).join("；")}` : "重新搜索并给出当前最匹配的项目";
}

function ConstraintEditor({ requirements, disabled, onRetry }: { requirements: EditableRequirement[]; disabled: boolean; onRetry?: (query: string) => void }) {
  const [items, setItems] = useState(requirements);
  if (!requirements.length) return null;
  const hasHard = items.some((item) => item.hard);
  return <section className="constraint-editor" aria-label="检索条件编辑器"><div className="constraint-editor-head"><strong>本轮检索条件</strong><span>可删除或切换硬约束 / 偏好</span></div><div className="constraint-chips">{items.length ? items.map((item, index) => <span className={`constraint-chip ${item.hard ? "hard" : "preference"}`} key={`${item.field}-${item.operator}-${String(item.value)}-${index}`}><button type="button" className="constraint-kind" disabled={disabled} onClick={() => setItems((current) => current.map((entry, entryIndex) => entryIndex === index ? { ...entry, hard: !entry.hard } : entry))} aria-label={`将${requirementLabel(item)}切换为${item.hard ? "偏好" : "硬约束"}`} title={`切换为${item.hard ? "偏好" : "硬约束"}`}>{item.hard ? "硬约束" : "偏好"}</button><span>{requirementLabel(item)}</span><button type="button" className="constraint-remove" disabled={disabled} onClick={() => setItems((current) => current.filter((_, entryIndex) => entryIndex !== index))} aria-label={`删除条件${requirementLabel(item)}`} title="删除条件"><X size={13} /></button></span>) : <span className="constraint-empty">已移除全部条件，将执行宽泛搜索。</span>}</div><div className="constraint-editor-actions"><button className="button" type="button" disabled={disabled || !onRetry} onClick={() => onRetry?.(constraintRetryQuery(items))}>应用条件重新搜索</button>{hasHard ? <button className="button constraint-relax" type="button" disabled={disabled || !onRetry} onClick={() => onRetry?.(constraintRetryQuery(items, true))}>一键放宽并重试</button> : null}</div></section>;
}

export function AnswerSummary({ answer, candidates, onRetry, retryDisabled = false }: { answer: RagAnswer; candidates: Candidate[]; onRetry?: (query: string) => void; retryDisabled?: boolean }) {
  const primary = selectPrimaryRecommendation(answer, candidates);
  const rest = primary ? candidates.filter((candidate) => candidate.full_name !== primary.full_name) : candidates;
  const semantics = answerConfidenceSemantics(answer);
  const clarification = answer.answer_mode === "clarification";
  const noMatch = answer.answer_mode === "no_match";
  const freshness = answer.answer_quality || answer.freshness;
  const freshnessText = freshness?.data_freshness === "fresh" ? "资料新鲜：三层水位已对齐" : `资料新鲜度：${freshness?.data_freshness || "unknown"}${freshness?.as_of ? `（核验日 ${freshness.as_of}）` : ""}`;
  const sourceText = answer.source_notice || (answer.data_source?.history_only ? "本机历史归档，仅作历史候选，无法确认当前状态。" : "来源状态待核实。");
  const modeText = ({ knowledge: "教学", project_search: "项目搜索", project_follow_up: "项目追问", project_compare: "项目比较", help: "帮助", clarify: "澄清" } as Record<string, string>)[answer.assistant_mode || ""] || answer.assistant_mode || "历史展示";
  const basisText = ({ model_general: "模型通用知识", project_evidence: "项目证据", mixed: "通用知识 + 项目证据", none: "无外部知识" } as Record<string, string>)[answer.knowledge_basis || ""] || answer.knowledge_basis || "历史最小记录";
  const modelText = answer.model_status?.configured ? `模型：${answer.model_status.model || "已配置"}` : "模型：未配置或未使用";
  return <section className="answer-summary"><ConstraintEditor requirements={answer.input_route?.requirements || []} disabled={retryDisabled} onRetry={onRetry} /><div className="answer-meta"><AnswerStatus mode={answer.answer_mode} quality={answer.answer_quality?.passed} /><span className="badge">模式：{modeText}</span><span className="badge">来源：{basisText}</span><span className="badge">{modelText}</span><span className="badge">{semantics.coverageLabel}</span><span className="badge">{semantics.matchLabel}</span><span className="badge">{freshnessText}</span></div><div className={`answer-notice ${answer.data_source?.history_only ? "warn" : ""}`}><strong>数据来源{answer.data_source?.run_date ? ` · ${answer.data_source.run_date}` : ""}</strong><span>{sourceText}</span></div>{clarification ? <div className="answer-notice warn"><strong>需要补充需求</strong><span>{answer.clarification_question || answer.answer}</span></div> : noMatch ? <div className="answer-notice bad"><strong>当前条件下没有匹配项目</strong><span>{answer.answer}</span></div> : primary ? <><div className="recommendation-title"><CheckCircle2 size={17} /><span>当前归档内最匹配候选</span></div><PrimaryProjectCard project={primary} evidenceCount={primary.evidenceCount} /></> : <div className="answer-notice warn"><strong>暂无可确认首选</strong><span>历史候选与待核实候选会保留展示，但不会标记为当前首选。</span></div>}{!clarification ? <><div className="answer-text"><p>{reasonSummary(answer)}</p></div><div className="answer-notice"><strong>质量边界</strong><span>当前闸门校验引用绑定、极性、结构化作用域、语义字段一致性和归档新鲜度；不代表 blind 泛化或真实需求匹配正确率。</span></div><details className="expanded-analysis"><summary>展开完整分析</summary><div className="answer-text">{answer.answer.replace(/\[\d+\]/g, "").split(/\n+/).map((paragraph, index) => <p key={index}>{paragraph}</p>)}</div></details>{answer.fallback_reason && !noMatch ? <div className="answer-notice warn"><strong>已采用保守结论</strong><span>{friendlyFallback(answer.fallback_reason)}</span></div> : null}{answer.answer_quality?.applicable !== false && answer.answer_quality?.passed === false ? <div className="answer-notice bad"><strong>质量校验未通过</strong><span>{(answer.answer_quality.issues || []).join("；") || "模型回答未通过证据质量闸门。"}</span></div> : null}{rest.length ? <div className="candidate-section"><div className="candidate-heading">{primary ? "其他可考虑项目" : "当前候选及约束状态"}</div><div className="project-grid">{rest.slice(0, primary ? 2 : 3).map((project) => <CandidateProjectCard key={project.full_name} project={project} evidenceCount={project.evidenceCount} />)}</div></div> : null}<EvidenceDrawer answer={answer} trigger={<button className="button evidence-trigger" type="button"><MessageSquareText size={15} />查看依据</button>} /></> : null}</section>;
}

export function StreamDraft({ draft, stage }: { draft: string; stage: string }) { return <section className="assistant-message stream-draft"><span className="message-label">研究 Agent</span><span className="stream-stage"><i />{stage}</span>{draft ? <div className="answer-text draft">{draft}</div> : <div className="draft">正在分析本轮证据…</div>}</section>; }

export function ScrollToLatestButton({ visible, onClick }: { visible: boolean; onClick: () => void }) { return visible ? <button className="scroll-latest" type="button" onClick={onClick}><ArrowDown size={16} />回到最新消息</button> : null; }
