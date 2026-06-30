# AGENTS

Each agent is a **stateless worker**. It is invoked by the Workflow Engine with
a context package, performs exactly one job, and returns a structured
**Stage Result** (see `ARCHITECTURE.md` §5). Agents never call each other and
never mutate shared state — the engine commits all results.

Every Stage Result includes: `confidence` (0–1), `risk_level`
(Low/Medium/High), `missing_information`, and `human_review_required`. The
engine uses these to decide retries and approval gates.

---

## Project Scanner (onboarding)

**Purpose:** Build or refresh a project's understanding and Markdown knowledge
base, then register it in SQLite with a `project_id`. Runs before the request
pipeline, not inside it.

- **Min tier:** Light (Soft Scan) / Medium–Heavy (Hard Scan)
- **Soft Scan:** LLM reads existing `*.md` files to understand the project.
- **Hard Scan:** deterministic walk of the whole repo (files, languages, Git
  history) → LLM synthesizes understanding → creates/updates the `*.md` files
  (non-destructive). See `ARCHITECTURE.md` §11.
- **Output:** populated/updated Markdown KB + `projects` row (`summary`,
  `languages`, `scan_type`, `last_scanned_at`)
- **Determinism note:** file walking and language detection are code; only the
  synthesis step uses an LLM (ADR-011).

---

## Request Logger

**Purpose:** Capture the client/manager request verbatim before anything else
touches it. The original text must never be overwritten or paraphrased.

- **Min tier:** Light
- **Input:** Raw client request
- **Output:** `REQUESTS.md` entry with a new `request_id` and `original_text`
- **Engine interaction:** First stage; engine assigns the Request ID and moves
  state `RECEIVED → LOGGED`.

---

## Planner

**Purpose:** Translate the natural-language request into structured engineering
tasks. Never writes code.

- **Min tier:** Light
- **Allowed models:** Cursor Free, GPT-4.1 Mini, Gemini Flash, Claude Haiku
- **Input:** Logged request (`REQUESTS.md` entry)
- **Output:**
  - `TASKS.md` — each task with description, priority, acceptance criteria,
    dependencies, estimated files, status
  - Planner interpretation stored alongside the request in `REQUESTS.md`
- **Responsibilities:** Requirement extraction, acceptance-criteria generation,
  affected-file estimation. Every task references its parent `request_id`.

---

## Traceability Check (engine-owned)

**Purpose:** Deterministic verification — not an LLM. Confirms every generated
task maps back to a request and no orphan/invented tasks exist before expensive
build work starts.

- **Input:** `REQUESTS.md` + `TASKS.md`
- **Output:** Pass/fail with a list of unmatched items
- **Engine interaction:** On fail, returns to Planner or halts for human review.

---

## Repository Analyzer

**Purpose:** Assemble the **minimal relevant context package** for the Builder.
Never sends the whole repo to a model.

- **Min tier:** Medium
- **Input:** Current task, `git diff`, changed/related files, `PROJECT_NOTES.md`,
  prior `LOGS.md` entries, existing architecture notes
- **Output:** Context package consumed by the Builder
- **Goal:** Smaller prompts, lower cost, fewer hallucinations.

---

## Builder

**Purpose:** Implement the requested tasks. Never writes project documentation.

- **Min tier:** Heavy
- **Preferred models:** Codex CLI, Claude Code
- **Reads:** `TASKS.md`, `PROJECT_NOTES.md`, `LOGS.md`, the context package
- **Output:** Code changes (a Git diff) + a Stage Result
- **Engine interaction:** High-risk diffs (auth, migrations, payments, deletion,
  deploy) trigger an approval gate before commit.

---

## Documentation Agent (Logger)

**Purpose:** Record what was implemented and why. Does not generate or modify
code or architecture decisions.

- **Min tier:** Light
- **Input:** Builder's diff and Stage Result
- **Output:**
  - `LOGS.md` — changes made, files modified, rationale, related Request IDs
  - `PROJECT_NOTES.md` — updated architectural knowledge when relevant

---

## Tester

**Purpose:** Generate and execute tests for the implemented work. Never rewrites
architecture.

- **Min tier:** Medium (Heavy preferred: Codex, Claude Code)
- **Input:** Builder's diff, tasks, acceptance criteria
- **Output:** `TEST_LOGS.md` — generated tests, execution results, coverage,
  regression history, known failures, recommendations

---

## Reviewer

**Purpose:** Validate everything without making implementation decisions.
Compares: Original Request vs `TASKS.md` vs Git Diff vs Tests.

- **Min tier:** Heavy
- **Preferred models:** Claude Code, Codex
- **Checks:**
  - Missing requirements
  - Invented / hallucinated functionality
  - Partial implementations
  - Scope creep
  - Risk assessment + confidence score
- **Output:** Review result feeding the Final Report and `TRACEABILITY.md`
- **Engine interaction:** Low confidence or high risk → approval gate before the
  request is marked `DONE`.

---

## Model Routing Summary

| Agent               | Min Tier | Notes                              |
|---------------------|----------|------------------------------------|
| Request Logger      | Light    | Verbatim capture                   |
| Planner             | Light    | NL → structured tasks              |
| Repository Analyzer | Medium   | Context assembly                   |
| Builder             | Heavy    | Codex / Claude Code                |
| Documentation Agent | Light    | Logging only                       |
| Tester             | Medium    | Heavy preferred                    |
| Reviewer            | Heavy    | Codex / Claude Code                |

The UI only offers models at or above each agent's minimum tier, preventing weak
models from being assigned to high-level engineering work.

**Default models** (all changeable from the frontend; ADR-009): Builder →
**Claude Code** (reasoning depth), Tester → **Codex** (token efficiency on a
high-volume stage), Reviewer → **Claude Code**. These are defaults only — the
user can pick any model at or above the stage's minimum tier.
