"""Step 2 — extract a structured :class:`CandidateProfile` from raw resume text."""

from __future__ import annotations

from llm import call_claude_structured, load_prompt
from schemas.candidate import CandidateProfile

__all__ = ["extract_profile"]


def extract_profile(
    resume_text: str,
    *,
    session_id: str | None = None,
) -> CandidateProfile:
    """Parse a single resume into a normalised candidate profile."""
    template = load_prompt("profile_extraction.md")
    prompt = template.replace("{{RESUME_TEXT}}", resume_text)
    return call_claude_structured(
        prompt,
        CandidateProfile,
        step="step2_profile",
        session_id=session_id,
        max_tokens=4096,
        temperature=0.2,
        mock_context={"resume_text": resume_text},
    )
