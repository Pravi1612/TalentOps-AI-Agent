import json
from typing import List

from llm import call_claude_structured, load_prompt
from schemas.candidate import (
    CandidateProfile,
    ComparisonReport,
    ComparisonRow,
    ComplianceGap,
    ComplianceReport,
    FitmentAnalysis,
    PanelBriefing,
)
from schemas.checklist import EvaluationChecklist


def _focus_areas(fitment: FitmentAnalysis) -> List[str]:
    focus: List[str] = []
    for mh in fitment.must_haves:
        if mh.rating != "Meets":
            focus.append(f"{mh.skill} ({mh.rating})")
    for rf in fitment.red_flags:
        if rf.rating != "None":
            focus.append(f"Red flag: {rf.indicator} ({rf.rating})")
    return focus


def build_comparison_report(
    fitments: List[FitmentAnalysis],
    checklist: EvaluationChecklist,
) -> ComparisonReport:
    rows: List[ComparisonRow] = []
    for f in fitments:
        worst_red = "None"
        order = {"None": 0, "Minor": 1, "Major": 2}
        for rf in f.red_flags:
            if order[rf.rating] > order[worst_red]:
                worst_red = rf.rating
        rows.append(
            ComparisonRow(
                candidate_name=f.candidate_name,
                must_have_ratings={mh.skill: mh.rating for mh in f.must_haves},
                nice_to_have_ratings={nh.skill: nh.rating for nh in f.nice_to_haves},
                red_flag_status=worst_red,
                recommended_focus_areas=_focus_areas(f),
            )
        )
    return ComparisonReport(role_title=checklist.role_title, rows=rows)


def build_compliance_report(
    profiles: List[CandidateProfile],
    checklist: EvaluationChecklist,
) -> ComplianceReport:
    required = [c.name for c in checklist.compliance_checks if c.required]
    gaps = [
        ComplianceGap(candidate_name=p.full_name, missing_checks=list(required))
        for p in profiles
    ]
    return ComplianceReport(all_required_checks=required, gaps=gaps)


def build_panel_briefing(
    profiles: List[CandidateProfile],
    fitments: List[FitmentAnalysis],
    checklist: EvaluationChecklist,
    *,
    session_id: str | None = None,
) -> PanelBriefing:
    slate = [
        {
            "profile": json.loads(p.model_dump_json()),
            "fitment": json.loads(f.model_dump_json()),
        }
        for p, f in zip(profiles, fitments)
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
