"""Derive an :class:`EvaluationChecklist` from a free-text role description.

Used when the recruiter does not supply a structured checklist — the role
description is fed to Claude and a checklist is returned matching the same
schema the recruiter could have authored by hand.
"""

from __future__ import annotations

from llm import call_claude_structured, load_prompt
from schemas.checklist import EvaluationChecklist

__all__ = ["derive_checklist"]


def derive_checklist(
    role_description: str,
    *,
    session_id: str | None = None,
) -> EvaluationChecklist:
    """Generate a checklist from a role description via Claude."""
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
