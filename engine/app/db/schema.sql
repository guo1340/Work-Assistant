-- Accepted schema from SCHEMA.md (ADR-012).
CREATE TABLE IF NOT EXISTS projects (
    id              INTEGER PRIMARY KEY,
    name            TEXT NOT NULL,
    root_path       TEXT NOT NULL,
    summary         TEXT,
    languages       TEXT,
    scan_type       TEXT,
    last_scanned_at TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS requests (
    request_id              TEXT PRIMARY KEY,
    project_id              INTEGER NOT NULL REFERENCES projects(id),
    original_text           TEXT NOT NULL,
    planner_interpretation  TEXT,
    state                   TEXT NOT NULL,
    created_at              TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS tasks (
    task_id             TEXT PRIMARY KEY,
    request_id          TEXT NOT NULL REFERENCES requests(request_id),
    description         TEXT NOT NULL,
    priority            TEXT NOT NULL,
    acceptance_criteria TEXT,
    dependencies        TEXT,
    estimated_files     TEXT,
    status              TEXT NOT NULL DEFAULT 'Pending'
);

CREATE TABLE IF NOT EXISTS stage_results (
    id                     INTEGER PRIMARY KEY,
    request_id             TEXT NOT NULL REFERENCES requests(request_id),
    task_id                TEXT REFERENCES tasks(task_id),
    stage                  TEXT NOT NULL,
    output                 TEXT,
    model_used             TEXT,
    confidence             REAL,
    risk_level             TEXT,
    missing_information    TEXT,
    human_review_required  INTEGER NOT NULL DEFAULT 0,
    status                 TEXT NOT NULL,
    error                  TEXT,
    started_at             TEXT,
    finished_at            TEXT,
    duration_ms            INTEGER
);

CREATE TABLE IF NOT EXISTS execution_history (
    id          INTEGER PRIMARY KEY,
    request_id  TEXT NOT NULL REFERENCES requests(request_id),
    stage       TEXT,
    from_state  TEXT,
    to_state    TEXT,
    event       TEXT NOT NULL,
    detail      TEXT,
    git_sha     TEXT,
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS approvals (
    id          INTEGER PRIMARY KEY,
    request_id  TEXT NOT NULL REFERENCES requests(request_id),
    stage       TEXT NOT NULL,
    status      TEXT NOT NULL DEFAULT 'pending',
    reason      TEXT,
    decided_by  TEXT,
    decided_at  TEXT,
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_requests_project_state ON requests(project_id, state);
CREATE INDEX IF NOT EXISTS idx_tasks_request          ON tasks(request_id);
CREATE INDEX IF NOT EXISTS idx_stage_results_request  ON stage_results(request_id);
CREATE INDEX IF NOT EXISTS idx_history_request_time   ON execution_history(request_id, created_at);
CREATE INDEX IF NOT EXISTS idx_approvals_request      ON approvals(request_id, status);
