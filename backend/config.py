import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_ROOT / ".env")


@dataclass(frozen=True)
class Settings:
    anthropic_api_key: str
    backend_port: int
    frontend_origin: str
    output_dir: Path
    llm_provider: str
    model: str = "claude-sonnet-4-20250514"
    audit_log_path: Path = Path(__file__).resolve().parent / "logs" / "audit.jsonl"


def _resolve_provider(api_key: str) -> str:
    raw = os.environ.get("LLM_PROVIDER", "").strip().lower()
    if raw:
        return raw
    if api_key and api_key != "sk-ant-...":
        return "anthropic"
    return "mock"


def _load() -> Settings:
    api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    return Settings(
        anthropic_api_key=api_key,
        backend_port=int(os.environ.get("BACKEND_PORT", "8000")),
        frontend_origin=os.environ.get("FRONTEND_ORIGIN", "http://localhost:5173"),
        output_dir=Path(os.environ.get("OUTPUT_DIR", _ROOT / "output")).resolve(),
        llm_provider=_resolve_provider(api_key),
    )


settings = _load()
