# SCHEMA

Concrete data contracts for **DevFlow Assistant**: the SQLite state store, the
Stage Result wire format, and the v1 risk-classification rules. Status: **Accepted** (see `DECISIONS.md` ADR-012,
ADR-013). This is the engine's internal index; Markdown files remain the
human-readable memory.

---

## 1. SQLite Schema (DDL)

```sql
-- Projects --------------------------------------------------------------
CREATE TABLE projects (
    id              INTEGER PRIMARY KEY,
    name            TEXT NOT NULL,
    root_path       TEXT NOT NULL,      -- local repo path
    summary         TEXT,               -- LLM understanding from last scan
    languages       TEXT,               -- JSON: detected langs/frameworks
    scan_type       TEXT,               -- soft | hard
    last_scanned_at TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Requests (1 project : many requests) ----------------------------------
CREATE TABLE requests (
    request_id              TEXT PRIMARY KEY,   -- REQ-2026-0001
    project_id              INTEGER NOT NULL REFERENCES projects(id),
    original_text           TEXT NOT NULL,      -- verbatim, never edited
    planner_interpretation  TEXT,
    state                   TEXT NOT NULL,      -- engine state machine
    created_at              TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Tasks (1 request : many tasks) ----------------------------------------
CREATE TABLE tasks (
    task_id             TEXT PRIMARY KEY,        -- TASK-0001-01
    request_id          TEXT NOT NULL REFERENCES requests(request_id),
    description         TEXT NOT NULL,
    priority            TEXT NOT NULL,           -- High | Medium | Low
    acceptance_criteria TEXT,                    -- JSON array of strings
    dependencies        TEXT,                    -- JSON array of task_ids
    estimated_files     TEXT,                    -- JSON array of paths
    status              TEXT NOT NULL DEFAULT 'Pending'
);

-- Stage results (every agent run) ---------------------------------------
CREATE TABLE stage_results (
    id                     INTEGER PRIMARY KEY,
    request_id             TEXT NOT NULL REFERENCES requests(request_id),
    task_id                TEXT REFERENCES tasks(task_id),  -- nullable
    stage                  TEXT NOT NULL,        -- planner | builder | ...
    output                 TEXT,                 -- JSON payload (free-form)
    model_used             TEXT,
    confidence             REAL,                 -- 0.0 - 1.0
    risk_level             TEXT,                 -- low | medium | high
    missing_information    TEXT,                 -- JSON array of strings
    human_review_required  INTEGER NOT NULL DEFAULT 0,  -- boolean
    status                 TEXT NOT NULL,        -- success | failed
    error                  TEXT,
    started_at             TEXT,
    finished_at            TEXT,
    duration_ms            INTEGER
);

-- Execution history (immutable, append-only run log) --------------------
CREATE TABLE execution_history (
    id          INTEGER PRIMARY KEY,
    request_id  TEXT NOT NULL REFERENCES requests(request_id),
    stage       TEXT,
    from_state  TEXT,
    to_state    TEXT,
    event       TEXT NOT NULL,          -- STAGE_STARTED | COMMITTED | RETRY | ...
    detail      TEXT,                   -- JSON
    git_sha     TEXT,                   -- commit pointer when relevant
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Approval gates --------------------------------------------------------
CREATE TABLE approvals (
    id          INTEGER PRIMARY KEY,
    request_id  TEXT NOT NULL REFERENCES requests(request_id),
    stage       TEXT NOT NULL,
    status      TEXT NOT NULL DEFAULT 'pending',  -- pending | approved | rejected
    reason      TEXT,                   -- why the gate fired
    decided_by  TEXT,
    decided_at  TEXT,
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Indexes ---------------------------------------------------------------
CREATE INDEX idx_requests_project_state ON requests(project_id, state);
CREATE INDEX idx_tasks_request          ON tasks(request_id);
CREATE INDEX idx_stage_results_request  ON stage_results(request_id);
CREATE INDEX idx_history_request_time   ON execution_history(request_id, created_at);
CREATE INDEX idx_approvals_request      ON approvals(request_id, status);
```

**JSON boundary rule:** columns are relational where you query/filter on them
(ids, state, status, risk, confidence) and JSON where the content is free-form
and only read whole (`output`, `acceptance_criteria`, `missing_information`,
`dependencies`, `estimated_files`).

---

## 2. Stage Result Contract

Every agent returns this object to the engine. The engine adds the envelope
fields (`status`, `error`, timing) on commit.

```jsonc
{
  // --- produced by the agent ---
  "stage": "builder",                 // planner | repo_analyzer | builder | tester | reviewer | documentation | request_logger
  "request_id": "REQ-2026-0001",
  "task_id": "TASK-0001-01",          // null for request-level stages
  "output": { /* stage-specific payload */ },
  "model_used": "claude-code",
  "confidence": 0.82,                 // 0.0 - 1.0
  "risk_level": "medium",             // low | medium | high
  "missing_information": [],          // array of strings
  "human_review_required": false,

  // --- added by the engine on commit ---
  "status": "success",               // success | failed
  "error": null,
  "started_at": "2026-06-30T14:05:00Z",
  "finished_at": "2026-06-30T14:06:12Z",
  "duration_ms": 72000
}
```

Per-stage `output` shapes (informal):

- **planner** → `{ "tasks": [Task, ...] }`
- **repo_analyzer** → `{ "context_files": [...], "git_diff": "...", "notes": "..." }`
- **builder** → `{ "git_sha": "...", "files_changed": [...], "diff_summary": "..." }`
- **tester** → `{ "passed": 11, "failed": 1, "coverage": 0.74, "regressions": [] }`
- **reviewer** → `{ "missing": [...], "invented": [...], "scope_creep": [...], "verdict": "..." }`

**Risk resolution:** the engine takes `max(agent.risk_level, rule_based_risk)`
(see §3) so an agent under-reporting risk cannot bypass a gate.

---

## 3. Risk-Classification Rules (v1)

Deterministic rules the engine runs on each stage's planned work. Output is the
**rule-based risk**, OR-combined with the agent's self-reported risk.

**HIGH (always gate):**

- Path matches: `migrations/`, `auth`, `login`, `session`, `payment`, `billing`,
  `secrets`, `.env`, `Dockerfile`, `deploy`, `.github/workflows/`
- Any file **deletion** in the diff
- Diff contains: `DROP TABLE`, `DELETE FROM`, `ALTER TABLE`, `rm -rf`,
  `private_key`, `credential`, `SECRET`

**MEDIUM:**

- New dependency added (changes to `package.json`, `requirements.txt`,
  `pyproject.toml`, `go.mod`, etc.)
- Config-file changes outside the above high-risk set
- Diff larger than a configurable line threshold (**default: > 400 changed
  lines**; tunable in config)

**LOW:** everything else.

The list is intentionally a starting point — expand patterns as real requests
surface new categories. Patterns live in engine config, not code, so they can be
tuned without a rebuild.
