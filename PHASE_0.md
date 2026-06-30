# Phase 0 — Local development

## Engine

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".\engine[dev]"
.\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir engine --reload
```

The API is available at `http://127.0.0.1:8000`; `GET /health` initializes
`data/devflow.db` and reports whether the accepted schema is ready.

## Frontend

```powershell
Set-Location frontend
npm.cmd install
npm.cmd run dev
```

Open `http://localhost:5173`. The status panel confirms that both the engine and
SQLite schema are available.

## Checks

```powershell
.\.venv\Scripts\python.exe -m pytest engine/tests
npm.cmd --prefix frontend run lint
npm.cmd --prefix frontend run build
```
