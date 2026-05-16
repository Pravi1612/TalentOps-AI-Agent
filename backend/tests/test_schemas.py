import json

from schemas.candidate import (
    CandidateProfile,
    ComparisonReport,
    ComparisonRow,
    ComplianceGap,
    ComplianceReport,
    FitmentAnalysis,
    MustHaveRating,
    PanelBriefing,
    CandidateBriefing,
    RedFlagRating,
)
from schemas.checklist import (
    ComplianceCheck,
    EvaluationChecklist,
    SkillRequirement,
)
from schemas.feedback import CompetencyEntry, FeedbackTemplate
from schemas.questions import InterviewQuestion, QuestionBank


def test_checklist_roundtrip():
    checklist = EvaluationChecklist(
        role_title="Senior Backend Engineer",
        must_have_skills=[SkillRequirement(name="Python", description="5+ years")],
        nice_to_have_skills=[SkillRequirement(name="Kubernetes")],
        red_flag_indicators=["Job-hopping"],
        min_years_experience=5,
        compliance_checks=[
            ComplianceCheck(name="BGV", description="Background verification"),
        ],
    )
    data = checklist.model_dump_json()
    restored = EvaluationChecklist.model_validate_json(data)
    assert restored == checklist


def test_candidate_profile_roundtrip():
    profile = CandidateProfile(
        full_name="Jane Doe",
        email="jane@example.com",
        total_years_experience=7.5,
        career_progression="growth",
    )
    restored = CandidateProfile.model_validate_json(profile.model_dump_json())
    assert restored.full_name == "Jane Doe"
    assert restored.career_progression == "growth"


def test_fitment_analysis_ratings_validate():
    fitment = FitmentAnalysis(
        candidate_name="Jane Doe",
        must_haves=[MustHaveRating(skill="Python", rating="Meets", justification="7 yrs")],
        red_flags=[RedFlagRating(indicator="Job-hopping", rating="None", justification="long tenures")],
    )
    payload = json.loads(fitment.model_dump_json())
    assert payload["must_haves"][0]["rating"] == "Meets"


def test_question_bank_categories_constrained():
    bank = QuestionBank(
        candidate_name="Jane Doe",
        role_title="Senior Backend Engineer",
        questions=[
            InterviewQuestion(
                category="Technical Depth",
                question="Describe a distributed system you designed.",
                rationale="Validates declared skill",
                expected_signals=["scale", "tradeoffs"],
            )
        ],
    )
    assert bank.questions[0].category == "Technical Depth"


def test_feedback_template_defaults():
    tpl = FeedbackTemplate(
        candidate_name="Jane Doe",
        role_title="Senior Backend Engineer",
        competencies=[CompetencyEntry(competency="Python")],
    )
    assert "Meets expectations" in tpl.rating_scale


def test_comparison_and_compliance_models():
    cr = ComparisonReport(
        role_title="X",
        rows=[
            ComparisonRow(
                candidate_name="A",
                must_have_ratings={"Python": "Meets"},
                red_flag_status="None",
            )
        ],
    )
    assert cr.rows[0].must_have_ratings["Python"] == "Meets"

    compliance = ComplianceReport(
        all_required_checks=["BGV"],
        gaps=[ComplianceGap(candidate_name="A", missing_checks=["BGV"])],
    )
    assert compliance.gaps[0].missing_checks == ["BGV"]

    briefing = PanelBriefing(
        headline="Strong slate",
        per_candidate=[CandidateBriefing(candidate_name="A", strengths=["s"], gaps=["g"])],
        panel_focus_areas=["distributed systems"],
    )
    assert briefing.per_candidate[0].candidate_name == "A"
