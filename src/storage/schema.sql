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

CREATE TABLE IF NOT EXISTS migration_meta (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
);
