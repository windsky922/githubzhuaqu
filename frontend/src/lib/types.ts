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

export type RequirementValue = string | boolean;

export type RequirementEvaluation = {
  field: string;
  operator: string;
  value: RequirementValue;
  status: "matched" | "unmet" | "unknown";
  reason: string;
  evidence_chunk_ids: string[];
};

export type RagRecommendation = {
  full_name: string;
  rank: number;
  match_score: number;
  matched_requirements: string[];
  unmet_requirements: string[];
  unknown_requirements: string[];
  reasons: string[];
  citation_indexes: number[];
  evidence_chunk_ids: string[];
  requirement_evaluations: RequirementEvaluation[];
  eligibility: "eligible" | "rejected" | "unknown";
};

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
  match_score?: number;
  matched_requirements?: string[];
  unmet_requirements?: string[];
  unknown_requirements?: string[];
  eligibility?: RagRecommendation["eligibility"];
  recommendation_rank?: number;
  [key: string]: unknown;
};

export type ProjectPage = { projects: Project[]; count: number; total: number; offset: number; limit: number; has_more: boolean; static_fallback?: boolean };
export type ComparisonProject = Project & Record<string, unknown>;
export type Comparison = {
  count: number;
  missing: string[];
  projects: ComparisonProject[];
  matrix: Array<{ key: string; label: string; values: Record<string, unknown> }>;
  best_by: Record<string, string>;
  recommendation: { summary?: string; reasons?: string[]; cautions?: string[] } | Record<string, unknown>;
  selection_summary: string[];
};

export type RagAnswer = {
  query: string;
  answer: string;
  answer_model: string;
  answer_mode: "llm" | "fallback_rule" | "refusal" | string;
  fallback_reason: string;
  confidence: string;
  evidence_coverage: string;
  match_confidence: string;
  count: number;
  citations: Citation[];
  evidence: Evidence[];
  recommendations: RagRecommendation[];
  resolved_query?: string;
  clarification_required?: boolean;
  clarification_question?: string;
  input_route?: {
    route?: "new_search" | "resume" | "refine" | "clarify";
    reason?: string;
    parser?: string;
    retrieval_performed?: boolean;
    candidate_scope?: "archive" | "previous_candidates" | "primary_candidate" | "none";
    requirement_schema_version?: "capability-v1" | string;
    requirements?: Array<{ field: string; operator: string; value: RequirementValue; hard: boolean }>;
  };
  prompt_context: string;
  answer_quality: {
    applicable?: boolean;
    passed?: boolean;
    issues?: string[];
    citation_validity?: boolean | string;
    evidence_relevance?: "not_evaluated" | string;
    claim_support?: "not_evaluated" | string;
    data_freshness?: "unknown" | string;
  };
  retrieval?: { mode?: string };
  model_status?: { configured?: boolean; used?: boolean };
  [key: string]: unknown;
};

export type AskIntentContext = {
  previous_user_goal: string;
  candidate_repository_ids: string[];
  primary_repository_id?: string;
  mode: "fts5" | "vector" | "hybrid";
  resumable: boolean;
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
