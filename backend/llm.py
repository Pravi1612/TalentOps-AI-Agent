import hashlib
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Type, TypeVar

from pydantic import BaseModel, TypeAdapter, ValidationError

from config import settings

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"


def load_prompt(name: str) -> str:
    path = PROMPTS_DIR / name
    if not path.exists():
        raise FileNotFoundError(f"Prompt not found: {path}")
    return path.read_text(encoding="utf-8")


def _audit(session_id: Optional[str], step: str, prompt_hash: str, max_tokens: int, temperature: float, provider: str) -> None:
    settings.audit_log_path.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "session_id": session_id,
        "step": step,
        "provider": provider,
        "model": settings.model if provider == "anthropic" else f"{provider}-stub",
        "prompt_hash": prompt_hash,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    with settings.audit_log_path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record) + "\n")


def _strip_fences(raw: str) -> str:
    s = raw.strip()
    if s.startswith("```"):
        first_nl = s.find("\n")
        if first_nl != -1:
            s = s[first_nl + 1 :]
        s = s.removeprefix("json").lstrip()
    if s.endswith("```"):
        s = s.rsplit("```", 1)[0]
    return s.strip()


def _anthropic_call(prompt: str, schema: Type[T], max_tokens: int, temperature: float) -> T:
    import anthropic
    key = settings.anthropic_api_key or os.environ.get("ANTHROPIC_API_KEY", "")
    if not key:
        raise RuntimeError("ANTHROPIC_API_KEY is not set")
    client = anthropic.Anthropic(api_key=key)

    def _invoke(prompt_text: str) -> T:
        resp = client.messages.create(
            model=settings.model,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=[{"role": "user", "content": prompt_text}],
        )
        raw = resp.content[0].text
        cleaned = _strip_fences(raw)
        return TypeAdapter(schema).validate_json(cleaned)

    try:
        return _invoke(prompt)
    except (ValidationError, json.JSONDecodeError) as err:
        logger.warning("Claude response failed validation, retrying once: %s", err)
        retry_prompt = (
            f"{prompt}\n\nYour previous response failed validation with this error:\n{err}\n"
            "Return ONLY valid JSON matching the requested schema. No markdown, no commentary."
        )
        return _invoke(retry_prompt)


def call_claude_structured(
    prompt: str,
    schema: Type[T],
    *,
    step: str,
    session_id: Optional[str] = None,
    max_tokens: int = 4096,
    temperature: float = 0.2,
    mock_context: Optional[Dict[str, Any]] = None,
) -> T:
    prompt_hash = hashlib.sha256(prompt.encode("utf-8")).hexdigest()[:16]
    provider = settings.llm_provider
    _audit(session_id, step, prompt_hash, max_tokens, temperature, provider)

    if provider == "mock":
        from mock_provider import mock_response
        logger.info("Mock LLM dispatch for step=%s", step)
        return mock_response(step, schema, mock_context or {})

    if provider == "anthropic":
        return _anthropic_call(prompt, schema, max_tokens, temperature)

    raise RuntimeError(f"Unsupported LLM_PROVIDER: {provider}")
