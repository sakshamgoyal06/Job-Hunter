"""Natural-language job search preferences (location, CTC, remote, startup vs MNC, etc.)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from src import db
from src.ai_client import chat_json
from src.prompts import parse_job_preferences_prompt


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def get_preferences(user_id: int) -> dict[str, Any] | None:
    row = db.fetch_one("SELECT * FROM job_search_preferences WHERE user_id = ?", (user_id,))
    return db.row_as_dict(row)


def upsert_preferences(user_id: int, *, preferences_nl: str, structured_json: str | None) -> None:
    ts = _now()
    row = get_preferences(user_id)
    if row:
        db.execute_write(
            """
            UPDATE job_search_preferences
            SET preferences_nl=?, structured_json=?, updated_at=?
            WHERE user_id=?
            """,
            (preferences_nl, structured_json, ts, user_id),
        )
    else:
        db.execute_write(
            """
            INSERT INTO job_search_preferences (user_id, preferences_nl, structured_json, updated_at)
            VALUES (?,?,?,?)
            """,
            (user_id, preferences_nl, structured_json, ts),
        )


def parse_preferences_nl(preferences_nl: str) -> dict[str, Any]:
    """Turn free-text answers into structured JSON for search + ranking."""
    sys_p, usr_p = parse_job_preferences_prompt(preferences_nl)
    return chat_json(system=sys_p, user=usr_p)
