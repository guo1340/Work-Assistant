# ARCHITECTURE

System architecture for **DevFlow Assistant** — a local-first AI software
engineering workflow orchestrator. This document is the technical source of
truth. Agent responsibilities live in `AGENTS.md`; decisions are recorded in
`DECISIONS.md`.

---

## 1. Guiding Principles

1. **Single Responsibility** — every agent does exactly one job.
2. **Local First** — Git, Markdown, local DB, and local CLIs (Codex, Claude
   Code) are the default. No cloud unless the user opts in.
3. **LLM Agnostic** — every layer talks to a provider interface, never a
   specific model. Model choice is constrained by task tier (see §7).
4. **Engine-Centric** — agents never call each other. The Workflow Engine is
   the only coordinator (see §3).
5. **Traceability First** — every request is preserved verbatim and traceable
   end-to-end (see `TRACEABILITY.md`).
6. **Markdown as Memory** — project state persists in Markdown files, not in
   conversation history.

---

## 1a. Technology Stack

| Layer        | Technology                                              |
|--------------|---------------------------------------------------------|
| Engine/backend | **Python** + FastAPI (local HTTP API)                 |
| State store  | **SQLite** (stdlib or SQLModel/SQLAlchemy)              |
| Frontend     | **React + TypeScript** (Vite + Tailwind) + **Impeccable** (design quality) |
| Providers    | Codex CLI, Claude Code CLI, Cursor — wrapped as subprocesses |

Python is chosen for the engine because it has the strongest ecosystem for
multi-LLM orchestration and CLI subprocess control (ADR-022).

### Frontend Design Standard

The frontend is built with **Impeccable** (github.com/pbakaus/impeccable), a
design tool/skill that integrates with our builder (Codex CLI / Claude Code) and
provides a shared design vocabulary plus deterministic detector rules to avoid
generic "AI slop" (ADR-023). Design quality is a first-class requirement — every
screen is audited against Impeccable's rules and anti-patterns before it is
considered done.

## 2. High-Level Component Map

```
+-----------------------------------------------------------+
|                      Frontend (React)                     |
|  Project selector · Request input · Per-stage model picks |
|  Live pipeline view · Approval prompts · Final report     |
+-----------------------------+-----------------------------+
                              | (API / IPC)
+-----------------------------v-----------------------------+
|                      WORKFLOW ENGINE                      |
|  Owns project state · Schedules stages · Enforces gates  |
|  Retries failures · Records execution history            |
+----+-----------+-----------+-----------+-----------+------+
     |           |           |           |           |
+----v---+  +----v----+ +----v----+ +----v----+ +----v----+
| Request|  | Planner | | Repo    | | Builder | | Tester  |  ... etc.
| Logger |  |         | | Analyzer| |         | |         |
+--------+  +---------+ +---------+ +---------+ +---------+
     (stateless agents — workers invoked by the engine only)
                              |
+-----------------------------v-----------------------------+
|              Provider Abstraction Layer                   |
|  Codex · Claude Code · Cursor · Gemini · OpenRouter · ... |
+-----------------------------+-----------------------------+
                              |
+-----------------------------v-----------------------------+
|   Local Substrate: Git repo · Markdown KB · Local DB      |
+-----------------------------------------------------------+
```

---

## 3. The Workflow Engine (Heart of the System)

Agents are **stateless workers**. They receive a context package, do one job,
and return a structured result. They have no knowledge of each other. The
Workflow Engine is the single component that coordinates everything.

### Responsibilities

- **State ownership** — the engine holds the authoritative state of every
  request and the project. Agents never mutate shared state directly; they
  return results and the engine commits them (including writes to the Markdown
  knowledge base).
- **Scheduling** — the engine decides which stage runs next based on the
  pipeline definition and the current request state.
- **Approval gates** — before any stage flagged high-risk, the engine halts and
  waits for human approval (see §6).
- **Retries** — failed stages are retried with backoff up to a configurable
  limit, then escalated to the user.
- **Execution history** — every stage transition, input, output, model used,
  duration, and result is appended to an immutable run log.

### Why decouple agents

Routing all communication through the engine means a new provider, a new stage,
or a reordered pipeline is a change to engine configuration — not a rewrite of
agent-to-agent wiring. This is what keeps the system provider-agnostic and
extensible.

### Engine State Machine

Each request moves through these states:

```
RECEIVED → LOGGED → PLANNING → PLANNED → ANALYZING → ANALYZED
   → BUILDING → BUILT → DOCUMENTING → TESTING → TESTED
   → REVIEWING → REVIEWED → REPORTED → DONE

Cross-cutting states (can occur from most stages):
   AWAITING_APPROVAL  (gate hit; paused for human)
   RETRYING           (stage failed; engine re-attempting)
   FAILED             (retries exhausted; escalated to user)
   REJECTED           (human declined an approval gate)
```

A request only advances when the engine commits the previous stage's result.
`AWAITING_APPROVAL` and `FAILED` are terminal until a human acts.

### Designed Direction (for implementation)

The engine is **deterministic code, never an LLM** (ADR-011). Orchestration —
state, scheduling, gates, retries, history — is a state machine. Fuzzy judgments
(risk classification, file relevance) begin as **deterministic rules**
(keyword/path matching, Git-diff heuristics). Only if rules prove too blunt may
the engine delegate *one narrow judgment* to a Light-tier model — never the
orchestration, scheduling, or gate decisions. Intelligence lives in the agents.

### Concurrency

The current build processes **one request at a time** (sequential) to avoid Git
working-tree conflicts and concurrent Markdown writes (ADR-010). All state is
keyed by `request_id` and the engine interface is concurrency-agnostic, so a
per-project / per-branch worker pool can be added later without redesign.

---

## 4. Pipeline (Canonical Stage Order)

```
Client Request
   ↓
Request Logger        → writes REQUESTS.md (verbatim, immutable)
   ↓
Planner               → writes TASKS.md, planner interpretation
   ↓
Traceability Check    → engine verifies tasks map to request
   ↓
Repository Analyzer   → builds minimal relevant context package
   ↓
Builder               → implements tasks (Codex / Claude Code)
   ↓
Documentation Agent   → writes LOGS.md, updates PROJECT_NOTES.md
   ↓
Tester                → generates + runs tests, writes TEST_LOGS.md
   ↓
Reviewer              → audits request vs tasks vs diff vs tests
   ↓
Final Report          → engine assembles, updates TRACEABILITY.md
```

> Naming note: the "Documentation Agent" and "Logger" are the same role.
> Canonical name is **Documentation Agent**; `LOGS.md` is its primary output.

The **Traceability Check** is an engine-owned verification step, not an LLM
agent. It runs deterministic checks (every task references a Request ID; no
orphan tasks) before expensive build work begins.

---

## 5. Data Model

State persists in **SQLite** (engine's internal index/state store; ADR-007),
with free-form stage `output` payloads stored as JSON columns. Markdown files
remain the human-readable shared memory (§11). The tables below map to the
core entities.

### Request

| Field            | Description                                       |
|------------------|---------------------------------------------------|
| `request_id`     | Unique ID, e.g. `REQ-2026-0042`                   |
| `original_text`  | Verbatim client/manager request, never overwritten|
| `planner_interpretation` | Planner's restatement of intent           |
| `task_ids`       | Tasks generated from this request                 |
| `state`          | Current engine state (see §3)                     |
| `created_at`     | Timestamp                                         |

### Task

| Field               | Description                                    |
|---------------------|------------------------------------------------|
| `task_id`           | Unique ID, e.g. `TASK-0042-01`                 |
| `request_id`        | Parent request (traceability link)             |
| `description`       | What to do                                     |
| `priority`          | High / Medium / Low                            |
| `acceptance_criteria` | Verifiable conditions for "done"             |
| `dependencies`      | Other task IDs                                 |
| `estimated_files`   | Files likely to change                         |
| `status`            | Pending / In Progress / Done / Blocked         |

### Stage Result (returned by every agent)

| Field                  | Description                                 |
|------------------------|---------------------------------------------|
| `stage`                | Which stage produced this                   |
| `request_id`           | Owning request                              |
| `output`               | Stage payload (tasks, diff, tests, etc.)    |
| `model_used`           | Provider + model identifier                 |
| `confidence`           | 0–1 self-reported confidence                |
| `risk_level`           | Low / Medium / High                         |
| `missing_information`  | What the agent lacked                       |
| `human_review_required`| Boolean                                     |

---

## 6. Human Approval Gates

The engine stops and requires explicit human approval before executing any
stage whose work touches:

- Database migrations
- Authentication or security
- Payment systems
- File deletion
- Production deployment

A gate also triggers when any stage returns `risk_level: High` or
`human_review_required: true`, regardless of category. Execution stays in
`AWAITING_APPROVAL` until approved (continue) or rejected (→ `REJECTED`).

---

## 7. Model Routing

Models are organized by **capability tier**, not selected from a flat list.
This simplifies the UI and prevents weak models from being assigned to
high-level engineering work.

| Tier   | Used for                                   | Example models                              |
|--------|--------------------------------------------|---------------------------------------------|
| Light  | Translation, logging, documentation        | Cursor Free, GPT-4.1 Mini, Gemini Flash, Claude Haiku |
| Medium | Testing, code explanation, doc updates     | Mid-tier coding models                      |
| Heavy  | Implementation, large refactors, review    | Codex, Claude Code                          |

Each stage declares the **minimum tier** it accepts. The UI only offers models
at or above that tier for the stage, so a user cannot assign a Light model to
the Builder or Reviewer.

**Default model per stage** (all overridable from the frontend; ADR-009):

| Stage    | Default model | Rationale                                  |
|----------|---------------|--------------------------------------------|
| Builder  | Claude Code   | Reasoning depth for multi-file changes     |
| Tester   | Codex         | Token efficiency lowers cost on a high-volume stage |
| Reviewer | Claude Code   | Heavy-tier audit against original intent   |

Defaults are pure configuration — the provider-agnostic design means changing
them touches no engine logic.

---

## 8. Provider Abstraction Layer

Every provider implements one common interface so the engine stays
provider-independent:

```
interface Provider {
  id: string
  tier: "light" | "medium" | "heavy"
  capabilities: Capability[]        // plan, build, test, review, document
  invoke(contextPackage): StageResult
}
```

Planned providers: Codex, Claude Code, Cursor, Gemini, OpenRouter, and future
local models. Adding one means implementing this interface and registering it —
no engine changes. This is the basis for the future plugin architecture.

---

## 9. Repository Context Strategy

The Repository Analyzer never ships the whole repo to a model. It assembles a
**minimal relevant context package** from:

- The current task and its acceptance criteria
- `git diff` and recently changed files
- Related source files (by dependency / reference)
- Project memory: `PROJECT_NOTES.md`, prior `LOGS.md` entries
- Existing architecture notes

Smaller, targeted context → smaller prompts, lower cost, fewer hallucinations,
better implementations.

---

## 10. Git Integration

Git is a first-class input. The engine and agents can read:

- Current branch
- Changed files and `git diff` summaries
- Recent commit history
- Potential merge conflicts

Builders and Reviewers use this to ground their work in the repo's real state.

---

## 11. Project Scanning & Onboarding

Before a project can be worked on, the system must *understand* it. The
**Project Scanner** builds (or refreshes) a project's Markdown knowledge base and
registers it in SQLite with a `project_id`. It has two modes:

**Soft Scan (default, on add).** If Markdown files exist (`ARCHITECTURE.md`,
`README.md`, `TASKS.md`, `LOGS.md`, `PROJECT_NOTES.md`, etc.), an LLM reads them
to build the project's understanding and seeds the `projects` record + summary.
Fast and cheap (Light/Medium tier). Trusts existing docs as the source of truth.

**Hard Scan (manual "Scan" button).** A deterministic walk of the *entire*
project regardless of whether any Markdown exists — file tree, detected
languages/frameworks, entry points, and Git history. An LLM (Medium/Heavy tier)
then synthesizes that into understanding and **creates or updates** the Markdown
files to match. Use it when docs are missing, stale, or you want a ground-truth
refresh.

> **Non-destructive:** Hard Scan updates and augments rather than blindly
> overwriting. Existing human-authored content is preserved (back up / merge,
> never clobber).

**Determinism boundary (ADR-011):** the file walking, language detection, and
Git inspection are deterministic code; only the *understanding/synthesis* step
is an LLM. The controller stays deterministic — scanning is an agent task, not
orchestration.

Each scanned project becomes a row in `projects` (`summary`, `languages`,
`scan_type`, `last_scanned_at`); its `project_id` links all of its requests and
tasks.

## 12. Project Memory (Markdown Knowledge Base)

| File              | Role                                              |
|-------------------|---------------------------------------------------|
| `README.md`       | Vision and overview                               |
| `ARCHITECTURE.md` | This document — technical source of truth         |
| `SCHEMA.md`       | SQLite schema, Stage Result contract, risk rules  |
| `AGENTS.md`       | Per-agent responsibilities and I/O contracts      |
| `TASKS.md`        | Structured engineering tasks (Builder's source)   |
| `LOGS.md`         | Implementation history                            |
| `PROJECT_NOTES.md`| Architectural knowledge, conventions, debt        |
| `TEST_LOGS.md`    | Test generation, results, coverage, regressions   |
| `REQUESTS.md`     | Verbatim client requests + planner interpretations|
| `TRACEABILITY.md` | Request → tasks → diff → tests → review mapping    |
| `DECISIONS.md`    | Architecture decision records                     |
| `BUILD_PLAN.md`   | Phased build order and MVP milestones             |

These files are the shared, persistent memory all agents read from and the
engine writes to.
