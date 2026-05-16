import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from agents.step2_profile import extract_profile
from agents.step3_fitment import analyse_fitment
from agents.step4_questions import generate_questions
from agents.step5_feedback import build_feedback_template
from agents.step6_comparison import (
    build_comparison_report,
    build_compliance_report,
    build_panel_briefing,
)
from exporters.html_exporter import write_dashboard_html
from exporters.xlsx_exporter import write_comparison_xlsx
from schemas.candidate import (
    CandidateProfile,
    ComparisonReport,
    ComplianceReport,
    FitmentAnalysis,
    PanelBriefing,
)
from schemas.checklist import EvaluationChecklist
from schemas.feedback import FeedbackTemplate
from schemas.questions import QuestionBank

logger = logging.getLogger(__name__)


@dataclass
class CandidateBundle:
    source_filename: str
    profile: CandidateProfile
    fitment: FitmentAnalysis
    questions: QuestionBank
    feedback_template: FeedbackTemplate
    feedback_path: Path


@dataclass
class SessionState:
    session_id: str
    checklist: EvaluationChecklist
    role_description: str = ""
    candidate_count: int = 0
    status: str = "pending"
    step_progress: Dict[int, str] = field(default_factory=dict)
    candidates: List[CandidateBundle] = field(default_factory=list)
    comparison: Optional[ComparisonReport] = None
    compliance: Optional[ComplianceReport] = None
    briefing: Optional[PanelBriefing] = None
    artifacts: Dict[str, object] = field(default_factory=dict)
    error: Optional[str] = None


def _set_step(state: SessionState, step: int, value: str) -> None:
    state.step_progress[step] = value


def run_pipeline(
    state: SessionState,
    resumes: List[Tuple[str, str]],
    output_root: Path,
) -> SessionState:
    state.status = "processing"
    state.candidate_count = len(resumes)

    feedback_dir = output_root / "feedback_templates"
    comparison_dir = output_root / "comparison_reports"
    feedback_dir.mkdir(parents=True, exist_ok=True)
    comparison_dir.mkdir(parents=True, exist_ok=True)

    _set_step(state, 1, "completed")

    _set_step(state, 2, "in_progress")
    profiles: List[CandidateProfile] = []
    for filename, text in resumes:
        if not text.strip():
            logger.warning("Empty resume text for %s; skipping profile extraction", filename)
            continue
        profile = extract_profile(text, session_id=state.session_id)
        profiles.append(profile)
    _set_step(state, 2, "completed")

    _set_step(state, 3, "in_progress")
    fitments: List[FitmentAnalysis] = [
        analyse_fitment(p, state.checklist, session_id=state.session_id)
        for p in profiles
    ]
    _set_step(state, 3, "completed")

    _set_step(state, 4, "in_progress")
    banks: List[QuestionBank] = [
        generate_questions(p, f, state.checklist, state.role_description, session_id=state.session_id)
        for p, f in zip(profiles, fitments)
    ]
    _set_step(state, 4, "completed")

    _set_step(state, 5, "in_progress")
    feedbacks: List[Tuple[FeedbackTemplate, Path]] = [
        build_feedback_template(f, state.checklist, feedback_dir) for f in fitments
    ]
    _set_step(state, 5, "completed")

    _set_step(state, 6, "in_progress")
    state.comparison = build_comparison_report(fitments, state.checklist)
    state.compliance = build_compliance_report(profiles, state.checklist)
    state.briefing = build_panel_briefing(profiles, fitments, state.checklist, session_id=state.session_id)

    xlsx_path = comparison_dir / f"comparison_{state.session_id}.xlsx"
    html_path = comparison_dir / f"dashboard_{state.session_id}.html"
    write_comparison_xlsx(state.comparison, state.compliance, xlsx_path)
    write_dashboard_html(state.comparison, state.compliance, state.briefing, banks, html_path)
    _set_step(state, 6, "completed")

    source_names = [name for name, text in resumes if text.strip()]
    for filename, profile, fitment, bank, (template, path) in zip(
        source_names, profiles, fitments, banks, feedbacks
    ):
        state.candidates.append(
            CandidateBundle(
                source_filename=filename,
                profile=profile,
                fitment=fitment,
                questions=bank,
                feedback_template=template,
                feedback_path=path,
            )
        )

    state.artifacts = {
        "feedback_template_files": [fb[1].name for fb in feedbacks],
        "comparison_xlsx_file": xlsx_path.name,
        "dashboard_html_file": html_path.name,
    }
    state.status = "completed"
    return state
