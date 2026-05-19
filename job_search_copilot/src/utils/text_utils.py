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
    """Lightweight profile: LinkedIn text + CV text + current CTC (LPA)."""
    missing: list[str] = []
    if not user:
        return True, ["No user selected"]
    ctc = user.get("current_ctc_lpa")
    try:
        ctc_ok = ctc is not None and float(ctc) > 0
    except (TypeError, ValueError):
        ctc_ok = False
    if not ctc_ok:
        missing.append("Current total CTC (LPA)")

    prof = profile or {}
    ln = clean_text(prof.get("linkedin_profile_text"))
    cv = clean_text(prof.get("resume_cv_text")) or clean_text(prof.get("base_resume_text"))
    if len(ln) < 40:
        missing.append("LinkedIn profile text (paste more from your profile)")
    if len(cv) < 40:
        missing.append("Resume / CV text (paste more or upload a file)")

    # Optional: name/email for exports — warn only, do not block
    return bool(missing), missing


def export_contact_incomplete(user: dict[str, Any] | None) -> tuple[bool, list[str]]:
    """Soft check for DOCX / outreach contact lines."""
    if not user:
        return True, ["No user selected"]
    miss: list[str] = []
    if not clean_text(user.get("name")):
        miss.append("Display name (for resume header)")
    if not clean_text(user.get("email")):
        miss.append("Email (optional but useful on resume)")
    return bool(miss), miss


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
