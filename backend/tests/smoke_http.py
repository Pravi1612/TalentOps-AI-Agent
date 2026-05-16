"""End-to-end HTTP smoke test using FastAPI's TestClient. Not a pytest test."""
import io
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient
from pypdf import PdfWriter
from pypdf.generic import (
    ContentStream,
    DictionaryObject,
    NameObject,
    NumberObject,
    TextStringObject,
)

from main import app


def make_pdf(text: str) -> bytes:
    w = PdfWriter()
    w.add_blank_page(width=400, height=400)
    page = w.pages[0]
    cs = ContentStream(None, w)
    cs.operations = [
        ([], b"BT"),
        ([NameObject("/F1"), NumberObject(12)], b"Tf"),
        ([NumberObject(50), NumberObject(200)], b"Td"),
        ([TextStringObject(text)], b"Tj"),
        ([], b"ET"),
    ]
    page[NameObject("/Contents")] = cs
    page[NameObject("/Resources")] = DictionaryObject({
        NameObject("/Font"): DictionaryObject({
            NameObject("/F1"): DictionaryObject({
                NameObject("/Type"): NameObject("/Font"),
                NameObject("/Subtype"): NameObject("/Type1"),
                NameObject("/BaseFont"): NameObject("/Helvetica"),
            })
        })
    })
    buf = io.BytesIO()
    w.write(buf)
    return buf.getvalue()


def main() -> None:
    with TestClient(app) as client:
        _run(client)


def _run(client: TestClient) -> None:
    r = client.get("/api/v1/health")
    print("HEALTH:", r.status_code, r.json())

    r = client.get("/")
    print("INDEX:", r.status_code, "html_len=", len(r.text), "tailwind_present=", "tailwindcss" in r.text)

    names = ["Alice Adams", "Bob Brown", "Cara Cole"]
    files = [
        ("resumes", (
            f"resume_{i}.pdf",
            make_pdf(f"{names[i]} jane{i}@example.com Senior Python Engineer"),
            "application/pdf",
        ))
        for i in range(3)
    ]
    jd = (
        "We're hiring a Senior Backend Engineer to own our payments platform. "
        "You'll design new APIs, lead the migration from monolith to microservices, "
        "and mentor 3-4 junior engineers. Stack: Python/FastAPI/PostgreSQL on AWS with Kafka. "
        "Scaling reconciliation pipeline by 10x."
    )
    data = {"role_description": jd}
    r = client.post("/api/v1/ingest", files=files, data=data)
    print("INGEST:", r.status_code, r.json())
    sid = r.json()["session_id"]

    for _ in range(30):
        r = client.get(f"/api/v1/session/{sid}/status")
        s = r.json()
        print("STATUS:", s["status"], s["step_progress"])
        if s["status"] == "completed":
            break
        if s["status"] == "failed":
            print("FAILED:", s.get("error"))
            return
        time.sleep(0.5)

    r = client.get(f"/api/v1/session/{sid}/results")
    res = r.json()
    print("RESULTS keys:", sorted(res.keys()))
    cl = res.get("checklist", {})
    print("DERIVED checklist role_title:", cl.get("role_title"))
    print("DERIVED must-haves:", [s["name"] for s in cl.get("must_have_skills", [])])
    print("DERIVED nice-to-haves:", [s["name"] for s in cl.get("nice_to_have_skills", [])])
    print("DERIVED min_years_experience:", cl.get("min_years_experience"))
    print("candidates:", len(res["candidates"]))
    print("names:", [c["profile"]["full_name"] for c in res["candidates"]])
    print("first candidate questions:", len(res["candidates"][0]["questions"]["questions"]))
    print("comparison rows:", len(res["comparison"]["rows"]))
    print("compliance gaps:", len(res["compliance_report"]["gaps"]))
    print("briefing focus areas:", res["panel_briefing"]["panel_focus_areas"])
    print("artifact_urls:", res["artifact_urls"])

    for label, url in [
        ("dashboard.html", res["artifact_urls"]["dashboard_html"]),
        ("comparison.xlsx", res["artifact_urls"]["comparison_xlsx"]),
        ("feedback[0].docx", res["artifact_urls"]["feedback_templates_docx"][0]),
    ]:
        r = client.get(url)
        print(f"{label}: status={r.status_code} bytes={len(r.content)}")


if __name__ == "__main__":
    main()
