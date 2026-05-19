"""Cold outreach: light company context + email draft (no auto-send)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from src import db
from src.ai_client import chat_json
from src.prompts import cold_company_outreach_prompt


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def generate_cold_pack(
    *,
    user: dict[str, Any],
    profile: dict[str, Any],
    preferences_nl: str,
    company_name: str,
    company_url: str,
) -> dict[str, Any]:
    sys_p, usr_p = cold_company_outreach_prompt(
        user=user,
        profile=profile,
        preferences_nl=preferences_nl,
        company_name=company_name,
        company_url=company_url,
    )
    return chat_json(system=sys_p, user=usr_p)


def save_draft(
    user_id: int,
    *,
    company_name: str,
    company_url: str,
    research_summary: str,
    email_subject: str,
    email_body: str,
) -> int:
    ts = _now()
    return db.execute_write(
        """
        INSERT INTO cold_outreach_drafts (
            user_id, company_name, company_url, research_summary,
            email_subject, email_body, created_at
        ) VALUES (?,?,?,?,?,?,?)
        """,
        (
            user_id,
            company_name,
            company_url,
            research_summary,
            email_subject,
            email_body,
            ts,
        ),
    )


def list_drafts(user_id: int) -> list[dict[str, Any]]:
    rows = db.fetch_all(
        """
        SELECT * FROM cold_outreach_drafts
        WHERE user_id=?
        ORDER BY datetime(created_at) DESC LIMIT 50
        """,
        (user_id,),
    )
    return [db.row_as_dict(r) or {} for r in rows]
