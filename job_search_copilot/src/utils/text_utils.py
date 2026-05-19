"""Text helpers for UI and AI post-processing."""

from __future__ import annotations

import re
from typing import Any


def clean_text(value: str | None, max_len: int | None = None) -> str:
    if not value:
        return ""
    t = str(value).strip()
    if max_len is not None and len(t) > max_len:
        return t[: max_len - 1] + "…"
    return t


def is_profile_incomplete(
    user: dict[str, Any] | None, profile: dict[str, Any] | None
) -> tuple[bool, list[str]]:
    missing: list[str] = []
    if not user:
        return True, ["No user selected"]
    for field, label in (
        ("name", "Name"),
        ("email", "Email"),
        ("current_title", "Current title"),
        ("current_company", "Current company"),
    ):
        if not clean_text(user.get(field)):
            missing.append(label)
    if profile:
        if not clean_text(profile.get("professional_summary")):
            missing.append("Professional summary")
        if not clean_text(profile.get("skills")):
            missing.append("Skills")
        if not clean_text(profile.get("work_experience")):
            missing.append("Work experience")
    else:
        missing.append("Profile details (summary, skills, experience)")
    return bool(missing), missing


def extract_json_object(raw: str) -> str | None:
    """Best-effort extraction of a JSON object substring."""
    if not raw:
        return None
    text = raw.strip()
    if text.startswith("{") and text.endswith("}"):
        return text
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    return text[start : end + 1]


def strip_code_fences(text: str) -> str:
    t = text.strip()
    if t.startswith("```"):
        t = re.sub(r"^```(?:json)?\s*", "", t, flags=re.IGNORECASE)
        t = re.sub(r"\s*```$", "", t)
    return t.strip()
