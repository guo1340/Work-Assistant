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

### 2026-07-01 — Phases 0–2 (Engine core, schema, providers)

- **Scope:** Reviewed Codex's Phase 0–2 build (`engine/`), ran its existing
  suite, and added coverage.
- **Confidence:** High
- **Risk:** Low
- **Tests Passed:** 37 / 37 (12 from Codex + 25 added)
- **Tests Failed:** 0
- **Coverage:** All Phase 0–2 modules exercised — `config`, `db.connection`,
  `db.store`, `domain.models`, `core.pipeline`, `providers` (base/mock/registry),
  `workflow.engine`, `api.health`, `main` (via TestClient).
- **Added tests:**
  - `test_models.py` (6) — StageResult validation (confidence bounds, required
    fields, frozen), RiskLevel/Tier ordering + `__str__`.
  - `test_store_extra.py` (7) — unknown-request KeyError, invalid-transition
    guard, FK enforcement, JSON/risk persistence, append-only history ordering,
    approval error paths.
  - `test_engine_extra.py` (6) — state→stage mapping, terminal-state guard,
    approve-without-pending, wrong-stage result → FAILED, retry history events,
    reject is terminal.
  - `test_config.py` (2), `test_health_extra.py` (1, DB-unavailable branch),
    `test_registry_extra.py` (3, eligibility + unknown provider).
- **Result:** No code changes required — Codex's implementation matched the spec
  and passed all added probes.
- **Recommendations:**
  - The code targets Python 3.11+ (uses `enum.StrEnum`, `datetime.UTC`), per
    `pyproject.toml`. The local sandbox only had 3.10, so this run used a
    non-invasive compatibility shim (injected via `PYTHONPATH`, source
    untouched). Run CI on 3.11+ to exercise the real interpreter.
  - Consider wiring a coverage tool (`pytest-cov`) in a later phase for hard
    numbers.

### 2026-07-01 — Phases 3–6

- **Scope:** Scanner, Markdown KB, full mock pipeline, traceability, risk rules,
  Git request branches, FastAPI workflow endpoints, and the React workspace.
- **Confidence:** High
- **Risk:** Medium
- **Tests Passed:** 45 / 45
- **Tests Failed:** 0
- **Frontend:** ESLint passed; TypeScript and Vite production build passed.
- **Impeccable:** Deterministic detector passed with zero findings after token
  consolidation; critique score 35 / 40.
- **Browser checks:** Empty onboarding, project registration, request selection,
  all eight pipeline stages, evidence tabs, final report, desktop layout, and
  375 px responsive layout. No console errors or horizontal overflow.
- **Regression found and fixed:** Browser `POST` requests were blocked by the
  Phase 0 CORS method allowlist; `POST` is now explicitly allowed.
