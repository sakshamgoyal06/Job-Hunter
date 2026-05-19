"""User and profile CRUD."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from src import db


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def list_users() -> list[dict[str, Any]]:
    rows = db.fetch_all("SELECT * FROM users ORDER BY name COLLATE NOCASE")
    return [db.row_as_dict(r) or {} for r in rows]


def get_user(user_id: int) -> dict[str, Any] | None:
    row = db.fetch_one("SELECT * FROM users WHERE id = ?", (user_id,))
    return db.row_as_dict(row)


def create_user(fields: dict[str, Any]) -> int:
    ts = _now()
    uid = db.execute_write(
        """
        INSERT INTO users (
            name, email, phone, current_location, current_title, current_company,
            current_ctc_lpa, fixed_ctc_lpa, variable_ctc_lpa, esops_value_lpa,
            expected_ctc_lpa, notice_period_days, preferred_locations, target_roles,
            target_industries, created_at, updated_at
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """,
        (
            fields.get("name") or "Friend",
            fields.get("email"),
            fields.get("phone"),
            fields.get("current_location"),
            fields.get("current_title"),
            fields.get("current_company"),
            fields.get("current_ctc_lpa"),
            fields.get("fixed_ctc_lpa"),
            fields.get("variable_ctc_lpa"),
            fields.get("esops_value_lpa"),
            fields.get("expected_ctc_lpa"),
            fields.get("notice_period_days"),
            fields.get("preferred_locations"),
            fields.get("target_roles"),
            fields.get("target_industries"),
            ts,
            ts,
        ),
    )
    return uid


def update_user(user_id: int, fields: dict[str, Any]) -> None:
    ts = _now()
    db.execute_write(
        """
        UPDATE users SET
            name=?, email=?, phone=?, current_location=?, current_title=?,
            current_company=?, current_ctc_lpa=?, fixed_ctc_lpa=?, variable_ctc_lpa=?,
            esops_value_lpa=?, expected_ctc_lpa=?, notice_period_days=?,
            preferred_locations=?, target_roles=?, target_industries=?,
            updated_at=?
        WHERE id=?
        """,
        (
            fields.get("name"),
            fields.get("email"),
            fields.get("phone"),
            fields.get("current_location"),
            fields.get("current_title"),
            fields.get("current_company"),
            fields.get("current_ctc_lpa"),
            fields.get("fixed_ctc_lpa"),
            fields.get("variable_ctc_lpa"),
            fields.get("esops_value_lpa"),
            fields.get("expected_ctc_lpa"),
            fields.get("notice_period_days"),
            fields.get("preferred_locations"),
            fields.get("target_roles"),
            fields.get("target_industries"),
            ts,
            user_id,
        ),
    )


def get_profile_for_user(user_id: int) -> dict[str, Any] | None:
    row = db.fetch_one("SELECT * FROM profiles WHERE user_id = ?", (user_id,))
    return db.row_as_dict(row)


def upsert_profile(user_id: int, fields: dict[str, Any]) -> None:
    ts = _now()
    existing = get_profile_for_user(user_id)
    if existing:
        db.execute_write(
            """
            UPDATE profiles SET
                professional_summary=?, skills=?, work_experience=?, projects=?,
                achievements=?, education=?, certifications=?, base_resume_text=?,
                updated_at=?
            WHERE user_id=?
            """,
            (
                fields.get("professional_summary"),
                fields.get("skills"),
                fields.get("work_experience"),
                fields.get("projects"),
                fields.get("achievements"),
                fields.get("education"),
                fields.get("certifications"),
                fields.get("base_resume_text"),
                ts,
                user_id,
            ),
        )
    else:
        db.execute_write(
            """
            INSERT INTO profiles (
                user_id, professional_summary, skills, work_experience, projects,
                achievements, education, certifications, base_resume_text,
                created_at, updated_at
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                user_id,
                fields.get("professional_summary"),
                fields.get("skills"),
                fields.get("work_experience"),
                fields.get("projects"),
                fields.get("achievements"),
                fields.get("education"),
                fields.get("certifications"),
                fields.get("base_resume_text"),
                ts,
                ts,
            ),
        )


def merge_user_profile_form(user_id: int | None, user_data: dict[str, Any], prof_data: dict[str, Any]) -> int:
    """Create or update user + profile; returns user_id."""
    if user_id:
        update_user(user_id, user_data)
        upsert_profile(user_id, prof_data)
        return user_id
    new_id = create_user(user_data)
    upsert_profile(new_id, prof_data)
    return new_id
