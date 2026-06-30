# REQUESTS

The permanent, **append-only** record of every client/manager request. The
`Original Request` field is captured verbatim by the Request Logger and is
**never overwritten** — not even by the Planner. The Planner's interpretation is
stored separately so the system can always answer:

- "What exactly did the client ask for?" → `Original Request`
- "What did the planner think they meant?" → `Planner Interpretation`
- "What was actually implemented?" → linked tasks + `TRACEABILITY.md`

## Request ID Scheme

`REQ-<YEAR>-<SEQ>` — e.g. `REQ-2026-0042`. Assigned by the engine at the moment
of capture; immutable for the life of the project.

## Entry Schema

Each request is recorded with the following fields:

- **Request ID** — unique, immutable
- **Received At** — timestamp
- **Original Request** — verbatim text, never edited
- **Planner Interpretation** — planner's restatement of intent
- **Generated Tasks** — list of `task_id`s produced from this request
- **State** — current engine state for this request
- **Notes** — optional clarifications captured during processing

---

## Template

```
### REQ-2026-0001
- Received At: 2026-06-30T14:00:00Z
- State: PLANNED
- Original Request: >
    "Can we redesign the dashboard, add dark mode for admins only, fix the
    login timeout issue, and make the mobile navigation easier to use?"
- Planner Interpretation: >
    Four distinct work items: (1) dashboard redesign, (2) admin-only dark mode,
    (3) login session timeout bug fix, (4) mobile navigation UX improvement.
- Generated Tasks: TASK-0001-01, TASK-0001-02, TASK-0001-03, TASK-0001-04
- Notes: "admins only" on dark mode flagged for confirmation.
```

---

## Log

_No production requests recorded yet. The entry above is an illustrative
template._
