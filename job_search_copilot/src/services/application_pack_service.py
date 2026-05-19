"""Cover letter and application helpers (human still applies on the portal)."""

from __future__ import annotations

from typing import Any

from src.ai_client import chat_json
from src.prompts import cover_letter_prompt


def generate_cover_letter(
    *, user: dict[str, Any], profile: dict[str, Any], job: dict[str, Any]
) -> dict[str, Any]:
    sys_p, usr_p = cover_letter_prompt(user, profile, job)
    return chat_json(system=sys_p, user=usr_p)
