export function StatusBadge({ mode, quality }: { mode: string; quality?: boolean }) {
  const tone = mode === "llm" && quality !== false ? "ok" : mode === "refusal" || quality === false ? "bad" : "warn";
  const label = mode === "llm" ? "证据回答" : mode === "refusal" ? "拒答" : "规则降级";
  return <span className={`badge ${tone}`}>{label}</span>;
}
