"""Pydantic models for the panelist feedback template (rendered to DOCX)."""

from __future__ import annotations

from pydantic import BaseModel, Field

__all__ = ["CompetencyEntry", "FeedbackTemplate"]


_DEFAULT_RATING_SCALE: list[str] = [
    "Exceeds expectations",
    "Meets expectations",
    "Below expectations",
    "Not assessed",
]


class CompetencyEntry(BaseModel):
    """A single competency the panelist will score on."""

    competency: str
    definition: str = ""


class FeedbackTemplate(BaseModel):
    """Pre-formatted feedback template for one candidate."""

    candidate_name: str
    role_title: str
    competencies: list[CompetencyEntry]
    red_flag_indicators: list[str] = Field(default_factory=list)
    compliance_checks: list[str] = Field(default_factory=list)
    rating_scale: list[str] = Field(default_factory=lambda: list(_DEFAULT_RATING_SCALE))
