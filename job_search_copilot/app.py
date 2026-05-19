"""
Indian Job Search Copilot — Streamlit entrypoint.

Run from repo root or this folder:
  streamlit run job_search_copilot/app.py
  cd job_search_copilot && streamlit run app.py
"""

from __future__ import annotations

import json
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.config import OPENAI_API_KEY
from src.db import init_db
from src.models import (
    JOB_SOURCES,
    JOB_STATUSES,
    MESSAGE_TYPES,
    OUTREACH_CHANNELS,
    PRIORITIES,
    WORK_MODES,
)
from src.services import (
    application_pack_service,
    candidate_brief_service,
    cold_prospecting_service,
    compensation_service,
    interview_service,
    job_discovery_service,
    job_import_service,
    job_service,
    outreach_service,
    playbook_service,
    preferences_service,
    profile_service,
    resume_service,
)
from src.utils.file_extract import extract_text_from_upload
from src.utils.text_utils import export_contact_incomplete, is_profile_incomplete

PAGES = [
    "Dashboard",
    "User Profile",
    "Job Discovery",
    "Add / Analyze Job",
    "Apply pack",
    "Resume Tailor",
    "Outreach Generator",
    "Interview Prep",
    "Application Tracker",
    "Compensation Comparator",
    "Cold prospecting",
]


def _today_str() -> str:
    return date.today().isoformat()


def _parse_date(s: Any) -> date | None:
    if s is None or s == "":
        return None
    try:
        return date.fromisoformat(str(s)[:10])
    except ValueError:
        return None


def _init_session() -> None:
    if "selected_user_id" not in st.session_state:
        st.session_state.selected_user_id = None
    if "resume_last_version_id" not in st.session_state:
        st.session_state.resume_last_version_id = None
    if "resume_last_payload" not in st.session_state:
        st.session_state.resume_last_payload = None


def _sidebar_profile_selector() -> None:
    st.sidebar.markdown("### Profile")
    users = profile_service.list_users()
    if not users:
        st.session_state.selected_user_id = None
        st.sidebar.info("No profiles yet. Open **User Profile** to create one.")
        return

    labels = [f"{u['name']} (#{u['id']})" for u in users]
    ids = [u["id"] for u in users]
    current = st.session_state.selected_user_id
    try:
        idx = ids.index(current) if current in ids else 0
    except ValueError:
        idx = 0

    choice = st.sidebar.selectbox("Active user", options=labels, index=idx)
    st.session_state.selected_user_id = ids[labels.index(choice)]


def _load_user_context(user_id: int) -> tuple[dict[str, Any], dict[str, Any]]:
    user = profile_service.get_user(user_id) or {}
    profile = profile_service.get_profile_for_user(user_id) or {}
    return user, profile


def _warn_incomplete_profile(user: dict[str, Any], profile: dict[str, Any]) -> None:
    bad, missing = is_profile_incomplete(user, profile)
    if bad:
        st.warning(
            "Add the essentials for accurate AI: " + ", ".join(missing) + ". See **User Profile**."
        )
    elif not (profile or {}).get("ai_candidate_brief"):
        st.info(
            "Optional: open **User Profile** and run **Update career brief (AI)** for role ideas and CTC target guidance."
        )


def _soft_contact_warning(user: dict[str, Any]) -> None:
    bad, miss = export_contact_incomplete(user)
    if bad and miss:
        st.caption("Tip: add " + ", ".join(miss) + " on **User Profile** for cleaner resume PDFs.")


def page_dashboard() -> None:
    st.header("Dashboard")
    uid = st.session_state.selected_user_id
    if not uid:
        st.info("Create your first profile under **User Profile**, then return here.")
        return

    user, profile = _load_user_context(uid)
    _warn_incomplete_profile(user, profile)

    jobs = job_service.list_jobs_for_user(uid)
    total = len(jobs)
    st.metric("Total jobs tracked", total)

    if not jobs:
        st.caption("Add roles from **Add / Analyze Job** to populate your pipeline.")
        return

    df = pd.DataFrame(jobs)
    if "status" in df.columns:
        counts = df["status"].value_counts().reindex(list(JOB_STATUSES)).fillna(0).astype(int)
        st.subheader("Applications by status")
        st.bar_chart(counts)

    fit_col = pd.to_numeric(df.get("fit_score"), errors="coerce")
    avg_fit = float(fit_col.dropna().mean()) if fit_col.notna().any() else None
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Average fit score", f"{avg_fit:.1f}" if avg_fit is not None else "—")
    with c2:
        high = int((fit_col >= 75).sum()) if fit_col.notna().any() else 0
        st.metric("High-fit jobs (≥75)", high)
    with c3:
        today = date.today()
        due = 0
        for _, row in df.iterrows():
            fd = _parse_date(row.get("follow_up_date"))
            if fd and fd <= today and row.get("status") not in ("Offer", "Rejected", "Paused"):
                due += 1
        st.metric("Follow-ups due / overdue", due)

    st.subheader("Follow-ups due soon")
    due_rows = []
    for j in jobs:
        fd = _parse_date(j.get("follow_up_date"))
        if fd and fd <= date.today() and j.get("status") not in ("Offer", "Rejected", "Paused"):
            due_rows.append(j)
    if due_rows:
        st.dataframe(pd.DataFrame(due_rows)[["id", "company_name", "role_title", "follow_up_date", "status"]], hide_index=True, use_container_width=True)
    else:
        st.caption("No follow-ups due today.")

    st.subheader("Recent jobs")
    recent = pd.DataFrame(jobs[:12])[
        ["company_name", "role_title", "fit_score", "status", "priority", "date_added"]
    ]
    st.dataframe(recent, hide_index=True, use_container_width=True)


def _clear_profile_widget_state(suffix: str) -> None:
    for k in (
        f"_hydr_sf_{suffix}",
        f"ln_{suffix}",
        f"cv_{suffix}",
        f"nm_{suffix}",
        f"em_{suffix}",
        f"ph_{suffix}",
        f"ctc_{suffix}",
    ):
        st.session_state.pop(k, None)


def page_user_profile() -> None:
    st.header("User Profile")
    st.caption(
        "Bring your **LinkedIn profile** as pasted text or a **PDF** (browser: open your profile → Print → Save as PDF). "
        "Add your **resume/CV** as text or PDF the same way. "
        "We only ask for your **current total CTC (LPA)** — the app infers skills, education, and experience from those sources."
    )
    users = profile_service.list_users()
    uid = st.session_state.selected_user_id

    with st.expander("Create another profile", expanded=False):
        st.caption("For friends sharing this app on one machine.")
        new_name = st.text_input("New profile label", key="new_prof_name")
        if st.button("Create blank profile") and new_name.strip():
            nid = profile_service.create_user({"name": new_name.strip()})
            profile_service.upsert_profile(
                nid,
                {
                    "linkedin_profile_text": "",
                    "resume_cv_text": "",
                    "base_resume_text": None,
                },
            )
            st.session_state.selected_user_id = nid
            _clear_profile_widget_state(str(nid))
            st.success(f"Created profile #{nid}")
            st.rerun()

    if uid:
        user, profile = _load_user_context(uid)
    else:
        user, profile = {}, {}
        if users:
            st.session_state.selected_user_id = users[0]["id"]
            st.rerun()

    suffix = str(uid) if uid else "new"
    hkey = f"_hydr_sf_{suffix}"
    if hkey not in st.session_state:
        if uid:
            st.session_state[f"ln_{suffix}"] = profile.get("linkedin_profile_text") or ""
            st.session_state[f"cv_{suffix}"] = (
                profile.get("resume_cv_text") or profile.get("base_resume_text") or ""
            )
            st.session_state[f"nm_{suffix}"] = user.get("name") or "My profile"
            st.session_state[f"em_{suffix}"] = user.get("email") or ""
            st.session_state[f"ph_{suffix}"] = user.get("phone") or ""
            st.session_state[f"ctc_{suffix}"] = float(user.get("current_ctc_lpa") or 0.0)
        else:
            st.session_state.setdefault(f"ln_{suffix}", "")
            st.session_state.setdefault(f"cv_{suffix}", "")
            st.session_state.setdefault(f"nm_{suffix}", "My profile")
            st.session_state.setdefault(f"em_{suffix}", "")
            st.session_state.setdefault(f"ph_{suffix}", "")
            st.session_state.setdefault(f"ctc_{suffix}", 0.0)
        st.session_state[hkey] = True

    st.subheader("Your inputs")
    st.text_input("Display name (sidebar label)", key=f"nm_{suffix}")
    st.text_input("Email (optional — for resume header)", key=f"em_{suffix}")
    st.text_input("Phone (optional)", key=f"ph_{suffix}")
    st.number_input("Current total CTC (LPA)", min_value=0.0, step=0.5, key=f"ctc_{suffix}")

    st.markdown(
        "**LinkedIn** — copy **Headline, About, Experience** from the site, "
        "or upload a **PDF** of your profile (print/save from the browser; text is extracted locally)."
    )
    ln_c1, ln_c2 = st.columns((2, 1))
    with ln_c1:
        st.text_area("LinkedIn profile text", key=f"ln_{suffix}", height=220)
    with ln_c2:
        st.markdown("**Or upload** PDF / text (appends on button).")
        up_ln = st.file_uploader("LinkedIn file", type=["pdf", "txt", "md"], key=f"ln_up_{suffix}")
        if up_ln is not None and st.button("Extract & append to LinkedIn", key=f"app_ln_{suffix}"):
            try:
                chunk = extract_text_from_upload(up_ln.name, up_ln.getvalue())
                if not chunk.strip():
                    st.error("No text extracted from file.")
                else:
                    cur_ln = str(st.session_state.get(f"ln_{suffix}", ""))
                    st.session_state[f"ln_{suffix}"] = (cur_ln + "\n\n" + chunk.strip()).strip()
                    st.success("Appended. Review the LinkedIn text box.")
                    st.rerun()
            except Exception as exc:  # noqa: BLE001
                st.error(str(exc))

    c1, c2 = st.columns((2, 1))
    with c1:
        st.markdown("**Resume / CV** — paste full text.")
        st.text_area("Resume / CV text", key=f"cv_{suffix}", height=320)
    with c2:
        st.markdown("**Or upload** PDF / text (appends on button).")
        up = st.file_uploader("File", type=["pdf", "txt", "md"], key=f"cv_up_{suffix}")
        if up is not None and st.button("Extract & append to CV", key=f"app_cv_{suffix}"):
            try:
                chunk = extract_text_from_upload(up.name, up.getvalue())
                if not chunk.strip():
                    st.error("No text extracted from file.")
                else:
                    cur = str(st.session_state.get(f"cv_{suffix}", ""))
                    st.session_state[f"cv_{suffix}"] = (cur + "\n\n" + chunk.strip()).strip()
                    st.success("Appended. Review the CV text box.")
                    st.rerun()
            except Exception as exc:  # noqa: BLE001
                st.error(str(exc))

    brief_raw = (profile or {}).get("ai_candidate_brief") if uid else None
    if brief_raw:
        st.subheader("Saved career brief (AI)")
        with st.expander("View raw JSON", expanded=False):
            st.json(brief_raw)

    st.subheader("Career guidance (AI)")
    st.caption(
        "Summarizes experience, education, and skills from your LinkedIn + CV only, then suggests **roles to explore** "
        "and **realistic CTC bands** for India given your stated current CTC."
    )
    if uid and st.button("Update career brief (AI)", type="secondary"):
        if not OPENAI_API_KEY:
            st.error("Add OPENAI_API_KEY to `.env` (see README).")
        else:
            ln = str(st.session_state.get(f"ln_{suffix}", ""))
            cv = str(st.session_state.get(f"cv_{suffix}", ""))
            ctc_val = float(st.session_state.get(f"ctc_{suffix}", 0.0) or 0.0)
            try:
                brief = candidate_brief_service.synthesize_brief(
                    linkedin_text=ln,
                    resume_cv_text=cv,
                    current_ctc_lpa=ctc_val if ctc_val > 0 else None,
                )
                candidate_brief_service.save_ai_brief(uid, brief)
                _clear_profile_widget_state(suffix)
                st.success("Career brief updated.")
                st.rerun()
            except Exception as exc:  # noqa: BLE001
                st.error(str(exc))

    if brief_raw and uid:
        try:
            b = json.loads(brief_raw)
            st.markdown("#### Roles to target")
            st.markdown(b.get("suggested_roles_to_target") or "—")
            st.markdown("#### CTC guidance")
            st.markdown(b.get("realistic_ctc_target_guidance") or "—")
            st.markdown("#### Caveats")
            st.markdown(b.get("caveats") or "—")
        except Exception:
            pass

    nm = str(st.session_state.get(f"nm_{suffix}", "My profile")).strip() or "My profile"
    em = str(st.session_state.get(f"em_{suffix}", "")).strip() or None
    ph = str(st.session_state.get(f"ph_{suffix}", "")).strip() or None
    ctc_v = float(st.session_state.get(f"ctc_{suffix}", 0.0) or 0.0)
    user_data = {
        "name": nm,
        "email": em,
        "phone": ph,
        "current_ctc_lpa": ctc_v if ctc_v > 0 else None,
        "current_location": None,
        "current_title": None,
        "current_company": None,
        "fixed_ctc_lpa": None,
        "variable_ctc_lpa": None,
        "esops_value_lpa": None,
        "expected_ctc_lpa": None,
        "notice_period_days": None,
        "preferred_locations": None,
        "target_roles": None,
        "target_industries": None,
    }
    ln_saved = str(st.session_state.get(f"ln_{suffix}", ""))
    cv_saved = str(st.session_state.get(f"cv_{suffix}", ""))
    existing_brief = (profile or {}).get("ai_candidate_brief") if uid else None
    prof_data = {
        "linkedin_profile_text": ln_saved or None,
        "resume_cv_text": cv_saved or None,
        "base_resume_text": cv_saved or None,
        "professional_summary": None,
        "skills": None,
        "work_experience": None,
        "projects": None,
        "achievements": None,
        "education": None,
        "certifications": None,
        "ai_candidate_brief": existing_brief,
    }

    if st.button("Save profile", type="primary"):
        if not uid:
            new_id = profile_service.merge_user_profile_form(None, user_data, prof_data)
            st.session_state.selected_user_id = new_id
            _clear_profile_widget_state("new")
        else:
            profile_service.merge_user_profile_form(uid, user_data, prof_data)
            _clear_profile_widget_state(suffix)
        st.success("Saved.")
        st.rerun()


def page_add_job() -> None:
    st.header("Add / Analyze Job")
    uid = st.session_state.selected_user_id
    if not uid:
        st.warning("Select a profile in the sidebar first.")
        return
    user, profile = _load_user_context(uid)
    _warn_incomplete_profile(user, profile)

    company = st.text_input("Company name")
    role = st.text_input("Role title")
    source = st.selectbox("Source", JOB_SOURCES)
    link = st.text_input("Job link")
    location = st.text_input("Location")
    mode = st.selectbox("Work mode", WORK_MODES)
    jd = st.text_area("Job description (paste full JD)", height=260)
    notes = st.text_area("Your notes", height=100)

    if st.button("Analyze Job Fit", type="primary"):
        if not jd.strip():
            st.error("Paste a job description first.")
        elif not OPENAI_API_KEY:
            st.error("Missing OPENAI_API_KEY in .env")
        else:
            base = {
                "company_name": company.strip() or None,
                "role_title": role.strip() or None,
                "source": source,
                "job_link": link or None,
                "location": location or None,
                "work_mode": mode,
                "jd_text": jd,
                "notes": notes or None,
                "date_added": _today_str(),
                "status": "Saved",
            }
            try:
                job_id, ai = job_service.analyze_and_save_job(
                    user_id=uid,
                    profile=profile,
                    user=user,
                    base_fields=base,
                )
                st.success(f"Saved job #{job_id}")
                st.json(ai)
            except Exception as exc:  # noqa: BLE001
                st.error(f"Analysis failed: {exc}")


def page_job_discovery() -> None:
    st.header("Job Discovery")
    uid = st.session_state.selected_user_id
    if not uid:
        st.warning("Select a profile in the sidebar first.")
        return
    user, profile = _load_user_context(uid)
    _warn_incomplete_profile(user, profile)

    st.markdown(
        "Run searches **in your own browser** on LinkedIn, Naukri, Instahyre, etc. This page gives an **AI playbook** "
        "(saved searches + queries), a **staging inbox** for links you paste, optional **JD blocks** for better ranking, "
        "then **import** into your tracker for resume tailoring and interview prep. **No SerpApi required.**"
    )

    prefs_row = preferences_service.get_preferences(uid)
    nl_default = (prefs_row or {}).get("preferences_nl") or ""
    prefs_struct: dict[str, Any] = {}
    if prefs_row and prefs_row.get("structured_json"):
        try:
            prefs_struct = json.loads(prefs_row["structured_json"])
        except json.JSONDecodeError:
            prefs_struct = {}

    tab_pref, tab_play, tab_imp, tab_stage = st.tabs(
        ["1. Preferences", "2. Playbook", "3. Import & JDs", "4. Stage & rank"]
    )

    with tab_pref:
        prefs_nl = st.text_area(
            "Job preferences (natural language)",
            value=nl_default,
            height=160,
            placeholder="Example: Bangalore or remote, min 45 LPA fixed-heavy, product roles in fintech, "
            "avoid IT services, open to Series B startups…",
            key=f"prefs_nl_{uid}",
        )
        c1, c2 = st.columns(2)
        with c1:
            if st.button("Save preferences", key=f"save_prefs_{uid}"):
                structured = (prefs_row or {}).get("structured_json")
                preferences_service.upsert_preferences(
                    uid, preferences_nl=prefs_nl, structured_json=structured
                )
                st.success("Saved.")
                st.rerun()
        with c2:
            if st.button("Parse preferences with AI", key=f"parse_prefs_{uid}"):
                if not OPENAI_API_KEY:
                    st.error("OPENAI_API_KEY missing.")
                else:
                    try:
                        parsed = preferences_service.parse_preferences_nl(prefs_nl)
                        preferences_service.upsert_preferences(
                            uid,
                            preferences_nl=prefs_nl,
                            structured_json=json.dumps(parsed, ensure_ascii=False),
                        )
                        st.success("Structured preferences updated.")
                        st.rerun()
                    except Exception as exc:  # noqa: BLE001
                        st.error(str(exc))
        with st.expander("Structured preferences (from AI)", expanded=False):
            st.json(prefs_struct or {})

    with tab_play:
        st.markdown("#### Quick portal links (from parsed prefs)")
        st.markdown(job_discovery_service.manual_search_links_markdown(prefs_struct or {}))
        st.divider()
        if st.button("Generate job hunt playbook (AI)", type="primary", key=f"pb_gen_{uid}"):
            if not OPENAI_API_KEY:
                st.error("OPENAI_API_KEY missing.")
            else:
                try:
                    pb = playbook_service.generate_playbook(
                        user,
                        profile,
                        preferences_nl=prefs_nl,
                        prefs_struct=prefs_struct or None,
                    )
                    st.session_state[f"playbook_json_{uid}"] = pb
                    st.success("Playbook ready — scroll down.")
                    st.rerun()
                except Exception as exc:  # noqa: BLE001
                    st.error(str(exc))
        pb = st.session_state.get(f"playbook_json_{uid}")
        if pb:
            st.markdown(pb.get("strategy_summary") or "")
            st.markdown("##### Saved LinkedIn-style searches")
            for s in pb.get("saved_searches") or []:
                name = s.get("name") or "Search"
                url = s.get("linkedin_jobs_url") or ""
                st.markdown(f"**{name}**")
                if url.startswith("http"):
                    st.link_button(f"Open: {name}", url)
                st.caption(s.get("notes") or "")
            st.markdown(pb.get("other_portals_markdown") or "")
            st.markdown("##### Google queries (paste into Google manually)")
            for q in pb.get("google_queries_for_manual_search") or []:
                st.code(q)
            st.markdown(pb.get("weekly_routine_markdown") or "")

    with tab_imp:
        st.markdown(
            "Paste **one URL per line**, or messy text (bullets, recruiter DMs). "
            "Then attach **JD text** in the next tab using blocks separated by the delimiter (default `---` line)."
        )
        raw_import = st.text_area("Paste URLs or job text", height=220, key=f"imp_raw_{uid}")
        mode = st.radio(
            "Import mode",
            ["URLs only (regex)", "AI extract rows (needs URLs in text)"],
            horizontal=True,
            key=f"imp_mode_{uid}",
        )
        if st.button("Append to staging table", type="primary", key=f"imp_go_{uid}"):
            if not raw_import.strip():
                st.error("Paste something first.")
            elif mode.startswith("URLs"):
                urls = job_import_service.extract_urls(raw_import)
                if not urls:
                    st.error("No http(s) URLs found.")
                else:
                    leads = job_import_service.leads_from_urls_only(urls)
                    n = job_discovery_service.append_leads(uid, leads)
                    st.success(f"Added {n} lead(s). Open tab 4 to attach JDs / rank / import.")
                    st.rerun()
            else:
                if not OPENAI_API_KEY:
                    st.error("OPENAI_API_KEY required for AI extract.")
                else:
                    try:
                        leads = job_import_service.leads_from_ai_extract(
                            raw_import, user=user, profile=profile
                        )
                        if not leads:
                            st.error("AI found no rows with valid URLs.")
                        else:
                            n = job_discovery_service.append_leads(uid, leads)
                            st.success(f"Added {n} lead(s).")
                            st.rerun()
                    except Exception as exc:  # noqa: BLE001
                        st.error(str(exc))

    with tab_stage:
        open_cnt = len(job_discovery_service.list_open_leads_ordered(uid))
        st.caption(f"Open (unimported) leads: **{open_cnt}** — sorted by id ascending for JD / rank order.")
        if st.button("Clear staging table", key=f"clr_leads_{uid}"):
            job_discovery_service.clear_leads(uid)
            st.session_state.pop(f"playbook_json_{uid}", None)
            st.success("Staging cleared.")
            st.rerun()

        delim = st.text_input(
            "JD separator (use between pasted JD blocks)",
            value="---",
            key=f"jd_delim_{uid}",
            help="First block → lowest lead id, second → next, etc.",
        )
        bulk_jd = st.text_area(
            "Paste JD blocks (same order as open leads, split by separator above)",
            height=200,
            key=f"bulk_jd_{uid}",
        )
        if st.button("Attach JD blocks to open leads", key=f"jd_apply_{uid}"):
            if not delim.strip():
                st.error("Set a non-empty delimiter.")
            else:
                n, extra = job_discovery_service.apply_bulk_jds_to_open_leads(
                    uid, bulk_jd, delimiter=delim
                )
                st.success(f"Updated {n} lead(s).")
                if extra:
                    st.warning(f"{extra} JD block(s) left over — add more leads or check order.")
                st.rerun()

        if st.button("AI rank open leads (uses JD/snippet + prefs)", type="primary", key=f"rank_open_{uid}"):
            if not OPENAI_API_KEY:
                st.error("OPENAI_API_KEY missing.")
            else:
                try:
                    n, warn = job_discovery_service.rank_and_persist_open_leads(
                        uid, user, profile, prefs_struct or {}
                    )
                    if n == 0:
                        st.info("No open leads to rank.")
                    else:
                        st.success(f"Ranked {n} lead(s).")
                    if warn:
                        st.warning(warn)
                    st.rerun()
                except Exception as exc:  # noqa: BLE001
                    st.error(str(exc))

        leads = job_discovery_service.list_leads(uid)
        if leads:
            st.subheader("Staging & history")
            df = pd.DataFrame(leads)
            show_cols = [
                c
                for c in [
                    "id",
                    "company_name",
                    "title",
                    "ai_fit_score",
                    "apply_recommendation",
                    "imported_job_id",
                    "job_url",
                ]
                if c in df.columns
            ]
            st.dataframe(df[show_cols], hide_index=True, use_container_width=True)
            open_opts = {
                f"#{row['id']} {row.get('company_name')} — {row.get('title')} (fit {row.get('ai_fit_score', '—')})": int(
                    row["id"]
                )
                for _, row in df.iterrows()
                if not row.get("imported_job_id") and row.get("job_url")
            }
            if open_opts:
                pick_open = st.selectbox("Open job link", ["—"] + list(open_opts.keys()), key=f"oplnk_{uid}")
                if pick_open != "—":
                    lid = open_opts[pick_open]
                    row = job_discovery_service.get_lead(lid)
                    url = (row or {}).get("job_url")
                    if url:
                        st.link_button("Open posting", url)

            imp_opts = {
                f"#{row['id']} {row.get('company_name')} — {row.get('title')}": int(row["id"])
                for _, row in df.iterrows()
                if not row.get("imported_job_id")
            }
            picked = st.multiselect(
                "Import into pipeline (runs JD fit analysis)", list(imp_opts.keys()), key=f"imp_ms_{uid}"
            )
            if st.button("Import selected to tracker", key=f"imp_sel_{uid}") and picked:
                if not OPENAI_API_KEY:
                    st.error("OPENAI_API_KEY missing.")
                else:
                    for label in picked:
                        lid = imp_opts[label]
                        try:
                            jid = job_discovery_service.import_lead(
                                lid, user_id=uid, user=user, profile=profile
                            )
                            st.success(f"Imported lead #{lid} → job #{jid}")
                        except Exception as exc:  # noqa: BLE001
                            st.error(f"Lead #{lid}: {exc}")
                    st.rerun()
        else:
            st.info("Staging is empty — use **Import & JDs** to add links.")


def page_apply_pack() -> None:
    st.header("Apply pack")
    uid = st.session_state.selected_user_id
    if not uid:
        st.warning("Select a profile in the sidebar first.")
        return
    user, profile = _load_user_context(uid)
    _warn_incomplete_profile(user, profile)
    _soft_contact_warning(user)

    st.markdown(
        "Generate a **cover letter** and use **Resume Tailor** for the same job. "
        "Complete the application on the employer or portal site yourself — this tool does not auto-apply."
    )

    jobs = job_service.list_jobs_for_user(uid)
    if not jobs:
        st.info("Add or import a job first.")
        return
    labels = {f"{j['company_name']} — {j['role_title']} (#{j['id']})": j["id"] for j in jobs}
    pick = st.selectbox("Job", list(labels.keys()), key="apply_job_pick")
    job = job_service.get_job(labels[pick]) or {}

    if job.get("job_link"):
        st.link_button("Open job posting", job["job_link"])

    if st.button("Generate cover letter + checklist", type="primary", key="gen_cl"):
        if not OPENAI_API_KEY:
            st.error("OPENAI_API_KEY missing.")
        else:
            try:
                pack = application_pack_service.generate_cover_letter(
                    user=user, profile=profile, job=job
                )
                st.session_state["last_cover_pack"] = pack
            except Exception as exc:  # noqa: BLE001
                st.error(str(exc))

    pack = st.session_state.get("last_cover_pack")
    if pack:
        st.text_area("Cover letter", value=pack.get("cover_letter_text") or "", height=260, key="cl_view")
        st.markdown(pack.get("application_checklist_markdown") or "")

    st.divider()
    st.caption("After you submit on the portal, mark the application here for tracker + interview prep.")
    if st.button("Mark this job as Applied", key="mark_applied"):
        job_service.patch_job(
            int(job["id"]),
            {"status": "Applied", "notes": (job.get("notes") or "") + "\nMarked applied from Apply pack."},
        )
        st.success("Status updated to Applied.")
        st.rerun()


def page_cold_prospecting() -> None:
    st.header("Cold prospecting")
    uid = st.session_state.selected_user_id
    if not uid:
        st.warning("Select a profile in the sidebar first.")
        return
    user, profile = _load_user_context(uid)
    _warn_incomplete_profile(user, profile)

    st.markdown(
        "Light **company research** (from name/URL + your profile only — no live scraping) and a **cold email draft**. "
        "Review assumptions, verify facts, then send from your own mailbox."
    )

    prefs_row = preferences_service.get_preferences(uid)
    prefs_nl = st.text_area(
        "Preferences context for this outreach",
        value=(prefs_row or {}).get("preferences_nl") or "",
        height=120,
        key=f"cold_prefs_{uid}",
    )
    cname = st.text_input("Company name", key=f"cold_co_{uid}")
    curl = st.text_input("Company or careers URL", key=f"cold_url_{uid}")

    if st.button("Generate research + email draft", type="primary", key=f"cold_go_{uid}"):
        if not OPENAI_API_KEY:
            st.error("OPENAI_API_KEY missing.")
        elif not cname.strip():
            st.error("Enter a company name.")
        else:
            try:
                out = cold_prospecting_service.generate_cold_pack(
                    user=user,
                    profile=profile,
                    preferences_nl=prefs_nl,
                    company_name=cname.strip(),
                    company_url=curl.strip(),
                )
                st.session_state["cold_last"] = out
            except Exception as exc:  # noqa: BLE001
                st.error(str(exc))

    out = st.session_state.get("cold_last")
    if out:
        st.subheader("Research")
        st.markdown(out.get("research_summary") or "")
        st.warning(out.get("assumptions_to_verify") or "Verify company facts before sending.")
        st.subheader("Email")
        st.text_input("Subject", value=out.get("email_subject") or "", key="cold_subj")
        st.text_area("Body", value=out.get("email_body") or "", height=280, key="cold_body")
        if st.button("Save draft to database", key="cold_save"):
            cold_prospecting_service.save_draft(
                uid,
                company_name=cname.strip(),
                company_url=curl.strip(),
                research_summary=out.get("research_summary") or "",
                email_subject=out.get("email_subject") or "",
                email_body=out.get("email_body") or "",
            )
            st.success("Saved draft.")
            st.rerun()

    drafts = cold_prospecting_service.list_drafts(uid)
    if drafts:
        st.subheader("Recent drafts")
        st.dataframe(
            pd.DataFrame(drafts)[["company_name", "email_subject", "created_at"]],
            hide_index=True,
            use_container_width=True,
        )


def page_resume() -> None:
    st.header("Resume Tailor")
    uid = st.session_state.selected_user_id
    if not uid:
        st.warning("Select a profile in the sidebar.")
        return
    user, profile = _load_user_context(uid)
    _warn_incomplete_profile(user, profile)
    _soft_contact_warning(user)

    jobs = job_service.list_jobs_for_user(uid)
    if not jobs:
        st.info("Add a job first.")
        return
    job_labels = {f"{j['company_name']} — {j['role_title']} (#{j['id']})": j["id"] for j in jobs}
    pick = st.selectbox("Job", list(job_labels.keys()))
    job_id = job_labels[pick]
    job = job_service.get_job(job_id) or {}

    st.subheader("JD context")
    st.write(f"**Fit score:** {job.get('fit_score') or '—'}")
    with st.expander("Fit summary & keywords"):
        st.write(job.get("fit_summary") or "—")
        st.caption(job.get("resume_keywords") or "")

    if st.button("Generate Tailored Resume", type="primary"):
        if not OPENAI_API_KEY:
            st.error("Missing OPENAI_API_KEY in .env")
        else:
            try:
                payload = resume_service.generate_tailored_resume(
                    user=user, profile=profile, job=job
                )
                vid = resume_service.save_resume_version(
                    uid, job_id, {**payload, "docx_path": None}
                )
                st.session_state.resume_last_version_id = vid
                st.session_state.resume_last_payload = payload
                st.success("Tailored resume generated and saved.")
            except Exception as exc:  # noqa: BLE001
                st.error(str(exc))

    payload = st.session_state.resume_last_payload
    if payload:
        st.subheader("Latest generated resume")
        st.text_input("Headline", value=payload.get("resume_headline") or "", disabled=True)
        st.text_area("Summary", value=payload.get("professional_summary") or "", height=120)
        st.text_area("Skills", value=payload.get("tailored_skills") or "", height=120)
        st.text_area("Experience", value=payload.get("tailored_experience") or "", height=220)
        st.text_area("Final resume text", value=payload.get("final_resume_text") or "", height=260)

    if st.button("Export DOCX") and st.session_state.resume_last_payload:
        try:
            p = st.session_state.resume_last_payload
            path = resume_service.export_resume_docx(user=user, profile=profile, resume=p, job=job)
            vid = st.session_state.resume_last_version_id
            if vid:
                resume_service.update_resume_docx_path(vid, str(path.relative_to(ROOT)))
            with open(path, "rb") as f:
                st.download_button(
                    "Download DOCX",
                    data=f.read(),
                    file_name=path.name,
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                )
            st.caption(f"Saved to `{path}`")
        except Exception as exc:  # noqa: BLE001
            st.error(str(exc))

    versions = resume_service.list_resume_versions(uid, job_id)
    if versions:
        st.subheader("History")
        st.dataframe(pd.DataFrame(versions).drop(columns=["docx_path"], errors="ignore"), hide_index=True, use_container_width=True)


def page_outreach() -> None:
    st.header("Outreach Generator")
    uid = st.session_state.selected_user_id
    if not uid:
        st.warning("Select a profile in the sidebar.")
        return
    user, profile = _load_user_context(uid)
    _warn_incomplete_profile(user, profile)
    _soft_contact_warning(user)

    jobs = job_service.list_jobs_for_user(uid)
    if not jobs:
        st.info("Add a job first.")
        return
    job_labels = {f"{j['company_name']} — {j['role_title']} (#{j['id']})": j["id"] for j in jobs}
    pick = st.selectbox("Job", list(job_labels.keys()), key="out_job")
    job_id = job_labels[pick]
    job = job_service.get_job(job_id) or {}

    r_name = st.text_input("Recipient name")
    r_role = st.text_input("Recipient role / title")
    channel = st.selectbox("Channel", OUTREACH_CHANNELS)
    mtype = st.selectbox("Message type", MESSAGE_TYPES)

    if st.button("Generate Message", type="primary"):
        if not OPENAI_API_KEY:
            st.error("Missing OPENAI_API_KEY in .env")
        else:
            try:
                data = outreach_service.generate_outreach(
                    profile=profile,
                    user=user,
                    job=job,
                    recipient_name=r_name,
                    recipient_role=r_role,
                    channel=channel,
                    message_type=mtype,
                )
                text = data.get("message_text") or ""
                st.session_state["outreach_draft_text"] = text
                st.session_state["outreach_draft_meta"] = {
                    "recipient_name": r_name,
                    "recipient_role": r_role,
                    "channel": channel,
                    "message_type": mtype,
                }
            except Exception as exc:  # noqa: BLE001
                st.error(str(exc))

    draft = st.session_state.get("outreach_draft_text")
    if draft is not None:
        st.text_area("Message", value=draft, height=240, key="outreach_editor")
        meta = st.session_state.get("outreach_draft_meta") or {}
        if meta.get("channel") == "LinkedIn" and len(draft) > 900:
            st.warning("LinkedIn DM is over 900 characters — shorten manually before sending.")
        if st.button("Save message to tracker", key="save_outreach"):
            outreach_service.save_outreach(
                uid,
                job_id,
                recipient_name=meta.get("recipient_name") or r_name,
                recipient_role=meta.get("recipient_role") or r_role,
                channel=meta.get("channel") or channel,
                message_type=meta.get("message_type") or mtype,
                message_text=st.session_state.get("outreach_editor", draft),
            )
            st.success("Saved outreach draft.")
            st.rerun()

    hist = outreach_service.list_outreach_for_job(uid, job_id)
    if hist:
        st.subheader("Saved messages")
        st.dataframe(pd.DataFrame(hist), hide_index=True, use_container_width=True)


def page_interview() -> None:
    st.header("Interview Prep")
    uid = st.session_state.selected_user_id
    if not uid:
        st.warning("Select a profile in the sidebar.")
        return
    user, profile = _load_user_context(uid)
    _warn_incomplete_profile(user, profile)

    jobs = job_service.list_jobs_for_user(uid)
    if not jobs:
        st.info("Add a job first.")
        return
    job_labels = {f"{j['company_name']} — {j['role_title']} (#{j['id']})": j["id"] for j in jobs}
    pick = st.selectbox("Job", list(job_labels.keys()), key="int_job")
    job_id = job_labels[pick]
    job = job_service.get_job(job_id) or {}

    if st.button("Generate Interview Prep Pack", type="primary"):
        if not OPENAI_API_KEY:
            st.error("Missing OPENAI_API_KEY in .env")
        else:
            try:
                pack = interview_service.generate_interview_prep(
                    profile=profile, user=user, job=job
                )
                interview_service.save_interview_prep(uid, job_id, pack)
                st.success("Prep pack saved.")
            except Exception as exc:  # noqa: BLE001
                st.error(str(exc))

    pack = interview_service.latest_interview_prep(uid, job_id)
    if pack:
        tabs = st.tabs(["Company", "Role", "Questions", "STAR", "Cases", "Salary"])
        with tabs[0]:
            st.markdown(pack.get("company_research") or "")
        with tabs[1]:
            st.markdown(pack.get("role_prep") or "")
        with tabs[2]:
            st.markdown(pack.get("likely_questions") or "")
        with tabs[3]:
            st.markdown(pack.get("star_stories") or "")
        with tabs[4]:
            st.markdown(pack.get("case_questions") or "")
        with tabs[5]:
            st.markdown(pack.get("salary_pitch") or "")


def page_tracker() -> None:
    st.header("Application Tracker")
    uid = st.session_state.selected_user_id
    if not uid:
        st.warning("Select a profile in the sidebar.")
        return

    jobs = job_service.list_jobs_for_user(uid)
    if not jobs:
        st.info("No jobs yet.")
        return

    df = pd.DataFrame(jobs)
    st.subheader("Filters")
    fc1, fc2, fc3, fc4 = st.columns(4)
    with fc1:
        f_status = st.multiselect("Status", JOB_STATUSES, default=[])
    with fc2:
        f_priority = st.multiselect("Priority", PRIORITIES, default=[])
    with fc3:
        f_source = st.multiselect("Source", JOB_SOURCES, default=[])
    with fc4:
        min_fit = st.number_input("Min fit score", min_value=0.0, max_value=100.0, value=0.0, step=1.0)

    view = df.copy()
    view["fit_score"] = pd.to_numeric(view["fit_score"], errors="coerce")
    if f_status:
        view = view[view["status"].isin(f_status)]
    if f_priority:
        view = view[view["priority"].isin(f_priority)]
    if f_source:
        view = view[view["source"].isin(f_source)]
    if min_fit > 0:
        view = view[view["fit_score"] >= min_fit]

    st.caption(f"Showing {len(view)} of {len(df)} jobs")

    editor_cols = [
        "id",
        "company_name",
        "role_title",
        "source",
        "fit_score",
        "status",
        "priority",
        "follow_up_date",
        "notes",
    ]
    for col in editor_cols:
        if col not in view.columns:
            view[col] = None
    edit_df = view[editor_cols].copy()

    edited = st.data_editor(
        edit_df,
        hide_index=True,
        use_container_width=True,
        disabled=["id", "company_name", "role_title", "source", "fit_score"],
        num_rows="fixed",
        key="job_tracker_editor",
    )

    if st.button("Save table changes"):
        for _, row in edited.iterrows():
            jid = int(row["id"])
            job_service.patch_job(
                jid,
                {
                    "status": row.get("status"),
                    "priority": row.get("priority") or None,
                    "follow_up_date": row.get("follow_up_date") or None,
                    "notes": row.get("notes"),
                },
            )
        st.success("Updates saved.")
        st.rerun()

    st.subheader("Follow-ups due")
    today = date.today()
    due = []
    for _, row in df.iterrows():
        fd = _parse_date(row.get("follow_up_date"))
        if fd and fd <= today and row.get("status") not in ("Offer", "Rejected", "Paused"):
            due.append(row)
    if due:
        st.dataframe(pd.DataFrame(due)[["company_name", "role_title", "follow_up_date", "status"]], hide_index=True, use_container_width=True)
    else:
        st.caption("None due.")


def page_compensation() -> None:
    st.header("Compensation Comparator")
    st.caption("All amounts in INR Lakhs per annum (LPA) unless noted.")

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Current offer**")
        cur_fixed = st.number_input("Current fixed", value=0.0, step=0.5, key="cc_cf")
        cur_var = st.number_input("Current variable", value=0.0, step=0.5, key="cc_cv")
        cur_esop = st.number_input("Current ESOP (annualized / fair value)", value=0.0, step=0.5, key="cc_ce")
    with c2:
        st.markdown("**New offer**")
        new_fixed = st.number_input("New fixed", value=0.0, step=0.5, key="cc_nf")
        new_var = st.number_input("New variable", value=0.0, step=0.5, key="cc_nv")
        join_bonus = st.number_input("Joining bonus (LPA)", value=0.0, step=0.5, key="cc_jb")
        retention = st.number_input("Retention bonus (LPA)", value=0.0, step=0.5, key="cc_rb")
        new_esop = st.number_input("New ESOP value (LPA)", value=0.0, step=0.5, key="cc_ne")

    tax = st.number_input("Optional expected tax rate %", min_value=0.0, max_value=60.0, value=0.0, step=0.5)
    relocation = st.number_input("Optional location change cost (LPA)", value=0.0, step=0.25)

    inputs = {
        "current_fixed": cur_fixed,
        "current_variable": cur_var,
        "current_esop_annual": cur_esop,
        "new_fixed": new_fixed,
        "new_variable": new_var,
        "joining_bonus": join_bonus,
        "retention_bonus": retention,
        "new_esop_value": new_esop,
        "tax_rate_pct": tax,
        "relocation_cost": relocation,
    }

    if st.button("Compare packages", type="primary"):
        st.session_state["cc_metrics"] = compensation_service.compute_compensation_metrics(inputs)
        st.session_state["cc_inputs"] = dict(inputs)

    metrics = st.session_state.get("cc_metrics")
    if metrics:
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Current total CTC", f"{metrics['current_total_ctc']:.2f} LPA")
        m2.metric("New total CTC", f"{metrics['new_total_ctc']:.2f} LPA")
        inc = metrics["total_increase_pct"]
        m3.metric("Total CTC change %", f"{inc:.1f}%" if inc is not None else "—")
        fx = metrics["fixed_increase_pct"]
        m4.metric("Fixed salary change %", f"{fx:.1f}%" if fx is not None else "—")

        st.metric("Risk-adjusted offer (heuristic)", f"{metrics['risk_adjusted_offer_value']:.2f} LPA")
        st.caption(
            f"Monthly pre-tax fixed (new): **{metrics['monthly_pre_tax_fixed']:.2f}** | "
            f"After-tax estimate (if tax% set): **{metrics['monthly_pre_tax_fixed_after_tax_estimate']:.2f}**"
        )

        if metrics.get("paper_ctc_up_fixed_weak"):
            st.error(
                "Heads up: paper CTC may be up, but **fixed salary is weaker** than your current fixed. "
                "Indian offers often inflate variable/ESOP — push for fixed or clarity on pay-out."
            )

        if st.button("Generate negotiation brief (AI)", key="cc_ai"):
            if not OPENAI_API_KEY:
                st.error("Missing OPENAI_API_KEY in .env")
            else:
                try:
                    inp = st.session_state.get("cc_inputs") or inputs
                    advice = compensation_service.ai_compensation_advice(inp, metrics)
                    st.session_state["cc_advice"] = advice
                except Exception as exc:  # noqa: BLE001
                    st.error(str(exc))

        advice = st.session_state.get("cc_advice")
        if advice:
            st.subheader("Negotiation recommendation")
            st.write(advice.get("negotiation_recommendation"))
            st.subheader("Talking points")
            st.write(advice.get("talking_points"))
            st.subheader("Risk notes")
            st.write(advice.get("risk_notes"))


def main() -> None:
    st.set_page_config(page_title="Job Search Copilot", layout="wide")
    init_db()
    _init_session()

    st.sidebar.title("Job Search Copilot")
    _sidebar_profile_selector()

    page = st.sidebar.radio("Navigate", PAGES)

    if page == "Dashboard":
        page_dashboard()
    elif page == "User Profile":
        page_user_profile()
    elif page == "Job Discovery":
        page_job_discovery()
    elif page == "Add / Analyze Job":
        page_add_job()
    elif page == "Apply pack":
        page_apply_pack()
    elif page == "Resume Tailor":
        page_resume()
    elif page == "Outreach Generator":
        page_outreach()
    elif page == "Interview Prep":
        page_interview()
    elif page == "Application Tracker":
        page_tracker()
    elif page == "Compensation Comparator":
        page_compensation()
    elif page == "Cold prospecting":
        page_cold_prospecting()


if __name__ == "__main__":
    main()
