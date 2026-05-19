"""Centralized LLM prompts — India-specific hiring context, honesty rules."""

from __future__ import annotations

import json
from typing import Any


def _profile_blob(profile: dict[str, Any], user: dict[str, Any]) -> str:
    payload = {
        "user": {
            k: user.get(k)
            for k in (
                "name",
                "email",
                "phone",
                "current_location",
                "current_title",
                "current_company",
                "current_ctc_lpa",
                "fixed_ctc_lpa",
                "variable_ctc_lpa",
                "esops_value_lpa",
                "expected_ctc_lpa",
                "notice_period_days",
                "preferred_locations",
                "target_roles",
                "target_industries",
            )
        },
        "profile": profile,
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def analyze_job_prompt(profile: dict[str, Any], user: dict[str, Any], jd: str) -> tuple[str, str]:
    system = """You are an expert India-focused career coach and recruiter analyst.
You understand Indian hiring: CTC in LPA, fixed vs variable pay, ESOPs, notice periods,
Indian portals (Naukri, Instahyre, LinkedIn India), referrals, recruiter spam vs real roles,
fintech, product, growth, strategy, analytics, operations, founder's office, AI/ML roles,
startups vs MNCs, BigTech, IT services, GCCs, and hybrid/remote norms in Indian cities.

Rules:
- Never invent candidate facts. Use ONLY the provided profile JSON.
- If JD is vague, infer cautiously and say so in fit_summary.
- Output STRICT JSON only (no markdown fences) matching the schema the user requests.
- fit_score is 0-100 integer based on skills + role alignment + seniority + domain transferability.
- Be candid about gaps; Indian hiring is credential and keyword sensitive for ATS.
- apply_recommendation: "Apply", "Maybe", or "Skip" with honest reasoning.
- priority: High, Medium, or Low for THIS candidate (not generic job quality).
- follow_up_suggestion: concrete India-context next step (referral path, recruiter, timeline)."""
    user_msg = f"""Candidate profile JSON:\n{_profile_blob(profile, user)}\n\nJob description (may include Hindi/English mix):\n{jd}\n\nReturn JSON with keys exactly:
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
- ONLY rephrase, reorder, compress, and highlight facts present in the profile JSON.
- ATS-friendly: clear headings, strong verbs, quantified ONLY if already in source text.
- Indian context: CTC/notice period not on resume unless user already included them.
- Prefer concise one-page style; sharp two-page max if content is rich.
- Output STRICT JSON only."""
    user_msg = f"""Profile JSON:\n{_profile_blob(profile, user)}\n\nJob record JSON:\n{json.dumps(job, ensure_ascii=False, indent=2)}\n\nReturn JSON keys:
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
- Never invent achievements; cite 1-2 proof points ONLY from profile JSON.
- Tone: confident, crisp, not desperate. Polite CTA.
- LinkedIn DM: max 900 characters for "message" field.
- WhatsApp: short, natural, mobile-friendly.
- Email: include subject line and body separated clearly in JSON.
- Output STRICT JSON only."""
    user_msg = f"""Profile JSON:\n{_profile_blob(profile, user)}\n\nJob JSON:\n{json.dumps(job, ensure_ascii=False, indent=2)}\n\nRecipient name: {recipient_name}\nRecipient role/title: {recipient_role}\nChannel: {channel}\nMessage type: {message_type}\n\nReturn JSON:
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
- Company facts: ONLY from JD + profile. If you need external data, explicitly say so in company_research.
- Do not invent interview process details.
- Behavioral stories must map to STAR using ONLY facts in profile; if thin, say what user should verify.
- Include India-relevant CTC discussion framing but no fabricated numbers beyond profile.
- Output STRICT JSON only with the keys specified."""
    user_msg = f"""Profile JSON:\n{_profile_blob(profile, user)}\n\nJob JSON:\n{json.dumps(job, ensure_ascii=False, indent=2)}\n\nReturn JSON keys:
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

role_prep should include: role expectations, likely interview themes, "why this role" answer, "tell me about yourself" answer — all grounded in profile+JD.

case_questions: If role_category suggests strategy/growth/business/product/founder's office/operations/analytics,
include 5 concise case prompts; else write "Not prioritized for this role category — focus on execution/technical depth instead." with 1-2 light cases max.

star_stories: suggest STAR outlines from profile only.

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
