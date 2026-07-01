# LOGS

Implementation history. Each completed task records what changed and why, so the
project's evolution is always reconstructable.

## Entry Schema

Each entry should capture:

- **Date**
- **Request ID(s)** — related requests (once the pipeline is live)
- **Task ID(s)** — what was worked on
- **Changes made** — summary of the work
- **Files modified**
- **Why** — rationale for the changes

---

## 2026-06-30 — Initial Design

- **Changes made:** Defined the system architecture and project memory model.
  Established the canonical agent pipeline:
  1. Request Logger
  2. Planner
  3. Traceability Check (engine-owned)
  4. Repository Analyzer
  5. Builder
  6. Documentation Agent
  7. Tester
  8. Reviewer
  9. Final Report
- **Decisions:** Adopted a central Workflow Engine (agents are stateless workers
  that talk only to the engine). Confirmed local-first, LLM-agnostic via a
  provider interface, capability-tiered model routing, Markdown-as-memory, and
  verbatim request preservation. Recorded as ADR-001 through ADR-006 in
  `DECISIONS.md`.
- **Files modified:** `README.md`, `AGENTS.md`, `TASKS.md`, `LOGS.md`,
  `PROJECT_NOTES.md`, `TEST_LOGS.md`. **Created:** `ARCHITECTURE.md`,
  `REQUESTS.md`, `TRACEABILITY.md`, `DECISIONS.md`.
- **Why:** Convert the initial skeleton into a detailed, consistent architecture
  spec ahead of implementation.

## 2026-07-01 — Phases 3–6

- **Changes made:** Added project scanning and Markdown persistence, implemented
  the complete mock-agent pipeline, deterministic traceability and risk
  enforcement, request-branch Git safety, local workflow API, and the responsive
  DevFlow product workspace.
- **Files modified:** `engine/app/{scanner,kb,agents,risk,git,services,api}`,
  `engine/config/risk_rules.json`, `frontend/src`, and Phase 3–6 tests.
- **Why:** Complete the mock-backed MVP workflow before real provider CLI
  integrations, preserving the deterministic engine and stateless-agent
  boundaries.

## 2026-07-01 — Phases 7–8

- **Changes made:** Added authenticated Codex, Claude Code, and Cursor
  subprocess providers; versioned prompt registry; TypeScript, Java, and Python
  test adapters; per-stage provider routing; OS proxy propagation; and Stage
  Result normalization.
- **Live validation:** Completed a real TypeScript request through all eight
  stages. The deterministic auth-path rule opened an approval gate, the engine
  committed the approved Builder changes on a request branch, and Vitest passed
  7/7 tests.
- **Defects fixed from live evidence:** Preserved the live Git-safety registry
  for projects added after startup, moved Claude prompts to stdin, removed
  Cursor's lossy shell wrapper, selected Cursor's read-only ask mode, disabled
  optional Codex MCP integrations, selected reliable Codex HTTP transport, and
  replaced placeholder output examples with stage-specific contracts.
- **Files modified:** `engine/app/providers`, `engine/app/testing`,
  `engine/app/prompts`, top-level `prompts`, `engine/app/services/devflow.py`,
  `engine/app/agents/committer.py`, `frontend/src`, and Phase 7 tests.
- **Why:** Complete ADR-021 and prove the MVP on a real repository without
  moving orchestration or shared-state mutation into an LLM.
