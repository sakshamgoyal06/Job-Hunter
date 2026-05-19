"""SQLite persistence with automatic schema initialization."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Generator, Iterable

from src.config import DB_PATH, ensure_directories


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


@contextmanager
def get_connection() -> Generator[sqlite3.Connection, None, None]:
    ensure_directories()
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    """Create tables if they do not exist."""
    ensure_directories()
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with get_connection() as conn:
        cur = conn.cursor()
        cur.executescript(
            """
            PRAGMA foreign_keys = ON;

            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT,
                phone TEXT,
                current_location TEXT,
                current_title TEXT,
                current_company TEXT,
                current_ctc_lpa REAL,
                fixed_ctc_lpa REAL,
                variable_ctc_lpa REAL,
                esops_value_lpa REAL,
                expected_ctc_lpa REAL,
                notice_period_days INTEGER,
                preferred_locations TEXT,
                target_roles TEXT,
                target_industries TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS profiles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL UNIQUE,
                professional_summary TEXT,
                skills TEXT,
                work_experience TEXT,
                projects TEXT,
                achievements TEXT,
                education TEXT,
                certifications TEXT,
                base_resume_text TEXT,
                linkedin_profile_text TEXT,
                resume_cv_text TEXT,
                ai_candidate_brief TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                company_name TEXT NOT NULL,
                role_title TEXT NOT NULL,
                source TEXT,
                job_link TEXT,
                location TEXT,
                work_mode TEXT,
                jd_text TEXT,
                role_category TEXT,
                seniority_level TEXT,
                required_skills TEXT,
                preferred_skills TEXT,
                responsibilities TEXT,
                resume_keywords TEXT,
                fit_score REAL,
                fit_summary TEXT,
                missing_skills TEXT,
                apply_recommendation TEXT,
                status TEXT NOT NULL DEFAULT 'Saved',
                priority TEXT,
                date_added TEXT,
                follow_up_date TEXT,
                notes TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS resume_versions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                job_id INTEGER NOT NULL,
                resume_headline TEXT,
                professional_summary TEXT,
                tailored_skills TEXT,
                tailored_experience TEXT,
                final_resume_text TEXT,
                docx_path TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY(job_id) REFERENCES jobs(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS outreach_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                job_id INTEGER NOT NULL,
                recipient_name TEXT,
                recipient_role TEXT,
                channel TEXT,
                message_type TEXT,
                message_text TEXT,
                status TEXT DEFAULT 'Draft',
                follow_up_date TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY(job_id) REFERENCES jobs(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS interview_prep (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                job_id INTEGER NOT NULL,
                company_research TEXT,
                role_prep TEXT,
                likely_questions TEXT,
                star_stories TEXT,
                case_questions TEXT,
                salary_pitch TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY(job_id) REFERENCES jobs(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_jobs_user ON jobs(user_id);
            CREATE INDEX IF NOT EXISTS idx_resume_user ON resume_versions(user_id);
            CREATE INDEX IF NOT EXISTS idx_outreach_user ON outreach_messages(user_id);
            CREATE INDEX IF NOT EXISTS idx_interview_user ON interview_prep(user_id);

            CREATE TABLE IF NOT EXISTS job_search_preferences (
                user_id INTEGER PRIMARY KEY,
                preferences_nl TEXT,
                structured_json TEXT,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS job_leads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                title TEXT,
                company_name TEXT,
                location TEXT,
                platform TEXT,
                job_url TEXT,
                snippet TEXT,
                jd_text TEXT,
                ai_fit_score REAL,
                ai_rationale TEXT,
                apply_recommendation TEXT,
                imported_job_id INTEGER,
                created_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS cold_outreach_drafts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                company_name TEXT,
                company_url TEXT,
                research_summary TEXT,
                email_subject TEXT,
                email_body TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_job_leads_user ON job_leads(user_id);
            CREATE INDEX IF NOT EXISTS idx_cold_outreach_user ON cold_outreach_drafts(user_id);
            """
        )
        _migrate_schema(conn)


def _migrate_schema(conn: sqlite3.Connection) -> None:
    """Add columns introduced after first schema version."""
    cur = conn.cursor()
    cur.execute("PRAGMA table_info(profiles)")
    cols = {row[1] for row in cur.fetchall()}
    for col, ddl in (
        ("linkedin_profile_text", "TEXT"),
        ("resume_cv_text", "TEXT"),
        ("ai_candidate_brief", "TEXT"),
    ):
        if col not in cols:
            cur.execute(f"ALTER TABLE profiles ADD COLUMN {col} {ddl}")


def fetch_one(query: str, params: tuple[Any, ...] = ()) -> sqlite3.Row | None:
    with get_connection() as conn:
        cur = conn.execute(query, params)
        return cur.fetchone()


def fetch_all(query: str, params: tuple[Any, ...] = ()) -> list[sqlite3.Row]:
    with get_connection() as conn:
        cur = conn.execute(query, params)
        return list(cur.fetchall())


def execute_write(query: str, params: tuple[Any, ...] = ()) -> int:
    with get_connection() as conn:
        cur = conn.execute(query, params)
        return int(cur.lastrowid or 0)


def executemany_write(query: str, seq: Iterable[tuple[Any, ...]]) -> None:
    with get_connection() as conn:
        conn.executemany(query, seq)


def row_as_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None
    return {k: row[k] for k in row.keys()}


def reset_database(db_path: Path | None = None) -> None:
    """Delete the SQLite file (for local reset)."""
    path = db_path or DB_PATH
    if path.exists():
        path.unlink()
