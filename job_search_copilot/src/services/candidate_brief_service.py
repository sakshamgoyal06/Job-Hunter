"""Synthesize role + CTC guidance from LinkedIn paste + CV text and current CTC."""

from __future__ import annotations

import json
from typing import Any

from src import db
from src.ai_client import chat_json
from src.prompts import candidate_synthesis_prompt
from src.services import profile_service


def _now() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def synthesize_brief(
    *,
    linkedin_text: str,
    resume_cv_text: str,
    current_ctc_lpa: float | None,
) -> dict[str, Any]:
    sys_p, usr_p = candidate_synthesis_prompt(
        linkedin_text=linkedin_text,
        resume_cv_text=resume_cv_text,
        current_ctc_lpa=current_ctc_lpa,
    )
    return chat_json(system=sys_p, user=usr_p)


def save_ai_brief(user_id: int, brief: dict[str, Any]) -> None:
    """Persist synthesis JSON; requires an existing profiles row (created on Save)."""
    ts = _now()
    blob = json.dumps(brief, ensure_ascii=False)
    row = profile_service.get_profile_for_user(user_id)
    if not row:
        profile_service.upsert_profile(
            user_id,
            {
                "linkedin_profile_text": "",
                "resume_cv_text": "",
                "base_resume_text": None,
                "ai_candidate_brief": blob,
            },
        )
        return
    db.execute_write(
        "UPDATE profiles SET ai_candidate_brief=?, updated_at=? WHERE user_id=?",
        (blob, ts, user_id),
    )
