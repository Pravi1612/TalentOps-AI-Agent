"""Render a :class:`FeedbackTemplate` as a panelist-friendly Microsoft Word document."""

from __future__ import annotations

from pathlib import Path

from docx import Document

from schemas.feedback import FeedbackTemplate

__all__ = ["write_feedback_docx"]

_DISCLAIMER = "AI-assisted analysis — recruiter review required."
_OBSERVATION_LINE = "________________________________________"


def write_feedback_docx(template: FeedbackTemplate, path: Path) -> None:
    """Write a panelist feedback DOCX to ``path``.

    Layout: title, italic disclaimer, rating scale, one section per
    competency (definition + rating tick boxes + observation lines), a
    red-flag checklist, a compliance checklist, and an overall recommendation
    section. All free-text fields are left blank — the document is a template
    the panelist fills in during the interview.
    """
    doc = Document()
    doc.add_heading(f"Panelist Feedback — {template.candidate_name}", level=1)
    doc.add_paragraph(f"Role: {template.role_title}")

    disclaimer_para = doc.add_paragraph()
    disclaimer_para.add_run(_DISCLAIMER).italic = True

    doc.add_heading("Rating Scale", level=2)
    for label in template.rating_scale:
        doc.add_paragraph(label, style="List Bullet")

    doc.add_heading("Competency Ratings", level=2)
    for competency in template.competencies:
        doc.add_heading(competency.competency, level=3)
        if competency.definition:
            doc.add_paragraph(f"Definition: {competency.definition}")
        doc.add_paragraph(
            "Rating (circle one): " + " / ".join(template.rating_scale)
        )
        doc.add_paragraph("Observations:")
        doc.add_paragraph(_OBSERVATION_LINE)
        doc.add_paragraph(_OBSERVATION_LINE)

    doc.add_heading("Red Flag Indicators", level=2)
    if template.red_flag_indicators:
        for flag in template.red_flag_indicators:
            doc.add_paragraph(f"[ ] {flag}")
    else:
        doc.add_paragraph("None defined.")

    doc.add_heading("Compliance Checklist", level=2)
    if template.compliance_checks:
        for check in template.compliance_checks:
            doc.add_paragraph(f"[ ] {check}")
    else:
        doc.add_paragraph("None defined.")

    doc.add_heading("Overall Recommendation", level=2)
    doc.add_paragraph("[ ] Proceed   [ ] Hold   [ ] Decline")
    doc.add_paragraph("Justification (required):")
    doc.add_paragraph(_OBSERVATION_LINE)
    doc.add_paragraph(_OBSERVATION_LINE)

    path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(path))
