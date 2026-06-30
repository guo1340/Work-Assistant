# TRACEABILITY

Solves the **"telephone game"** problem: as a request passes through multiple
LLMs, information can be lost, invented, or distorted. This file maps every
request through every stage so nothing disappears between them.

## The Trace Chain

```
Original Request (REQUESTS.md)
   ↓
TASKS.md (generated tasks)
   ↓
Git Diff (actual implementation)
   ↓
Tests (TEST_LOGS.md)
   ↓
Final Implementation + Review
```

Every link references the same `request_id`, so any stage can be compared
against the original intent.

## What the Reviewer Detects

By comparing the links in the chain, the system flags:

- **Missing requirements** — in the request but absent from tasks/diff
- **Invented functionality** — in the diff but not traceable to any request
- **Partial implementations** — task started but acceptance criteria unmet
- **Scope creep** — work expanding beyond the original request

## Traceability Matrix

| Request ID | Tasks | Implemented (Diff) | Tested | Reviewed | Status |
|------------|-------|--------------------|--------|----------|--------|
| _example_ REQ-2026-0001 | TASK-0001-01..04 | 3 of 4 | partial | flagged | scope gap |

Each row should resolve to one of: **Complete**, **Partial**, **Missing**,
**Scope Creep**, or **Under Review**.

## Per-Request Trace Template

```
### REQ-2026-0001
- Requirements extracted: 4
- Tasks generated: 4   (TASK-0001-01 … 04)
- Tasks implemented:  3
- Missing: "make mobile navigation easier" — no matching diff
- Invented: none detected
- Scope creep: none detected
- Tests: 3 of 4 work items covered
- Reviewer confidence: 0.78
- Outcome: AWAITING_APPROVAL (missing requirement)
```

---

## Log

_No traces recorded yet. The entries above are illustrative templates._
