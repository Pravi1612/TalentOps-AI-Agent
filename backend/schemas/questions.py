from typing import List, Literal

from pydantic import BaseModel, Field


QuestionCategory = Literal[
    "Technical Depth",
    "Behavioural Scenarios",
    "Gap Probing",
    "Situational",
]


class InterviewQuestion(BaseModel):
    category: QuestionCategory
    question: str
    rationale: str
    expected_signals: List[str] = Field(default_factory=list)


class QuestionBank(BaseModel):
    candidate_name: str
    role_title: str
    questions: List[InterviewQuestion]
