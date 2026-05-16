"""Pydantic models for the per-candidate interview question bank."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

__all__ = ["QuestionCategory", "InterviewQuestion", "QuestionBank"]


QuestionCategory = Literal[
    "Technical Depth",
    "Behavioural Scenarios",
    "Gap Probing",
    "Situational",
]


class InterviewQuestion(BaseModel):
    """A single tailored interview question with rationale and expected signals."""

    category: QuestionCategory
    question: str
    rationale: str
    expected_signals: list[str] = Field(default_factory=list)


class QuestionBank(BaseModel):
    """The full 10–14 question bank generated for one candidate."""

    candidate_name: str
    role_title: str
    questions: list[InterviewQuestion]
