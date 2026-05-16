from typing import List, Optional

from pydantic import BaseModel, Field


class SkillRequirement(BaseModel):
    name: str
    description: Optional[str] = None


class ComplianceCheck(BaseModel):
    name: str
    required: bool = True
    description: str


class EvaluationChecklist(BaseModel):
    role_title: str
    must_have_skills: List[SkillRequirement]
    nice_to_have_skills: List[SkillRequirement] = Field(default_factory=list)
    red_flag_indicators: List[str] = Field(default_factory=list)
    min_years_experience: int = 0
    max_years_experience: Optional[int] = None
    compliance_checks: List[ComplianceCheck] = Field(default_factory=list)
