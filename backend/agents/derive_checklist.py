from llm import call_claude_structured, load_prompt
from schemas.checklist import EvaluationChecklist


def derive_checklist(role_description: str, *, session_id: str | None = None) -> EvaluationChecklist:
    template = load_prompt("derive_checklist.md")
    prompt = template.replace("{{ROLE_DESCRIPTION}}", role_description or "")
    return call_claude_structured(
        prompt,
        EvaluationChecklist,
        step="derive_checklist",
        session_id=session_id,
        max_tokens=4096,
        temperature=0.3,
        mock_context={"role_description": role_description or ""},
    )
