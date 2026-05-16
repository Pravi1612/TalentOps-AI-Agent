# Build Plan — TalentOps Agent

> Milestone-by-milestone delivery plan, mapped to the 15-step build order in [CLAUDE.md](CLAUDE.md) §10.
> Build one slice end-to-end before broadening — do not generate all six agent steps in one shot.

---

## Status at a glance

| Milestone | Status |
|---|---|
| M1 — Scaffold & PDF parser | ✅ Done |
| M2 — Schemas | ✅ Done |
| M3 — Step 2: profile extraction | ✅ Done |
| M4 — Step 3: fitment analysis | ✅ Done |
| M5 — Step 4: question bank | ✅ Done |
| M6 — Step 5: feedback template (DOCX) | ✅ Done |
| M7 — Step 6: comparison + compliance (XLSX/HTML) | ✅ Done |
| M8 — Orchestrator + FastAPI endpoints | ✅ Done |
| M9 — Frontend MVP | ✅ Done |
| M10 — End-to-end test with sample resumes | 🚧 In progress |
| M11 — Hackathon presentation pack | ✅ Done |
| M12 — Hardening & roadmap items | ⏳ Planned |

---

## Milestone 1 — Scaffold & PDF parser

**Goal:** Empty project compiles and a sample resume parses to text.

- [x] Create folder structure per [CLAUDE.md](CLAUDE.md) §3
- [x] `backend/requirements.txt`, `frontend/package.json`, `.env.example`
- [x] `backend/parsers/pdf_parser.py` — `pdfplumber` primary, `pypdf` fallback
- [x] Unit test against a sample resume in `backend/tests/fixtures/`

**Deliverable:** `pytest backend/tests/test_pdf_parser.py` green.

---

## Milestone 2 — Schemas

**Goal:** Every Pydantic model exists so subsequent steps can validate against them.

- [x] `schemas/checklist.py` — `EvaluationChecklist`, `SkillRequirement`, `ComplianceCheck`
- [x] `schemas/candidate.py` — `CandidateProfile`, `FitmentAnalysis`
- [x] `schemas/questions.py` — `QuestionBank`
- [x] `schemas/feedback.py` — `FeedbackTemplate`
- [x] Round-trip tests: `model_dump_json()` → `model_validate_json()` for each

---

## Milestone 3 — Step 2: profile extraction

**Goal:** A single resume produces a validated `CandidateProfile` end-to-end.

- [x] `agents/step2_profile.py` — load prompt, call Claude Sonnet 4, validate
- [x] Prompt at `backend/prompts/profile_extraction.md`
- [x] `call_claude_structured` helper with one-retry-on-parse-failure
- [x] Integration test against fixture resume

---

## Milestone 4 — Step 3: fitment analysis

**Goal:** Given a profile and a checklist, produce a `FitmentAnalysis` with qualitative ratings only.

- [x] `agents/step3_fitment.py`
- [x] Prompt at `backend/prompts/fitment_analysis.md` — explicit "no numerical scores" instruction
- [x] Tests verify enum values (`Meets` / `Partially Meets` / `Does Not Meet`)

---

## Milestone 5 — Step 4: question bank

**Goal:** 10–14 questions per candidate, distributed across four categories.

- [x] `agents/step4_questions.py`
- [x] Prompt at `backend/prompts/question_generation.md` with explicit bias-avoidance clause
- [x] `max_tokens=8192`, `temperature=0.5` per [CLAUDE.md](CLAUDE.md) §7

---

## Milestone 6 — Step 5: feedback template

**Goal:** Per-candidate `.docx` feedback template ready for panelists.

- [x] `agents/step5_feedback.py`
- [x] `exporters/docx_exporter.py` using `python-docx`
- [x] Includes rating scale, observation fields, red-flag section, compliance checklist

---

## Milestone 7 — Step 6: comparison + compliance

**Goal:** Side-by-side `.xlsx` comparison plus an `.html` panel briefing.

- [x] `agents/step6_comparison.py`
- [x] Prompt at `backend/prompts/comparison_summary.md`
- [x] `exporters/xlsx_exporter.py` and `exporters/html_exporter.py`

---

## Milestone 8 — Orchestrator + FastAPI endpoints

**Goal:** A single `POST /api/v1/ingest` call drives Steps 1 → 6 and surfaces progress.

- [x] `agents/orchestrator.py` with `SessionState` + `run_pipeline`
- [x] Helper `agents/derive_checklist.py` (auto-derive a checklist from a role description)
- [x] `main.py` endpoints:
  - [x] `POST /api/v1/ingest`
  - [x] `GET /api/v1/session/{session_id}/status`
  - [x] `GET /api/v1/session/{session_id}/results`
  - [x] `GET /api/v1/download/{filename}`
- [x] CORS configured for `FRONTEND_ORIGIN`
- [x] Audit logging to `backend/logs/audit.jsonl` with PII redaction

---

## Milestone 9 — Frontend MVP

**Goal:** Recruiter can drive the full flow from the browser.

- [x] Vite + React + Tailwind scaffold
- [x] `UploadPanel.jsx` — resume + JD + checklist upload
- [x] `ChecklistEditor.jsx` — edit checklist JSON inline
- [x] `ProcessingView.jsx` — polls `/status`, shows per-step progress
- [x] `CandidateCard.jsx`, `ComparisonTable.jsx`, `QuestionBankView.jsx`, `ComplianceReport.jsx`
- [x] Axios wrapper at `frontend/src/api/client.js`

---

## Milestone 10 — End-to-end test (in progress)

**Goal:** Three sample resumes processed without manual intervention; artifacts download cleanly.

- [ ] Add 3 fixture resumes to `backend/tests/fixtures/`
- [ ] Add a fixture role description and checklist JSON
- [ ] Write `backend/tests/test_orchestrator.py` happy-path test
- [ ] Manual smoke test from UI: upload → wait → download all three artifacts

---

## Milestone 11 — Hackathon presentation pack

**Goal:** Demo-ready collateral.

- [x] `TalentOps_Agent_Presentation.docx` generated via `scripts/generate_presentation.py`
- [x] `projectbrief.md`, `plan.md`, `prompts.md` indexes at repo root
- [ ] 5-minute live demo script with sample inputs queued

---

## Milestone 12 — Hardening & roadmap (planned)

### Near-term (next 4–6 weeks)
- [ ] ATS integrations (Workday, Greenhouse, SmartRecruiters) — webhook + REST adapters
- [ ] Multi-language resume support (Spanish, German, Hindi to start)
- [ ] Recorded interview transcript ingestion for post-panel summaries
- [ ] Cron job to purge `/output` after 30 days

### Longer-term
- [ ] Calibration loop — feed hire / no-hire outcomes back to tune fitment rubrics
- [ ] Live in-interview panel co-pilot
- [ ] Role-family templates (engineering, sales, design, ops) shipped out of the box
- [ ] SSO + RBAC for multi-recruiter teams

---

## Definition of done (per milestone)

A milestone is "done" when:
1. Code merged and type-clean (`pyright` or `mypy` if added)
2. Tests pass (`pytest backend/tests/`)
3. Manual smoke test from the UI covers the slice
4. Audit log shows clean entries with no PII leakage
5. Any new prompt is committed under `backend/prompts/` (not inline in Python)

---

## Open questions / risks to retire

- [ ] Where do generated artifacts live in a multi-tenant deployment? (S3 vs. local FS)
- [ ] How long is "session" state retained server-side? Currently in-memory only.
- [ ] Do we need rate-limiting on `/api/v1/ingest` for the hackathon demo? Probably not — single-user.
- [ ] Should `derive_checklist` be exposed as its own endpoint for the demo, or remain internal?
