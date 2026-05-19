"""Interview preparation packs."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from src import db
from src.ai_client import chat_json
from src.prompts import interview_prep_prompt


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def generate_interview_prep(
    *, profile: dict[str, Any], user: dict[str, Any], job: dict[str, Any]
) -> dict[str, Any]:
    sys_p, usr_p = interview_prep_prompt(profile, user, job)
    return chat_json(system=sys_p, user=usr_p)


def save_interview_prep(user_id: int, job_id: int, payload: dict[str, Any]) -> int:
    ts = _now()
    return db.execute_write(
        """
        INSERT INTO interview_prep (
            user_id, job_id, company_research, role_prep, likely_questions,
            star_stories, case_questions, salary_pitch, created_at
        ) VALUES (?,?,?,?,?,?,?,?,?)
        """,
        (
            user_id,
            job_id,
            payload.get("company_research"),
            payload.get("role_prep"),
            payload.get("likely_questions"),
            payload.get("star_stories"),
            payload.get("case_questions"),
            payload.get("salary_pitch"),
            ts,
        ),
    )


def latest_interview_prep(user_id: int, job_id: int) -> dict[str, Any] | None:
    row = db.fetch_one(
        """
        SELECT * FROM interview_prep
        WHERE user_id=? AND job_id=?
        ORDER BY datetime(created_at) DESC LIMIT 1
        """,
        (user_id, job_id),
    )
    return db.row_as_dict(row)
