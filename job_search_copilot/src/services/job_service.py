"""Job CRUD and AI-backed analysis."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from src import db
from src.ai_client import chat_json
from src.prompts import analyze_job_prompt


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def list_jobs_for_user(user_id: int) -> list[dict[str, Any]]:
    rows = db.fetch_all(
        "SELECT * FROM jobs WHERE user_id = ? ORDER BY datetime(created_at) DESC",
        (user_id,),
    )
    return [db.row_as_dict(r) or {} for r in rows]


def get_job(job_id: int) -> dict[str, Any] | None:
    row = db.fetch_one("SELECT * FROM jobs WHERE id = ?", (job_id,))
    return db.row_as_dict(row)


def create_job_stub(user_id: int, fields: dict[str, Any]) -> int:
    ts = _now()
    return db.execute_write(
        """
        INSERT INTO jobs (
            user_id, company_name, role_title, source, job_link, location, work_mode,
            jd_text, role_category, seniority_level, required_skills, preferred_skills,
            responsibilities, resume_keywords, fit_score, fit_summary, missing_skills,
            apply_recommendation, status, priority, date_added, follow_up_date, notes,
            created_at, updated_at
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """,
        (
            user_id,
            fields.get("company_name") or "Unknown",
            fields.get("role_title") or "Unknown",
            fields.get("source"),
            fields.get("job_link"),
            fields.get("location"),
            fields.get("work_mode"),
            fields.get("jd_text"),
            fields.get("role_category"),
            fields.get("seniority_level"),
            fields.get("required_skills"),
            fields.get("preferred_skills"),
            fields.get("responsibilities"),
            fields.get("resume_keywords"),
            fields.get("fit_score"),
            fields.get("fit_summary"),
            fields.get("missing_skills"),
            fields.get("apply_recommendation"),
            fields.get("status") or "Saved",
            fields.get("priority"),
            fields.get("date_added") or ts[:10],
            fields.get("follow_up_date"),
            fields.get("notes"),
            ts,
            ts,
        ),
    )


def patch_job(job_id: int, updates: dict[str, Any]) -> None:
    """Merge partial updates into an existing job row."""
    job = get_job(job_id)
    if not job:
        return
    merged = {**job, **updates}
    update_job(job_id, merged)


def update_job(job_id: int, fields: dict[str, Any]) -> None:
    ts = _now()
    db.execute_write(
        """
        UPDATE jobs SET
            company_name=?, role_title=?, source=?, job_link=?, location=?, work_mode=?,
            jd_text=?, role_category=?, seniority_level=?, required_skills=?, preferred_skills=?,
            responsibilities=?, resume_keywords=?, fit_score=?, fit_summary=?, missing_skills=?,
            apply_recommendation=?, status=?, priority=?, follow_up_date=?, notes=?,
            updated_at=?
        WHERE id=?
        """,
        (
            fields.get("company_name"),
            fields.get("role_title"),
            fields.get("source"),
            fields.get("job_link"),
            fields.get("location"),
            fields.get("work_mode"),
            fields.get("jd_text"),
            fields.get("role_category"),
            fields.get("seniority_level"),
            fields.get("required_skills"),
            fields.get("preferred_skills"),
            fields.get("responsibilities"),
            fields.get("resume_keywords"),
            fields.get("fit_score"),
            fields.get("fit_summary"),
            fields.get("missing_skills"),
            fields.get("apply_recommendation"),
            fields.get("status"),
            fields.get("priority"),
            fields.get("follow_up_date"),
            fields.get("notes"),
            ts,
            job_id,
        ),
    )


def analyze_and_save_job(
    *,
    user_id: int,
    profile: dict[str, Any],
    user: dict[str, Any],
    base_fields: dict[str, Any],
) -> tuple[int, dict[str, Any]]:
    """Run AI analysis and insert a new job row."""
    jd = base_fields.get("jd_text") or ""
    sys_p, usr_p = analyze_job_prompt(profile, user, jd)
    data = chat_json(system=sys_p, user=usr_p)

    notes = base_fields.get("notes") or ""
    sug = data.get("follow_up_suggestion")
    if sug:
        notes = (notes + "\n\n" if notes else "") + f"Follow-up suggestion (AI): {sug}"

    merged = {
        **base_fields,
        "company_name": data.get("company_name") or base_fields.get("company_name"),
        "role_title": data.get("role_title") or base_fields.get("role_title"),
        "role_category": data.get("role_category"),
        "seniority_level": data.get("seniority_level"),
        "required_skills": data.get("required_skills"),
        "preferred_skills": data.get("preferred_skills"),
        "responsibilities": data.get("responsibilities"),
        "resume_keywords": data.get("resume_keywords"),
        "fit_score": data.get("fit_score"),
        "fit_summary": data.get("fit_summary"),
        "missing_skills": data.get("missing_skills"),
        "apply_recommendation": data.get("apply_recommendation"),
        "priority": data.get("priority"),
        "notes": notes,
    }
    job_id = create_job_stub(user_id, merged)
    return job_id, data
