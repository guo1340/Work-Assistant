# TEST LOGS

Test history produced by the Tester agent and consumed by the Reviewer.

## Test Strategy

Each completed task should generate:

- Unit tests
- Integration tests (where applicable)
- Regression tests

The Reviewer then checks that:

- The original request is satisfied
- All acceptance criteria are met
- No unintended functionality was introduced
- Existing functionality is preserved

## Report Schema

Each test run records:

- **Date**
- **Request ID / Task ID**
- **Confidence** — Tester self-assessment (0–1)
- **Risk** — Low / Medium / High
- **Tests Passed**
- **Tests Failed**
- **Coverage** — percentage or scope description
- **Regressions** — newly failing previously-passing tests
- **Known Failures**
- **Recommendations**

---

## Template

```
### 2026-06-30 — TASK-0001-03 (REQ-2026-0001)
- Confidence: 0.82
- Risk: Medium
- Tests Passed: 11
- Tests Failed: 1
- Coverage: ~74% of changed lines
- Regressions: none
- Known Failures: timeout edge case under load
- Recommendations: add load test before marking DONE
```

---

## Log

_No test runs recorded yet. The entry above is an illustrative template._
