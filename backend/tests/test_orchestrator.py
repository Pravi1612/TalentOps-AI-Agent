from pathlib import Path

from agents import orchestrator as orch
from schemas.candidate import (
    CandidateBriefing,
    CandidateProfile,
    FitmentAnalysis,
    MustHaveRating,
    PanelBriefing,
)
from schemas.checklist import ComplianceCheck, EvaluationChecklist, SkillRequirement
from schemas.questions import InterviewQuestion, QuestionBank


def _make_profile(name: str) -> CandidateProfile:
    return CandidateProfile(
        full_name=name,
        email=f"{name.lower().replace(' ', '.')}@example.com",
        total_years_experience=6.0,
        career_progression="growth",
    )


def _make_fitment(name: str) -> FitmentAnalysis:
    return FitmentAnalysis(
        candidate_name=name,
        must_haves=[
            MustHaveRating(skill="Python", rating="Meets", justification="6+ years"),
            MustHaveRating(skill="Distributed systems", rating="Partially Meets", justification="some exposure"),
        ],
        overall_summary="Strong technical candidate",
    )


def _make_bank(name: str) -> QuestionBank:
    return QuestionBank(
        candidate_name=name,
        role_title="Senior Backend Engineer",
        questions=[
            InterviewQuestion(
                category="Technical Depth",
                question="Describe a Python service you scaled.",
                rationale="Validates declared skill",
                expected_signals=["scale", "tradeoffs"],
            ),
            InterviewQuestion(
                category="Gap Probing",
                question="Walk me through your distributed systems experience.",
                rationale="Address Partially Meets rating",
                expected_signals=["depth", "real examples"],
            ),
        ],
    )


def _checklist() -> EvaluationChecklist:
    return EvaluationChecklist(
        role_title="Senior Backend Engineer",
        must_have_skills=[
            SkillRequirement(name="Python", description="5+ years"),
            SkillRequirement(name="Distributed systems"),
        ],
        nice_to_have_skills=[SkillRequirement(name="Kubernetes")],
        red_flag_indicators=["Job-hopping with <12 month tenures"],
        min_years_experience=5,
        compliance_checks=[
            ComplianceCheck(name="BGV", description="Background verification"),
            ComplianceCheck(name="Right to work", description="Authorisation confirmed"),
        ],
    )


def test_orchestrator_happy_path(monkeypatch, tmp_path):
    names = ["Alice Adams", "Bob Brown", "Cara Cole"]
    name_iter = iter(names)

    def fake_extract(text, *, session_id=None):
        return _make_profile(next(name_iter))

    def fake_analyse(profile, checklist, *, session_id=None):
        return _make_fitment(profile.full_name)

    def fake_questions(profile, fitment, checklist, role_description, *, session_id=None):
        return _make_bank(profile.full_name)

    def fake_briefing(profiles, fitments, checklist, *, session_id=None):
        return PanelBriefing(
            headline="Solid slate",
            per_candidate=[
                CandidateBriefing(
                    candidate_name=p.full_name,
                    strengths=["Python depth"],
                    gaps=["Distributed systems exposure"],
                )
                for p in profiles
            ],
            panel_focus_areas=["Distributed systems"],
        )

    monkeypatch.setattr(orch, "extract_profile", fake_extract)
    monkeypatch.setattr(orch, "analyse_fitment", fake_analyse)
    monkeypatch.setattr(orch, "generate_questions", fake_questions)
    monkeypatch.setattr(orch, "build_panel_briefing", fake_briefing)

    state = orch.SessionState(
        session_id="test-session",
        checklist=_checklist(),
        role_description="Owns the payments service.",
    )
    resumes = [(f"resume_{i}.pdf", f"Resume text for candidate {i}") for i in range(3)]

    result = orch.run_pipeline(state, resumes, tmp_path)

    assert result.status == "completed"
    assert result.candidate_count == 3
    assert len(result.candidates) == 3
    assert result.comparison is not None
    assert len(result.comparison.rows) == 3
    assert result.compliance is not None
    assert result.briefing is not None
    assert result.step_progress[6] == "completed"

    xlsx = tmp_path / "comparison_reports" / "comparison_test-session.xlsx"
    html = tmp_path / "comparison_reports" / "dashboard_test-session.html"
    assert xlsx.exists()
    assert html.exists()

    feedback_dir = tmp_path / "feedback_templates"
    feedback_files = list(feedback_dir.glob("feedback_*.docx"))
    assert len(feedback_files) == 3
