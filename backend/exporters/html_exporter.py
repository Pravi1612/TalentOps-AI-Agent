import html
from pathlib import Path
from typing import List

from schemas.candidate import ComparisonReport, ComplianceReport, PanelBriefing
from schemas.questions import QuestionBank


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


def _pill(rating: str) -> str:
    cls = "pill-" + rating.split(" ")[0]
    return f'<span class="pill {cls}">{html.escape(rating)}</span>'


def write_dashboard_html(
    comparison: ComparisonReport,
    compliance: ComplianceReport,
    briefing: PanelBriefing,
    question_banks: List[QuestionBank],
    path: Path,
) -> None:
    must_have_skills: list[str] = []
    seen: set[str] = set()
    for row in comparison.rows:
        for skill in row.must_have_ratings.keys():
            if skill not in seen:
                seen.add(skill)
                must_have_skills.append(skill)

    parts: list[str] = []
    parts.append(f"""<!doctype html><html><head><meta charset="utf-8"><title>TalentOps Dashboard — {html.escape(comparison.role_title)}</title><style>{_BASE_CSS}</style></head><body>""")
    parts.append(f"<h1>Panel Briefing — {html.escape(comparison.role_title)}</h1>")
    parts.append('<div class="disclaimer">AI-assisted analysis — recruiter review required.</div>')

    parts.append(f"<section><h2>Headline</h2><p>{html.escape(briefing.headline)}</p>")
    if briefing.panel_focus_areas:
        parts.append("<h3>Panel focus areas</h3><ul class='tight'>")
        for area in briefing.panel_focus_areas:
            parts.append(f"<li>{html.escape(area)}</li>")
        parts.append("</ul>")
    parts.append("</section>")

    parts.append("<section><h2>Side-by-side comparison</h2><table>")
    parts.append("<tr><th>Candidate</th>")
    for skill in must_have_skills:
        parts.append(f"<th>{html.escape(skill)}</th>")
    parts.append("<th>Red flag</th><th>Recommended focus</th></tr>")
    for row in comparison.rows:
        parts.append(f"<tr><td><strong>{html.escape(row.candidate_name)}</strong></td>")
        for skill in must_have_skills:
            rating = row.must_have_ratings.get(skill, "—")
            parts.append(f"<td>{_pill(rating)}</td>")
        parts.append(f"<td>{_pill(row.red_flag_status)}</td>")
        parts.append("<td><ul class='tight'>")
        for fa in row.recommended_focus_areas:
            parts.append(f"<li>{html.escape(fa)}</li>")
        parts.append("</ul></td></tr>")
    parts.append("</table></section>")

    parts.append("<section><h2>Per-candidate briefing</h2>")
    for cb in briefing.per_candidate:
        parts.append(f"<div class='candidate'><h3>{html.escape(cb.candidate_name)}</h3>")
        parts.append("<strong>Strengths</strong><ul class='tight'>")
        for s in cb.strengths:
            parts.append(f"<li>{html.escape(s)}</li>")
        parts.append("</ul><strong>Gaps</strong><ul class='tight'>")
        for g in cb.gaps:
            parts.append(f"<li>{html.escape(g)}</li>")
        parts.append("</ul></div>")
    parts.append("</section>")

    parts.append("<section><h2>Compliance gaps</h2><table>")
    parts.append("<tr><th>Candidate</th><th>Missing required checks</th></tr>")
    for gap in compliance.gaps:
        missing = ", ".join(gap.missing_checks) if gap.missing_checks else "None"
        parts.append(f"<tr><td>{html.escape(gap.candidate_name)}</td><td>{html.escape(missing)}</td></tr>")
    parts.append("</table></section>")

    if question_banks:
        parts.append("<section><h2>Interview question banks</h2>")
        for bank in question_banks:
            parts.append(f"<div class='candidate'><h3>{html.escape(bank.candidate_name)}</h3>")
            current = None
            for q in bank.questions:
                if q.category != current:
                    if current is not None:
                        parts.append("</ul>")
                    parts.append(f"<h4>{html.escape(q.category)}</h4><ul class='tight'>")
                    current = q.category
                parts.append(
                    f"<li><strong>{html.escape(q.question)}</strong><br><em>{html.escape(q.rationale)}</em></li>"
                )
            if current is not None:
                parts.append("</ul>")
            parts.append("</div>")
        parts.append("</section>")

    parts.append("</body></html>")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(parts), encoding="utf-8")
