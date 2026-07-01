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

### 2026-07-01 — Phases 3–6 (Scanner, Agents, Risk/Git, API)

- **Scope:** Reviewed Codex's Phase 3–6 build (scanner, KB, agents/committer,
  risk rules, Git safety, DevFlow service + API), ran the suite, added coverage.
- **Confidence:** High
- **Risk:** Low
- **Tests Passed:** 66 / 66 (46 prior + 20 added/fixed)
- **Tests Failed:** 0
- **Defect fixed:** `test_phase6_api.py::test_api_project_request_and_pipeline`
  was **empty** — its setup ran but it had no assertions, while the real
  project→request→pipeline assertions had been pasted into the CORS test. Split
  them so each test covers its own concern; the pipeline test now genuinely
  drives the API end-to-end to `DONE`.
- **Added tests:**
  - `test_phase3_extra.py` (5) — invalid scan_type, soft scan does not fabricate
    KB files, hard-scan framework detection, vendored-dir exclusion,
    unknown-project update guard.
  - `test_phase4_extra.py` (4) — traceability checker (empty/duplicate/foreign
    request-id/well-formed).
  - `test_phase5_extra.py` (6) — high-diff-pattern risk, config-file medium,
    large-diff boundary at threshold, `resolve()` max(agent, rule), confidence
    threshold, Git path-escape guard.
  - `test_phase6_extra.py` (5) — engine↔risk integration (rule-detected high risk
    and low confidence both force approval), API error paths (400 bad root, 400
    blank text, 404 unknown request).
- **Environment note:** Again run on Python 3.10 via the compatibility shim, and
  additionally against a clean tree materialized from Git (`git archive HEAD`)
  because the sandbox working-tree mount served a truncated copy of `store.py`.
  The committed file is intact (461 lines); the truncation was a mount artifact,
  not a code defect. Real dev/CI on 3.11+ against the working tree is unaffected.
- **Still stubbed (by design, for Phase 7+):** Repository Analyzer context
  assembly, Reviewer traceability audit, and Tester execution are mock outputs;
  the only registered provider is the mock. See build-readiness notes below.

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

### 2026-07-01 — Phases 7–8 (Real providers and live pipeline)

- **Confidence:** High
- **Risk:** Medium
- **Backend:** 80/80 tests passed after live tuning.
- **Live provider smokes:** Claude Code, Codex, and Cursor each returned a valid
  Stage Result through the production adapter.
- **Live end-to-end:** Request reached `DONE`; 8/8 stages succeeded; the
  high-risk auth-path approval gate fired and was approved; Git commit
  `74cce2524aab5e3d7f5100db4c21c12522ea7ff5` was recorded.
- **Native tests:** Vitest 7/7 passed across 2 files.
- **Frontend:** ESLint passed; TypeScript/Vite production build passed.
- **Impeccable:** Deterministic detector returned zero findings; desktop and
  390 px browser checks showed no horizontal overflow and 44 px or larger
  actionable controls.
- **Regressions:** none.
- **Known limitation:** Full Impeccable critique requires explicit permission
  to run its two independent sub-agents.
