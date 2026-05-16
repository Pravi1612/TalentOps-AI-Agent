# TalentOps Agent

> Resume screening + interview prep, automated with Claude. Cuts panel prep from **45–90 min per candidate to under 5**.

Upload 3–10 resume PDFs and a role description. Get back, for every candidate: a structured profile, a fitment analysis, a tailored 10–14 question interview bank, a panelist feedback DOCX, and a slate-wide comparison + compliance dashboard.

**Stack:** Python 3.11+ · FastAPI · Claude Sonnet 4 · React (Vite) · Tailwind

---

## Why this exists

Hiring panels waste hours per candidate stitching together resumes, JDs, and scoring rubrics into question banks and feedback forms. This tool runs that stitching as a six-step agent pipeline and produces ready-to-use artifacts in seconds.

It runs **fully offline by default** — no API key required — via a deterministic mock LLM, so you can demo, dev, and test end-to-end without any cost.

---

## Quick start

### Prerequisites

- Python 3.11+
- Node 18+
- (Optional) An Anthropic API key. Without one, the app runs in mock mode.

### 1. Clone

```bash
git clone https://github.com/<you>/talentops-agent.git
cd talentops-agent
```

### 2. Backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1       # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
copy ..\.env.example ..\.env       # macOS/Linux: cp ../.env.example ../.env
uvicorn main:app --reload --port 8000
```

### 3. Frontend (new terminal)

```bash
cd frontend
npm install
npm run dev
```

### 4. Open the app

<http://localhost:5173>

Upload 3–10 resume PDFs, paste a role description, click **Run analysis**. Generated artifacts download from the results screen.

> **Note:** In mock mode any PDF works — content is parsed but stub responses are deterministic and don't depend on it. A yellow banner in the UI confirms mock mode is active.

---

## Switching to real Claude

Edit `.env`:

```env
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-...your-real-key...
```

Restart the backend. That's it — the mock banner disappears and real LLM calls take over.

---

## How it works

```
┌─────────────────────────────────────────────────────────────────┐
│  Upload: 3–10 resume PDFs + role description + (optional)       │
│          evaluation checklist JSON                              │
└──────────────────────────────┬──────────────────────────────────┘
                               ▼
   ┌───────────────────────────────────────────────────────────┐
   │  Step 1  Ingest & parse PDFs (pdfplumber → pypdf)         │
   │  Step 2  Extract structured CandidateProfile              │
   │  Step 3  Score fitment (Meets / Partially / Does Not)     │
   │  Step 4  Generate 10–14 tailored interview questions      │
   │  Step 5  Build panelist feedback DOCX                     │
   │  Step 6  Aggregate comparison + compliance + briefing     │
   └───────────────────────────────┬───────────────────────────┘
                                   ▼
┌─────────────────────────────────────────────────────────────────┐
│  Outputs: per-candidate feedback DOCX, comparison XLSX,         │
│           interactive HTML dashboard, JSON results bundle       │
└─────────────────────────────────────────────────────────────────┘
```

Each step is a single Python module under [backend/agents/](backend/agents/). Steps 2, 3, 4, and 6 call Claude with a prompt loaded from [backend/prompts/](backend/prompts/) and validate the response against a Pydantic schema in [backend/schemas/](backend/schemas/).

**Guardrails:**
- Fitment uses **qualitative ratings only** (no numeric scores) to avoid bias amplification.
- The question prompt explicitly forbids probing protected characteristics.
- Every Claude call is logged (prompt hash only, no PII) to `backend/logs/audit.jsonl`.
- Every output is labelled **"AI-assisted analysis — recruiter review required"**.

---

## Project structure

```
talentops-agent/
├── README.md                       ← you are here
├── CLAUDE.md                       project spec (source of truth)
├── .env.example                    env var template
├── docs/                           planning notes and prompt drafts
├── backend/
│   ├── main.py                     FastAPI entrypoint, 4 endpoints
│   ├── config.py                   env loading, provider auto-detection
│   ├── llm.py                      Anthropic / mock dispatcher
│   ├── mock_provider.py            deterministic stub LLM
│   ├── agents/                     pipeline steps + orchestrator
│   ├── parsers/                    PDF text extraction
│   ├── schemas/                    Pydantic models
│   ├── exporters/                  DOCX, XLSX, HTML writers
│   ├── prompts/                    LLM prompt templates (.md)
│   └── tests/                      pytest + HTTP smoke test
└── frontend/
    ├── src/
    │   ├── App.jsx
    │   ├── api/client.js           axios wrapper
    │   └── components/             upload, processing, results views
    └── package.json
```

---

## API

All endpoints are mounted under `/api/v1`.

| Method | Path                                | Purpose                                  |
|--------|-------------------------------------|------------------------------------------|
| GET    | `/health`                           | Liveness + active provider               |
| POST   | `/ingest`                           | Upload resumes + checklist, start a run  |
| GET    | `/session/{session_id}/status`      | Poll pipeline progress (step 1–6)        |
| GET    | `/session/{session_id}/results`     | Fetch the final analysis bundle          |
| GET    | `/download/{filename}`              | Stream a generated artifact              |

`POST /ingest` accepts `multipart/form-data`:
- `resumes` — 3 to 10 PDF files
- `role_description` — free text *or* a `role_description_file` PDF/TXT upload
- `checklist` — JSON string matching `EvaluationChecklist` (optional; auto-derived from the role description if omitted)

See [backend/main.py](backend/main.py) for full request/response shapes.

---

## Testing

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
pytest tests/ -v
```

10 unit tests cover the PDF parser, every Pydantic schema, and the orchestrator happy-path (with all LLM steps mocked).

End-to-end smoke test (runs the full HTTP flow against an in-process app):

```powershell
python -m tests.smoke_http
```

---

## Configuration

| Variable            | Default                   | Purpose                                            |
|---------------------|---------------------------|----------------------------------------------------|
| `ANTHROPIC_API_KEY` | *(unset)*                 | Real Claude API key                                |
| `LLM_PROVIDER`      | auto                      | `mock` or `anthropic`; auto-detected from the key  |
| `BACKEND_PORT`      | `8000`                    | Uvicorn port                                       |
| `FRONTEND_ORIGIN`   | `http://localhost:5173`   | CORS allow-origin                                  |
| `OUTPUT_DIR`        | `./output`                | Where generated artifacts are written              |

---

## License

This project is provided as-is for educational and demonstration purposes.

See [CLAUDE.md](CLAUDE.md) for the full project specification and design rationale.
