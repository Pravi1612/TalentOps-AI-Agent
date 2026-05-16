"""Pydantic models for candidate profiles, fitment analyses, and report bundles.

These models flow through the pipeline like this::

    resume PDF  ->  CandidateProfile  (step 2)
                       |
                       v
                  FitmentAnalysis     (step 3)
                       |
                       v
                  ComparisonRow + ComplianceGap + CandidateBriefing (step 6)

The qualitative rating literals (``MustHaveLabel`` and friends) are
intentionally not numeric — see CLAUDE.md §4 for the bias-avoidance rationale.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

__all__ = [
    "WorkHistoryEntry",
    "Skills",
    "EducationEntry",
    "ResumeFlag",
    "CandidateProfile",
    "MustHaveLabel",
    "NiceToHaveLabel",
    "RedFlagLabel",
    "MustHaveRating",
    "NiceToHaveRating",
    "RedFlagRating",
    "FitmentAnalysis",
    "ComparisonRow",
    "ComparisonReport",
    "ComplianceGap",
    "ComplianceReport",
    "CandidateBriefing",
    "PanelBriefing",
]


# --- Candidate profile -----------------------------------------------------

class WorkHistoryEntry(BaseModel):
    """A single employment record extracted from the resume."""

    company: str
    role: str
    start_date: str
    end_date: str
    tenure_months: int
    responsibilities: list[str] = Field(default_factory=list)
    achievements: list[str] = Field(default_factory=list)


class Skills(BaseModel):
    """Technical skills and certifications declared on the resume."""

    technical: list[str] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)


class EducationEntry(BaseModel):
    """A single degree / credential entry."""

    degree: str
    institution: str
    year: int


class ResumeFlag(BaseModel):
    """A self-reported red flag found while parsing the resume."""

    type: Literal["gap", "short_tenure", "inconsistency"]
    detail: str


class CandidateProfile(BaseModel):
    """Structured profile derived from a single resume."""

    full_name: str
    email: str | None = None
    phone: str | None = None
    total_years_experience: float = 0.0
    work_history: list[WorkHistoryEntry] = Field(default_factory=list)
    skills: Skills = Field(default_factory=Skills)
    education: list[EducationEntry] = Field(default_factory=list)
    industry_domains: list[str] = Field(default_factory=list)
    career_progression: Literal["growth", "lateral", "mixed"] = "lateral"
    resume_flags: list[ResumeFlag] = Field(default_factory=list)


# --- Fitment ratings -------------------------------------------------------

MustHaveLabel = Literal["Meets", "Partially Meets", "Does Not Meet"]
NiceToHaveLabel = Literal["Present", "Absent"]
RedFlagLabel = Literal["None", "Minor", "Major"]


class MustHaveRating(BaseModel):
    """Qualitative rating for a single must-have skill."""

    skill: str
    rating: MustHaveLabel
    justification: str


class NiceToHaveRating(BaseModel):
    """Qualitative rating for a single nice-to-have skill."""

    skill: str
    rating: NiceToHaveLabel
    justification: str


class RedFlagRating(BaseModel):
    """Qualitative rating for a single red-flag indicator."""

    indicator: str
    rating: RedFlagLabel
    justification: str


class FitmentAnalysis(BaseModel):
    """Full per-candidate fitment assessment against the checklist."""

    candidate_name: str
    must_haves: list[MustHaveRating]
    nice_to_haves: list[NiceToHaveRating] = Field(default_factory=list)
    red_flags: list[RedFlagRating] = Field(default_factory=list)
    overall_summary: str = ""


# --- Comparison & compliance reports --------------------------------------

class ComparisonRow(BaseModel):
    """A single row in the side-by-side comparison table."""

    candidate_name: str
    must_have_ratings: dict[str, MustHaveLabel]
    nice_to_have_ratings: dict[str, NiceToHaveLabel] = Field(default_factory=dict)
    red_flag_status: RedFlagLabel = "None"
    recommended_focus_areas: list[str] = Field(default_factory=list)


class ComparisonReport(BaseModel):
    """Full side-by-side comparison across the candidate slate."""

    role_title: str
    rows: list[ComparisonRow]


class ComplianceGap(BaseModel):
    """Missing mandatory compliance items for a single candidate."""

    candidate_name: str
    missing_checks: list[str] = Field(default_factory=list)


class ComplianceReport(BaseModel):
    """Slate-wide compliance gap report."""

    all_required_checks: list[str]
    gaps: list[ComplianceGap]


# --- Panel briefing --------------------------------------------------------

class CandidateBriefing(BaseModel):
    """Per-candidate briefing card surfaced in the dashboard."""

    candidate_name: str
    strengths: list[str] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)


class PanelBriefing(BaseModel):
    """Top-of-page briefing summary for the interview panel."""

    headline: str
    per_candidate: list[CandidateBriefing]
    panel_focus_areas: list[str] = Field(default_factory=list)
