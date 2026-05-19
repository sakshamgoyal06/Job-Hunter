"""
Indian Job Search Copilot — Streamlit entrypoint.

Run from repo root or this folder:
  streamlit run job_search_copilot/app.py
  cd job_search_copilot && streamlit run app.py
"""

from __future__ import annotations

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
    compensation_service,
    interview_service,
    job_service,
    outreach_service,
    profile_service,
    resume_service,
)
from src.utils.text_utils import is_profile_incomplete

PAGES = [
    "Dashboard",
    "User Profile",
    "Add / Analyze Job",
    "Resume Tailor",
    "Outreach Generator",
    "Interview Prep",
    "Application Tracker",
    "Compensation Comparator",
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
            "Profile looks incomplete for best AI results: "
            + ", ".join(missing)
            + ". Visit **User Profile**."
        )


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


def page_user_profile() -> None:
    st.header("User Profile")
    users = profile_service.list_users()
    uid = st.session_state.selected_user_id

    with st.expander("Create another profile", expanded=False):
        st.caption("Use this for friends sharing the same app instance.")
        new_name = st.text_input("New profile name", key="new_prof_name")
        if st.button("Create blank profile") and new_name.strip():
            nid = profile_service.create_user({"name": new_name.strip()})
            profile_service.upsert_profile(nid, {})
            st.session_state.selected_user_id = nid
            st.success(f"Created profile #{nid}")
            st.rerun()

    if uid:
        user, profile = _load_user_context(uid)
    else:
        user, profile = {}, {}
        if users:
            st.session_state.selected_user_id = users[0]["id"]
            st.rerun()

    st.subheader("Basics")
    c1, c2 = st.columns(2)
    with c1:
        name = st.text_input("Name", value=user.get("name") or "")
        email = st.text_input("Email", value=user.get("email") or "")
        phone = st.text_input("Phone", value=user.get("phone") or "")
        loc = st.text_input("Current location", value=user.get("current_location") or "")
        title = st.text_input("Current title", value=user.get("current_title") or "")
        company = st.text_input("Current company", value=user.get("current_company") or "")
    with c2:
        cur_ctc = st.number_input("Current CTC (LPA)", value=float(user.get("current_ctc_lpa") or 0.0), step=0.5)
        fixed_ctc = st.number_input("Fixed CTC (LPA)", value=float(user.get("fixed_ctc_lpa") or 0.0), step=0.5)
        var_ctc = st.number_input("Variable CTC (LPA)", value=float(user.get("variable_ctc_lpa") or 0.0), step=0.5)
        esop = st.number_input("ESOPs value (LPA equiv.)", value=float(user.get("esops_value_lpa") or 0.0), step=0.5)
        exp_ctc = st.number_input("Expected CTC (LPA)", value=float(user.get("expected_ctc_lpa") or 0.0), step=0.5)
        notice = st.number_input("Notice period (days)", value=int(user.get("notice_period_days") or 0), step=1)
        pref_loc = st.text_area("Preferred locations", value=user.get("preferred_locations") or "")
        tgt_roles = st.text_area("Target roles", value=user.get("target_roles") or "")
        tgt_ind = st.text_area("Target industries", value=user.get("target_industries") or "")

    st.subheader("Profile content")
    summary = st.text_area("Professional summary", value=profile.get("professional_summary") or "", height=120)
    skills = st.text_area("Skills", value=profile.get("skills") or "", height=120)
    work_exp = st.text_area("Work experience", value=profile.get("work_experience") or "", height=220)
    projects = st.text_area("Projects", value=profile.get("projects") or "", height=160)
    achievements = st.text_area("Achievements", value=profile.get("achievements") or "", height=160)
    education = st.text_area("Education", value=profile.get("education") or "", height=120)
    certs = st.text_area("Certifications", value=profile.get("certifications") or "", height=100)
    base_resume = st.text_area("Base resume text", value=profile.get("base_resume_text") or "", height=260)

    user_data = {
        "name": name.strip() or "Friend",
        "email": email or None,
        "phone": phone or None,
        "current_location": loc or None,
        "current_title": title or None,
        "current_company": company or None,
        "current_ctc_lpa": cur_ctc or None,
        "fixed_ctc_lpa": fixed_ctc or None,
        "variable_ctc_lpa": var_ctc or None,
        "esops_value_lpa": esop or None,
        "expected_ctc_lpa": exp_ctc or None,
        "notice_period_days": int(notice) if notice else None,
        "preferred_locations": pref_loc or None,
        "target_roles": tgt_roles or None,
        "target_industries": tgt_ind or None,
    }
    prof_data = {
        "professional_summary": summary or None,
        "skills": skills or None,
        "work_experience": work_exp or None,
        "projects": projects or None,
        "achievements": achievements or None,
        "education": education or None,
        "certifications": certs or None,
        "base_resume_text": base_resume or None,
    }

    if st.button("Save profile", type="primary"):
        new_id = profile_service.merge_user_profile_form(uid, user_data, prof_data)
        st.session_state.selected_user_id = new_id
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


def page_resume() -> None:
    st.header("Resume Tailor")
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
    elif page == "Add / Analyze Job":
        page_add_job()
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


if __name__ == "__main__":
    main()
