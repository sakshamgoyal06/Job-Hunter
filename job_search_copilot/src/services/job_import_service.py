"""Parse pasted job links / messy text into staging rows (no SerpApi)."""

from __future__ import annotations

import re
from typing import Any

from src.ai_client import chat_json
from src.prompts import bulk_job_import_extract_prompt

_URL_RE = re.compile(r"https?://[^\s<>\"{}|\\^`\[\]]+", re.IGNORECASE)


def extract_urls(text: str) -> list[str]:
    if not text or not text.strip():
        return []
    return list(dict.fromkeys(_URL_RE.findall(text.strip())))


def infer_platform(url: str) -> str:
    u = (url or "").lower()
    if "linkedin.com" in u:
        return "LinkedIn"
    if "naukri.com" in u:
        return "Naukri"
    if "instahyre.com" in u:
        return "Instahyre"
    if "wellfound.com" in u or "angel.co" in u:
        return "Wellfound"
    if any(x in u for x in ("lever.co", "greenhouse.io", "ashbyhq.com", "myworkdayjobs.com")):
        return "ATS / Careers"
    return "Other"


def leads_from_urls_only(urls: list[str]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for u in urls:
        rows.append(
            {
                "title": "Add JD (bulk step)",
                "company_name": "Unknown (from URL)",
                "location": "",
                "platform": infer_platform(u),
                "job_url": u,
                "snippet": "",
                "jd_text": "",
            }
        )
    return rows


def leads_from_ai_extract(
    pasted: str, *, user: dict[str, Any], profile: dict[str, Any]
) -> list[dict[str, Any]]:
    sys_p, usr_p = bulk_job_import_extract_prompt(pasted, user, profile)
    data = chat_json(system=sys_p, user=usr_p)
    items = data.get("items") or []
    rows: list[dict[str, Any]] = []
    for it in items:
        url = (it.get("job_url") or "").strip()
        if not url.startswith("http"):
            continue
        rows.append(
            {
                "title": it.get("title") or "Role",
                "company_name": it.get("company_name") or "Company",
                "location": it.get("location") or "",
                "platform": infer_platform(url),
                "job_url": url,
                "snippet": "",
                "jd_text": "",
            }
        )
    return rows
