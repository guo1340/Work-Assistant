# Phases 7–8 — Real Providers and Live Validation

## Phase 7

Implemented real subprocess providers behind the existing `Provider` interface:

- Codex CLI for analysis, build, test, review, documentation, and reporting.
- Claude Code for all stage capabilities.
- Cursor Agent for request logging and planning.
- Versioned prompts loaded from `prompts/<agent>/v1.md`.
- TypeScript/JavaScript, Java, and Python native test-runner adapters in the
  required priority order.
- Per-stage, tier-filtered provider selection in the frontend.

All providers run non-interactively and return the fixed Stage Result envelope.
The engine remains deterministic and is the only component that writes shared
state or commits Builder output.

### Authentication

```powershell
codex login
claude auth login --claudeai
wsl.exe ~/.local/bin/cursor-agent login
```

Verify with:

```powershell
codex login status
claude auth status --json
wsl.exe ~/.local/bin/cursor-agent status
```

On Windows systems where the browser uses a localhost proxy, WSL mirrored
networking and automatic proxy propagation allow Cursor Agent to share it:

```ini
# %USERPROFILE%\.wslconfig
[wsl2]
networkingMode=mirrored
autoProxy=true
```

Run `wsl --shutdown` once after changing that file.

## Phase 8

The live run used a real TypeScript/Vitest Git repository and this request:

> Add an exported `maskToken(token: string): string` function in
> `src/auth/token.ts`. It must return the original token when its length is 4
> or less; otherwise return asterisks for every character except the final
> four. Add Vitest coverage for both cases. Do not change dependencies.

Routing:

- Request Logger and Planner: Cursor
- Repository Analyzer and Tester: Codex
- Builder, Documentation, Reviewer, and Final Report: Claude Code

Observed result:

- Request reached `DONE`.
- Verbatim request and planner interpretation remained separate.
- Two tasks mapped to `REQ-2026-0001`.
- Builder produced two complete-file changes on
  `devflow/REQ-2026-0001`.
- Auth-path risk rules opened an approval gate before commit.
- Approval produced Git commit `74cce2524aab5e3d7f5100db4c21c12522ea7ff5`.
- Vitest passed 7/7 tests across 2 files.
- Reviewer approved with no missing, invented, partial, or scope-creep work.
- Immutable history recorded 20 events from receipt through completion.

The controlled fixture and SQLite evidence are under ignored `data/` paths.

## Run

```powershell
# Terminal 1
.\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir engine --reload

# Terminal 2
cd frontend
npm install
npm run dev
```

Open `http://127.0.0.1:5173`.
