"""End-to-end HTTP smoke test using FastAPI's ``TestClient``.

Runs the full ingest -> status-poll -> results flow in-process against the
mounted ASGI app (no external server). Designed for manual / CI invocation —
not picked up by pytest because the filename does not start with ``test_``.

Usage::

    cd backend
    python -m tests.smoke_http
"""

from __future__ import annotations

import io
import logging
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient  # noqa: E402
from pypdf import PdfWriter  # noqa: E402
from pypdf.generic import (  # noqa: E402
    ContentStream, DictionaryObject, NameObject, NumberObject, TextStringObject,
)

from main import app  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("smoke")

_STATUS_POLL_INTERVAL_SECONDS = 0.5
_STATUS_POLL_MAX_ATTEMPTS = 30


def make_pdf(text: str) -> bytes:
    """Build a minimal single-page PDF containing the given text."""
    writer = PdfWriter()
    writer.add_blank_page(width=400, height=400)
    page = writer.pages[0]

    content_stream = ContentStream(None, writer)
    content_stream.operations = [
        ([], b"BT"),
        ([NameObject("/F1"), NumberObject(12)], b"Tf"),
        ([NumberObject(50), NumberObject(200)], b"Td"),
        ([TextStringObject(text)], b"Tj"),
        ([], b"ET"),
    ]
    page[NameObject("/Contents")] = content_stream
    page[NameObject("/Resources")] = DictionaryObject({
        NameObject("/Font"): DictionaryObject({
            NameObject("/F1"): DictionaryObject({
                NameObject("/Type"): NameObject("/Font"),
                NameObject("/Subtype"): NameObject("/Type1"),
                NameObject("/BaseFont"): NameObject("/Helvetica"),
            }),
        }),
    })

    buffer = io.BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


def main() -> None:
    """Run the full smoke flow against the in-process app."""
    with TestClient(app) as client:
        _check_health(client)
        _check_index(client)
        session_id = _ingest_sample(client)
        if session_id is None:
            return
        _poll_until_complete(client, session_id)
        _fetch_and_log_results(client, session_id)


def _check_health(client: TestClient) -> None:
    response = client.get("/api/v1/health")
    logger.info("HEALTH: status=%s body=%s", response.status_code, response.json())


def _check_index(client: TestClient) -> None:
    response = client.get("/")
    logger.info(
        "INDEX: status=%s html_len=%d tailwind_present=%s",
        response.status_code, len(response.text), "tailwindcss" in response.text,
    )


def _ingest_sample(client: TestClient) -> str | None:
    candidate_names = ["Alice Adams", "Bob Brown", "Cara Cole"]
    files = [
        (
            "resumes",
            (
                f"resume_{i}.pdf",
                make_pdf(f"{candidate_names[i]} jane{i}@example.com Senior Python Engineer"),
                "application/pdf",
            ),
        )
        for i in range(3)
    ]
    job_description = (
        "We're hiring a Senior Backend Engineer to own our payments platform. "
        "You'll design new APIs, lead the migration from monolith to microservices, "
        "and mentor 3-4 junior engineers. Stack: Python/FastAPI/PostgreSQL on AWS with Kafka. "
        "Scaling reconciliation pipeline by 10x."
    )
    response = client.post(
        "/api/v1/ingest",
        files=files,
        data={"role_description": job_description},
    )
    logger.info("INGEST: status=%s body=%s", response.status_code, response.json())
    if response.status_code != 200:
        return None
    return response.json()["session_id"]


def _poll_until_complete(client: TestClient, session_id: str) -> None:
    for _ in range(_STATUS_POLL_MAX_ATTEMPTS):
        response = client.get(f"/api/v1/session/{session_id}/status")
        snapshot = response.json()
        logger.info("STATUS: %s %s", snapshot["status"], snapshot["step_progress"])
        if snapshot["status"] == "completed":
            return
        if snapshot["status"] == "failed":
            logger.error("FAILED: %s", snapshot.get("error"))
            return
        time.sleep(_STATUS_POLL_INTERVAL_SECONDS)
    logger.warning("Session %s did not complete within poll budget", session_id)


def _fetch_and_log_results(client: TestClient, session_id: str) -> None:
    response = client.get(f"/api/v1/session/{session_id}/results")
    results = response.json()
    logger.info("RESULTS keys: %s", sorted(results.keys()))

    checklist = results.get("checklist", {})
    logger.info("DERIVED checklist role_title: %s", checklist.get("role_title"))
    logger.info(
        "DERIVED must-haves: %s",
        [s["name"] for s in checklist.get("must_have_skills", [])],
    )
    logger.info(
        "DERIVED nice-to-haves: %s",
        [s["name"] for s in checklist.get("nice_to_have_skills", [])],
    )
    logger.info("DERIVED min_years_experience: %s", checklist.get("min_years_experience"))
    logger.info("candidates: %d", len(results["candidates"]))
    logger.info("names: %s", [c["profile"]["full_name"] for c in results["candidates"]])
    logger.info(
        "first candidate questions: %d",
        len(results["candidates"][0]["questions"]["questions"]),
    )
    logger.info("comparison rows: %d", len(results["comparison"]["rows"]))
    logger.info("compliance gaps: %d", len(results["compliance_report"]["gaps"]))
    logger.info(
        "briefing focus areas: %s", results["panel_briefing"]["panel_focus_areas"],
    )
    logger.info("artifact_urls: %s", results["artifact_urls"])

    artifact_urls = results["artifact_urls"]
    for label, url in [
        ("dashboard.html", artifact_urls["dashboard_html"]),
        ("comparison.xlsx", artifact_urls["comparison_xlsx"]),
        ("feedback[0].docx", artifact_urls["feedback_templates_docx"][0]),
    ]:
        artifact_response = client.get(url)
        logger.info(
            "%s: status=%s bytes=%d",
            label, artifact_response.status_code, len(artifact_response.content),
        )


if __name__ == "__main__":
    main()
