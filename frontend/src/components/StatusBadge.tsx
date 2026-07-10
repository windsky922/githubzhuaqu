export function answerStatus(mode: string, quality?: boolean) {
  if (mode === "refusal") return { tone: "bad", label: "当前归档没有足够证据" };
  if (quality === false) return { tone: "bad", label: "模型回答未通过质量校验" };
  if (mode === "fallback_rule") return { tone: "warn", label: "已切换为证据约束结论" };
  return { tone: "ok", label: "证据已校验" };
}

export function AnswerStatus({ mode, quality }: { mode: string; quality?: boolean }) {
  const status = answerStatus(mode, quality);
  return <span className={`answer-status ${status.tone}`}>{status.label}</span>;
}

export const StatusBadge = AnswerStatus;
