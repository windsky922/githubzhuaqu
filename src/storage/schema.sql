CREATE TABLE IF NOT EXISTS runs (
  run_date TEXT PRIMARY KEY,
  status TEXT NOT NULL DEFAULT '',
  collected_count INTEGER NOT NULL DEFAULT 0,
  selected_count INTEGER NOT NULL DEFAULT 0,
  previously_sent_selected_count INTEGER NOT NULL DEFAULT 0,
  kimi_used INTEGER NOT NULL DEFAULT 0,
  fallback_used INTEGER NOT NULL DEFAULT 0,
  telegram_sent INTEGER NOT NULL DEFAULT 0,
  report_path TEXT NOT NULL DEFAULT '',
  telegram_report_url TEXT NOT NULL DEFAULT '',
  payload_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS repositories (
  full_name TEXT PRIMARY KEY,
  html_url TEXT NOT NULL DEFAULT '',
  description TEXT NOT NULL DEFAULT '',
  language TEXT NOT NULL DEFAULT '',
  stargazers_count INTEGER NOT NULL DEFAULT 0,
  forks_count INTEGER NOT NULL DEFAULT 0,
  license_name TEXT NOT NULL DEFAULT '',
  archived INTEGER NOT NULL DEFAULT 0,
  fork INTEGER NOT NULL DEFAULT 0,
  pushed_at TEXT NOT NULL DEFAULT '',
  payload_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS selections (
  run_date TEXT NOT NULL,
  full_name TEXT NOT NULL,
  position INTEGER NOT NULL,
  score REAL NOT NULL DEFAULT 0,
  star_growth INTEGER NOT NULL DEFAULT 0,
  trending_rank INTEGER NOT NULL DEFAULT 0,
  category TEXT NOT NULL DEFAULT 'Other',
  sources_json TEXT NOT NULL DEFAULT '[]',
  selection_reasons_json TEXT NOT NULL DEFAULT '[]',
  security_flags_json TEXT NOT NULL DEFAULT '[]',
  payload_json TEXT NOT NULL,
  PRIMARY KEY (run_date, full_name)
);

CREATE INDEX IF NOT EXISTS idx_selections_run_date_position ON selections(run_date, position);
CREATE INDEX IF NOT EXISTS idx_selections_full_name ON selections(full_name);

CREATE TABLE IF NOT EXISTS project_corpus (
  corpus_id TEXT PRIMARY KEY,
  run_date TEXT NOT NULL DEFAULT '',
  full_name TEXT NOT NULL DEFAULT '',
  html_url TEXT NOT NULL DEFAULT '',
  title TEXT NOT NULL DEFAULT '',
  language TEXT NOT NULL DEFAULT '',
  category TEXT NOT NULL DEFAULT '',
  sources_json TEXT NOT NULL DEFAULT '[]',
  search_text TEXT NOT NULL DEFAULT '',
  corpus_version TEXT NOT NULL DEFAULT 'legacy-v0',
  cleaner_version TEXT NOT NULL DEFAULT 'legacy-v0',
  content_hash TEXT NOT NULL DEFAULT '',
  noise_json TEXT NOT NULL DEFAULT '{}',
  source_manifest_json TEXT NOT NULL DEFAULT '[]',
  payload_json TEXT NOT NULL DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_project_corpus_run_date ON project_corpus(run_date);
CREATE INDEX IF NOT EXISTS idx_project_corpus_full_name ON project_corpus(full_name);
CREATE INDEX IF NOT EXISTS idx_project_corpus_language_category ON project_corpus(language, category);

CREATE VIRTUAL TABLE IF NOT EXISTS project_corpus_fts USING fts5(
  corpus_id UNINDEXED,
  full_name,
  title,
  language,
  category,
  search_text
);

CREATE TABLE IF NOT EXISTS rag_chunks (
  chunk_id TEXT PRIMARY KEY,
  corpus_id TEXT NOT NULL DEFAULT '',
  chunk_index INTEGER NOT NULL DEFAULT 0,
  run_date TEXT NOT NULL DEFAULT '',
  full_name TEXT NOT NULL DEFAULT '',
  html_url TEXT NOT NULL DEFAULT '',
  language TEXT NOT NULL DEFAULT '',
  category TEXT NOT NULL DEFAULT '',
  sources_json TEXT NOT NULL DEFAULT '[]',
  chunk_text TEXT NOT NULL DEFAULT '',
  token_estimate INTEGER NOT NULL DEFAULT 0,
  corpus_version TEXT NOT NULL DEFAULT 'legacy-v0',
  cleaner_version TEXT NOT NULL DEFAULT 'legacy-v0',
  content_hash TEXT NOT NULL DEFAULT '',
  is_untrusted INTEGER NOT NULL DEFAULT 0,
  payload_json TEXT NOT NULL DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_rag_chunks_corpus_id ON rag_chunks(corpus_id);
CREATE INDEX IF NOT EXISTS idx_rag_chunks_run_date ON rag_chunks(run_date);
CREATE INDEX IF NOT EXISTS idx_rag_chunks_full_name ON rag_chunks(full_name);
CREATE INDEX IF NOT EXISTS idx_rag_chunks_language_category ON rag_chunks(language, category);

CREATE VIRTUAL TABLE IF NOT EXISTS rag_chunks_fts USING fts5(
  chunk_id UNINDEXED,
  full_name,
  language,
  category,
  chunk_text
);

CREATE TABLE IF NOT EXISTS rag_embeddings (
  chunk_id TEXT NOT NULL DEFAULT '',
  corpus_id TEXT NOT NULL DEFAULT '',
  run_date TEXT NOT NULL DEFAULT '',
  full_name TEXT NOT NULL DEFAULT '',
  html_url TEXT NOT NULL DEFAULT '',
  embedding_model TEXT NOT NULL DEFAULT '',
  dimensions INTEGER NOT NULL DEFAULT 0,
  vector_json TEXT NOT NULL DEFAULT '[]',
  payload_json TEXT NOT NULL DEFAULT '{}',
  updated_at TEXT NOT NULL DEFAULT '',
  PRIMARY KEY (chunk_id, embedding_model)
);

CREATE INDEX IF NOT EXISTS idx_rag_embeddings_model ON rag_embeddings(embedding_model);
CREATE INDEX IF NOT EXISTS idx_rag_embeddings_full_name ON rag_embeddings(full_name);
CREATE INDEX IF NOT EXISTS idx_rag_embeddings_run_date ON rag_embeddings(run_date);

CREATE TABLE IF NOT EXISTS rag_explanations (
  explanation_id TEXT PRIMARY KEY,
  query TEXT NOT NULL DEFAULT '',
  language TEXT NOT NULL DEFAULT '',
  category TEXT NOT NULL DEFAULT '',
  source TEXT NOT NULL DEFAULT '',
  mode TEXT NOT NULL DEFAULT '',
  model TEXT NOT NULL DEFAULT '',
  context_count INTEGER NOT NULL DEFAULT 0,
  confidence TEXT NOT NULL DEFAULT '',
  quality_score INTEGER NOT NULL DEFAULT 0,
  quality_level TEXT NOT NULL DEFAULT '',
  quality_json TEXT NOT NULL DEFAULT '{}',
  answer TEXT NOT NULL DEFAULT '',
  repositories_json TEXT NOT NULL DEFAULT '[]',
  citations_json TEXT NOT NULL DEFAULT '[]',
  explanation_json TEXT NOT NULL DEFAULT '{}',
  retrieval_json TEXT NOT NULL DEFAULT '{}',
  prompt_context TEXT NOT NULL DEFAULT '',
  payload_json TEXT NOT NULL DEFAULT '{}',
  created_at TEXT NOT NULL DEFAULT ''
);

CREATE INDEX IF NOT EXISTS idx_rag_explanations_created_at ON rag_explanations(created_at);
CREATE INDEX IF NOT EXISTS idx_rag_explanations_query ON rag_explanations(query);
CREATE INDEX IF NOT EXISTS idx_rag_explanations_confidence ON rag_explanations(confidence);
CREATE INDEX IF NOT EXISTS idx_rag_explanations_quality ON rag_explanations(quality_score, quality_level);

CREATE TABLE IF NOT EXISTS project_feedback (
  feedback_id TEXT PRIMARY KEY,
  full_name TEXT NOT NULL DEFAULT '',
  profile TEXT NOT NULL DEFAULT '',
  rating INTEGER NOT NULL DEFAULT 0,
  labels_json TEXT NOT NULL DEFAULT '[]',
  note TEXT NOT NULL DEFAULT '',
  source TEXT NOT NULL DEFAULT '',
  created_at TEXT NOT NULL DEFAULT '',
  updated_at TEXT NOT NULL DEFAULT '',
  payload_json TEXT NOT NULL DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_project_feedback_full_name_updated_at ON project_feedback(full_name, updated_at);
CREATE INDEX IF NOT EXISTS idx_project_feedback_profile_updated_at ON project_feedback(profile, updated_at);
CREATE INDEX IF NOT EXISTS idx_project_feedback_rating_updated_at ON project_feedback(rating, updated_at);

CREATE TABLE IF NOT EXISTS project_agent_tasks (
  task_id TEXT PRIMARY KEY,
  full_name TEXT NOT NULL DEFAULT '',
  profile TEXT NOT NULL DEFAULT '',
  task_type TEXT NOT NULL DEFAULT 'observe',
  priority INTEGER NOT NULL DEFAULT 3,
  status TEXT NOT NULL DEFAULT 'planned',
  reason TEXT NOT NULL DEFAULT '',
  result_summary TEXT NOT NULL DEFAULT '',
  source TEXT NOT NULL DEFAULT '',
  dedupe_key TEXT NOT NULL DEFAULT '',
  created_at TEXT NOT NULL DEFAULT '',
  updated_at TEXT NOT NULL DEFAULT '',
  started_at TEXT NOT NULL DEFAULT '',
  finished_at TEXT NOT NULL DEFAULT '',
  payload_json TEXT NOT NULL DEFAULT '{}'
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_project_agent_tasks_dedupe_key ON project_agent_tasks(dedupe_key) WHERE dedupe_key <> '';
CREATE INDEX IF NOT EXISTS idx_project_agent_tasks_full_name_updated_at ON project_agent_tasks(full_name, updated_at);
CREATE INDEX IF NOT EXISTS idx_project_agent_tasks_status_priority ON project_agent_tasks(status, priority, updated_at);
CREATE INDEX IF NOT EXISTS idx_project_agent_tasks_profile_updated_at ON project_agent_tasks(profile, updated_at);

CREATE TABLE IF NOT EXISTS project_agent_task_runs (
  run_id TEXT PRIMARY KEY,
  task_id TEXT NOT NULL DEFAULT '',
  status TEXT NOT NULL DEFAULT 'running',
  started_at TEXT NOT NULL DEFAULT '',
  finished_at TEXT NOT NULL DEFAULT '',
  input_json TEXT NOT NULL DEFAULT '{}',
  evidence_json TEXT NOT NULL DEFAULT '[]',
  citations_json TEXT NOT NULL DEFAULT '[]',
  result_json TEXT NOT NULL DEFAULT '{}',
  error TEXT NOT NULL DEFAULT '',
  payload_json TEXT NOT NULL DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_project_agent_task_runs_task_started_at ON project_agent_task_runs(task_id, started_at);
CREATE INDEX IF NOT EXISTS idx_project_agent_task_runs_status_started_at ON project_agent_task_runs(status, started_at);

CREATE TABLE IF NOT EXISTS dev_runs (
  run_id TEXT PRIMARY KEY,
  status TEXT NOT NULL DEFAULT '',
  started_at TEXT NOT NULL DEFAULT '',
  finished_at TEXT NOT NULL DEFAULT '',
  source_count INTEGER NOT NULL DEFAULT 0,
  chunk_count INTEGER NOT NULL DEFAULT 0,
  embedding_count INTEGER NOT NULL DEFAULT 0,
  command_count INTEGER NOT NULL DEFAULT 0,
  error TEXT NOT NULL DEFAULT '',
  payload_json TEXT NOT NULL DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_dev_runs_started_at ON dev_runs(started_at);
CREATE INDEX IF NOT EXISTS idx_dev_runs_status ON dev_runs(status);

CREATE TABLE IF NOT EXISTS dev_corpus (
  corpus_id TEXT PRIMARY KEY,
  run_id TEXT NOT NULL DEFAULT '',
  source_type TEXT NOT NULL DEFAULT '',
  source_path TEXT NOT NULL DEFAULT '',
  title TEXT NOT NULL DEFAULT '',
  content_hash TEXT NOT NULL DEFAULT '',
  content_text TEXT NOT NULL DEFAULT '',
  metadata_json TEXT NOT NULL DEFAULT '{}',
  created_at TEXT NOT NULL DEFAULT ''
);

CREATE INDEX IF NOT EXISTS idx_dev_corpus_run_id ON dev_corpus(run_id);
CREATE INDEX IF NOT EXISTS idx_dev_corpus_source_type ON dev_corpus(source_type);
CREATE INDEX IF NOT EXISTS idx_dev_corpus_source_path ON dev_corpus(source_path);

CREATE TABLE IF NOT EXISTS dev_chunks (
  chunk_id TEXT PRIMARY KEY,
  corpus_id TEXT NOT NULL DEFAULT '',
  run_id TEXT NOT NULL DEFAULT '',
  chunk_index INTEGER NOT NULL DEFAULT 0,
  source_type TEXT NOT NULL DEFAULT '',
  source_path TEXT NOT NULL DEFAULT '',
  title TEXT NOT NULL DEFAULT '',
  chunk_text TEXT NOT NULL DEFAULT '',
  token_estimate INTEGER NOT NULL DEFAULT 0,
  metadata_json TEXT NOT NULL DEFAULT '{}',
  created_at TEXT NOT NULL DEFAULT ''
);

CREATE INDEX IF NOT EXISTS idx_dev_chunks_corpus_id ON dev_chunks(corpus_id);
CREATE INDEX IF NOT EXISTS idx_dev_chunks_run_id ON dev_chunks(run_id);
CREATE INDEX IF NOT EXISTS idx_dev_chunks_source_type ON dev_chunks(source_type);

CREATE VIRTUAL TABLE IF NOT EXISTS dev_chunks_fts USING fts5(
  chunk_id UNINDEXED,
  source_type,
  source_path,
  title,
  chunk_text
);

CREATE TABLE IF NOT EXISTS dev_embeddings (
  chunk_id TEXT NOT NULL DEFAULT '',
  corpus_id TEXT NOT NULL DEFAULT '',
  run_id TEXT NOT NULL DEFAULT '',
  source_type TEXT NOT NULL DEFAULT '',
  source_path TEXT NOT NULL DEFAULT '',
  embedding_model TEXT NOT NULL DEFAULT '',
  dimensions INTEGER NOT NULL DEFAULT 0,
  vector_json TEXT NOT NULL DEFAULT '[]',
  metadata_json TEXT NOT NULL DEFAULT '{}',
  updated_at TEXT NOT NULL DEFAULT '',
  PRIMARY KEY (chunk_id, embedding_model)
);

CREATE INDEX IF NOT EXISTS idx_dev_embeddings_model ON dev_embeddings(embedding_model);
CREATE INDEX IF NOT EXISTS idx_dev_embeddings_run_id ON dev_embeddings(run_id);
CREATE INDEX IF NOT EXISTS idx_dev_embeddings_source_type ON dev_embeddings(source_type);

CREATE TABLE IF NOT EXISTS trend_summaries (
  run_date TEXT PRIMARY KEY,
  total_projects INTEGER NOT NULL DEFAULT 0,
  trending_project_count INTEGER NOT NULL DEFAULT 0,
  total_star_growth INTEGER NOT NULL DEFAULT 0,
  payload_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sent_repositories (
  full_name TEXT PRIMARY KEY,
  html_url TEXT NOT NULL DEFAULT '',
  first_sent_at TEXT NOT NULL DEFAULT '',
  payload_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS star_history (
  full_name TEXT PRIMARY KEY,
  html_url TEXT NOT NULL DEFAULT '',
  stargazers_count INTEGER NOT NULL DEFAULT 0,
  last_seen_at TEXT NOT NULL DEFAULT '',
  payload_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS jobs (
  job_id TEXT PRIMARY KEY,
  kind TEXT NOT NULL DEFAULT '',
  status TEXT NOT NULL DEFAULT '',
  run_date TEXT NOT NULL DEFAULT '',
  submitted_at TEXT NOT NULL DEFAULT '',
  started_at TEXT NOT NULL DEFAULT '',
  finished_at TEXT NOT NULL DEFAULT '',
  request_json TEXT NOT NULL DEFAULT '{}',
  result_json TEXT NOT NULL DEFAULT '{}',
  error TEXT NOT NULL DEFAULT '',
  payload_json TEXT NOT NULL DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_jobs_status_submitted_at ON jobs(status, submitted_at);
CREATE INDEX IF NOT EXISTS idx_jobs_run_date ON jobs(run_date);

CREATE TABLE IF NOT EXISTS job_events (
  event_id TEXT PRIMARY KEY,
  job_id TEXT NOT NULL DEFAULT '',
  event_type TEXT NOT NULL DEFAULT '',
  status TEXT NOT NULL DEFAULT '',
  actor TEXT NOT NULL DEFAULT '',
  created_at TEXT NOT NULL DEFAULT '',
  message TEXT NOT NULL DEFAULT '',
  payload_json TEXT NOT NULL DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_job_events_job_id_created_at ON job_events(job_id, created_at);
CREATE INDEX IF NOT EXISTS idx_job_events_type_created_at ON job_events(event_type, created_at);

CREATE TABLE IF NOT EXISTS subscriptions (
  subscription_id TEXT PRIMARY KEY,
  name TEXT NOT NULL DEFAULT '',
  status TEXT NOT NULL DEFAULT 'enabled',
  profile TEXT NOT NULL DEFAULT '',
  language TEXT NOT NULL DEFAULT '',
  category TEXT NOT NULL DEFAULT '',
  query TEXT NOT NULL DEFAULT '',
  sort TEXT NOT NULL DEFAULT 'score',
  limit_count INTEGER NOT NULL DEFAULT 20,
  channels_json TEXT NOT NULL DEFAULT '[]',
  created_at TEXT NOT NULL DEFAULT '',
  updated_at TEXT NOT NULL DEFAULT '',
  payload_json TEXT NOT NULL DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_subscriptions_status_updated_at ON subscriptions(status, updated_at);
CREATE INDEX IF NOT EXISTS idx_subscriptions_profile_language ON subscriptions(profile, language);

CREATE TABLE IF NOT EXISTS subscription_events (
  event_id TEXT PRIMARY KEY,
  event_type TEXT NOT NULL DEFAULT '',
  full_name TEXT NOT NULL DEFAULT '',
  source_run_id TEXT NOT NULL DEFAULT '',
  severity TEXT NOT NULL DEFAULT 'info',
  status TEXT NOT NULL DEFAULT 'detected',
  title TEXT NOT NULL DEFAULT '',
  summary TEXT NOT NULL DEFAULT '',
  evidence_json TEXT NOT NULL DEFAULT '[]',
  citations_json TEXT NOT NULL DEFAULT '[]',
  dedupe_key TEXT NOT NULL DEFAULT '',
  detected_at TEXT NOT NULL DEFAULT '',
  updated_at TEXT NOT NULL DEFAULT '',
  payload_json TEXT NOT NULL DEFAULT '{}'
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_subscription_events_dedupe_key ON subscription_events(dedupe_key) WHERE dedupe_key <> '';
CREATE INDEX IF NOT EXISTS idx_subscription_events_full_name_detected_at ON subscription_events(full_name, detected_at);
CREATE INDEX IF NOT EXISTS idx_subscription_events_type_severity ON subscription_events(event_type, severity, detected_at);
CREATE INDEX IF NOT EXISTS idx_subscription_events_status_detected_at ON subscription_events(status, detected_at);

CREATE TABLE IF NOT EXISTS notification_candidates (
  candidate_id TEXT PRIMARY KEY,
  subscription_id TEXT NOT NULL DEFAULT '',
  event_id TEXT NOT NULL DEFAULT '',
  full_name TEXT NOT NULL DEFAULT '',
  status TEXT NOT NULL DEFAULT 'pending',
  channels_json TEXT NOT NULL DEFAULT '[]',
  title TEXT NOT NULL DEFAULT '',
  message TEXT NOT NULL DEFAULT '',
  dedupe_key TEXT NOT NULL DEFAULT '',
  created_at TEXT NOT NULL DEFAULT '',
  updated_at TEXT NOT NULL DEFAULT '',
  payload_json TEXT NOT NULL DEFAULT '{}'
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_notification_candidates_dedupe_key ON notification_candidates(dedupe_key) WHERE dedupe_key <> '';
CREATE INDEX IF NOT EXISTS idx_notification_candidates_status_created_at ON notification_candidates(status, created_at);
CREATE INDEX IF NOT EXISTS idx_notification_candidates_subscription_created_at ON notification_candidates(subscription_id, created_at);
CREATE INDEX IF NOT EXISTS idx_notification_candidates_event_id ON notification_candidates(event_id);

CREATE TABLE IF NOT EXISTS notification_deliveries (
  delivery_id TEXT PRIMARY KEY,
  candidate_id TEXT NOT NULL DEFAULT '',
  subscription_id TEXT NOT NULL DEFAULT '',
  event_id TEXT NOT NULL DEFAULT '',
  channel TEXT NOT NULL DEFAULT '',
  status TEXT NOT NULL DEFAULT 'planned',
  attempt_count INTEGER NOT NULL DEFAULT 0,
  started_at TEXT NOT NULL DEFAULT '',
  finished_at TEXT NOT NULL DEFAULT '',
  error TEXT NOT NULL DEFAULT '',
  response_json TEXT NOT NULL DEFAULT '{}',
  dedupe_key TEXT NOT NULL DEFAULT '',
  payload_json TEXT NOT NULL DEFAULT '{}'
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_notification_deliveries_dedupe_key ON notification_deliveries(dedupe_key) WHERE dedupe_key <> '';
CREATE INDEX IF NOT EXISTS idx_notification_deliveries_candidate_channel ON notification_deliveries(candidate_id, channel);
CREATE INDEX IF NOT EXISTS idx_notification_deliveries_status_finished_at ON notification_deliveries(status, finished_at);
CREATE INDEX IF NOT EXISTS idx_notification_deliveries_subscription_event ON notification_deliveries(subscription_id, event_id);

CREATE TABLE IF NOT EXISTS migration_meta (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
);
