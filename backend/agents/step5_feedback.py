import re
from pathlib import Path
from typing import Tuple

from exporters.docx_exporter import write_feedback_docx
from schemas.candidate import FitmentAnalysis
from schemas.checklist import EvaluationChecklist
from schemas.feedback import CompetencyEntry, FeedbackTemplate


def _safe_filename(name: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", name.strip()) or "candidate"
    return cleaned[:80]


def build_feedback_template(
    fitment: FitmentAnalysis,
    checklist: EvaluationChecklist,
    output_dir: Path,
) -> Tuple[FeedbackTemplate, Path]:
    competencies = [
        CompetencyEntry(competency=s.name, definition=s.description or "")
        for s in checklist.must_have_skills
    ]
    if checklist.nice_to_have_skills:
        competencies.extend(
            CompetencyEntry(
                competency=f"{s.name} (nice-to-have)",
                definition=s.description or "",
            )
            for s in checklist.nice_to_have_skills
        )

    template = FeedbackTemplate(
        candidate_name=fitment.candidate_name,
        role_title=checklist.role_title,
        competencies=competencies,
        red_flag_indicators=checklist.red_flag_indicators,
        compliance_checks=[c.name for c in checklist.compliance_checks],
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"feedback_{_safe_filename(fitment.candidate_name)}.docx"
    write_feedback_docx(template, path)
    return template, path
