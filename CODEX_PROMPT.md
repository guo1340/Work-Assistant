# Codex Build Prompt

Copy the block below as the instruction to Codex (or Claude Code) when starting
the build. It points at the Markdown spec and constrains scope to one phase at a
time.

---

```
You are building "DevFlow Assistant," a local-first AI software engineering
workflow orchestrator. The complete design already exists as Markdown files in
this project. Read them before writing any code:

- README.md         — vision and overview
- ARCHITECTURE.md   — technical source of truth (engine, pipeline, stack)
- SCHEMA.md         — SQLite schema, Stage Result JSON contract, risk rules
- AGENTS.md         — each agent's responsibility and I/O contract
- DECISIONS.md      — accepted architecture decisions (ADRs); follow them
- BUILD_PLAN.md     — the phased build order you must follow
- TASKS.md          — task breakdown

Stack (non-negotiable, per DECISIONS.md):
- Engine/backend: Python + FastAPI, SQLite state store.
- Frontend: React + TypeScript (Vite + Tailwind), built with Impeccable
  (github.com/pbakaus/impeccable) enabled for design quality — use its commands
  (polish, audit, critique) and avoid AI-slop anti-patterns.
- Providers wrapped as subprocesses; build against a MOCK provider first.
  Real CLIs (Codex, Claude Code, Cursor free tier) are wired LAST (Phase 7).

Hard rules:
- The Workflow Engine is deterministic code, never an LLM. Agents are stateless
  workers that only talk to the engine and return a Stage Result.
- Initialize SQLite exactly from SCHEMA.md.
- Do not skip ahead: implement BUILD_PLAN.md one phase at a time, starting at
  Phase 0. After each phase, stop and report what you built and how to run/test
  it, then wait for me to say continue.
- Preserve the verbatim-request and traceability behavior described in the spec.
- Keep code modular so providers and stages can be added without engine changes.

Begin with Phase 0 (Skeleton & Scaffolding). Propose the repo structure first,
then implement it. Ask me if any decision in the spec is ambiguous rather than
guessing.
```
