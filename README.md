# DevFlow Assistant

## Vision

DevFlow Assistant is a **local-first AI software engineering workflow
orchestrator** — think of it as an AI Engineering Manager.

It does **not** replace coding models. Instead, it coordinates specialized LLMs
so they work together rather than independently. It solves the core problems of
working with multiple models: preserving project context, ensuring
traceability, and stopping requirements from getting lost in the "telephone
game" as work passes between models.

The system:

- Translates client/manager requests into structured engineering tasks.
- Executes implementation through Codex or Claude Code.
- Preserves the complete history of every decision.
- Generates and runs tests.
- Reviews implementation against the original request.
- Ensures no client request is ever lost across the pipeline.

## The Workflow Engine

At the heart of the application is a **Workflow Engine**. Agents never call each
other — they only talk to the engine. The engine owns project state, schedules
the next stage, enforces approval gates, retries failed stages, and records a
complete execution history. This decoupling makes it easy to swap models, add
stages, or support new providers without rewriting the pipeline. See
`ARCHITECTURE.md` for the full design.

## Pipeline

```
Client Request → Request Logger → Planner → Traceability Check
   → Repository Analyzer → Builder → Documentation Agent
   → Tester → Reviewer → Final Report
```

Each stage has exactly one responsibility.

## Core Features

- Engine-centric orchestration (agents are stateless workers)
- Multi-project support
- Local-first (Git, Markdown, local DB, local CLIs)
- LLM-agnostic with capability-tiered model routing
- Repository-aware context (only relevant files reach the Builder)
- Git integration as a first-class input
- Markdown knowledge base as persistent project memory
- End-to-end traceability from request to implementation
- Human approval gates for high-risk work

## Tech Stack

Python + FastAPI engine, SQLite state store, React + TypeScript frontend
(Vite + Tailwind) built with Impeccable (github.com/pbakaus/impeccable) for
design quality. Real model providers
(Codex CLI, Claude Code CLI, Cursor free tier) are wired in last; the pipeline is
built and tested against a mock provider first.

## Design Philosophy

1. **Single Responsibility** — each agent does one job; planners never code,
   builders never write docs, reviewers never implement.
2. **Local First** — no cloud dependency unless the user explicitly enables it.
3. **LLM Agnostic** — every layer supports multiple providers, constrained by
   task complexity tier.

## Project Files

| File              | Purpose                                          |
|-------------------|--------------------------------------------------|
| `README.md`       | Vision and overview (this file)                  |
| `ARCHITECTURE.md` | Technical source of truth                         |
| `SCHEMA.md`       | SQLite schema, Stage Result contract, risk rules  |
| `AGENTS.md`       | Agent responsibilities and I/O contracts          |
| `TASKS.md`        | Structured engineering tasks                      |
| `LOGS.md`         | Implementation history                            |
| `PROJECT_NOTES.md`| Architectural knowledge and conventions           |
| `TEST_LOGS.md`    | Test results and coverage                         |
| `REQUESTS.md`     | Verbatim client requests + planner interpretations|
| `TRACEABILITY.md` | Request-to-implementation mapping                 |
| `DECISIONS.md`    | Architecture decision records                     |
| `BUILD_PLAN.md`   | Phased build order and MVP milestones             |

## Long-Term Vision

A complete AI engineering workspace that functions as an intelligent
engineering manager — coordinating specialized AI workers while maintaining
complete project knowledge, preserving every client request, preventing context
loss, enforcing engineering best practices, and ensuring every implementation
can always be traced back to the original requirements.
