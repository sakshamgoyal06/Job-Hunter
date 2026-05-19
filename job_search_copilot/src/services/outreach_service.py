"""Outreach message generation and persistence."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from src import db
from src.ai_client import chat_json
from src.prompts import outreach_prompt


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def generate_outreach(
    *,
    profile: dict[str, Any],
    user: dict[str, Any],
    job: dict[str, Any],
    recipient_name: str,
    recipient_role: str,
    channel: str,
    message_type: str,
) -> dict[str, Any]:
    sys_p, usr_p = outreach_prompt(
        profile, user, job, recipient_name, recipient_role, channel, message_type
    )
    return chat_json(system=sys_p, user=usr_p)


def save_outreach(
    user_id: int,
    job_id: int,
    *,
    recipient_name: str,
    recipient_role: str,
    channel: str,
    message_type: str,
    message_text: str,
    status: str = "Draft",
    follow_up_date: str | None = None,
) -> int:
    ts = _now()
    return db.execute_write(
        """
        INSERT INTO outreach_messages (
            user_id, job_id, recipient_name, recipient_role, channel, message_type,
            message_text, status, follow_up_date, created_at
        ) VALUES (?,?,?,?,?,?,?,?,?,?)
        """,
        (
            user_id,
            job_id,
            recipient_name,
            recipient_role,
            channel,
            message_type,
            message_text,
            status,
            follow_up_date,
            ts,
        ),
    )


def list_outreach_for_job(user_id: int, job_id: int) -> list[dict[str, Any]]:
    rows = db.fetch_all(
        """
        SELECT * FROM outreach_messages
        WHERE user_id=? AND job_id=?
        ORDER BY datetime(created_at) DESC
        """,
        (user_id, job_id),
    )
    return [db.row_as_dict(r) or {} for r in rows]
