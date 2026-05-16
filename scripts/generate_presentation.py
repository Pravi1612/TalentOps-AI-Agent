"""Generate a presentation-style Word document for the TalentOps Agent app."""
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from docx.shared import Pt, RGBColor, Inches

OUTPUT = Path(__file__).resolve().parent.parent / "TalentOps_Agent_Presentation.docx"

PRIMARY = RGBColor(0x0B, 0x3D, 0x91)   # deep blue
ACCENT = RGBColor(0x1E, 0x88, 0xE5)    # bright blue
MUTED = RGBColor(0x55, 0x55, 0x55)
DARK = RGBColor(0x1A, 0x1A, 0x1A)


def set_cell_bg(cell, hex_color: str) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hex_color)
    tc_pr.append(shd)


def add_heading(doc, text: str, size: int = 28, color: RGBColor = PRIMARY,
                align=WD_ALIGN_PARAGRAPH.LEFT) -> None:
    p = doc.add_paragraph()
    p.alignment = align
    run = p.add_run(text)
    run.bold = True
    run.font.size = Pt(size)
    run.font.color.rgb = color
    run.font.name = "Calibri"


def add_subheading(doc, text: str, size: int = 16, color: RGBColor = ACCENT) -> None:
    p = doc.add_paragraph()
    run = p.add_run(text)
    run.italic = True
    run.font.size = Pt(size)
    run.font.color.rgb = color


def add_body(doc, text: str, size: int = 12, color: RGBColor = DARK,
             bold: bool = False, align=WD_ALIGN_PARAGRAPH.LEFT) -> None:
    p = doc.add_paragraph()
    p.alignment = align
    run = p.add_run(text)
    run.font.size = Pt(size)
    run.font.color.rgb = color
    run.bold = bold


def add_bullets(doc, items, size: int = 12) -> None:
    for item in items:
        p = doc.add_paragraph(style="List Bullet")
        run = p.add_run(item)
        run.font.size = Pt(size)
        run.font.color.rgb = DARK


def page_break(doc) -> None:
    doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)


def add_section_label(doc, label: str) -> None:
    p = doc.add_paragraph()
    run = p.add_run(label.upper())
    run.bold = True
    run.font.size = Pt(10)
    run.font.color.rgb = ACCENT


def build_two_col_table(doc, rows, header=None):
    table = doc.add_table(rows=0, cols=2)
    table.autofit = True
    if header:
        hdr = table.add_row().cells
        for i, h in enumerate(header):
            hdr[i].text = ""
            run = hdr[i].paragraphs[0].add_run(h)
            run.bold = True
            run.font.size = Pt(11)
            run.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
            set_cell_bg(hdr[i], "0B3D91")
    for left, right in rows:
        row = table.add_row().cells
        row[0].text = ""
        r0 = row[0].paragraphs[0].add_run(left)
        r0.bold = True
        r0.font.size = Pt(11)
        r0.font.color.rgb = PRIMARY
        row[1].text = ""
        r1 = row[1].paragraphs[0].add_run(right)
        r1.font.size = Pt(11)
        r1.font.color.rgb = DARK
    return table


def build():
    doc = Document()

    # Page margins
    for section in doc.sections:
        section.top_margin = Inches(0.7)
        section.bottom_margin = Inches(0.7)
        section.left_margin = Inches(0.8)
        section.right_margin = Inches(0.8)

    # ===== Slide 1: Title =====
    for _ in range(4):
        doc.add_paragraph()
    add_heading(doc, "TalentOps Agent", size=44, align=WD_ALIGN_PARAGRAPH.CENTER)
    add_subheading(doc,
                   "AI-Assisted Interview Panel & Resume Screening Assistant",
                   size=18)
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run(
        "Reducing per-candidate screening prep from 45–90 minutes to under 5"
    )
    run.font.size = Pt(14)
    run.font.color.rgb = MUTED
    for _ in range(6):
        doc.add_paragraph()
    add_body(doc, "Presented by: Praveen CK", size=12, bold=True,
             align=WD_ALIGN_PARAGRAPH.CENTER)
    add_body(doc, "Cognizant  •  Hackathon Submission", size=11,
             color=MUTED, align=WD_ALIGN_PARAGRAPH.CENTER)
    page_break(doc)

    # ===== Slide 2: Agenda =====
    add_section_label(doc, "Agenda")
    add_heading(doc, "What we will cover today", size=26)
    add_bullets(doc, [
        "The hiring bottleneck we are solving",
        "What TalentOps Agent does",
        "Six-step agent workflow",
        "System architecture and tech stack",
        "Live demo flow",
        "Business impact and metrics",
        "Guardrails: bias avoidance, compliance, audit trail",
        "Roadmap and next steps",
    ], size=14)
    page_break(doc)

    # ===== Slide 3: Problem =====
    add_section_label(doc, "The Problem")
    add_heading(doc, "Interview prep is slow, manual, and inconsistent", size=24)
    add_bullets(doc, [
        "Recruiters spend 45–90 minutes per candidate preparing for panels",
        "Resume screening, fitment analysis, and question prep are repeated for every role",
        "Panel feedback varies wildly — no shared rubric, no audit trail",
        "Compliance items (BGV, right-to-work, video consent) are tracked in spreadsheets",
        "Side-by-side comparison across candidates is manual and error-prone",
    ], size=13)
    add_body(doc, "")
    add_body(doc, "Result: slower hiring loops, biased decisions, missed compliance.",
             size=13, bold=True, color=PRIMARY)
    page_break(doc)

    # ===== Slide 4: Solution =====
    add_section_label(doc, "The Solution")
    add_heading(doc, "An AI agent that prepares the entire panel kit", size=24)
    add_body(doc,
             "Upload 3–10 resumes plus a role description and an evaluation "
             "checklist. The agent returns a complete, panel-ready briefing pack.",
             size=13)
    add_body(doc, "")
    add_body(doc, "Deliverables produced per session:", size=13, bold=True)
    add_bullets(doc, [
        "Structured candidate profile per resume",
        "Must-have / nice-to-have / red-flag fitment analysis",
        "Tailored 10–14 question interview bank per candidate",
        "Pre-formatted panelist feedback template (.docx)",
        "Side-by-side candidate comparison view (.xlsx)",
        "Compliance gap report and panel briefing dashboard (.html)",
    ], size=13)
    page_break(doc)

    # ===== Slide 5: Six-step workflow =====
    add_section_label(doc, "How It Works")
    add_heading(doc, "Six-step agent workflow", size=24)
    workflow = [
        ("Step 1 — Ingestion",
         "Parse PDF resumes + role description + evaluation checklist (JSON)."),
        ("Step 2 — Profile Extraction",
         "Claude extracts work history, skills, education, progression, and resume flags."),
        ("Step 3 — Fitment Analysis",
         "Qualitative ratings: Meets / Partially Meets / Does Not Meet — never numerical."),
        ("Step 4 — Question Bank",
         "10–14 questions per candidate across Technical, Behavioural, Gap-probing, and Situational."),
        ("Step 5 — Feedback Template",
         "Per-competency rating scale and observation fields, exported as Word document."),
        ("Step 6 — Comparison + Compliance",
         "Side-by-side table, compliance gap report, and panel briefing dashboard."),
    ]
    build_two_col_table(doc, workflow, header=["Step", "What happens"])
    page_break(doc)

    # ===== Slide 6: Architecture =====
    add_section_label(doc, "Architecture")
    add_heading(doc, "How the pieces fit together", size=24)
    add_body(doc, "End-to-end flow:", size=13, bold=True)
    add_bullets(doc, [
        "React (Vite) UI uploads resumes, role description, and checklist",
        "FastAPI backend receives multipart payload at POST /api/v1/ingest",
        "Orchestrator dispatches Steps 1 → 6, each calling Claude Sonnet 4",
        "Pydantic v2 validates every model returned by Claude — one retry on parse failure",
        "Exporters render artifacts to .docx, .xlsx, and .html in /output",
        "Frontend polls /api/v1/session/{id}/status and renders results",
    ], size=13)
    add_body(doc, "")
    add_body(doc, "Key design choices:", size=13, bold=True)
    add_bullets(doc, [
        "Prompts live as Markdown files in backend/prompts/ — non-engineers can edit them",
        "No global mutable state — sessions held via dependency-injected store",
        "Structured logging with PII redaction; audit trail in backend/logs/audit.jsonl",
    ], size=13)
    page_break(doc)

    # ===== Slide 7: Tech stack =====
    add_section_label(doc, "Tech Stack")
    add_heading(doc, "Built with proven, focused tools", size=24)
    stack_rows = [
        ("Frontend", "React 18 (Vite, JavaScript), Tailwind CSS, Axios"),
        ("Backend", "Python 3.11+, FastAPI, Uvicorn"),
        ("LLM", "Claude Sonnet 4 (claude-sonnet-4-20250514) via Anthropic SDK"),
        ("PDF parsing", "pdfplumber (primary), pypdf (fallback)"),
        ("Document export", "python-docx (Word), openpyxl (Excel), Jinja (HTML)"),
        ("Validation", "Pydantic v2 with TypeAdapter for structured Claude output"),
        ("Logging", "Python logging + JSONL audit trail, PII-redacted"),
    ]
    build_two_col_table(doc, stack_rows, header=["Layer", "Technology"])
    page_break(doc)

    # ===== Slide 8: Demo flow =====
    add_section_label(doc, "Demo")
    add_heading(doc, "What you will see in the live demo", size=24)
    add_bullets(doc, [
        "Drop 3–5 sample PDF resumes into the upload panel",
        "Paste a Senior Backend Engineer role description",
        "Either upload a checklist JSON or let the agent derive one from the role description",
        "Watch the ProcessingView stream progress through Steps 1 → 6",
        "Review CandidateCards with profile + fitment + question bank inline",
        "Open the ComparisonTable and ComplianceReport tabs",
        "Download the feedback templates (.docx), comparison (.xlsx), and dashboard (.html)",
    ], size=13)
    page_break(doc)

    # ===== Slide 9: Impact =====
    add_section_label(doc, "Business Impact")
    add_heading(doc, "From hours of prep to minutes — with better quality", size=24)
    impact_rows = [
        ("Time saved", "45–90 min → under 5 min per candidate (>90% reduction)"),
        ("Consistency", "Every panelist works from the same competency rubric"),
        ("Coverage", "Gap-probing and behavioural questions never get skipped"),
        ("Compliance", "Mandatory checks surfaced before the interview, not after"),
        ("Audit trail", "Every Claude call logged with prompt hash and session ID"),
        ("Throughput", "A recruiter can prep a 10-candidate panel in one coffee break"),
    ]
    build_two_col_table(doc, impact_rows, header=["Dimension", "Outcome"])
    page_break(doc)

    # ===== Slide 10: Guardrails =====
    add_section_label(doc, "Guardrails")
    add_heading(doc, "Designed for responsible hiring", size=24)
    add_bullets(doc, [
        "Bias avoidance: prompts explicitly forbid probing protected characteristics "
        "(age, marital status, religion, national origin, disability)",
        "Qualitative ratings only — no numerical scores that amplify spurious precision",
        "Human-in-the-loop: every output labelled \"AI-assisted analysis — recruiter review required\"",
        "No PII in logs — candidate names and emails redacted from log lines",
        "Data retention: generated artifacts purged after 30 days",
        "Auditability: prompt hash, model, timestamp, and session_id logged for every Claude call",
    ], size=13)
    page_break(doc)

    # ===== Slide 11: Roadmap =====
    add_section_label(doc, "Roadmap")
    add_heading(doc, "Where we go next", size=24)
    add_body(doc, "Near-term (next 4–6 weeks):", size=13, bold=True)
    add_bullets(doc, [
        "ATS integrations (Workday, Greenhouse, SmartRecruiters)",
        "Recorded interview transcript ingestion for post-panel summary",
        "Multi-language resume support (currently English-first)",
    ], size=13)
    add_body(doc, "")
    add_body(doc, "Longer-term:", size=13, bold=True)
    add_bullets(doc, [
        "Calibration loop — feed actual hire/no-hire outcomes back to tune fitment rubrics",
        "Live panel co-pilot during the interview itself",
        "Role-family templates (engineering, sales, design, ops) shipped out of the box",
    ], size=13)
    page_break(doc)

    # ===== Slide 12: Thank you =====
    for _ in range(6):
        doc.add_paragraph()
    add_heading(doc, "Thank you", size=44, align=WD_ALIGN_PARAGRAPH.CENTER)
    add_subheading(doc, "Questions, please.", size=18)
    for _ in range(6):
        doc.add_paragraph()
    add_body(doc, "Praveen CK  •  praveen.ck2@cognizant.com",
             size=12, color=MUTED, align=WD_ALIGN_PARAGRAPH.CENTER)
    add_body(doc, "TalentOps Agent  •  Hackathon 2026",
             size=11, color=MUTED, align=WD_ALIGN_PARAGRAPH.CENTER)

    doc.save(OUTPUT)
    print(f"Wrote: {OUTPUT}")


if __name__ == "__main__":
    build()
