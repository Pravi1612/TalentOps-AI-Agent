"""Application configuration loaded from environment variables.

A single immutable ``settings`` object is exported and consumed throughout the
backend. Configuration is read once at import time from the project ``.env``
file (loaded via ``python-dotenv``) and falls back to sensible defaults.

The LLM provider is auto-detected:
    - If ``LLM_PROVIDER`` is set explicitly, it wins.
    - Otherwise, a non-placeholder ``ANTHROPIC_API_KEY`` selects ``anthropic``.
    - Otherwise, ``mock`` mode is used (no network calls).
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

_PLACEHOLDER_KEY = "sk-ant-..."
_PROJECT_ROOT = Path(__file__).resolve().parent.parent

load_dotenv(_PROJECT_ROOT / ".env")


@dataclass(frozen=True)
class Settings:
    """Immutable runtime configuration."""

    anthropic_api_key: str
    backend_port: int
    frontend_origin: str
    output_dir: Path
    llm_provider: str
    model: str = "claude-sonnet-4-20250514"
    audit_log_path: Path = Path(__file__).resolve().parent / "logs" / "audit.jsonl"


def _resolve_provider(api_key: str) -> str:
    """Return the LLM provider name, honouring explicit ``LLM_PROVIDER`` first."""
    explicit = os.environ.get("LLM_PROVIDER", "").strip().lower()
    if explicit:
        return explicit
    if api_key and api_key != _PLACEHOLDER_KEY:
        return "anthropic"
    return "mock"


def _load_settings() -> Settings:
    api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    return Settings(
        anthropic_api_key=api_key,
        backend_port=int(os.environ.get("BACKEND_PORT", "8000")),
        frontend_origin=os.environ.get("FRONTEND_ORIGIN", "http://localhost:5173"),
        output_dir=Path(os.environ.get("OUTPUT_DIR", _PROJECT_ROOT / "output")).resolve(),
        llm_provider=_resolve_provider(api_key),
    )


settings: Settings = _load_settings()
