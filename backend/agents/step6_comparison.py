"""Step 6 — slate-wide comparison, compliance, and panel briefing artifacts.

This step is the only one that operates on *all* candidates at once:
    - :func:`build_comparison_report` is pure aggregation (no LLM)
    - :func:`build_compliance_report` is pure aggregation (no LLM)
    - :func:`build_panel_briefing` calls Claude to synthesise the slate narrative
"""

from __future__ import annotations

import json

from llm import call_claude_structured, load_prompt
from schemas.candidate import (
    CandidateProfile,
    ComparisonReport,
    ComparisonRow,
    ComplianceGap,
    ComplianceReport,
    FitmentAnalysis,
    PanelBriefing,
    RedFlagLabel,
)
from schemas.checklist import EvaluationChecklist

__all__ = [
    "build_comparison_report",
    "build_compliance_report",
    "build_panel_briefing",
]

_RED_FLAG_SEVERITY: dict[RedFlagLabel, int] = {"None": 0, "Minor": 1, "Major": 2}


def _focus_areas(fitment: FitmentAnalysis) -> list[str]:
    """Return the must-haves that aren't fully met plus any non-None red flags."""
    focus: list[str] = []
    for must_have in fitment.must_haves:
        if must_have.rating != "Meets":
            focus.append(f"{must_have.skill} ({must_have.rating})")
    for red_flag in fitment.red_flags:
        if red_flag.rating != "None":
            focus.append(f"Red flag: {red_flag.indicator} ({red_flag.rating})")
    return focus


def _worst_red_flag(fitment: FitmentAnalysis) -> RedFlagLabel:
    """Return the most severe red-flag label across all indicators."""
    worst: RedFlagLabel = "None"
    for red_flag in fitment.red_flags:
        if _RED_FLAG_SEVERITY[red_flag.rating] > _RED_FLAG_SEVERITY[worst]:
            worst = red_flag.rating
    return worst


def build_comparison_report(
    fitments: list[FitmentAnalysis],
    checklist: EvaluationChecklist,
) -> ComparisonReport:
    """Aggregate per-candidate fitments into a slate-wide comparison table."""
    rows = [
        ComparisonRow(
            candidate_name=fitment.candidate_name,
            must_have_ratings={mh.skill: mh.rating for mh in fitment.must_haves},
            nice_to_have_ratings={nh.skill: nh.rating for nh in fitment.nice_to_haves},
            red_flag_status=_worst_red_flag(fitment),
            recommended_focus_areas=_focus_areas(fitment),
        )
        for fitment in fitments
    ]
    return ComparisonReport(role_title=checklist.role_title, rows=rows)


def build_compliance_report(
    profiles: list[CandidateProfile],
    checklist: EvaluationChecklist,
) -> ComplianceReport:
    """Build a compliance-gap report listing required checks as missing for all.

    Compliance status comes from outside the resume (BGV, right-to-work,
    consent forms). We surface every required check as "missing" so the
    recruiter actively ticks each off rather than defaulting to "all clear".
    """
    required = [check.name for check in checklist.compliance_checks if check.required]
    gaps = [
        ComplianceGap(candidate_name=profile.full_name, missing_checks=list(required))
        for profile in profiles
    ]
    return ComplianceReport(all_required_checks=required, gaps=gaps)


def build_panel_briefing(
    profiles: list[CandidateProfile],
    fitments: list[FitmentAnalysis],
    checklist: EvaluationChecklist,
    *,
    session_id: str | None = None,
) -> PanelBriefing:
    """Synthesise the slate-wide panel briefing via Claude."""
    slate = [
        {
            "profile": json.loads(profile.model_dump_json()),
            "fitment": json.loads(fitment.model_dump_json()),
        }
        for profile, fitment in zip(profiles, fitments)
    ]
    template = load_prompt("comparison_summary.md")
    prompt = (
        template
        .replace("{{CHECKLIST_JSON}}", checklist.model_dump_json(indent=2))
        .replace("{{SLATE_JSON}}", json.dumps(slate, indent=2))
    )
    return call_claude_structured(
        prompt,
        PanelBriefing,
        step="step6_briefing",
        session_id=session_id,
        max_tokens=4096,
        temperature=0.3,
        mock_context={
            "profiles": profiles,
            "fitments": fitments,
            "checklist": checklist,
        },
    )
