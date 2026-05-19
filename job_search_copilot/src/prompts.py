"""Centralized LLM prompts — India-specific hiring context, honesty rules."""

from __future__ import annotations

import json
from typing import Any


def candidate_inputs_json(user: dict[str, Any], profile: dict[str, Any] | None) -> str:
    """Single JSON blob for all downstream tasks: LinkedIn + CV + CTC + optional AI synthesis."""
    profile = profile or {}
    brief: Any = {}
    raw = profile.get("ai_candidate_brief")
    if raw:
        try:
            brief = json.loads(raw)
        except json.JSONDecodeError:
            brief = {"_note": "Could not parse stored synthesis JSON."}
    payload = {
        "contact": {
            "name": user.get("name"),
            "email": user.get("email"),
            "phone": user.get("phone"),
        },
        "current_ctc_lpa": user.get("current_ctc_lpa"),
        "linkedin_profile_text": profile.get("linkedin_profile_text") or "",
        "resume_cv_text": (profile.get("resume_cv_text") or profile.get("base_resume_text") or ""),
        "ai_synthesis": brief,
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def candidate_synthesis_prompt(
    *,
    linkedin_text: str,
    resume_cv_text: str,
    current_ctc_lpa: float | None,
) -> tuple[str, str]:
    system = """You are an India-focused career advisor for employed professionals.
You ONLY infer facts from the pasted LinkedIn profile text and resume/CV text the user provides.
If either source is missing or very thin, say so in caveats — do not invent employers, degrees, skills, or metrics.

The user has stated their current total CTC in Indian Lakhs per annum (LPA). Use it to give realistic
switch / stretch CTC guidance for the Indian market (fixed-heavy vs variable/ESOP-heavy offers, startups vs MNCs).

Output STRICT JSON only (no markdown fences)."""
    user_msg = f"""Current total CTC (LPA) as stated by user: {current_ctc_lpa!s}

LinkedIn profile text (may include headline, about, experience bullets — pasted by user):
---
{linkedin_text or "(empty)"}
---

Resume / CV text (pasted by user):
---
{resume_cv_text or "(empty)"}
---

Return JSON with keys exactly:
{{
  "experience_summary": string,
  "education_summary": string,
  "skills": string,
  "suggested_roles_to_target": string,
  "realistic_ctc_target_guidance": string,
  "seniority_read": string,
  "caveats": string
}}

realistic_ctc_target_guidance: concrete LPA ranges (e.g. conservative switch vs stretch) with 2–4 sentences,
grounded in the seniority and domains visible in the text. If CTC is missing/null, explain ranges qualitatively
and ask the user to add current CTC for tighter guidance.

suggested_roles_to_target: bullet-style lines of role titles / families to explore in India (product, fintech,
analytics, strategy, founder's office, etc.) based ONLY on evidence in the two texts."""
    return system, user_msg


def analyze_job_prompt(profile: dict[str, Any], user: dict[str, Any], jd: str) -> tuple[str, str]:
    system = """You are an expert India-focused career coach and recruiter analyst.
You understand Indian hiring: CTC in LPA, fixed vs variable pay, ESOPs, notice periods,
Indian portals (Naukri, Instahyre, LinkedIn India), referrals, recruiter spam vs real roles,
fintech, product, growth, strategy, analytics, operations, founder's office, AI/ML roles,
startups vs MNCs, BigTech, IT services, GCCs, and hybrid/remote norms in Indian cities.

Rules:
- Candidate facts come ONLY from linkedin_profile_text, resume_cv_text, and current_ctc_lpa in the JSON.
  The ai_synthesis block is a convenience summary — if it conflicts with raw LinkedIn/CV text, trust the raw text.
- Never invent candidate facts not supported by those sources.
- If JD is vague, infer cautiously and say so in fit_summary.
- Output STRICT JSON only (no markdown fences) matching the schema the user requests.
- fit_score is 0-100 integer based on skills + role alignment + seniority + domain transferability.
- Be candid about gaps; Indian hiring is credential and keyword sensitive for ATS.
- apply_recommendation: "Apply", "Maybe", or "Skip" with honest reasoning.
- priority: High, Medium, or Low for THIS candidate (not generic job quality).
- follow_up_suggestion: concrete India-context next step (referral path, recruiter, timeline)."""
    user_msg = f"""Candidate JSON (LinkedIn paste + CV + CTC + optional synthesis):\n{candidate_inputs_json(user, profile)}\n\nJob description (may include Hindi/English mix):\n{jd}\n\nReturn JSON with keys exactly:
{{
  "company_name": string,
  "role_title": string,
  "role_category": string,
  "seniority_level": string,
  "required_skills": string,
  "preferred_skills": string,
  "responsibilities": string,
  "resume_keywords": string,
  "fit_score": number,
  "fit_summary": string,
  "missing_skills": string,
  "apply_recommendation": string,
  "priority": "High" | "Medium" | "Low",
  "follow_up_suggestion": string
}}
Use comma-separated or newline-separated lists inside string fields where multiple items exist."""
    return system, user_msg


def tailor_resume_prompt(
    profile: dict[str, Any], user: dict[str, Any], job: dict[str, Any]
) -> tuple[str, str]:
    system = """You tailor resumes for Indian professionals. Rules:
- NEVER invent employers, titles, dates, metrics, promotions, skills, or education.
- Factual content must come ONLY from linkedin_profile_text and resume_cv_text in the candidate JSON.
  ai_synthesis may help ordering/titles but must not add new facts.
- ONLY rephrase, reorder, compress, and highlight facts present in those two texts.
- ATS-friendly: clear headings, strong verbs, quantified ONLY if already in source text.
- Indian context: do not put CTC on the resume unless it already appears in the source text.
- Prefer concise one-page style; sharp two-page max if content is rich.
- Output STRICT JSON only."""
    user_msg = f"""Candidate JSON:\n{candidate_inputs_json(user, profile)}\n\nJob record JSON:\n{json.dumps(job, ensure_ascii=False, indent=2)}\n\nReturn JSON keys:
{{
  "resume_headline": string,
  "professional_summary": string,
  "tailored_skills": string,
  "tailored_experience": string,
  "final_resume_text": string
}}
final_resume_text should be a cohesive plain-text resume the candidate could paste into a doc."""
    return system, user_msg


def outreach_prompt(
    profile: dict[str, Any],
    user: dict[str, Any],
    job: dict[str, Any],
    recipient_name: str,
    recipient_role: str,
    channel: str,
    message_type: str,
) -> tuple[str, str]:
    system = """You write short, warm, professional outreach for Indian job seekers.
Rules:
- Never invent achievements; cite 1-2 proof points ONLY from linkedin_profile_text / resume_cv_text (or contact name/title if present).
- Tone: confident, crisp, not desperate. Polite CTA.
- LinkedIn DM: max 900 characters for "message" field.
- WhatsApp: short, natural, mobile-friendly.
- Email: include subject line and body separated clearly in JSON.
- Output STRICT JSON only."""
    user_msg = f"""Candidate JSON:\n{candidate_inputs_json(user, profile)}\n\nJob JSON:\n{json.dumps(job, ensure_ascii=False, indent=2)}\n\nRecipient name: {recipient_name}\nRecipient role/title: {recipient_role}\nChannel: {channel}\nMessage type: {message_type}\n\nReturn JSON:
{{
  "message_text": string,
  "linkedin_char_count": number or null,
  "notes": string
}}
For Email, message_text must start with a line "Subject: ..." then blank line then body.
For LinkedIn, ensure message_text length <= 900 characters."""
    return system, user_msg


def interview_prep_prompt(
    profile: dict[str, Any], user: dict[str, Any], job: dict[str, Any]
) -> tuple[str, str]:
    system = """You create interview prep for Indian tech/business roles.
Rules:
- Candidate facts: ONLY from linkedin_profile_text and resume_cv_text in the JSON (ai_synthesis is secondary).
- Company facts: ONLY from JD + those candidate sources. If you need external data, explicitly say so in company_research.
- Do not invent interview process details.
- Behavioral stories must map to STAR using ONLY facts in the texts; if thin, say what user should verify.
- Include India-relevant CTC discussion framing using stated current_ctc_lpa when present — no fabricated numbers.
- Output STRICT JSON only with the keys specified."""
    user_msg = f"""Candidate JSON:\n{candidate_inputs_json(user, profile)}\n\nJob JSON:\n{json.dumps(job, ensure_ascii=False, indent=2)}\n\nReturn JSON keys:
{{
  "company_research": string,
  "role_prep": string,
  "likely_questions": string,
  "star_stories": string,
  "case_questions": string,
  "salary_pitch": string
}}

Populate likely_questions with structured sections inside the string, using headings like:
THEMES:, TECHNICAL (15):, BEHAVIORAL (5):, QUESTIONS_TO_ASK: each as bullet lists.

role_prep should include: role expectations, likely interview themes, "why this role" answer, "tell me about yourself" answer — all grounded in candidate sources + JD.

case_questions: If role_category suggests strategy/growth/business/product/founder's office/operations/analytics,
include 5 concise case prompts; else write "Not prioritized for this role category — focus on execution/technical depth instead." with 1-2 light cases max.

star_stories: suggest STAR outlines from candidate sources only.

salary_pitch: CTC discussion script + questions for interviewer + negotiation angles (honest, non-greedy)."""
    return system, user_msg


def compensation_prompt(inputs: dict[str, Any]) -> tuple[str, str]:
    system = """You are an India compensation advisor for salaried professionals.
Explain fixed vs variable vs ESOP vs joining/retention bonuses clearly.
Never invent user numbers; use only provided inputs.
Be practical about liquidity of ESOPs and tax (rough).
Output STRICT JSON only."""
    user_msg = f"""Numeric inputs (all in INR Lakhs per annum except percentages and costs):\n{json.dumps(inputs, ensure_ascii=False, indent=2)}\n\nReturn JSON:
{{
  "negotiation_recommendation": string,
  "talking_points": string,
  "risk_notes": string
}}
talking_points: bullet text suitable for email/WhatsApp notes to self."""
    return system, user_msg


def parse_job_preferences_prompt(preferences_nl: str) -> tuple[str, str]:
    system = """You parse a job seeker's natural-language preferences about the Indian market into structured JSON.
Infer only what is reasonably implied; use null or empty string when unknown.
Output STRICT JSON only."""
    user_msg = f"""The user answered these free-text preference questions (location, CTC, remote, startup vs big tech, industries, etc.):

---
{preferences_nl}
---

Return JSON with keys:
{{
  "locations": string,
  "primary_role_keywords": string,
  "min_ctc_lpa": number | null,
  "remote_preference": "remote_first" | "hybrid_ok" | "office_ok" | "no_pref",
  "company_type_preference": "startup" | "bigtech" | "both" | "services_ok" | "no_pref",
  "industries_interest": string,
  "industries_avoid": string,
  "other_constraints": string
}}
locations: comma-separated Indian cities or "Pan-India" / "Remote India" if stated."""
    return system, user_msg


def rank_job_leads_prompt(
    user: dict[str, Any],
    profile: dict[str, Any],
    prefs_struct: dict[str, Any],
    leads: list[dict[str, Any]],
) -> tuple[str, str]:
    system = """You rank job postings for an Indian professional.
Use the candidate JSON (LinkedIn + CV + CTC + synthesis) and the structured preferences JSON.
Each lead may only contain a snippet — score conservatively if information is thin.
Never invent facts about the employer beyond the snippet.
Output STRICT JSON only."""
    slim = []
    for i, L in enumerate(leads[:18]):
        slim.append(
            {
                "index": i,
                "title": L.get("title"),
                "company_name": L.get("company_name"),
                "location": L.get("location"),
                "platform": L.get("platform"),
                "snippet": (L.get("snippet") or "")[:1200],
                "job_url": L.get("job_url"),
            }
        )
    user_msg = f"""Candidate JSON:\n{candidate_inputs_json(user, profile)}\n\nPreferences JSON:\n{json.dumps(prefs_struct, ensure_ascii=False, indent=2)}\n\nJob leads (parallel array, use index):\n{json.dumps(slim, ensure_ascii=False, indent=2)}\n\nReturn JSON:
{{
  "evaluations": [
    {{
      "index": number,
      "ai_fit_score": number,
      "ai_rationale": string,
      "apply_recommendation": "Strong apply" | "Maybe" | "Skip"
    }}
  ]
}}
Provide one evaluation object per lead index (0..n-1). ai_fit_score is 0-100."""
    return system, user_msg


def cover_letter_prompt(
    user: dict[str, Any], profile: dict[str, Any], job: dict[str, Any]
) -> tuple[str, str]:
    system = """You write a concise cover email / letter for an Indian job application.
Rules:
- Facts only from candidate JSON; no invented metrics or employers.
- One page max in plain text; warm, specific to the JD snippet.
- Mention notice period / joining timeline only if inferable from candidate JSON.
- Output STRICT JSON only."""
    user_msg = f"""Candidate JSON:\n{candidate_inputs_json(user, profile)}\n\nJob JSON:\n{json.dumps(job, ensure_ascii=False, indent=2)}\n\nReturn JSON:
{{
  "cover_letter_text": string,
  "application_checklist_markdown": string
}}
application_checklist_markdown: short markdown checklist (tailor resume, fill form, attach docs, follow-up date)."""
    return system, user_msg


def cold_company_outreach_prompt(
    *,
    user: dict[str, Any],
    profile: dict[str, Any],
    preferences_nl: str,
    company_name: str,
    company_url: str,
) -> tuple[str, str]:
    system = """You draft cold outreach for Indian professionals targeting a specific company.
You do NOT have live web browsing — infer cautiously from company name/URL pattern and user context only.
Clearly separate "Assumptions / needs verification" from factual user content.
No fabricated metrics. Output STRICT JSON only."""
    user_msg = f"""Candidate JSON:\n{candidate_inputs_json(user, profile)}\n\nUser job-search preferences (natural language):\n{preferences_nl}\n\nTarget company name: {company_name}\nCompany URL (may be careers page or homepage): {company_url}\n\nReturn JSON:
{{
  "research_summary": string,
  "assumptions_to_verify": string,
  "email_subject": string,
  "email_body": string
}}
email_body: professional, concise, India-appropriate; include polite CTA; under 350 words."""
    return system, user_msg
