"""Pipeline orchestrator — wires the six analysis steps end-to-end.

Lifecycle of a request::

    main.ingest()
       |  validates upload, parses PDFs
       v
    SessionState (in-memory)
       |
       v
    run_pipeline()
       |  step 2: extract_profile         (per candidate)
       |  step 3: analyse_fitment         (per candidate)
       |  step 4: generate_questions      (per candidate)
       |  step 5: build_feedback_template (per candidate, writes DOCX)
       |  step 6: build_*_report          (slate-wide, writes XLSX + HTML)
       v
    SessionState.status = "completed"

Step 1 (ingestion) is performed by the HTTP layer before the pipeline starts;
we mark it complete on entry purely for UI progress reporting.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

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

__all__ = ["CandidateBundle", "SessionState", "run_pipeline"]

logger = logging.getLogger(__name__)


@dataclass
class CandidateBundle:
    """All artifacts produced for a single candidate."""

    source_filename: str
    profile: CandidateProfile
    fitment: FitmentAnalysis
    questions: QuestionBank
    feedback_template: FeedbackTemplate
    feedback_path: Path


@dataclass
class SessionState:
    """Per-request state, held in-memory until the process restarts.

    Persistence is intentionally out of scope for v1 — see CLAUDE.md §12.
    """

    session_id: str
    checklist: EvaluationChecklist
    role_description: str = ""
    candidate_count: int = 0
    status: str = "pending"
    step_progress: dict[int, str] = field(default_factory=dict)
    candidates: list[CandidateBundle] = field(default_factory=list)
    comparison: ComparisonReport | None = None
    compliance: ComplianceReport | None = None
    briefing: PanelBriefing | None = None
    artifacts: dict[str, object] = field(default_factory=dict)
    error: str | None = None


def _mark_step(state: SessionState, step: int, value: str) -> None:
    """Update the UI-facing progress map for a single pipeline step."""
    state.step_progress[step] = value


def run_pipeline(
    state: SessionState,
    resumes: list[tuple[str, str]],
    output_root: Path,
) -> SessionState:
    """Run steps 2–6 of the pipeline in sequence and populate ``state``.

    Parameters
    ----------
    state:
        Pre-populated session state (checklist, role description, session_id).
    resumes:
        List of ``(filename, extracted_text)`` pairs. Empty-text entries are
        skipped with a warning — they're typically the result of a PDF parse
        failure upstream.
    output_root:
        Directory under which ``feedback_templates/`` and ``comparison_reports/``
        artifact subdirectories are created.

    Returns
    -------
    SessionState
        The same ``state`` object, mutated in place with results and status.
    """
    state.status = "processing"
    state.candidate_count = len(resumes)

    feedback_dir = output_root / "feedback_templates"
    comparison_dir = output_root / "comparison_reports"
    feedback_dir.mkdir(parents=True, exist_ok=True)
    comparison_dir.mkdir(parents=True, exist_ok=True)

    _mark_step(state, 1, "completed")  # ingestion handled by HTTP layer

    profiles, source_names = _extract_profiles(state, resumes)
    fitments = _score_fitments(state, profiles)
    question_banks = _generate_question_banks(state, profiles, fitments)
    feedbacks = _build_feedback_templates(state, fitments, feedback_dir)
    xlsx_name, html_name = _build_slate_artifacts(
        state, profiles, fitments, question_banks, comparison_dir,
    )

    for filename, profile, fitment, bank, (template, path) in zip(
        source_names, profiles, fitments, question_banks, feedbacks
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
        "feedback_template_files": [path.name for _, path in feedbacks],
        "comparison_xlsx_file": xlsx_name,
        "dashboard_html_file": html_name,
    }
    state.status = "completed"
    return state


def _extract_profiles(
    state: SessionState,
    resumes: list[tuple[str, str]],
) -> tuple[list[CandidateProfile], list[str]]:
    """Step 2: parse each resume's text into a structured profile."""
    _mark_step(state, 2, "in_progress")
    profiles: list[CandidateProfile] = []
    source_names: list[str] = []
    for filename, text in resumes:
        if not text.strip():
            logger.warning("Empty resume text for %s; skipping profile extraction", filename)
            continue
        profiles.append(extract_profile(text, session_id=state.session_id))
        source_names.append(filename)
    _mark_step(state, 2, "completed")
    return profiles, source_names


def _score_fitments(
    state: SessionState,
    profiles: list[CandidateProfile],
) -> list[FitmentAnalysis]:
    """Step 3: score each profile against the checklist."""
    _mark_step(state, 3, "in_progress")
    fitments = [
        analyse_fitment(profile, state.checklist, session_id=state.session_id)
        for profile in profiles
    ]
    _mark_step(state, 3, "completed")
    return fitments


def _generate_question_banks(
    state: SessionState,
    profiles: list[CandidateProfile],
    fitments: list[FitmentAnalysis],
) -> list[QuestionBank]:
    """Step 4: produce a tailored question bank per candidate."""
    _mark_step(state, 4, "in_progress")
    banks = [
        generate_questions(
            profile, fitment, state.checklist, state.role_description,
            session_id=state.session_id,
        )
        for profile, fitment in zip(profiles, fitments)
    ]
    _mark_step(state, 4, "completed")
    return banks


def _build_feedback_templates(
    state: SessionState,
    fitments: list[FitmentAnalysis],
    feedback_dir: Path,
) -> list[tuple[FeedbackTemplate, Path]]:
    """Step 5: build per-candidate feedback templates and write DOCX files."""
    _mark_step(state, 5, "in_progress")
    feedbacks = [
        build_feedback_template(fitment, state.checklist, feedback_dir)
        for fitment in fitments
    ]
    _mark_step(state, 5, "completed")
    return feedbacks


def _build_slate_artifacts(
    state: SessionState,
    profiles: list[CandidateProfile],
    fitments: list[FitmentAnalysis],
    question_banks: list[QuestionBank],
    comparison_dir: Path,
) -> tuple[str, str]:
    """Step 6: build the slate-wide comparison, compliance, briefing, and exports.

    Returns the (xlsx_filename, html_filename) pair so the caller can register
    them in ``state.artifacts``.
    """
    _mark_step(state, 6, "in_progress")
    state.comparison = build_comparison_report(fitments, state.checklist)
    state.compliance = build_compliance_report(profiles, state.checklist)
    state.briefing = build_panel_briefing(
        profiles, fitments, state.checklist, session_id=state.session_id,
    )

    xlsx_path = comparison_dir / f"comparison_{state.session_id}.xlsx"
    html_path = comparison_dir / f"dashboard_{state.session_id}.html"
    write_comparison_xlsx(state.comparison, state.compliance, xlsx_path)
    write_dashboard_html(
        state.comparison, state.compliance, state.briefing, question_banks, html_path,
    )
    _mark_step(state, 6, "completed")
    return xlsx_path.name, html_path.name
