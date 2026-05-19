"""OpenAI client with JSON helpers and conservative defaults."""

from __future__ import annotations

import json
import re
from typing import Any

from openai import OpenAI

from src.config import (
    OPENAI_API_KEY,
    OPENAI_MODEL,
    OPENAI_TEMPERATURE_CREATIVE,
    OPENAI_TEMPERATURE_STRUCTURED,
)
from src.utils.text_utils import extract_json_object, strip_code_fences


def get_client() -> OpenAI:
    if not OPENAI_API_KEY:
        raise RuntimeError(
            "OPENAI_API_KEY is not set. Copy .env.example to .env and add your key."
        )
    return OpenAI(api_key=OPENAI_API_KEY)


def parse_json_response(content: str) -> dict[str, Any]:
    """Parse model output into a dict with repair attempts."""
    cleaned = strip_code_fences(content)
    try:
        obj = json.loads(cleaned)
        if isinstance(obj, dict):
            return obj
    except json.JSONDecodeError:
        pass
    extracted = extract_json_object(cleaned)
    if extracted:
        try:
            obj = json.loads(extracted)
            if isinstance(obj, dict):
                return obj
        except json.JSONDecodeError:
            pass
    # trailing comma repair (simple)
    try:
        repaired = re.sub(r",\s*}", "}", extracted or cleaned)
        repaired = re.sub(r",\s*]", "]", repaired)
        obj = json.loads(repaired)
        if isinstance(obj, dict):
            return obj
    except json.JSONDecodeError:
        pass
    raise ValueError("Model returned invalid JSON")


def chat_json(
    *,
    system: str,
    user: str,
    temperature: float | None = None,
    model: str | None = None,
) -> dict[str, Any]:
    """Chat Completions with JSON object response format."""
    client = get_client()
    use_model = model or OPENAI_MODEL
    use_temp = (
        temperature
        if temperature is not None
        else OPENAI_TEMPERATURE_STRUCTURED
    )
    resp = client.chat.completions.create(
        model=use_model,
        temperature=use_temp,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )
    content = resp.choices[0].message.content or "{}"
    return parse_json_response(content)


def chat_text(
    *,
    system: str,
    user: str,
    temperature: float | None = None,
    model: str | None = None,
) -> str:
    client = get_client()
    use_model = model or OPENAI_MODEL
    use_temp = temperature if temperature is not None else OPENAI_TEMPERATURE_CREATIVE
    resp = client.chat.completions.create(
        model=use_model,
        temperature=use_temp,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )
    return (resp.choices[0].message.content or "").strip()


def chat_json_messages(
    messages: list[dict[str, str]],
    *,
    temperature: float | None = None,
    model: str | None = None,
) -> dict[str, Any]:
    client = get_client()
    use_model = model or OPENAI_MODEL
    use_temp = (
        temperature
        if temperature is not None
        else OPENAI_TEMPERATURE_STRUCTURED
    )
    resp = client.chat.completions.create(
        model=use_model,
        temperature=use_temp,
        response_format={"type": "json_object"},
        messages=messages,
    )
    content = resp.choices[0].message.content or "{}"
    return parse_json_response(content)
