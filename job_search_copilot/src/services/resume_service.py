"""Resume tailoring and versioning."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src import db
from src.ai_client import chat_json
from src.config import EXPORTS_DIR
from src.prompts import tailor_resume_prompt
from src.utils.docx_exporter import build_resume_docx


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def generate_tailored_resume(
    *,
    user: dict[str, Any],
    profile: dict[str, Any],
    job: dict[str, Any],
) -> dict[str, Any]:
    sys_p, usr_p = tailor_resume_prompt(profile, user, job)
    return chat_json(system=sys_p, user=usr_p)


def save_resume_version(user_id: int, job_id: int, payload: dict[str, Any]) -> int:
    ts = _now()
    return db.execute_write(
        """
        INSERT INTO resume_versions (
            user_id, job_id, resume_headline, professional_summary, tailored_skills,
            tailored_experience, final_resume_text, docx_path, created_at
        ) VALUES (?,?,?,?,?,?,?,?,?)
        """,
        (
            user_id,
            job_id,
            payload.get("resume_headline"),
            payload.get("professional_summary"),
            payload.get("tailored_skills"),
            payload.get("tailored_experience"),
            payload.get("final_resume_text"),
            payload.get("docx_path"),
            ts,
        ),
    )


def export_resume_docx(
    *,
    user: dict[str, Any],
    profile: dict[str, Any],
    resume: dict[str, Any],
    job: dict[str, Any],
) -> Path:
    safe_company = "".join(c for c in (job.get("company_name") or "company") if c.isalnum() or c in (" ", "-", "_"))[:40].strip().replace(" ", "_") or "company"
    fname = f"resume_{user.get('id')}_{job.get('id')}_{safe_company}.docx"
    path = EXPORTS_DIR / fname
    build_resume_docx(output_path=path, user=user, resume=resume, profile=profile)
    return path


def update_resume_docx_path(version_id: int, docx_path: str) -> None:
    db.execute_write(
        "UPDATE resume_versions SET docx_path=? WHERE id=?",
        (docx_path, version_id),
    )


def list_resume_versions(user_id: int, job_id: int) -> list[dict[str, Any]]:
    rows = db.fetch_all(
        """
        SELECT * FROM resume_versions
        WHERE user_id=? AND job_id=?
        ORDER BY datetime(created_at) DESC
        """,
        (user_id, job_id),
    )
    return [db.row_as_dict(r) or {} for r in rows]
