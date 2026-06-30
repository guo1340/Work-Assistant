# Phases 3–6 — Scanning, agents, safety, and application UI

## Phase 3

- Engine-owned Markdown knowledge-base layer with non-destructive merge behavior
- Soft scan of existing Markdown documents
- Deterministic hard scan of repository files, languages, frameworks, branch,
  and recent commits
- Provider-backed synthesis through the mock provider
- Project registration and scan metadata persisted in SQLite

## Phase 4

- Engine-owned agent-result committer
- Request Logger, Planner, Repository Analyzer, Builder, Documentation, Tester,
  Reviewer, and Final Report outputs
- Deterministic traceability check before analysis/build work
- Verbatim request capture plus updates to `REQUESTS.md`, `TASKS.md`, `LOGS.md`,
  `TEST_LOGS.md`, and `TRACEABILITY.md`

## Phase 5

- Config-driven deterministic risk rules from `SCHEMA.md`
- Effective risk is `max(agent risk, rule risk)`
- High-risk, human-review, and low-confidence approval gates
- Request branches named `devflow/REQ-XXXX`
- Builder commit SHA recorded in immutable execution history
- Rejection returns to the base branch and deletes the request branch

## Phase 6

- Local FastAPI endpoints for projects, scans, requests, pipeline advancement,
  approvals, provider options, and final reports
- Responsive React workspace with project selection, scan actions, request
  capture, stage timeline, evidence tabs, approval controls, and reports
- Impeccable design system, critique snapshot, deterministic audit, and live
  browser verification

## Run

Use the Phase 0 setup, then start both processes:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir engine --reload
npm.cmd --prefix frontend run dev
```

Open `http://127.0.0.1:5173`.

## Verify

```powershell
.\.venv\Scripts\python.exe -m pytest engine/tests
npm.cmd --prefix frontend run lint
npm.cmd --prefix frontend run build
node .agents/skills/impeccable/scripts/detect.mjs --json frontend/src/App.tsx frontend/index.html
```
