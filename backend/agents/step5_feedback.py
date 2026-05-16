"""Step 5 — assemble the panelist feedback template and render it to DOCX."""

from __future__ import annotations

import re
from pathlib import Path

from exporters.docx_exporter import write_feedback_docx
from schemas.candidate import FitmentAnalysis
from schemas.checklist import EvaluationChecklist
from schemas.feedback import CompetencyEntry, FeedbackTemplate

__all__ = ["build_feedback_template"]

_FILENAME_MAX_LENGTH = 80
_FILENAME_INVALID_CHARS = re.compile(r"[^A-Za-z0-9._-]+")


def _safe_filename(name: str) -> str:
    """Sanitise a candidate name into a filesystem-safe filename fragment."""
    cleaned = _FILENAME_INVALID_CHARS.sub("_", name.strip()) or "candidate"
    return cleaned[:_FILENAME_MAX_LENGTH]


def build_feedback_template(
    fitment: FitmentAnalysis,
    checklist: EvaluationChecklist,
    output_dir: Path,
) -> tuple[FeedbackTemplate, Path]:
    """Build the feedback template for one candidate and write the DOCX file.

    Returns the (template, output_path) pair so callers can both serialise the
    structured form and link to the downloadable artifact.
    """
    competencies = [
        CompetencyEntry(competency=skill.name, definition=skill.description or "")
        for skill in checklist.must_have_skills
    ]
    competencies.extend(
        CompetencyEntry(
            competency=f"{skill.name} (nice-to-have)",
            definition=skill.description or "",
        )
        for skill in checklist.nice_to_have_skills
    )

    template = FeedbackTemplate(
        candidate_name=fitment.candidate_name,
        role_title=checklist.role_title,
        competencies=competencies,
        red_flag_indicators=checklist.red_flag_indicators,
        compliance_checks=[c.name for c in checklist.compliance_checks],
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"feedback_{_safe_filename(fitment.candidate_name)}.docx"
    write_feedback_docx(template, output_path)
    return template, output_path
