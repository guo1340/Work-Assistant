# TASKS

Structured engineering tasks — the Builder's source of truth. Each task should
carry: description, priority, acceptance criteria, dependencies, estimated
files, status, and a parent `request_id` once requests start flowing.

> Task ID scheme: `TASK-<reqseq>-<n>`, e.g. `TASK-0042-01`. Tasks below are
> bootstrap (building DevFlow itself) and predate the request pipeline.

## Workflow Engine (foundational — build first)

- [ ] Engine state machine (states per `ARCHITECTURE.md` §3)
- [ ] Stage scheduler (advance request on committed result)
- [ ] Project state store (authoritative, engine-owned)
- [ ] Approval gate mechanism (pause / resume / reject)
- [ ] Retry with backoff + escalation
- [ ] Immutable execution history / run log

## Provider Abstraction Layer

- [ ] Common `Provider` interface (id, tier, capabilities, invoke)
- [ ] Provider registry + tier enforcement
- [ ] **Mock provider** (canned Stage Results for deterministic testing)

> Real CLI integrations are deferred to the final pre-live phase below
> (ADR-021). Build and test the whole pipeline against the mock provider first.

## MVP Frontend (React)

- [ ] Project selector
- [ ] Request input
- [ ] Per-stage model selection (tier-filtered)
- [ ] Live pipeline / stage view
- [ ] Approval prompt UI
- [ ] Final report view

## Project Scanner (onboarding)

- [ ] Project registration → `projects` row + `project_id`
- [ ] Soft Scan: LLM reads existing `*.md` to understand project
- [ ] Hard Scan: deterministic repo walk (files, languages, Git history)
- [ ] Hard Scan: LLM synthesis → create/update `*.md` (non-destructive)
- [ ] Language/framework detection (TS/Vue/React, Java, Python)
- [ ] "Scan" button in frontend (soft default, hard on demand)

## Request Logger

- [ ] Assign Request IDs
- [ ] Capture verbatim original request to `REQUESTS.md`

## Planner

- [ ] Convert requests into structured tasks
- [ ] Generate acceptance criteria
- [ ] Estimate affected files
- [ ] Store planner interpretation separately from original

## Traceability Check

- [ ] Deterministic task-to-request mapping check
- [ ] Orphan / invented task detection before build

## Repository Analyzer

- [ ] Git integration (branch, diff, commits)
- [ ] Relevant-file detection
- [ ] Minimal context-package assembly

## Builder

- [ ] Codex integration
- [ ] Claude Code integration
- [ ] Task execution workflow
- [ ] High-risk diff detection → approval gate

## Documentation Agent

- [ ] Update `LOGS.md` (changes, files, rationale, Request IDs)
- [ ] Update `PROJECT_NOTES.md` when architecture changes

## Tester

- [ ] `TestRunner` adapter interface (detect → install → run → parse)
- [ ] TypeScript/JS adapter (Vitest / Jest) — first
- [ ] Java adapter (JUnit via Maven / Gradle) — second
- [ ] Python adapter (pytest) — third
- [ ] Generate tests
- [ ] Run tests
- [ ] Write `TEST_LOGS.md` (results, coverage, regressions)

## Reviewer

- [ ] Compare request vs tasks vs diff vs tests
- [ ] Detect missing / invented / partial / scope-creep
- [ ] Confidence score
- [ ] Risk score
- [ ] Trigger human approval gate on low confidence / high risk

## Final Report

- [ ] Assemble per-request report
- [ ] Update `TRACEABILITY.md` matrix

## Final Steps Before Live Testing (ADR-021)

> Everything above is built and tested against the **mock provider** first.
> These real integrations are the last thing wired in before live testing.

- [ ] Codex CLI integration (real provider behind `Provider` interface)
- [ ] Claude Code CLI integration (real provider)
- [ ] Cursor free tier integration (translation / Planner stage)
- [ ] End-to-end live test on a real project after integrations land

## Future

- [ ] Plugin architecture (provider plugins)
- [ ] Additional providers: Gemini, OpenRouter, local models
- [ ] Custom model profiles
- [ ] CI integration
- [ ] Multiple repositories per project
- [ ] Parallel request processing

- [ ] Plugin architecture (provider plugins)
- [ ] Additional providers: Cursor, Gemini, OpenRouter, local models
- [ ] Custom model profiles
- [ ] CI integration
- [ ] Multiple repositories per project
- [ ] Parallel request processing
