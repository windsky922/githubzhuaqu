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

CREATE TABLE IF NOT EXISTS migration_meta (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
);
