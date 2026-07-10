export type Evidence = {
  index?: number;
  full_name?: string;
  html_url?: string;
  run_date?: string;
  chunk_id?: string;
  quote?: string;
  matched_evidence?: string[];
};

export type Citation = Pick<Evidence, "index" | "full_name" | "html_url" | "run_date" | "chunk_id">;

export type Project = {
  full_name: string;
  html_url?: string;
  description?: string;
  language?: string;
  category?: string;
  source?: string;
  sources?: string[];
  run_date?: string;
  stars?: number;
  stars_added?: number;
  recommendation_reason?: string;
  rag_reason?: string;
  recommendation_score?: number;
  quality?: { level?: string; score?: number };
  risk_summary?: string;
  [key: string]: unknown;
};

export type RagAnswer = {
  query: string;
  answer: string;
  answer_model: string;
  answer_mode: "llm" | "fallback_rule" | "refusal" | string;
  fallback_reason: string;
  confidence: string;
  count: number;
  citations: Citation[];
  evidence: Evidence[];
  prompt_context: string;
  answer_quality: { passed?: boolean; issues?: string[] };
  retrieval?: { mode?: string };
  model_status?: { configured?: boolean; used?: boolean };
  [key: string]: unknown;
};

export type ChatTurn = {
  id: string;
  question: string;
  createdAt: string;
  response?: RagAnswer;
};

export type Conversation = {
  id: string;
  title: string;
  updatedAt: string;
  turns: ChatTurn[];
};
