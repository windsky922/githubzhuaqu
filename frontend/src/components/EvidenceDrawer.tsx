import * as Dialog from "@radix-ui/react-dialog";
import { ExternalLink, X } from "lucide-react";
import type { RagAnswer } from "../lib/types";
import { answerStatus } from "./StatusBadge";

function DetailSection({ title, children, open = false }: { title: string; children: React.ReactNode; open?: boolean }) { return <details className="evidence-block" open={open}><summary>{title}</summary><div className="evidence-content">{children}</div></details>; }

export function EvidenceDrawer({ answer, trigger }: { answer: RagAnswer; trigger: React.ReactNode }) {
  const status = answerStatus(answer.answer_mode, answer.answer_quality?.passed);
  return <Dialog.Root><Dialog.Trigger asChild>{trigger}</Dialog.Trigger><Dialog.Portal><Dialog.Overlay className="dialog-overlay" /><Dialog.Content className="dialog-content" aria-describedby={undefined}><div className="dialog-head"><div><Dialog.Title>本轮依据</Dialog.Title><span>只展示本轮检索到的可引用信息</span></div><Dialog.Close className="icon-button" aria-label="关闭依据" title="关闭依据"><X size={17} /></Dialog.Close></div><div className="dialog-body">
    <DetailSection title="推荐依据" open><p>{answer.answer || "未生成结论。"}</p></DetailSection>
    <DetailSection title={`引用仓库（${Math.min(answer.citations?.length || 0, 5)}）`} open>{(answer.citations || []).slice(0, 5).map((citation, index) => <div className="citation-row" key={`${citation.chunk_id || index}`}><span>[{citation.index || index + 1}]</span><div>{citation.html_url ? <a className="small-link" href={citation.html_url} target="_blank" rel="noreferrer">{citation.full_name || "GitHub 项目"}<ExternalLink size={11} /></a> : citation.full_name || "GitHub 项目"}<small>{citation.run_date || "无日期"}</small></div></div>) || <p>无可展示引用。</p>}</DetailSection>
    <DetailSection title={`检索片段（${Math.min(answer.evidence?.length || 0, 5)}）`}>{(answer.evidence || []).slice(0, 5).map((evidence, index) => <article className="evidence-quote" key={`${evidence.chunk_id || index}`}><strong>{evidence.full_name || "未标记项目"}</strong><p>{evidence.quote || "无可展示片段"}</p>{evidence.matched_evidence ? <small>{evidence.matched_evidence}</small> : null}</article>) || <p>无可展示片段。</p>}</DetailSection>
    <DetailSection title="质量与模型"><div className="diagnostic-grid"><span>回答状态</span><b className={status.tone}>{status.label}</b><span>模型</span><b>{answer.answer_model || "未使用模型"}</b><span>证据覆盖</span><b>{answer.evidence_coverage || answer.confidence || "未知"}</b><span>匹配把握</span><b>尚未校准</b><span>质量边界</span><b>只校验引用有效性</b>{answer.answer_quality?.passed === false ? <><span>质量问题</span><b>{(answer.answer_quality.issues || []).join("；") || "未通过"}</b></> : null}</div>{answer.fallback_reason ? <details className="technical-detail"><summary>技术详情</summary><code>{answer.fallback_reason}</code></details> : null}</DetailSection>
    <DetailSection title="原始上下文"><pre>{answer.prompt_context || "无"}</pre></DetailSection>
  </div></Dialog.Content></Dialog.Portal></Dialog.Root>;
}
