"""Step 3 — score a candidate profile against the evaluation checklist."""

from __future__ import annotations

from llm import call_claude_structured, load_prompt
from schemas.candidate import CandidateProfile, FitmentAnalysis
from schemas.checklist import EvaluationChecklist

__all__ = ["analyse_fitment"]


def analyse_fitment(
    profile: CandidateProfile,
    checklist: EvaluationChecklist,
    *,
    session_id: str | None = None,
) -> FitmentAnalysis:
    """Produce a qualitative fitment rating per must-have / nice-to-have / red flag.

    Uses *only* the qualitative labels defined in
    :mod:`schemas.candidate` — never numeric scores — per the bias-avoidance
    guardrails in CLAUDE.md §12.
    """
    template = load_prompt("fitment_analysis.md")
    prompt = (
        template
        .replace("{{CANDIDATE_PROFILE_JSON}}", profile.model_dump_json(indent=2))
        .replace("{{CHECKLIST_JSON}}", checklist.model_dump_json(indent=2))
    )
    return call_claude_structured(
        prompt,
        FitmentAnalysis,
        step="step3_fitment",
        session_id=session_id,
        max_tokens=4096,
        temperature=0.2,
        mock_context={"profile": profile, "checklist": checklist},
    )
