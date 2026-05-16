"""Pydantic models describing the recruiter-supplied evaluation checklist.

The checklist is the single source of truth for what "fit" means for a role.
It is supplied either as a JSON string in the ingest request or auto-derived
from a free-text role description via :func:`agents.derive_checklist`.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

__all__ = [
    "SkillRequirement",
    "ComplianceCheck",
    "EvaluationChecklist",
]


class SkillRequirement(BaseModel):
    """A single skill the role requires, with an optional clarifying description."""

    name: str
    description: str | None = None


class ComplianceCheck(BaseModel):
    """A mandatory or optional compliance item to confirm during the panel."""

    name: str
    required: bool = True
    description: str


class EvaluationChecklist(BaseModel):
    """The full rubric used to evaluate candidates for a single role."""

    role_title: str
    must_have_skills: list[SkillRequirement]
    nice_to_have_skills: list[SkillRequirement] = Field(default_factory=list)
    red_flag_indicators: list[str] = Field(default_factory=list)
    min_years_experience: int = 0
    max_years_experience: int | None = None
    compliance_checks: list[ComplianceCheck] = Field(default_factory=list)
