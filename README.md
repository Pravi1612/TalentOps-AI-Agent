# TalentOps Agent

Interview Panel / Resume Screening Assistant. See [CLAUDE.md](CLAUDE.md) for the full project spec.

## Run locally (no API key required)

The backend auto-detects: if no `ANTHROPIC_API_KEY` is set, it runs in **mock mode** — deterministic, schema-valid stub responses so you can exercise the full UI without any LLM. A yellow banner in the UI confirms mock mode.

### 1. Backend (Windows / PowerShell)

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy ..\.env.example ..\.env
uvicorn main:app --reload --port 8000
```

### 2. Frontend

```powershell
cd frontend
npm install
npm run dev
```

Open <http://localhost:5173>.

Upload 3–10 PDF resumes (any PDFs will do in mock mode — content is parsed but the stub responses don't depend on it), paste a role description, edit the checklist, click **Run analysis**.

## Switching to real Claude

Edit `.env`:

```
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-...your-real-key...
```

Restart the backend.

## Tests

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
pytest tests/ -v
```

## Status

Full end-to-end build per [CLAUDE.md §10](CLAUDE.md). 10/10 backend tests pass. Frontend covers upload → progress → comparison → compliance → per-candidate cards → question banks → artifact downloads.
