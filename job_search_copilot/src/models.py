"""Lightweight row types and constants for the job search copilot."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Final, Sequence

JOB_STATUSES: Final[tuple[str, ...]] = (
    "Saved",
    "Applied",
    "Referral Requested",
    "Recruiter Screen",
    "Interviewing",
    "Offer",
    "Rejected",
    "Paused",
)

JOB_SOURCES: Final[tuple[str, ...]] = (
    "LinkedIn",
    "Naukri",
    "Instahyre",
    "Wellfound",
    "Company Website",
    "Referral",
    "Recruiter",
    "Other",
)

WORK_MODES: Final[tuple[str, ...]] = ("Remote", "Hybrid", "Office", "Unknown")

OUTREACH_CHANNELS: Final[tuple[str, ...]] = (
    "LinkedIn",
    "Email",
    "WhatsApp",
    "Naukri",
    "Other",
)

MESSAGE_TYPES: Final[tuple[str, ...]] = (
    "Referral Request",
    "Recruiter Message",
    "Hiring Manager DM",
    "Follow-up",
    "Thank You",
    "Salary Discussion",
)

PRIORITIES: Final[tuple[str, ...]] = ("High", "Medium", "Low")


@dataclass
class UserRow:
    id: int
    name: str
    email: str | None
    phone: str | None
    current_location: str | None
    current_title: str | None
    current_company: str | None
    current_ctc_lpa: float | None
    fixed_ctc_lpa: float | None
    variable_ctc_lpa: float | None
    esops_value_lpa: float | None
    expected_ctc_lpa: float | None
    notice_period_days: int | None
    preferred_locations: str | None
    target_roles: str | None
    target_industries: str | None
    created_at: str | None = None
    updated_at: str | None = None


def row_to_dict(row: Sequence[Any], keys: list[str]) -> dict[str, Any]:
    return {k: row[i] for i, k in enumerate(keys)}
