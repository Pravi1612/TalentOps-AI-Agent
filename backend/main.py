"""FastAPI entrypoint for the TalentOps Agent.

Exposes four endpoints:
    POST /api/v1/ingest                          Upload resumes + checklist
    GET  /api/v1/session/{session_id}/status     Poll pipeline progress
    GET  /api/v1/session/{session_id}/results    Fetch final analysis bundle
    GET  /api/v1/download/{filename}             Stream a generated artifact

Plus a health check at ``/api/v1/health`` and a static-asset frontend at ``/``.

Sessions are held in-memory only (see CLAUDE.md §12 on persistence) — restart
the server and in-flight or completed sessions are lost.
"""

from __future__ import annotations

import asyncio
import io
import logging
import re
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import (
    Depends, FastAPI, File, Form, HTTPException, Request, UploadFile,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError

from agents.derive_checklist import derive_checklist
from agents.orchestrator import SessionState, run_pipeline
from config import settings
from parsers.pdf_parser import parse_pdf_stream
from schemas.checklist import EvaluationChecklist

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("talentops")

MIN_RESUMES = 3
MAX_RESUMES = 10
_FILENAME_GUARD = re.compile(r"[\\/]|\.\.")
_ARTIFACT_SUBDIRS = ("feedback_templates", "comparison_reports")
_STATIC_DIR = Path(__file__).resolve().parent / "static"

app = FastAPI(title="TalentOps Agent", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if _STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(_STATIC_DIR)), name="static")


@app.on_event("startup")
async def _initialise_state() -> None:
    """Initialise in-memory session storage and ensure the output dir exists."""
    app.state.sessions = {}
    settings.output_dir.mkdir(parents=True, exist_ok=True)


def get_sessions(request: Request) -> dict[str, SessionState]:
    """FastAPI dependency that exposes the in-memory session map."""
    return request.app.state.sessions


@app.get("/")
async def index() -> FileResponse:
    """Serve the bundled frontend (if present) at the root URL."""
    return FileResponse(_STATIC_DIR / "index.html")


@app.get("/api/v1/health")
async def health() -> dict[str, str]:
    """Lightweight liveness probe returning the active provider and model."""
    model_label = (
        settings.model
        if settings.llm_provider == "anthropic"
        else f"{settings.llm_provider}-stub"
    )
    return {"status": "ok", "provider": settings.llm_provider, "model": model_label}


@app.post("/api/v1/ingest")
async def ingest(
    resumes: list[UploadFile] = File(...),
    role_description: str | None = Form(None),
    checklist: str | None = Form(None),
    role_description_file: UploadFile | None = File(None),
    sessions: dict = Depends(get_sessions),
) -> dict[str, Any]:
    """Accept 3–10 resume PDFs + checklist / role description, start the pipeline."""
    if not (MIN_RESUMES <= len(resumes) <= MAX_RESUMES):
        raise HTTPException(
            status_code=400,
            detail=f"Provide between {MIN_RESUMES} and {MAX_RESUMES} resumes",
        )

    role_text = await _resolve_role_description(role_description, role_description_file)
    checklist_obj = await _resolve_checklist(checklist, role_text)
    parsed_resumes = await _parse_resume_uploads(resumes)

    session_id = str(uuid4())
    state = SessionState(
        session_id=session_id,
        checklist=checklist_obj,
        role_description=role_text,
        candidate_count=len(parsed_resumes),
        status="queued",
    )
    sessions[session_id] = state

    asyncio.create_task(_run_pipeline_safely(state, parsed_resumes))

    return {
        "session_id": session_id,
        "candidate_count": len(parsed_resumes),
        "status": "processing",
        "checklist_derived": checklist is None,
    }


@app.get("/api/v1/session/{session_id}/status")
async def status(
    session_id: str,
    sessions: dict = Depends(get_sessions),
) -> dict[str, Any]:
    """Return the current status and per-step progress for a session."""
    state = _require_session(sessions, session_id)
    return {
        "session_id": state.session_id,
        "status": state.status,
        "candidate_count": state.candidate_count,
        "step_progress": state.step_progress,
        "error": state.error,
    }


@app.get("/api/v1/session/{session_id}/results")
async def results(
    session_id: str,
    sessions: dict = Depends(get_sessions),
) -> JSONResponse:
    """Return the final analysis bundle once the pipeline has completed."""
    state = _require_session(sessions, session_id)
    if state.status != "completed":
        raise HTTPException(status_code=409, detail=f"Session status is {state.status}")

    feedback_files = state.artifacts.get("feedback_template_files", [])
    xlsx_file = state.artifacts.get("comparison_xlsx_file")
    html_file = state.artifacts.get("dashboard_html_file")

    payload = {
        "session_id": state.session_id,
        "checklist": state.checklist.model_dump(mode="json"),
        "role_description": state.role_description,
        "candidates": [
            {
                "source_filename": candidate.source_filename,
                "profile": candidate.profile.model_dump(mode="json"),
                "fitment": candidate.fitment.model_dump(mode="json"),
                "questions": candidate.questions.model_dump(mode="json"),
                "feedback_template": candidate.feedback_template.model_dump(mode="json"),
                "feedback_download_url": f"/api/v1/download/{candidate.feedback_path.name}",
            }
            for candidate in state.candidates
        ],
        "comparison": state.comparison.model_dump(mode="json") if state.comparison else None,
        "compliance_report": state.compliance.model_dump(mode="json") if state.compliance else None,
        "panel_briefing": state.briefing.model_dump(mode="json") if state.briefing else None,
        "artifact_urls": {
            "feedback_templates_docx": [f"/api/v1/download/{name}" for name in feedback_files],
            "comparison_xlsx": f"/api/v1/download/{xlsx_file}" if xlsx_file else None,
            "dashboard_html": f"/api/v1/download/{html_file}" if html_file else None,
        },
    }
    return JSONResponse(payload)


@app.get("/api/v1/download/{filename}")
async def download(filename: str) -> FileResponse:
    """Stream a generated artifact (feedback DOCX, comparison XLSX, or dashboard HTML)."""
    return FileResponse(_resolve_artifact_path(filename), filename=filename)


# --- Helpers --------------------------------------------------------------

def _require_session(sessions: dict[str, SessionState], session_id: str) -> SessionState:
    state = sessions.get(session_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return state


def _resolve_artifact_path(filename: str) -> Path:
    """Return the on-disk path for a generated artifact, guarding against traversal."""
    if _FILENAME_GUARD.search(filename):
        raise HTTPException(status_code=400, detail="Invalid filename")
    for subdir in _ARTIFACT_SUBDIRS:
        candidate = settings.output_dir / subdir / filename
        if candidate.exists() and candidate.is_file():
            return candidate
    raise HTTPException(status_code=404, detail="Artifact not found")


async def _resolve_role_description(
    role_description: str | None,
    role_description_file: UploadFile | None,
) -> str:
    """Return the role description text from either the form field or uploaded PDF/TXT."""
    if role_description:
        return role_description
    if role_description_file is None:
        return ""
    raw_bytes = await role_description_file.read()
    if not raw_bytes:
        return ""
    if (role_description_file.filename or "").lower().endswith(".pdf"):
        try:
            return parse_pdf_stream(io.BytesIO(raw_bytes))
        except Exception:
            logger.exception("Failed to parse role description PDF")
            return ""
    return raw_bytes.decode("utf-8", errors="replace")


async def _resolve_checklist(
    checklist_json: str | None,
    role_text: str,
) -> EvaluationChecklist:
    """Validate a recruiter-supplied checklist or auto-derive one from ``role_text``."""
    if checklist_json:
        try:
            return EvaluationChecklist.model_validate_json(checklist_json)
        except ValidationError as err:
            raise HTTPException(status_code=400, detail=f"Invalid checklist: {err.errors()}")

    if not role_text.strip():
        raise HTTPException(
            status_code=400,
            detail="Provide either a role description (to auto-derive a checklist) or a checklist JSON.",
        )
    try:
        return await asyncio.to_thread(derive_checklist, role_text)
    except Exception as err:
        logger.exception("Checklist derivation failed")
        raise HTTPException(status_code=500, detail=f"Failed to derive checklist: {err}")


async def _parse_resume_uploads(
    resumes: list[UploadFile],
) -> list[tuple[str, str]]:
    """Read each upload and return ``(filename, extracted_text)`` pairs."""
    parsed: list[tuple[str, str]] = []
    for upload in resumes:
        blob = await upload.read()
        if not blob:
            continue
        try:
            text = parse_pdf_stream(io.BytesIO(blob))
        except Exception:
            logger.exception("PDF parse failed for %s", upload.filename)
            text = ""
        parsed.append((upload.filename or "resume.pdf", text))
    return parsed


async def _run_pipeline_safely(
    state: SessionState,
    parsed_resumes: list[tuple[str, str]],
) -> None:
    """Run the pipeline in a background thread, capturing any failure on ``state``."""
    try:
        await asyncio.to_thread(run_pipeline, state, parsed_resumes, settings.output_dir)
    except Exception as err:
        logger.exception("Pipeline failed for session %s", state.session_id)
        state.status = "failed"
        state.error = str(err)
