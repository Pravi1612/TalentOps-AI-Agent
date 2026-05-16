"""LLM dispatch layer.

Exposes a single entry point — :func:`call_claude_structured` — used by every
agent step. It transparently dispatches to either the real Anthropic API or
the in-process mock provider based on :mod:`config.settings`.

All calls are audited to ``backend/logs/audit.jsonl`` (no PII, only a prompt
hash, token budget, and timing metadata) so prompts can be traced after the
fact without leaking candidate data.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Type, TypeVar

from pydantic import BaseModel, TypeAdapter, ValidationError

from config import settings

__all__ = ["call_claude_structured", "load_prompt"]

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

_PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"


def load_prompt(name: str) -> str:
    """Load a prompt template from ``backend/prompts/<name>``."""
    path = _PROMPTS_DIR / name
    if not path.exists():
        raise FileNotFoundError(f"Prompt not found: {path}")
    return path.read_text(encoding="utf-8")


def call_claude_structured(
    prompt: str,
    schema: Type[T],
    *,
    step: str,
    session_id: str | None = None,
    max_tokens: int = 4096,
    temperature: float = 0.2,
    mock_context: dict[str, Any] | None = None,
) -> T:
    """Invoke the active LLM provider and validate the response against ``schema``.

    Parameters
    ----------
    prompt:
        Fully rendered prompt sent to the model (real provider only).
    schema:
        Pydantic model class describing the expected JSON shape.
    step:
        Pipeline step identifier, e.g. ``"step2_profile"``. Used for audit
        logging and mock dispatch.
    session_id:
        Optional session identifier recorded in the audit log.
    max_tokens, temperature:
        Generation parameters for the Anthropic call.
    mock_context:
        Extra inputs forwarded to :func:`mock_provider.mock_response` when
        running in mock mode.

    Returns
    -------
    T
        A validated instance of ``schema``.
    """
    prompt_hash = hashlib.sha256(prompt.encode("utf-8")).hexdigest()[:16]
    provider = settings.llm_provider
    _write_audit(session_id, step, prompt_hash, max_tokens, temperature, provider)

    if provider == "mock":
        from mock_provider import mock_response

        logger.info("Mock LLM dispatch for step=%s", step)
        return mock_response(step, schema, mock_context or {})

    if provider == "anthropic":
        return _call_anthropic(prompt, schema, max_tokens, temperature)

    raise RuntimeError(f"Unsupported LLM_PROVIDER: {provider}")


def _call_anthropic(
    prompt: str,
    schema: Type[T],
    max_tokens: int,
    temperature: float,
) -> T:
    """Call Anthropic Messages API once, retrying once on validation failure."""
    import anthropic

    api_key = settings.anthropic_api_key or os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY is not set")

    client = anthropic.Anthropic(api_key=api_key)

    def invoke(prompt_text: str) -> T:
        response = client.messages.create(
            model=settings.model,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=[{"role": "user", "content": prompt_text}],
        )
        raw_text = response.content[0].text
        return TypeAdapter(schema).validate_json(_strip_code_fences(raw_text))

    try:
        return invoke(prompt)
    except (ValidationError, json.JSONDecodeError) as err:
        logger.warning("Claude response failed validation; retrying once: %s", err)
        retry_prompt = (
            f"{prompt}\n\nYour previous response failed validation with this error:\n{err}\n"
            "Return ONLY valid JSON matching the requested schema. No markdown, no commentary."
        )
        return invoke(retry_prompt)


def _strip_code_fences(raw: str) -> str:
    """Strip Markdown ```json``` fences that some models emit despite instructions."""
    text = raw.strip()
    if text.startswith("```"):
        newline = text.find("\n")
        if newline != -1:
            text = text[newline + 1:]
        text = text.removeprefix("json").lstrip()
    if text.endswith("```"):
        text = text.rsplit("```", 1)[0]
    return text.strip()


def _write_audit(
    session_id: str | None,
    step: str,
    prompt_hash: str,
    max_tokens: int,
    temperature: float,
    provider: str,
) -> None:
    """Append a single JSON-lines record describing this LLM call."""
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
