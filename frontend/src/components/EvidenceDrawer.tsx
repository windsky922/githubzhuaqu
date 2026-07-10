import * as Dialog from "@radix-ui/react-dialog";
import { ExternalLink, X } from "lucide-react";
import type { RagAnswer } from "../lib/types";

export function EvidenceDrawer({ answer, trigger }: { answer: RagAnswer; trigger: React.ReactNode }) {
  return (
    <Dialog.Root>
      <Dialog.Trigger asChild>{trigger}</Dialog.Trigger>
      <Dialog.Portal>
        <Dialog.Overlay className="dialog-overlay" />
        <Dialog.Content className="dialog-content" aria-describedby={undefined}>
          <div className="dialog-head">
            <Dialog.Title>本轮证据</Dialog.Title>
            <Dialog.Close className="icon-button" aria-label="关闭证据"><X size={17} /></Dialog.Close>
          </div>
          <div className="dialog-body">
            <div className="evidence-block">
              <strong>回答状态</strong>
              <p>{answer.answer_model} · {answer.answer_mode} · {answer.confidence}</p>
              {answer.fallback_reason ? <p>降级原因：{answer.fallback_reason}</p> : null}
              {answer.answer_quality?.passed === false ? <p>质量闸门：{(answer.answer_quality.issues || []).join("；") || "未通过"}</p> : null}
            </div>
            <div className="evidence-block">
              <strong>引用</strong>
              {(answer.citations || []).slice(0, 5).map((citation, index) => (
                <p key={`${citation.chunk_id || index}`}>
                  [{citation.index || index + 1}] {citation.html_url ? <a className="small-link" href={citation.html_url} target="_blank" rel="noreferrer">{citation.full_name || "GitHub 项目"} <ExternalLink size={11} /></a> : citation.full_name} · {citation.run_date || "无日期"}<br />
                  <code>{citation.chunk_id}</code>
                </p>
              ))}
            </div>
            <div className="evidence-block">
              <strong>证据片段</strong>
              {(answer.evidence || []).slice(0, 5).map((evidence, index) => <p key={`${evidence.chunk_id || index}`}><b>{evidence.full_name || "未标记项目"}</b><br />{evidence.quote || "无可展示片段"}</p>)}
            </div>
            <details className="evidence-block">
              <summary>提示词上下文</summary>
              <p>{answer.prompt_context || "无"}</p>
            </details>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
