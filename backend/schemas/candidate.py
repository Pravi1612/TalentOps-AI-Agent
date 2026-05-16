from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class WorkHistoryEntry(BaseModel):
    company: str
    role: str
    start_date: str
    end_date: str
    tenure_months: int
    responsibilities: List[str] = Field(default_factory=list)
    achievements: List[str] = Field(default_factory=list)


class Skills(BaseModel):
    technical: List[str] = Field(default_factory=list)
    certifications: List[str] = Field(default_factory=list)


class EducationEntry(BaseModel):
    degree: str
    institution: str
    year: int


class ResumeFlag(BaseModel):
    type: Literal["gap", "short_tenure", "inconsistency"]
    detail: str


class CandidateProfile(BaseModel):
    full_name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    total_years_experience: float = 0.0
    work_history: List[WorkHistoryEntry] = Field(default_factory=list)
    skills: Skills = Field(default_factory=Skills)
    education: List[EducationEntry] = Field(default_factory=list)
    industry_domains: List[str] = Field(default_factory=list)
    career_progression: Literal["growth", "lateral", "mixed"] = "lateral"
    resume_flags: List[ResumeFlag] = Field(default_factory=list)


MustHaveLabel = Literal["Meets", "Partially Meets", "Does Not Meet"]
NiceToHaveLabel = Literal["Present", "Absent"]
RedFlagLabel = Literal["None", "Minor", "Major"]


class MustHaveRating(BaseModel):
    skill: str
    rating: MustHaveLabel
    justification: str


class NiceToHaveRating(BaseModel):
    skill: str
    rating: NiceToHaveLabel
    justification: str


class RedFlagRating(BaseModel):
    indicator: str
    rating: RedFlagLabel
    justification: str


class FitmentAnalysis(BaseModel):
    candidate_name: str
    must_haves: List[MustHaveRating]
    nice_to_haves: List[NiceToHaveRating] = Field(default_factory=list)
    red_flags: List[RedFlagRating] = Field(default_factory=list)
    overall_summary: str = ""


class ComparisonRow(BaseModel):
    candidate_name: str
    must_have_ratings: dict[str, MustHaveLabel]
    nice_to_have_ratings: dict[str, NiceToHaveLabel] = Field(default_factory=dict)
    red_flag_status: RedFlagLabel = "None"
    recommended_focus_areas: List[str] = Field(default_factory=list)


class ComparisonReport(BaseModel):
    role_title: str
    rows: List[ComparisonRow]


class ComplianceGap(BaseModel):
    candidate_name: str
    missing_checks: List[str] = Field(default_factory=list)


class ComplianceReport(BaseModel):
    all_required_checks: List[str]
    gaps: List[ComplianceGap]


class CandidateBriefing(BaseModel):
    candidate_name: str
    strengths: List[str] = Field(default_factory=list)
    gaps: List[str] = Field(default_factory=list)


class PanelBriefing(BaseModel):
    headline: str
    per_candidate: List[CandidateBriefing]
    panel_focus_areas: List[str] = Field(default_factory=list)
