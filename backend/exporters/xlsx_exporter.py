"""Render the side-by-side comparison and compliance gaps as an Excel workbook."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

from openpyxl import Workbook
from openpyxl.cell.cell import Cell
from openpyxl.styles import Alignment, Font, PatternFill

from schemas.candidate import ComparisonReport, ComplianceReport

__all__ = ["write_comparison_xlsx"]

_HEADER_FILL_COLOR = "1F2937"
_DISCLAIMER = "AI-assisted analysis — recruiter review required."
_DEFAULT_COLUMN_WIDTH = 22


def _apply_header_style(cell: Cell, text: str) -> None:
    """Apply the dark-grey header style and wrap-text alignment to one cell."""
    cell.value = text
    cell.font = Font(bold=True, color="FFFFFF")
    cell.fill = PatternFill("solid", fgColor=_HEADER_FILL_COLOR)
    cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)


def _unique_preserving_order(items: Iterable[str]) -> list[str]:
    """Return items deduplicated while preserving first-seen order."""
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result


def write_comparison_xlsx(
    comparison: ComparisonReport,
    compliance: ComplianceReport,
    path: Path,
) -> None:
    """Write an Excel workbook with two sheets: comparison and compliance gaps."""
    workbook = Workbook()
    _write_comparison_sheet(workbook, comparison)
    _write_compliance_sheet(workbook, compliance)
    path.parent.mkdir(parents=True, exist_ok=True)
    workbook.save(str(path))


def _write_comparison_sheet(workbook: Workbook, comparison: ComparisonReport) -> None:
    sheet = workbook.active
    sheet.title = "Comparison"

    must_have_skills = _unique_preserving_order(
        skill for row in comparison.rows for skill in row.must_have_ratings
    )
    headers = ["Candidate", *must_have_skills, "Red Flag", "Recommended Focus"]

    for column_index, header in enumerate(headers, start=1):
        _apply_header_style(sheet.cell(row=1, column=column_index), header)

    for row_index, row in enumerate(comparison.rows, start=2):
        sheet.cell(row=row_index, column=1, value=row.candidate_name)
        for col_index, skill in enumerate(must_have_skills, start=2):
            sheet.cell(
                row=row_index,
                column=col_index,
                value=row.must_have_ratings.get(skill, "—"),
            )
        sheet.cell(
            row=row_index,
            column=len(must_have_skills) + 2,
            value=row.red_flag_status,
        )
        sheet.cell(
            row=row_index,
            column=len(must_have_skills) + 3,
            value="; ".join(row.recommended_focus_areas),
        )

    for col_index in range(1, len(headers) + 1):
        column_letter = sheet.cell(row=1, column=col_index).column_letter
        sheet.column_dimensions[column_letter].width = _DEFAULT_COLUMN_WIDTH

    disclaimer_cell = sheet.cell(
        row=len(comparison.rows) + 3,
        column=1,
        value=_DISCLAIMER,
    )
    disclaimer_cell.font = Font(italic=True)


def _write_compliance_sheet(workbook: Workbook, compliance: ComplianceReport) -> None:
    sheet = workbook.create_sheet("Compliance Gaps")
    _apply_header_style(sheet.cell(row=1, column=1), "Candidate")
    _apply_header_style(sheet.cell(row=1, column=2), "Missing Required Checks")

    for row_index, gap in enumerate(compliance.gaps, start=2):
        sheet.cell(row=row_index, column=1, value=gap.candidate_name)
        sheet.cell(
            row=row_index,
            column=2,
            value=", ".join(gap.missing_checks) if gap.missing_checks else "None",
        )

    sheet.column_dimensions["A"].width = 28
    sheet.column_dimensions["B"].width = 60
