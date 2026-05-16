from llm import call_claude_structured, load_prompt
from schemas.candidate import CandidateProfile, FitmentAnalysis
from schemas.checklist import EvaluationChecklist
from schemas.questions import QuestionBank


def generate_questions(
    profile: CandidateProfile,
    fitment: FitmentAnalysis,
    checklist: EvaluationChecklist,
    role_description: str,
    *,
    session_id: str | None = None,
) -> QuestionBank:
    template = load_prompt("question_generation.md")
    prompt = (
        template
        .replace("{{ROLE_DESCRIPTION}}", role_description or checklist.role_title)
        .replace("{{CHECKLIST_JSON}}", checklist.model_dump_json(indent=2))
        .replace("{{CANDIDATE_PROFILE_JSON}}", profile.model_dump_json(indent=2))
        .replace("{{FITMENT_JSON}}", fitment.model_dump_json(indent=2))
    )
    return call_claude_structured(
        prompt,
        QuestionBank,
        step="step4_questions",
        session_id=session_id,
        max_tokens=8192,
        temperature=0.5,
        mock_context={
            "profile": profile,
            "fitment": fitment,
            "checklist": checklist,
            "role_description": role_description,
        },
    )
