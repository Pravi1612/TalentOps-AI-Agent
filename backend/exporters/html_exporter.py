"""Render the panel briefing dashboard as a self-contained HTML file.

The output is a single ``.html`` document with inline CSS — no external assets,
no JavaScript — so it can be e-mailed, attached to a calendar invite, or
archived for compliance without breaking.
"""

from __future__ import annotations

import html
from pathlib import Path

from schemas.candidate import ComparisonReport, ComplianceReport, PanelBriefing
from schemas.questions import QuestionBank

__all__ = ["write_dashboard_html"]


_BASE_CSS = """
body { font-family: -apple-system, Segoe UI, Roboto, sans-serif; max-width: 1100px; margin: 2rem auto; padding: 0 1rem; color: #111827; }
h1, h2, h3 { color: #1f2937; }
.disclaimer { background: #fef3c7; border-left: 4px solid #f59e0b; padding: 0.75rem 1rem; margin: 1rem 0; font-style: italic; }
table { border-collapse: collapse; width: 100%; margin: 1rem 0; font-size: 0.9rem; }
th, td { border: 1px solid #e5e7eb; padding: 0.5rem 0.75rem; text-align: left; vertical-align: top; }
th { background: #1f2937; color: white; }
tr:nth-child(even) td { background: #f9fafb; }
.pill { display: inline-block; padding: 0.15rem 0.5rem; border-radius: 999px; font-size: 0.8rem; font-weight: 600; }
.pill-Meets, .pill-Present, .pill-None { background: #d1fae5; color: #065f46; }
.pill-Partially { background: #fef3c7; color: #92400e; }
.pill-Does, .pill-Major { background: #fee2e2; color: #991b1b; }
.pill-Absent, .pill-Minor { background: #fef3c7; color: #92400e; }
section { margin-bottom: 2.5rem; }
ul.tight { margin: 0.25rem 0; padding-left: 1.25rem; }
.candidate { border: 1px solid #e5e7eb; border-radius: 8px; padding: 1rem; margin-bottom: 1rem; background: white; }
"""

_DISCLAIMER = "AI-assisted analysis — recruiter review required."


def write_dashboard_html(
    comparison: ComparisonReport,
    compliance: ComplianceReport,
    briefing: PanelBriefing,
    question_banks: list[QuestionBank],
    path: Path,
) -> None:
    """Build the dashboard HTML and write it to ``path``."""
    must_have_skills = _unique_preserving_order(
        skill for row in comparison.rows for skill in row.must_have_ratings
    )

    sections = [
        _render_header(comparison),
        _render_briefing(briefing),
        _render_comparison_table(comparison, must_have_skills),
        _render_candidate_briefings(briefing),
        _render_compliance_gaps(compliance),
        _render_question_banks(question_banks),
    ]
    document = (
        f'<!doctype html><html><head><meta charset="utf-8">'
        f'<title>TalentOps Dashboard — {html.escape(comparison.role_title)}</title>'
        f'<style>{_BASE_CSS}</style></head><body>'
        + "".join(sections)
        + "</body></html>"
    )

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(document, encoding="utf-8")


def _render_header(comparison: ComparisonReport) -> str:
    return (
        f"<h1>Panel Briefing — {html.escape(comparison.role_title)}</h1>"
        f'<div class="disclaimer">{html.escape(_DISCLAIMER)}</div>'
    )


def _render_briefing(briefing: PanelBriefing) -> str:
    parts = [f"<section><h2>Headline</h2><p>{html.escape(briefing.headline)}</p>"]
    if briefing.panel_focus_areas:
        parts.append("<h3>Panel focus areas</h3><ul class='tight'>")
        parts.extend(f"<li>{html.escape(area)}</li>" for area in briefing.panel_focus_areas)
        parts.append("</ul>")
    parts.append("</section>")
    return "".join(parts)


def _render_comparison_table(
    comparison: ComparisonReport,
    must_have_skills: list[str],
) -> str:
    parts = ["<section><h2>Side-by-side comparison</h2><table>", "<tr><th>Candidate</th>"]
    parts.extend(f"<th>{html.escape(skill)}</th>" for skill in must_have_skills)
    parts.append("<th>Red flag</th><th>Recommended focus</th></tr>")

    for row in comparison.rows:
        parts.append(f"<tr><td><strong>{html.escape(row.candidate_name)}</strong></td>")
        for skill in must_have_skills:
            rating = row.must_have_ratings.get(skill, "—")
            parts.append(f"<td>{_render_pill(rating)}</td>")
        parts.append(f"<td>{_render_pill(row.red_flag_status)}</td>")
        parts.append("<td><ul class='tight'>")
        parts.extend(f"<li>{html.escape(item)}</li>" for item in row.recommended_focus_areas)
        parts.append("</ul></td></tr>")

    parts.append("</table></section>")
    return "".join(parts)


def _render_candidate_briefings(briefing: PanelBriefing) -> str:
    parts = ["<section><h2>Per-candidate briefing</h2>"]
    for candidate in briefing.per_candidate:
        parts.append(
            f"<div class='candidate'><h3>{html.escape(candidate.candidate_name)}</h3>"
            "<strong>Strengths</strong><ul class='tight'>"
        )
        parts.extend(f"<li>{html.escape(s)}</li>" for s in candidate.strengths)
        parts.append("</ul><strong>Gaps</strong><ul class='tight'>")
        parts.extend(f"<li>{html.escape(g)}</li>" for g in candidate.gaps)
        parts.append("</ul></div>")
    parts.append("</section>")
    return "".join(parts)


def _render_compliance_gaps(compliance: ComplianceReport) -> str:
    parts = [
        "<section><h2>Compliance gaps</h2><table>",
        "<tr><th>Candidate</th><th>Missing required checks</th></tr>",
    ]
    for gap in compliance.gaps:
        missing = ", ".join(gap.missing_checks) if gap.missing_checks else "None"
        parts.append(
            f"<tr><td>{html.escape(gap.candidate_name)}</td>"
            f"<td>{html.escape(missing)}</td></tr>"
        )
    parts.append("</table></section>")
    return "".join(parts)


def _render_question_banks(question_banks: list[QuestionBank]) -> str:
    if not question_banks:
        return ""
    parts = ["<section><h2>Interview question banks</h2>"]
    for bank in question_banks:
        parts.append(f"<div class='candidate'><h3>{html.escape(bank.candidate_name)}</h3>")
        current_category: str | None = None
        for question in bank.questions:
            if question.category != current_category:
                if current_category is not None:
                    parts.append("</ul>")
                parts.append(
                    f"<h4>{html.escape(question.category)}</h4><ul class='tight'>"
                )
                current_category = question.category
            parts.append(
                f"<li><strong>{html.escape(question.question)}</strong>"
                f"<br><em>{html.escape(question.rationale)}</em></li>"
            )
        if current_category is not None:
            parts.append("</ul>")
        parts.append("</div>")
    parts.append("</section>")
    return "".join(parts)


def _render_pill(rating: str) -> str:
    """Render a colour-coded rating pill (CSS class derived from first word)."""
    css_class = "pill-" + rating.split(" ")[0]
    return f'<span class="pill {css_class}">{html.escape(rating)}</span>'


def _unique_preserving_order(items) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result
