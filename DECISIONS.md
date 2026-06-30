# DECISIONS

Architecture Decision Records (ADRs). Each entry captures a decision, its
context, and its consequences so the reasoning behind the architecture is never
lost. Newest at the bottom.

Format per entry: **Status** (Accepted / Superseded / Proposed) · **Context** ·
**Decision** · **Consequences**.

---

## ADR-001: Central Workflow Engine

- **Status:** Accepted (2026-06-30)
- **Context:** Agents calling each other directly couples them tightly, making
  it hard to swap models, add stages, or support new providers.
- **Decision:** Introduce a Workflow Engine as the heart of the system. Agents
  are stateless workers that communicate only with the engine. The engine owns
  project state, schedules stages, enforces approval gates, retries failures,
  and records execution history.
- **Consequences:** Adding a provider or stage becomes an engine-config change,
  not a pipeline rewrite. Agents become simpler and independently testable. The
  engine becomes a critical component requiring its own robustness and tests.

## ADR-002: Local-First

- **Status:** Accepted (2026-06-30)
- **Context:** Cloud dependencies add cost, latency, and privacy concerns for
  what is fundamentally local engineering work.
- **Decision:** Default to local Git, Markdown, local DB, and local CLIs (Codex,
  Claude Code). No cloud services unless the user explicitly enables them.
- **Consequences:** Works offline and keeps code local; cloud-only models are
  opt-in and clearly marked.

## ADR-003: LLM-Agnostic via Provider Interface

- **Status:** Accepted (2026-06-30)
- **Context:** Tying the system to one model is brittle and limits quality.
- **Decision:** Every provider implements a common interface; the engine never
  references a specific model. This is the basis for the future plugin
  architecture.
- **Consequences:** New providers register without core changes; the engine
  stays provider-independent.

## ADR-004: Capability-Tiered Model Routing

- **Status:** Accepted (2026-06-30)
- **Context:** A flat list of hundreds of models lets users accidentally assign
  weak models to high-level engineering work.
- **Decision:** Organize models into Light / Medium / Heavy tiers. Each stage
  declares a minimum tier; the UI only offers models at or above it.
- **Consequences:** Simpler UI, safer defaults. Requires maintaining a
  tier mapping as new models appear.

## ADR-005: Markdown as Persistent Project Memory

- **Status:** Accepted (2026-06-30)
- **Context:** Conversation memory is lossy and not shared across agents.
- **Decision:** Persist all project state in Markdown files that every agent
  reads and the engine writes.
- **Consequences:** Human-readable, Git-versioned memory. Requires disciplined
  schemas (defined across the project files).

## ADR-006: Verbatim Request Preservation

- **Status:** Accepted (2026-06-30)
- **Context:** Requirements get lost as requests pass between models (the
  "telephone game").
- **Decision:** The Request Logger captures every request verbatim into
  `REQUESTS.md`; the original is never overwritten. Planner interpretation is
  stored separately. Full chain tracked in `TRACEABILITY.md`.
- **Consequences:** The system can always reconstruct original intent and detect
  missing, invented, partial, or scope-crept work.

## ADR-007: SQLite as Engine State Store

- **Status:** Accepted (2026-06-30)
- **Context:** The engine needs an internal store for requests, tasks, stage
  results, and execution history. Data is highly relational and traceability
  queries ("which requirements have no matching diff?") are central.
- **Decision:** Use **SQLite** (single-file, zero-server, transactional). Store
  free-form stage `output` payloads as JSON columns. This is the engine's
  internal index/state store; Markdown files remain the human-readable shared
  memory (ADR-005). SQLite is the index, Markdown is the memory.
- **Consequences:** Atomic stage commits, trivial relational traceability
  queries, native support in Python/Node. Requires schema definition and
  migrations as the model evolves.

## ADR-008: Frontend ↔ Engine Transport via Local HTTP API

- **Status:** Accepted (2026-06-30)
- **Context:** The React frontend must talk to the engine.
- **Decision:** Use a **local HTTP API**. Simplest to build and lets the
  frontend be swapped or run separately later. Revisit only if a need arises.
- **Consequences:** Clean client/server boundary; minor local-port management.

## ADR-009: Per-Stage Default Models (UI-Changeable)

- **Status:** Accepted (2026-06-30)
- **Context:** Builder and Tester both accept multiple providers; we want good
  defaults without locking users in.
- **Decision:** Default **Builder → Claude Code** (reasoning depth for
  multi-file changes) and **Tester → Codex** (token efficiency lowers cost on a
  high-volume stage). **All per-stage model selections are overridable from the
  frontend**, subject to each stage's minimum tier (ADR-004). Reviewer default
  remains Heavy (Claude Code).
- **Consequences:** Sensible, cost-aware defaults; full user control retained.
  Provider-agnostic design (ADR-003) makes the defaults pure configuration.

## ADR-010: Sequential Concurrency First (Abstracted for Parallel)

- **Status:** Accepted (2026-06-30)
- **Context:** Parallel request processing raises Git working-tree conflicts and
  concurrent Markdown writes. Tokens saved by parallel builds can be lost to
  resolving merge issues.
- **Decision:** Process **one request at a time** in the current build, but keep
  all state keyed by `request_id` and the engine interface
  concurrency-agnostic, so a per-project / per-branch worker pool can be added
  later without redesign.
- **Consequences:** Simple, conflict-free MVP; clear upgrade path. Throughput is
  limited until parallelism is added.

## ADR-011: Deterministic Controller (No LLM in Orchestration)

- **Status:** Accepted (2026-06-30)
- **Context:** The controller could be driven by an LLM or by plain code.
- **Decision:** The Workflow Engine is **deterministic code**, never an LLM.
  Orchestration — state, scheduling, approval gates, retries, history — must be
  reliable and reproducible. Designed direction for builders:
  - Orchestration logic = a state machine in code (see `ARCHITECTURE.md` §3).
  - Fuzzy judgments (risk classification, file relevance) start as
    **deterministic rules** (keyword/path matching, Git-diff heuristics).
  - Only if rules prove too blunt, the engine may delegate *one narrow
    judgment* to a **Light-tier** model — never the orchestration, scheduling,
    or gate decisions themselves.
- **Consequences:** Predictable, cheap, trustworthy control flow. Intelligence
  lives in the agents, not the engine.

## ADR-012: SQLite Schema & Stage Result Contract — ACCEPTED

- **Status:** Accepted (2026-06-30)
- **Decision:** Adopt the schema, contract, and risk rules drafted in
  `SCHEMA.md`. Tables: `projects`, `requests`, `tasks`, `stage_results`,
  `execution_history` (immutable), `approvals`. Relational columns for anything
  queried; JSON columns for free-form payloads. Stage Result is a fixed JSON
  object with an engine-added envelope.
- **Consequences:** Concrete contract the engine and every agent are written
  against. `execution_history` is append-only for an auditable run log.

## ADR-013: Risk-Classification Rules v1 — ACCEPTED

- **Status:** Accepted (2026-06-30)
- **Decision:** Use the deterministic path/keyword rule set in `SCHEMA.md` §3.
  Engine computes `max(agent_risk, rule_risk)` so an agent can't under-report to
  skip a gate. Patterns live in config, not code.
- **Consequences:** Safety model has a concrete, tunable v1. Expect to expand
  patterns as real requests surface new categories.

## ADR-014: Prompt Templates as Versioned Files — ACCEPTED

- **Status:** Accepted (2026-06-30)
- **Context:** Agent quality lives in prompts; they need storage + versioning.
- **Decision:** Store prompts as files under `prompts/<agent>/<version>.md` with
  a small front-matter header (agent, version, min_tier) and `{{variable}}`
  placeholders the engine fills (task, repo context, etc.). A registry maps each
  stage to its active prompt version.
- **Consequences:** Human-readable, Git-versioned, diff-reviewable (fits
  local-first + Markdown-as-memory). Engine owns variable injection.

## ADR-015: Git Safety — Branch per Request — ACCEPTED

- **Status:** Accepted (2026-06-30)
- **Context:** Builder changes must be reversible and isolated.
- **Decision:** Builder works on a dedicated branch `devflow/REQ-XXXX`, never
  committing directly to main. The commit SHA is recorded in
  `execution_history`. Rollback = reset/delete the branch. Merge to main is a
  separate, human-gated step. Move to Git **worktrees** when parallelism is
  added (isolates working dirs per request).
- **Consequences:** Fully reversible; isolates work; aligns with the per-branch
  parallelism path (ADR-010). Slightly more Git plumbing.

## ADR-016: Test Framework — Language Priority — ACCEPTED

- **Status:** Accepted (2026-06-30)
- **Context:** "Support all languages" is a trap for the MVP; adapters should be
  built in the order the user's real projects need them.
- **Decision:** Tester invokes language-native runners through a thin
  `TestRunner` adapter interface (detect → install deps → run → parse). Build
  adapters in priority order:
  1. **TypeScript / JavaScript** (React, Vue) — Vitest / Jest
  2. **Java** (backend) — JUnit via Maven / Gradle
  3. **Python** — pytest
  Additional languages plug in later via the same interface.
- **Consequences:** Tester ships against the user's primary stacks first;
  new languages add without redesign.

## ADR-017: Provider Plugins — Interface Now, Loader Later — ACCEPTED

- **Status:** Accepted (2026-06-30)
- **Decision:** For the MVP, hardcode two providers (Claude Code, Codex) behind
  the `Provider` interface (ARCHITECTURE §8) but do not build the dynamic
  plugin-loading machinery yet. Keep the interface clean so a loader is added
  later without touching the engine.
- **Consequences:** Less upfront work; clear extension path preserved.

## ADR-018: Multi-Project — Model Now, One Active at a Time — ACCEPTED

- **Status:** Accepted (2026-06-30)
- **Decision:** Include `projects` and `project_id` foreign keys in the schema
  from day one (cheap), but the MVP engine/UI operate on **one active project at
  a time**. No cross-project orchestration.
- **Consequences:** Avoids a painful migration later; keeps the MVP simple.

## ADR-019: Project Scanner (Soft & Hard Scan) — ACCEPTED

- **Status:** Accepted (2026-06-30)
- **Context:** The system must understand a project before working on it, and
  projects vary in how well they're documented.
- **Decision:** A **Project Scanner** onboarding component with two modes:
  - **Soft Scan** (default on add): an LLM reads existing `*.md` files
    (`ARCHITECTURE.md`, `README.md`, `TASKS.md`, `LOGS.md`, `PROJECT_NOTES.md`,
    …) to understand the project. Cheap, trusts existing docs.
  - **Hard Scan** (manual button): deterministic walk of the entire repo
    regardless of Markdown presence → LLM synthesizes understanding →
    **creates/updates** the `*.md` files (non-destructive). For missing/stale
    docs or a ground-truth refresh.
  - Each scanned project is registered in `projects` with a `project_id` that
    links its requests and tasks.
- **Determinism:** file walking, language detection, and Git inspection are
  deterministic code; only synthesis uses an LLM (consistent with ADR-011).
- **Consequences:** Works on documented and undocumented repos alike; bootstraps
  the Markdown knowledge base automatically. Hard Scan must preserve
  human-authored content (merge/back up, never clobber).

## ADR-020: Large-Diff Risk Threshold — ACCEPTED

- **Status:** Accepted (2026-06-30)
- **Decision:** A diff exceeding **400 changed lines** is flagged Medium risk
  (configurable). Resolves the open threshold question for ADR-013.
- **Consequences:** Big sweeping changes get a human glance by default; tune as
  real behavior is observed.

## ADR-021: Provider Integrations as Final Pre-Live Step — ACCEPTED

- **Status:** Accepted (2026-06-30)
- **Context:** The engine, scanner, schema, and Markdown pipeline can be built
  and exercised with stubbed/mock providers. Wiring the real CLIs is the last
  thing needed before live testing.
- **Decision:** Implement the real provider integrations — **Codex CLI**,
  **Claude Code CLI**, and **Cursor free tier** (used for translation / Planner)
  — as the **final steps before live testing**. Until then, develop against mock
  providers that return canned Stage Results so the pipeline can be tested
  deterministically. Merge-to-main stays **manual / human-gated** (ADR-015).
- **Consequences:** Core system is testable without burning tokens or depending
  on external CLIs; live testing begins once the three integrations land.

## ADR-022: DevFlow Implementation Stack — ACCEPTED

- **Status:** Accepted (2026-06-30)
- **Context:** The spec pinned the frontend and state store but not the
  engine/backend language. This blocked scaffolding.
- **Decision:** The **engine/backend is Python** — strongest ecosystem for
  multi-LLM orchestration and CLI subprocess control. Recommended pieces:
  **FastAPI** for the local HTTP API (ADR-008), **SQLite** via the stdlib or
  SQLModel/SQLAlchemy (ADR-007), CLI providers wrapped as subprocesses. The
  **frontend is React + TypeScript** (Vite + Tailwind) built with **Impeccable**
  enabled for design quality (ADR-023).
- **Consequences:** Clear two-language split (Python engine, TS frontend) joined
  by a local HTTP API. Codex/Claude Code can now scaffold against a known stack.

## ADR-023: Frontend Design via Impeccable — ACCEPTED

- **Status:** Accepted (2026-06-30)
- **Context:** AI-generated UIs tend toward generic "AI slop" (same fonts,
  gradients, nested cards). We want a high, consistent design bar.
- **Decision:** Use **Impeccable** (github.com/pbakaus/impeccable) — a design
  tool/skill that plugs into AI coding harnesses (Codex CLI, Claude Code, Cursor,
  Copilot) and provides a shared design vocabulary (polish, audit, critique,
  etc.) plus deterministic detector rules. Since Codex CLI is our builder, the
  frontend is developed with Impeccable enabled to enforce design quality.
- **Consequences:** Frontend held to Impeccable's standard; UI is audited against
  its detector rules and anti-patterns before a screen is considered done.

---

## Resolved

- Engine language: **Python** (ADR-022). Frontend: React + TypeScript.
- Merge-to-main: **manual / human-gated** (ADR-015).
- ADRs 012–018 accepted as recommended; 400-line large-diff threshold (ADR-020).

## Open Questions

- _None blocking the MVP._ All foundational decisions are settled; remaining
  items are implementation details captured in `BUILD_PLAN.md`.
