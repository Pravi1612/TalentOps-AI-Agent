# Prompts Index — TalentOps Agent

> All Claude prompts live as Markdown files in [backend/prompts/](backend/prompts/) so non-engineers can edit them. This page indexes them, explains how each one wires into the pipeline, and documents the conventions every prompt follows.

---

## Conventions every prompt must follow

1. **Return JSON only.** No markdown fences, no commentary, no preamble — the Python side parses with `pydantic.TypeAdapter`.
2. **Match the schema exactly.** Field names, optionality, and enums must mirror the corresponding Pydantic model in [backend/schemas/](backend/schemas/).
3. **Template variables use `{{NAME}}` (double-brace UPPER_SNAKE_CASE).** They are substituted by Python `str.replace` in each agent's code.
4. **Bias avoidance is non-negotiable.** Prompts must not generate, infer, or probe protected characteristics (age, marital status, religion, national origin, disability).
5. **Qualitative only.** Never assign numerical scores — use the controlled-vocabulary ratings defined in [CLAUDE.md](CLAUDE.md) §4 Step 3.
6. **Grounded justifications.** Every rating or claim must cite specific resume evidence in 1–2 sentences.

Model and decoding parameters per call (from [CLAUDE.md](CLAUDE.md) §7):

| Step | Model | max_tokens | temperature |
|---|---|---:|---:|
| Profile extraction | `claude-sonnet-4-20250514` | 4096 | 0.2 |
| Fitment analysis | `claude-sonnet-4-20250514` | 4096 | 0.2 |
| Question generation | `claude-sonnet-4-20250514` | 8192 | 0.5 |
| Comparison summary | `claude-sonnet-4-20250514` | 4096 | 0.2 |
| Derive checklist | `claude-sonnet-4-20250514` | 4096 | 0.2 |

Every call is wrapped in `call_claude_structured(...)` with **one retry on Pydantic parse failure**, where the validation error is appended to the user message on the retry.

---

## Prompt registry

### 1. [profile_extraction.md](backend/prompts/profile_extraction.md)
- **Used by:** [step2_profile.py](backend/agents/step2_profile.py)
- **Variables:** `{{RESUME_TEXT}}`
- **Returns:** `CandidateProfile` ([backend/schemas/candidate.py](backend/schemas/candidate.py))
- **Purpose:** Parse a single resume's raw text into a structured profile (work history, skills, education, industry exposure, progression pattern, resume flags).
- **Key rules:**
  - Tenure is computed in months as an integer; `end_date` may be `"Present"`
  - `career_progression` is one of `growth | lateral | mixed`
  - `resume_flags[].type` is one of `gap | short_tenure | inconsistency`

### 2. [fitment_analysis.md](backend/prompts/fitment_analysis.md)
- **Used by:** [step3_fitment.py](backend/agents/step3_fitment.py)
- **Variables:** `{{CANDIDATE_PROFILE_JSON}}`, `{{CHECKLIST_JSON}}`
- **Returns:** `FitmentAnalysis` ([backend/schemas/candidate.py](backend/schemas/candidate.py))
- **Purpose:** Compare profile to checklist and rate fit, qualitatively.
- **Controlled vocabulary:**
  - Must-haves → `Meets | Partially Meets | Does Not Meet`
  - Nice-to-haves → `Present | Absent`
  - Red flags → `None | Minor | Major`
- **Hard rule:** No numerical scores. Each rating must include a justification grounded in resume evidence.

### 3. [question_generation.md](backend/prompts/question_generation.md)
- **Used by:** [step4_questions.py](backend/agents/step4_questions.py)
- **Variables:** `{{CANDIDATE_PROFILE_JSON}}`, `{{FITMENT_ANALYSIS_JSON}}`, `{{ROLE_DESCRIPTION}}`
- **Returns:** `QuestionBank` ([backend/schemas/questions.py](backend/schemas/questions.py))
- **Purpose:** Produce 10–14 questions per candidate, distributed across the four categories.
- **Category mix:**
  - Technical Depth — validates declared skills
  - Behavioural Scenarios — STAR-format, tied to competencies
  - Gap Probing — targets gaps / short tenures / mismatches from Step 3
  - Situational — grounded in real role challenges
- **Hard rule:** Never probe protected characteristics. The prompt states this constraint explicitly.

### 4. [comparison_summary.md](backend/prompts/comparison_summary.md)
- **Used by:** [step6_comparison.py](backend/agents/step6_comparison.py)
- **Variables:** `{{CANDIDATES_JSON}}`, `{{CHECKLIST_JSON}}`
- **Returns:** Comparison + compliance gap data structure consumed by [xlsx_exporter.py](backend/exporters/xlsx_exporter.py) and [html_exporter.py](backend/exporters/html_exporter.py)
- **Purpose:** Generate side-by-side comparison and panel briefing summary across all candidates in the session.
- **Output expectations:**
  - Per-candidate must-have rating row
  - Red-flag status column
  - Recommended question focus areas
  - Compliance gap flags per candidate

### 5. [derive_checklist.md](backend/prompts/derive_checklist.md)
- **Used by:** [derive_checklist.py](backend/agents/derive_checklist.py)
- **Variables:** `{{ROLE_DESCRIPTION}}`
- **Returns:** `EvaluationChecklist` ([backend/schemas/checklist.py](backend/schemas/checklist.py))
- **Purpose:** Helper agent — when a recruiter has a role description but no checklist, derive a starter checklist they can edit.
- **Not part of the canonical 6-step flow** — it is an optional pre-step exposed via the UI's ChecklistEditor.

---

## How prompts wire into the pipeline

```
POST /api/v1/ingest
    │
    ▼
Step 1 — Ingestion (pdf_parser.py)            ──►  raw resume text
    │
    ▼
Step 2 — profile_extraction.md                ──►  CandidateProfile (×N)
    │
    ▼
Step 3 — fitment_analysis.md                  ──►  FitmentAnalysis (×N)
    │
    ▼
Step 4 — question_generation.md               ──►  QuestionBank (×N)
    │
    ▼
Step 5 — feedback template (no LLM call)      ──►  FeedbackTemplate.docx (×N)
    │
    ▼
Step 6 — comparison_summary.md                ──►  comparison.xlsx + dashboard.html
```

`derive_checklist.md` runs **before** Step 1 only when the recruiter chooses to auto-generate a checklist.

---

## Editing a prompt safely

When tweaking a prompt:

1. **Do not change template variable names** (`{{CANDIDATE_PROFILE_JSON}}`, etc.) without updating the calling agent in [backend/agents/](backend/agents/).
2. **Keep the JSON schema description in the prompt aligned** with the matching Pydantic model. Drift here causes parse failures — Pydantic's error is appended on retry, but two failures fail the step.
3. **Run the relevant test in [backend/tests/](backend/tests/)** before merging. Each step has a fixture-based test that exercises a representative resume.
4. **Check the audit log** at `backend/logs/audit.jsonl` after a manual smoke test — verify the prompt hash changed (proof your edit shipped) and there's no PII leakage.

---

## Related documents

- [CLAUDE.md](CLAUDE.md) — full engineering spec, including prompt design rationale (§7, §11, §12)
- [projectbrief.md](projectbrief.md) — one-page project summary
- [plan.md](plan.md) — milestone-by-milestone build plan
