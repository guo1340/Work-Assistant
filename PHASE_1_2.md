# Phases 1 and 2 — Engine core and mock provider

## What is implemented

- Declarative canonical pipeline and request states
- Compare-and-set state transitions
- Stage scheduling only from valid ready states
- SQLite persistence for projects, requests, stage results, approvals, and
  append-only execution history
- Human approval pause, approve, and reject flows
- Configurable retry count and exponential backoff
- Provider interface, capability tiers, registry enforcement, and mock provider
- Deterministic end-to-end mock pipeline

## Run the tests

```powershell
.\.venv\Scripts\python.exe -m pytest engine/tests
```

The end-to-end workflow test creates an isolated SQLite database, runs all eight
pipeline stages through the mock provider, commits every Stage Result, and
finishes the request in `DONE`. Separate tests cover gates, rejection, retries,
retry exhaustion, provider tier enforcement, and verbatim request preservation.
