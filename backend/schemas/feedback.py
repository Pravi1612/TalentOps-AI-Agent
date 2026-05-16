from typing import List

from pydantic import BaseModel, Field


class CompetencyEntry(BaseModel):
    competency: str
    definition: str = ""


class FeedbackTemplate(BaseModel):
    candidate_name: str
    role_title: str
    competencies: List[CompetencyEntry]
    red_flag_indicators: List[str] = Field(default_factory=list)
    compliance_checks: List[str] = Field(default_factory=list)
    rating_scale: List[str] = Field(
        default_factory=lambda: [
            "Exceeds expectations",
            "Meets expectations",
            "Below expectations",
            "Not assessed",
        ]
    )
