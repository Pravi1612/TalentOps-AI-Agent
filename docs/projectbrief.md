# Project Brief — TalentOps Agent

> One-page summary of what this project is, who it is for, and what success looks like.

---

## 1. Project name

**TalentOps Agent** — an AI-assisted interview panel and resume screening assistant.

## 2. Problem statement

Hiring panels spend **45–90 minutes per candidate** preparing for interviews: reading resumes, scoring them against role requirements, drafting tailored questions, building feedback templates, and assembling side-by-side comparisons. The work is repetitive, inconsistent across panelists, and prone to bias. Compliance items (background verification, right-to-work, video consent) are tracked in spreadsheets and easy to miss.

## 3. Target users

- **Primary:** Recruiters and hiring managers preparing for interview panels
- **Secondary:** Interview panelists who need consistent rubrics and pre-formatted feedback templates
- **Tertiary:** Talent operations / compliance teams who need an audit trail

## 4. What the agent does

Given **3–10 PDF resumes** + a role description + an evaluation checklist (JSON), the agent produces a complete panel-ready briefing pack:

1. Structured candidate profile per resume
2. Must-have / nice-to-have / red-flag fitment analysis (qualitative ratings only)
3. Tailored 10–14 question interview bank per candidate
4. Pre-formatted panelist feedback template (`.docx`)
5. Side-by-side candidate comparison view (`.xlsx`)
6. Compliance gap report and panel briefing dashboard (`.html`)

## 5. Success metric

**Reduce per-candidate screening prep from 45–90 minutes to under 5 minutes** — a >90% time reduction — while improving consistency, coverage of gap-probing questions, and compliance hygiene.

## 6. Solution overview

- **Frontend:** React 18 (Vite + JavaScript) + Tailwind CSS, uploads resumes and streams progress
- **Backend:** Python 3.11+ / FastAPI orchestrator dispatching six step-agents
- **LLM:** Claude Sonnet 4 (`claude-sonnet-4-20250514`) via the Anthropic SDK
- **Validation:** Pydantic v2 with `TypeAdapter` for every structured Claude response, one retry on parse failure
- **Exports:** `python-docx`, `openpyxl`, Jinja-based HTML

See [CLAUDE.md](CLAUDE.md) for the full source-of-truth spec.

## 7. Scope — in / out

**In scope for v1:**
- PDF resume ingestion (English)
- Role description as text or PDF
- Checklist-driven fitment analysis with qualitative ratings
- Six-step orchestrated workflow
- Word / Excel / HTML artifact exports
- Audit log with PII redaction
- Recruiter-facing web UI

**Out of scope for v1 (see [plan.md](plan.md) → roadmap):**
- ATS integrations (Workday, Greenhouse, SmartRecruiters)
- Multi-language resumes
- Live in-interview co-pilot
- Calibration loop using actual hire / no-hire outcomes
- Automated artifact purge cron (intent documented; manual for v1)

## 8. Constraints & guardrails

- **Bias avoidance:** prompts forbid probing protected characteristics (age, marital status, religion, national origin, disability)
- **No numerical scores:** qualitative ratings only — `Meets` / `Partially Meets` / `Does Not Meet`, `Present` / `Absent`, `None` / `Minor` / `Major`
- **Human-in-the-loop:** every output is labelled "AI-assisted analysis — recruiter review required"
- **No PII in logs:** candidate names and emails redacted
- **Audit trail:** prompt hash, model, timestamp, and `session_id` logged for every Claude call to `backend/logs/audit.jsonl`
- **Data retention:** artifacts in `/output` purged after 30 days (intent for v1)

## 9. Key risks

| Risk | Mitigation |
|---|---|
| Hallucinated profile fields | Pydantic validation + retry-on-parse-failure pattern |
| Biased question generation | Explicit prompt constraint + human review label on UI |
| PDF parse failures | `pdfplumber` primary, `pypdf` fallback |
| Schema drift between Claude versions | Pin model ID (`claude-sonnet-4-20250514`); regression tests on fixtures |
| Leaked candidate PII | Redact in logs; restrict artifact downloads behind session ID |

## 10. Stakeholders

- **Project owner:** Praveen CK (praveen.ck2@cognizant.com)
- **Sponsor:** Cognizant Hackathon 2026
- **Reviewers:** Hiring partners, talent ops, compliance / legal

## 11. Related documents

- [CLAUDE.md](CLAUDE.md) — engineering source of truth (architecture, schemas, prompts, build order)
- [plan.md](plan.md) — milestone-by-milestone build plan and roadmap
- [prompts.md](prompts.md) — index of all Claude prompts and how they wire to schemas
