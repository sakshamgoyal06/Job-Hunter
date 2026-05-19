"""Job discovery: optional SerpApi Google Jobs + AI ranking vs preferences."""

from __future__ import annotations

import json
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Any

from src import db
from src.ai_client import chat_json
from src.config import SERPAPI_API_KEY
from src.prompts import rank_job_leads_prompt
from src.services import job_service


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def fetch_google_jobs_serpapi(*, query: str, location: str = "India") -> list[dict[str, Any]]:
    """Google Jobs results via SerpApi (aggregates many employer portals)."""
    if not SERPAPI_API_KEY:
        return []
    params = urllib.parse.urlencode(
        {
            "engine": "google_jobs",
            "q": query,
            "location": location,
            "api_key": SERPAPI_API_KEY,
            "hl": "en",
            "gl": "in",
        }
    )
    url = f"https://serpapi.com/search.json?{params}"
    req = urllib.request.Request(url, headers={"User-Agent": "JobSearchCopilot/1.0"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.loads(resp.read().decode())
    raw = data.get("jobs_results") or []
    out: list[dict[str, Any]] = []
    for j in raw[:20]:
        link = j.get("apply_link")
        if not link:
            aos = j.get("apply_options") or []
            if aos and isinstance(aos[0], dict):
                link = aos[0].get("link")
        if not link:
            link = j.get("share_link") or j.get("job_url") or ""
        desc = (j.get("description") or "").strip()
        out.append(
            {
                "title": j.get("title") or "Role",
                "company_name": j.get("company_name") or "Company",
                "location": j.get("location") or "",
                "platform": "Google Jobs (SerpApi)",
                "job_url": str(link or ""),
                "snippet": desc[:4000] if desc else "",
                "jd_text": desc[:8000] if desc else "",
            }
        )
    return out


def clear_leads(user_id: int) -> None:
    db.execute_write("DELETE FROM job_leads WHERE user_id=?", (user_id,))


def insert_leads(user_id: int, leads: list[dict[str, Any]]) -> None:
    ts = _now()
    for L in leads:
        db.execute_write(
            """
            INSERT INTO job_leads (
                user_id, title, company_name, location, platform, job_url, snippet, jd_text,
                ai_fit_score, ai_rationale, apply_recommendation, imported_job_id, created_at
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                user_id,
                L.get("title"),
                L.get("company_name"),
                L.get("location"),
                L.get("platform"),
                L.get("job_url"),
                L.get("snippet"),
                L.get("jd_text") or L.get("snippet"),
                L.get("ai_fit_score"),
                L.get("ai_rationale"),
                L.get("apply_recommendation"),
                None,
                ts,
            ),
        )


def list_leads(user_id: int) -> list[dict[str, Any]]:
    rows = db.fetch_all(
        """
        SELECT * FROM job_leads WHERE user_id=? ORDER BY datetime(created_at) DESC, id DESC
        """,
        (user_id,),
    )
    return [db.row_as_dict(r) or {} for r in rows]


def get_lead(lead_id: int) -> dict[str, Any] | None:
    row = db.fetch_one("SELECT * FROM job_leads WHERE id=?", (lead_id,))
    return db.row_as_dict(row)


def rank_leads_with_ai(
    user: dict[str, Any],
    profile: dict[str, Any],
    prefs_struct: dict[str, Any],
    leads: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    sys_p, usr_p = rank_job_leads_prompt(user, profile, prefs_struct, leads)
    data = chat_json(system=sys_p, user=usr_p)
    evals = data.get("evaluations") or []
    by_idx: dict[int, dict[str, Any]] = {}
    for e in evals:
        try:
            idx = int(e.get("index"))
            by_idx[idx] = e
        except (TypeError, ValueError):
            continue
    merged: list[dict[str, Any]] = []
    for i, L in enumerate(leads):
        ev = by_idx.get(i) or {}
        merged.append(
            {
                **L,
                "ai_fit_score": ev.get("ai_fit_score"),
                "ai_rationale": ev.get("ai_rationale"),
                "apply_recommendation": ev.get("apply_recommendation"),
            }
        )
    return merged


def discover_and_store(
    user_id: int,
    user: dict[str, Any],
    profile: dict[str, Any],
    prefs_struct: dict[str, Any],
    *,
    query: str,
    location: str,
) -> list[dict[str, Any]]:
    raw = fetch_google_jobs_serpapi(query=query, location=location)
    if not raw:
        return []
    ranked = rank_leads_with_ai(user, profile, prefs_struct, raw)
    clear_leads(user_id)
    insert_leads(user_id, ranked)
    return ranked


def import_lead(
    lead_id: int,
    *,
    user_id: int,
    user: dict[str, Any],
    profile: dict[str, Any],
) -> int:
    L = get_lead(lead_id)
    if not L or int(L["user_id"]) != user_id:
        raise ValueError("Lead not found")
    if L.get("imported_job_id"):
        return int(L["imported_job_id"])
    jd = L.get("jd_text") or L.get("snippet") or ""
    url = L.get("job_url") or ""
    base = {
        "company_name": L.get("company_name") or "Unknown",
        "role_title": L.get("title") or "Unknown",
        "source": L.get("platform") or "Other",
        "job_link": url or None,
        "location": L.get("location"),
        "work_mode": "Unknown",
        "jd_text": jd + (f"\n\nSource URL: {url}" if url else ""),
        "notes": "Imported from Job Discovery",
        "date_added": _now()[:10],
        "status": "Saved",
    }
    job_id, _ = job_service.analyze_and_save_job(
        user_id=user_id,
        profile=profile,
        user=user,
        base_fields=base,
    )
    db.execute_write(
        "UPDATE job_leads SET imported_job_id=? WHERE id=?",
        (job_id, lead_id),
    )
    return job_id


def build_search_query_from_prefs(
    prefs: dict[str, Any], role_hint: str = ""
) -> tuple[str, str]:
    pr = prefs.get("primary_role_keywords")
    if isinstance(pr, list) and pr:
        role = str(pr[0])
    elif isinstance(pr, str) and pr.strip():
        role = pr.strip()
    else:
        role = (role_hint or "professional jobs").strip()
    loc = prefs.get("locations")
    if isinstance(loc, list) and loc:
        loc_str = ", ".join(str(x) for x in loc[:4])
    elif isinstance(loc, str) and loc.strip():
        loc_str = loc.strip()
    else:
        loc_str = "India"
    q = role[:200] if role else "jobs India"
    return q, loc_str


def manual_search_links_markdown(prefs: dict[str, Any]) -> str:
    """When SerpApi is off, give deep links so the user can search manually."""
    pr = prefs.get("primary_role_keywords")
    if isinstance(pr, list) and pr:
        role = str(pr[0])
    elif isinstance(pr, str):
        role = pr or "Product Manager"
    else:
        role = "Product Manager"
    role_q = urllib.parse.quote_plus(role)
    loc = prefs.get("locations")
    if isinstance(loc, list) and loc:
        loc_s = str(loc[0])
    else:
        loc_s = str(loc or "India")
    loc_q = urllib.parse.quote_plus(loc_s)
    li = f"https://www.linkedin.com/jobs/search/?keywords={role_q}&location={loc_q}"
    return (
        f"- [Open LinkedIn Jobs search]({li})\n"
        "- [Naukri.com](https://www.naukri.com/) — use the search bar with the same role keywords and city.\n"
        "- Instahyre / Wellfound / company career pages: repeat the same keywords.\n"
    )
