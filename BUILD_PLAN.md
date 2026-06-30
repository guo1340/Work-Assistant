# BUILD PLAN

Build order and MVP milestones for **DevFlow Assistant**. Read alongside
`ARCHITECTURE.md` (design), `SCHEMA.md` (data contracts), `AGENTS.md` (agent
contracts), and `DECISIONS.md` (accepted ADRs).

**Stack:** Python + FastAPI engine, SQLite state store, React + TypeScript
frontend (Vite + Tailwind) built with **Impeccable**
(github.com/pbakaus/impeccable) for design quality. Build the whole pipeline
against a **mock provider**; wire real CLIs last (ADR-021).

**Golden rule of ordering:** the deterministic core (engine, schema, scanner)
comes before any LLM wiring, and real model CLIs come last.

---

## Phase 0 — Skeleton & Scaffolding

Goal: a runnable empty app.

- Repo layout: `engine/` (Python), `frontend/` (React+TS), `prompts/`, root
  Markdown KB.
- Python venv, FastAPI app with a health endpoint, config loader.
- SQLite initialized from `SCHEMA.md` (all tables + indexes).
- Vite + React + TypeScript + Tailwind frontend that calls the health endpoint.

**Done when:** frontend loads and confirms it can reach the engine; DB file is
created with the full schema.

## Phase 1 — Workflow Engine Core (deterministic)

Goal: the heart of the system, with no LLMs yet.

- Engine state machine (states per `ARCHITECTURE.md` §3).
- Stage scheduler (advance a request only on a committed Stage Result).
- State store: persist requests/tasks/stage_results in SQLite.
- Immutable `execution_history` run log.
- Approval-gate mechanism (pause → `AWAITING_APPROVAL` → resume/reject).
- Retry with backoff + escalation to `FAILED`.

**Done when:** a request can be driven through dummy stages end-to-end, with
history, gates, and retries all observable in SQLite.

## Phase 2 — Provider Abstraction + Mock

Goal: pluggable providers without real models.

- `Provider` interface (id, tier, capabilities, invoke) per `ARCHITECTURE.md` §8.
- Provider registry + tier enforcement.
- **Mock provider** returning canned Stage Results (shapes per `SCHEMA.md` §2).

**Done when:** the engine runs stages through the mock provider and commits
valid Stage Results.

## Phase 3 — Markdown KB + Project Scanner

Goal: project understanding and persistent memory.

- Markdown read/write layer for the KB files.
- Project registration → `projects` row + `project_id`.
- **Soft Scan**: read existing `*.md` to understand a project.
- **Hard Scan**: deterministic repo walk (files, languages, Git history) → LLM
  synthesis → create/update `*.md` (non-destructive).

**Done when:** adding a project soft-scans it; the Scan button hard-scans an
undocumented repo and produces the Markdown KB.

## Phase 4 — Agents (against mock provider)

Goal: the full pipeline as stages.

- Request Logger → Planner → Traceability Check (deterministic) → Repository
  Analyzer → Builder → Documentation → Tester → Reviewer → Final Report.
- Each agent reads/writes the right KB files and returns a Stage Result.

**Done when:** a request flows the whole pipeline on the mock provider and
updates `REQUESTS.md`, `TASKS.md`, `LOGS.md`, `TEST_LOGS.md`, `TRACEABILITY.md`.

## Phase 5 — Risk & Git Safety

Goal: the safety model.

- Risk-rule engine (`SCHEMA.md` §3); `max(agent_risk, rule_risk)`; 400-line
  large-diff threshold.
- Git branch-per-request (`devflow/REQ-XXXX`), commit SHA in history.
- Approval gates triggered by high risk / category / low confidence.

**Done when:** high-risk mock work halts at a gate; Builder commits to a request
branch; rejection rolls back cleanly.

## Phase 6 — Frontend (built with Impeccable)

Goal: the user-facing app, developed with Impeccable enabled for design quality.

- Project selector + Scan button (soft default, hard on demand).
- Request input.
- Per-stage model selection (tier-filtered; defaults per ADR-009).
- Live pipeline / stage view.
- Approval prompt UI.
- Final report view.

**Done when:** a user can add/scan a project, submit a request, watch the
pipeline, approve gates, and read the report — all polished and responsive, and
the UI passes Impeccable's audit.

## Phase 7 — Final Steps Before Live Testing (ADR-021)

Goal: swap the mock for real models.

- Codex CLI provider (subprocess wrapper).
- Claude Code CLI provider.
- Cursor free tier (translation / Planner).
- Tester language adapters in priority order: **TypeScript/JS → Java → Python**.

**Done when:** real providers are selectable and produce valid Stage Results.

## Phase 8 — Live Testing

Goal: prove it on a real project.

- End-to-end run on a real repo with a real request.
- Verify traceability: original request → tasks → diff → tests → review.
- Tune risk rules and prompts from observed behavior.

**Done when:** a real request is implemented, tested, reviewed, and fully
traceable, with gates firing appropriately.

---

## MVP Definition

The MVP is **Phases 0–8 for a single project, one request at a time**, with
Codex + Claude Code as real providers and the TypeScript test adapter working.
Parallel requests, additional providers, plugin loading, and CI integration are
explicitly post-MVP (`TASKS.md` → Future).
