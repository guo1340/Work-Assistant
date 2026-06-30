# PROJECT NOTES

Architectural knowledge that evolves with the project: framework choices, folder
conventions, coding standards, known limitations, and technical debt. For the
authoritative system design see `ARCHITECTURE.md`; for decision rationale see
`DECISIONS.md`.

## Architecture Summary

Local-first orchestration platform built around a central **Workflow Engine**.
Agents are stateless workers that communicate only with the engine; the engine
owns state, scheduling, approval gates, retries, and execution history.
Cross-agent communication and persistent memory happen through Markdown files,
not direct prompts or conversation memory.

## Design Principles

- Single responsibility per agent
- Engine-centric orchestration (no agent-to-agent calls)
- Deterministic, inspectable workflow
- Human approval for risky operations
- Repository-aware, minimal context
- Preserve complete project history and original requests

## Model Routing

Stages declare a minimum capability tier; the UI only offers qualifying models.

- **Light** — Request Logger, Planner, Documentation Agent
  (Cursor Free, GPT-4.1 Mini, Gemini Flash, Claude Haiku)
- **Medium** — Repository Analyzer, Tester
- **Heavy** — Builder, Reviewer (Codex, Claude Code)

## Traceability

- Every request receives an immutable Request ID at capture.
- Every generated task maps back to its parent request.
- Every review validates implementation against the original request and flags
  missing, invented, partial, or scope-crept work.

## Resolved Technical Choices

- **Engine language:** Python + FastAPI; frontend React + TypeScript
  (Vite + Tailwind) built with **Impeccable** (github.com/pbakaus/impeccable)
  for design quality. (ADR-022, ADR-023)
- **State store:** SQLite (engine index/state); Markdown stays human-readable
  memory. Stage `output` payloads as JSON columns. (ADR-007)
- **Transport:** local HTTP API between frontend and engine. (ADR-008)
- **Default models:** Builder → Claude Code, Tester → Codex, Reviewer → Claude
  Code; all changeable from the frontend, tier-constrained. (ADR-009)
- **Concurrency:** sequential (one request at a time), abstracted so per-project
  parallelism can be added later. (ADR-010)
- **Controller:** deterministic code, no LLM in orchestration. (ADR-011)

## Conventions

- Project memory lives in the root Markdown files listed in `README.md`.
- IDs: requests `REQ-YEAR-SEQ`; tasks `TASK-<reqseq>-<n>`.
- The original request text is append-only and never edited.

## Known Open Items (see DECISIONS.md)

- SQLite schema details (tables, indexes, JSON boundaries).
- Risk-classification rule set for approval gates.
- Git rollback strategy when a stage is rejected after a commit.
- Prompt template storage and versioning per agent.

## Technical Debt

_None yet — project is in design phase._
