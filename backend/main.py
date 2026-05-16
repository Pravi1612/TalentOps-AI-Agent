import asyncio
import io
import json
import logging
import re
from pathlib import Path
from typing import List, Optional
from uuid import uuid4

from fastapi import (
    Depends,
    FastAPI,
    File,
    Form,
    HTTPException,
    Request,
    UploadFile,
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

app = FastAPI(title="TalentOps Agent", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_STATIC_DIR = Path(__file__).resolve().parent / "static"
if _STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(_STATIC_DIR)), name="static")


@app.on_event("startup")
async def _init_state() -> None:
    app.state.sessions = {}
    settings.output_dir.mkdir(parents=True, exist_ok=True)


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(_STATIC_DIR / "index.html")


def get_sessions(request: Request) -> dict[str, SessionState]:
    return request.app.state.sessions


def _safe_artifact(name: str) -> Path:
    if re.search(r"[\\/]|\.\.", name):
        raise HTTPException(status_code=400, detail="Invalid filename")
    candidates = [
        settings.output_dir / "feedback_templates" / name,
        settings.output_dir / "comparison_reports" / name,
    ]
    for c in candidates:
        if c.exists() and c.is_file():
            return c
    raise HTTPException(status_code=404, detail="Artifact not found")


@app.get("/api/v1/health")
async def health() -> dict:
    return {
        "status": "ok",
        "provider": settings.llm_provider,
        "model": settings.model if settings.llm_provider == "anthropic" else f"{settings.llm_provider}-stub",
    }


@app.post("/api/v1/ingest")
async def ingest(
    resumes: List[UploadFile] = File(...),
    role_description: Optional[str] = Form(None),
    checklist: Optional[str] = Form(None),
    role_description_file: Optional[UploadFile] = File(None),
    sessions: dict = Depends(get_sessions),
) -> dict:
    if not (3 <= len(resumes) <= 10):
        raise HTTPException(status_code=400, detail="Provide between 3 and 10 resumes")

    role_text = role_description or ""
    if not role_text and role_description_file is not None:
        rd_bytes = await role_description_file.read()
        if rd_bytes:
            if (role_description_file.filename or "").lower().endswith(".pdf"):
                try:
                    role_text = parse_pdf_stream(io.BytesIO(rd_bytes))
                except Exception:
                    logger.exception("Failed to parse role description PDF")
            else:
                role_text = rd_bytes.decode("utf-8", errors="replace")

    if checklist:
        try:
            checklist_obj = EvaluationChecklist.model_validate_json(checklist)
        except ValidationError as err:
            raise HTTPException(status_code=400, detail=f"Invalid checklist: {err.errors()}")
    else:
        if not role_text.strip():
            raise HTTPException(
                status_code=400,
                detail="Provide either a role description (to auto-derive a checklist) or a checklist JSON.",
            )
        try:
            checklist_obj = await asyncio.to_thread(derive_checklist, role_text)
        except Exception as err:
            logger.exception("Checklist derivation failed")
            raise HTTPException(status_code=500, detail=f"Failed to derive checklist: {err}")

    parsed_resumes: list[tuple[str, str]] = []
    for upload in resumes:
        blob = await upload.read()
        if not blob:
            continue
        try:
            text = parse_pdf_stream(io.BytesIO(blob))
        except Exception:
            logger.exception("PDF parse failed for %s", upload.filename)
            text = ""
        parsed_resumes.append((upload.filename or "resume.pdf", text))

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


async def _run_pipeline_safely(
    state: SessionState,
    parsed_resumes: list[tuple[str, str]],
) -> None:
    try:
        await asyncio.to_thread(run_pipeline, state, parsed_resumes, settings.output_dir)
    except Exception as err:
        logger.exception("Pipeline failed for session %s", state.session_id)
        state.status = "failed"
        state.error = str(err)


@app.get("/api/v1/session/{session_id}/status")
async def status(session_id: str, sessions: dict = Depends(get_sessions)) -> dict:
    state = sessions.get(session_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return {
        "session_id": state.session_id,
        "status": state.status,
        "candidate_count": state.candidate_count,
        "step_progress": state.step_progress,
        "error": state.error,
    }


@app.get("/api/v1/session/{session_id}/results")
async def results(session_id: str, sessions: dict = Depends(get_sessions)) -> JSONResponse:
    state = sessions.get(session_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Session not found")
    if state.status != "completed":
        raise HTTPException(status_code=409, detail=f"Session status is {state.status}")

    candidates_payload = [
        {
            "source_filename": c.source_filename,
            "profile": json.loads(c.profile.model_dump_json()),
            "fitment": json.loads(c.fitment.model_dump_json()),
            "questions": json.loads(c.questions.model_dump_json()),
            "feedback_template": json.loads(c.feedback_template.model_dump_json()),
            "feedback_download_url": f"/api/v1/download/{c.feedback_path.name}",
        }
        for c in state.candidates
    ]

    feedback_files = state.artifacts.get("feedback_template_files", [])
    xlsx_file = state.artifacts.get("comparison_xlsx_file")
    html_file = state.artifacts.get("dashboard_html_file")

    return JSONResponse(
        {
            "session_id": state.session_id,
            "checklist": json.loads(state.checklist.model_dump_json()),
            "role_description": state.role_description,
            "candidates": candidates_payload,
            "comparison": json.loads(state.comparison.model_dump_json()) if state.comparison else None,
            "compliance_report": json.loads(state.compliance.model_dump_json()) if state.compliance else None,
            "panel_briefing": json.loads(state.briefing.model_dump_json()) if state.briefing else None,
            "artifact_urls": {
                "feedback_templates_docx": [f"/api/v1/download/{n}" for n in feedback_files],
                "comparison_xlsx": f"/api/v1/download/{xlsx_file}" if xlsx_file else None,
                "dashboard_html": f"/api/v1/download/{html_file}" if html_file else None,
            },
        }
    )


@app.get("/api/v1/download/{filename}")
async def download(filename: str) -> FileResponse:
    path = _safe_artifact(filename)
    return FileResponse(path, filename=path.name)
