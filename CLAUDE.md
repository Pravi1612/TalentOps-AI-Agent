  # CLAUDE.md — Interview Panel / Resume Screening Assistant

> **Project codename:** TalentOps Agent
> **Purpose:** This file is the source of truth for Claude Code when building, extending, or debugging this project. Read it before generating any code.

---

## 1. Project overview

A TalentOps agent that ingests a batch of candidate resumes alongside a role description and evaluation checklist, then produces:

1. Structured candidate profile per resume
2. Must-have / nice-to-have / red-flag fitment analysis
3. Tailored 10–14 question interview bank per candidate
4. Pre-formatted panelist feedback template
5. Side-by-side candidate comparison view
6. Compliance gap report
7. Panel briefing summary document

**Business impact target:** Reduce per-candidate screening prep from 45–90 minutes to under 5 minutes.

---

## 2. Tech stack

| Layer | Technology |
|---|---|
| Frontend | React.js (Vite + JavaScript) |
| Backend | Python 3.11+ (FastAPI) |
| LLM | Claude Sonnet 4 (`claude-sonnet-4-20250514`) via Anthropic SDK |
| PDF parsing | `pdfplumber` (primary), `pypdf` (fallback) |
| Document output | `python-docx` (Word), `openpyxl` (Excel) |
| Schema validation | `pydantic` v2 |
| API client (frontend) | `axios` |
| Styling | Tailwind CSS |
| State management | React hooks (no Redux needed for v1) |

---

## 3. Repository structure

```
talentops-agent/
├── CLAUDE.md                       # ← you are here
├── README.md                       # human-facing setup instructions
├── .env.example                    # ANTHROPIC_API_KEY=...
├── .gitignore
│
├── backend/
│   ├── requirements.txt
│   ├── main.py                     # FastAPI entrypoint
│   ├── config.py                   # env loading, constants
│   │
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── orchestrator.py         # ties all 6 steps together
│   │   ├── step1_ingestion.py
│   │   ├── step2_profile.py
│   │   ├── step3_fitment.py
│   │   ├── step4_questions.py
│   │   ├── step5_feedback.py
│   │   └── step6_comparison.py
│   │
│   ├── parsers/
│   │   ├── __init__.py
│   │   └── pdf_parser.py           # pdfplumber wrapper
│   │
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── checklist.py            # EvaluationChecklist pydantic model
│   │   ├── candidate.py            # CandidateProfile, FitmentAnalysis
│   │   ├── questions.py            # QuestionBank
│   │   └── feedback.py             # FeedbackTemplate
│   │
│   ├── exporters/
│   │   ├── __init__.py
│   │   ├── docx_exporter.py        # panelist feedback → .docx
│   │   ├── xlsx_exporter.py        # comparison → .xlsx
│   │   └── html_exporter.py        # dashboard → .html
│   │
│   ├── prompts/                    # all Claude prompts as .md files
│   │   ├── profile_extraction.md
│   │   ├── fitment_analysis.md
│   │   ├── question_generation.md
│   │   └── comparison_summary.md
│   │
│   └── tests/
│       ├── fixtures/               # sample resumes, checklists
│       └── test_*.py
│
├── frontend/
│   ├── package.json
│   ├── vite.config.js
│   ├── tailwind.config.js
│   ├── index.html
│   └── src/
│       ├── main.jsx
│       ├── App.jsx
│       ├── api/
│       │   └── client.js           # axios wrapper
│       ├── components/
│       │   ├── UploadPanel.jsx     # resume + JD + checklist upload
│       │   ├── ChecklistEditor.jsx
│       │   ├── ProcessingView.jsx  # step-by-step progress
│       │   ├── CandidateCard.jsx
│       │   ├── ComparisonTable.jsx
│       │   ├── QuestionBankView.jsx
│       │   └── ComplianceReport.jsx
│       └── styles/
│           └── index.css
│
└── output/                         # generated artifacts land here
    ├── profiles/
    ├── feedback_templates/
    ├── comparison_reports/
    └── compliance_reports/
```

---

## 4. The six-step agent workflow

### Step 1 — Resume and role description ingestion
- Recruiter uploads **3–10 PDF resumes** + role description (text or PDF) + evaluation checklist (JSON).
- Backend endpoint: `POST /api/v1/ingest`
- The checklist JSON defines: must-have skills, nice-to-have skills, red-flag indicators, years-of-experience thresholds, and mandatory compliance checks (background verification, right-to-work, video consent).
- Each resume is parsed via `pdfplumber` into raw text + page metadata.

### Step 2 — Structured candidate profile extraction
For each resume, Claude extracts and normalises:
- Work history (company, role, tenure, responsibilities)
- Technical skills and certifications
- Educational background
- Industry domain exposure
- Notable achievements / impact statements
- Career progression pattern (growth vs lateral)
- Resume flags: unexplained gaps, very short tenures, role/responsibility inconsistencies

Output: `CandidateProfile` pydantic model serialised to JSON.

### Step 3 — Fitment analysis against role requirements
For each candidate, score across three dimensions:
- **Must-haves:** `Meets` / `Partially Meets` / `Does Not Meet` per criterion
- **Nice-to-haves:** `Present` / `Absent` per criterion
- **Red flags:** `None` / `Minor` / `Major`

**Important:** Use qualitative ratings, not numerical scores, to avoid bias-amplifying scoring. Each rating includes a brief justification.

### Step 4 — Tailored interview question bank generation
Generate **10–14 questions per candidate** across four categories:
1. **Technical Depth** — validates declared skills
2. **Behavioural Scenarios** — STAR-format, tied to role competencies
3. **Gap Probing** — addresses gaps, short tenures, mismatches from Step 3
4. **Situational / Role-Specific** — grounded in actual role challenges

### Step 5 — Panelist feedback template generation
A pre-formatted template per candidate containing:
- Candidate name + role
- Rating scale per competency (with definitions)
- Free-text observation field per competency
- Red flags section
- Overall recommendation: `Proceed` / `Hold` / `Decline` with mandatory justification
- Compliance checklist (video consent, right-to-work, mandatory questions asked)

Exported as `.docx` via `python-docx`.

### Step 6 — Candidate comparison summary + compliance report
- Side-by-side table: all candidates' must-have ratings, red-flag status, recommended question focus areas
- Compliance gap report: flags any missing mandatory items per candidate
- Panel briefing summary document

Exported as `.xlsx` (table) and `.html` (dashboard).

---

## 5. API contracts

### `POST /api/v1/ingest`
**Request (multipart/form-data):**
- `resumes`: array of PDF files (3–10)
- `role_description`: string or PDF file
- `checklist`: JSON string conforming to `EvaluationChecklist` schema

**Response:**
```json
{
  "session_id": "uuid",
  "candidate_count": 5,
  "status": "processing"
}
```

### `GET /api/v1/session/{session_id}/status`
Returns progress per step (1–6) for streaming UI updates.

### `GET /api/v1/session/{session_id}/results`
Returns full results bundle:
```json
{
  "candidates": [...],
  "comparison": {...},
  "compliance_report": {...},
  "artifact_urls": {
    "feedback_templates_docx": "/output/...",
    "comparison_xlsx": "/output/...",
    "dashboard_html": "/output/..."
  }
}
```

### `GET /api/v1/download/{filename}`
Streams generated artifacts.

---

## 6. Evaluation checklist schema

```python
# backend/schemas/checklist.py
from pydantic import BaseModel
from typing import List

class SkillRequirement(BaseModel):
    name: str
    description: str | None = None

class ComplianceCheck(BaseModel):
    name: str
    required: bool = True
    description: str

class EvaluationChecklist(BaseModel):
    role_title: str
    must_have_skills: List[SkillRequirement]
    nice_to_have_skills: List[SkillRequirement]
    red_flag_indicators: List[str]
    min_years_experience: int
    max_years_experience: int | None = None
    compliance_checks: List[ComplianceCheck]
```

**Example input:**
```json
{
  "role_title": "Senior Backend Engineer",
  "must_have_skills": [
    {"name": "Python", "description": "5+ years production experience"},
    {"name": "Distributed systems", "description": "Designed services at scale"}
  ],
  "nice_to_have_skills": [
    {"name": "Kubernetes"},
    {"name": "Go"}
  ],
  "red_flag_indicators": [
    "Job-hopping with <12 month tenures",
    "Unexplained gap > 12 months",
    "Title/responsibility mismatch"
  ],
  "min_years_experience": 5,
  "compliance_checks": [
    {"name": "Background verification", "required": true, "description": "BGV consent and clearance"},
    {"name": "Right to work", "required": true, "description": "Work authorisation confirmed"},
    {"name": "Video consent", "required": true, "description": "Recording consent form signed"}
  ]
}
```

---

## 7. Claude integration patterns

**Always use the Messages API with structured output.** For each step that calls Claude:

1. Load the prompt from `backend/prompts/<step>.md`
2. Inject the candidate text + checklist as variables
3. Instruct Claude to return **only** valid JSON matching the expected pydantic schema
4. Parse with `pydantic.TypeAdapter` for validation
5. On parse failure, retry once with the error message appended

**Model:** `claude-sonnet-4-20250514`
**Max tokens:** 4096 per call (8192 for question bank generation)
**Temperature:** 0.2 for extraction/analysis steps, 0.5 for question generation

**Pseudocode for each step:**
```python
import anthropic
from pydantic import TypeAdapter

client = anthropic.Anthropic()

def call_claude_structured(prompt: str, schema_class):
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4096,
        temperature=0.2,
        messages=[{"role": "user", "content": prompt}]
    )
    raw = response.content[0].text
    cleaned = raw.strip().removeprefix("```json").removesuffix("```").strip()
    return TypeAdapter(schema_class).validate_json(cleaned)
```

---

## 8. Setup instructions

### Backend
```bash
cd backend
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp ../.env.example ../.env         # add your ANTHROPIC_API_KEY
uvicorn main:app --reload --port 8000
```

**`requirements.txt`:**
```
fastapi==0.115.0
uvicorn[standard]==0.32.0
python-multipart==0.0.12
pdfplumber==0.11.4
pypdf==5.0.0
python-docx==1.1.2
openpyxl==3.1.5
pydantic==2.9.0
anthropic==0.39.0
python-dotenv==1.0.1
```

### Frontend
```bash
cd frontend
npm install
npm run dev                        # serves on http://localhost:5173
```

**`package.json` dependencies:**
```json
{
  "dependencies": {
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "axios": "^1.7.7"
  },
  "devDependencies": {
    "@vitejs/plugin-react": "^4.3.3",
    "vite": "^5.4.10",
    "tailwindcss": "^3.4.14",
    "postcss": "^8.4.47",
    "autoprefixer": "^10.4.20"
  }
}
```

### Environment variables (`.env`)
```
ANTHROPIC_API_KEY=sk-ant-...
BACKEND_PORT=8000
FRONTEND_ORIGIN=http://localhost:5173
OUTPUT_DIR=./output
```

---

## 9. Coding conventions for Claude Code

When Claude generates code in this repo, it must follow these rules:

- **Backend:** Use type hints everywhere. Validate all I/O with pydantic. Use `async def` for FastAPI endpoints. Log structured events with `logging` (not `print`).
- **Frontend:** Functional components only. Use hooks (`useState`, `useEffect`). Keep components under 200 lines — split when larger. Tailwind classes inline; no separate CSS files except `index.css` for resets.
- **Error handling:** Every Claude API call is wrapped in try/except with one retry. Every file I/O checks existence first.
- **No hardcoded secrets.** Always read from `os.environ`.
- **No global mutable state** in the backend — use FastAPI dependency injection.
- **Prompts live in `backend/prompts/*.md`**, not in Python string literals, so non-engineers can edit them.
- **Tests:** Use `pytest`. Cover at least the parser, each step's schema validation, and the orchestrator happy path.

---

## 10. Build order (recommended for Claude Code sessions)

When asked to "build the project", proceed in this order. Verify each step works before moving on.

1. **Project scaffold** — create folder structure, empty files, `requirements.txt`, `package.json`
2. **PDF parser** (`backend/parsers/pdf_parser.py`) — extract text from a sample resume
3. **Schemas** (`backend/schemas/*.py`) — all pydantic models first
4. **Step 2: profile extraction** — single-candidate Claude call, validated output
5. **Step 3: fitment analysis** — depends on Step 2 output
6. **Step 4: question bank** — depends on Steps 2 + 3
7. **Step 5: feedback template** — DOCX export
8. **Step 6: comparison + compliance** — XLSX + HTML export
9. **Orchestrator** (`backend/agents/orchestrator.py`) — wire steps 1→6
10. **FastAPI endpoints** (`backend/main.py`)
11. **Frontend scaffold** — Vite + Tailwind setup
12. **UploadPanel + ChecklistEditor** components
13. **ProcessingView** — polls status endpoint
14. **Results views** — CandidateCard, ComparisonTable, ComplianceReport
15. **End-to-end test** with 3 sample resumes

---

## 11. Sample prompts (excerpts)

### `backend/prompts/profile_extraction.md`
```
You are a resume parsing assistant. Extract structured information from the resume text below.

Return ONLY a JSON object matching this schema (no markdown, no commentary):
{
  "full_name": str,
  "email": str | null,
  "phone": str | null,
  "total_years_experience": float,
  "work_history": [
    {"company": str, "role": str, "start_date": "YYYY-MM", "end_date": "YYYY-MM | Present",
     "tenure_months": int, "responsibilities": [str], "achievements": [str]}
  ],
  "skills": {"technical": [str], "certifications": [str]},
  "education": [{"degree": str, "institution": str, "year": int}],
  "industry_domains": [str],
  "career_progression": "growth" | "lateral" | "mixed",
  "resume_flags": [{"type": "gap" | "short_tenure" | "inconsistency", "detail": str}]
}

Resume text:
---
{{RESUME_TEXT}}
---
```

### `backend/prompts/fitment_analysis.md`
```
You are a hiring analyst. Compare the candidate profile to the role checklist and produce
a fitment analysis using ONLY the qualitative ratings specified.

Do NOT assign numerical scores. Use:
- Must-haves: "Meets" | "Partially Meets" | "Does Not Meet"
- Nice-to-haves: "Present" | "Absent"
- Red flags: "None" | "Minor" | "Major"

Provide a 1–2 sentence justification for each rating, grounded in specific resume evidence.

Return JSON only, matching the FitmentAnalysis schema.

Candidate profile:
{{CANDIDATE_PROFILE_JSON}}

Role checklist:
{{CHECKLIST_JSON}}
```

(Question generation and comparison prompts follow the same pattern — see `backend/prompts/` once scaffolded.)

---

## 12. Constraints and guardrails

- **Bias avoidance:** Never generate questions that probe protected characteristics (age, marital status, religion, national origin, disability). The question generation prompt must include this constraint explicitly.
- **Human-in-the-loop:** The agent's fitment ratings are advisory. The UI must clearly label outputs as "AI-assisted analysis — recruiter review required."
- **Data retention:** Generated artifacts in `/output` should be purged after 30 days (cron job, out of scope for v1 but document the intent).
- **Audit trail:** Every Claude call logs the prompt hash, model, timestamp, and session_id to a JSON-lines file in `backend/logs/audit.jsonl`.
- **No PII in logs.** Candidate names and emails are redacted from log lines.

---

## 13. Running the project end-to-end

```bash
# Terminal 1 — backend
cd backend && uvicorn main:app --reload --port 8000

# Terminal 2 — frontend
cd frontend && npm run dev

# Open http://localhost:5173
# Upload 3–10 resumes, paste role description, edit checklist JSON, click "Run analysis"
# Download generated artifacts from the results screen
```

---

## 14. What to ask Claude Code next

After reading this file, ask Claude Code one of:
- "Scaffold the full project structure with empty files and dependency files."
- "Implement the PDF parser and write a unit test using a sample resume."
- "Implement Step 2 (profile extraction) end-to-end with a test."
- "Build the React UploadPanel component."

Build one slice end-to-end before broadening. Do not generate all six steps in one shot — it produces brittle code.
