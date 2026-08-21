"""AI-generated job hunt playbook (search URLs + strategy, no web scraping)."""

from __future__ import annotations

from typing import Any

from src.ai_client import chat_json
from src.prompts import job_hunt_playbook_prompt


def generate_playbook(
    user: dict[str, Any],
    profile: dict[str, Any],
    *,
    preferences_nl: str,
    prefs_struct: dict[str, Any] | None,
) -> dict[str, Any]:
    sys_p, usr_p = job_hunt_playbook_prompt(
        user, profile, preferences_nl or "", prefs_struct
    )
    return chat_json(system=sys_p, user=usr_p)
