# Indian Job Search Copilot (MVP)

A small **Streamlit** app for Indian professionals to paste JDs, score fit, tailor resumes honestly, draft outreach, prep for interviews, track applications, and sanity-check compensation offers. Data stays **local in SQLite**.

## Philosophy

This is **not** a mass auto-apply bot. It is a **high-quality copilot**: honest tailoring, thoughtful outreach, pipeline tracking, and negotiation support.

## Setup

1. **Python 3.10+** recommended.

2. Create a virtual environment (optional but recommended):

   ```bash
   cd job_search_copilot
   python -m venv .venv
   source .venv/bin/activate   # Windows: .venv\Scripts\activate
   ```

3. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

4. **Environment variables**

   ```bash
   cp .env.example .env
   ```

   Edit `.env` and set `OPENAI_API_KEY`. Optional: `OPENAI_MODEL` (defaults to `gpt-4o-mini`).

   You can also export the key in your shell instead of using a file: `export OPENAI_API_KEY=...`

   **Cursor:** if you use Cursor global secrets / environment injection, the same variable name `OPENAI_API_KEY` is read by the app (via `python-dotenv` and the process environment).

5. **Run the app**

   From the `job_search_copilot` folder:

   ```bash
   python3 -m streamlit run app.py
   ```

   Or from the repository root:

   ```bash
   python3 -m streamlit run job_search_copilot/app.py
   ```

## First run

- The SQLite database file is created automatically at `data/app.db` on first launch.
- If **no users** exist, create a profile under **User Profile**. Use the sidebar selector to switch between friends sharing the same instance.

## How to use (short)

1. **User Profile** — Paste **LinkedIn profile text** and **resume/CV** (or upload PDF/txt). Enter **current total CTC (LPA)** only. Optionally add name/email for PDF headers. Use **Update career brief (AI)** for suggested roles and CTC bands in India.
2. **Job Discovery** — Save & parse **preferences**, open **Playbook** for AI-built LinkedIn links + Google queries, **Import** pasted URLs or messy text into **staging**, optionally attach **JD blocks** (delimiter `---`), **AI rank**, then **import** into your tracker. No SerpApi required.
3. **Add / Analyze Job** — Manually paste a JD and run **Analyze Job Fit** (use this for Naukri/LinkedIn tabs when not using SerpApi discovery).
4. **Apply pack** — Generate a **cover letter + checklist**, open the posting link, tailor your resume on **Resume Tailor**, then **Mark as Applied** when done.
5. **Resume Tailor** — Pick a job, generate a tailored resume (no invented facts), then **Export DOCX**.
6. **Outreach Generator** — Short India-context messages; verify length on LinkedIn before sending.
7. **Interview Prep** — After a recruiter call, generate a prep pack; use **Application Tracker** for status and follow-ups.
8. **Application Tracker** — Filter and edit status, priority, follow-up date, and notes.
9. **Compensation Comparator** — LPA math plus optional AI negotiation brief.
10. **Cold prospecting** — Target a company with a URL + your preference notes; get a cautious research summary and cold email draft (you send from your inbox).

## Database reset

Stop the app, then delete the SQLite file:

```bash
rm job_search_copilot/data/app.db
```

On next run, tables are recreated empty.

## Limitations (MVP)

- **No auto-apply** — LinkedIn, Naukri, Instahyre, and similar sites require you to sign in and submit applications yourself. This app prepares materials and tracks state only.
- **Discovery source** — You paste job URLs / text from portals you searched manually. Optional **SERPAPI_API_KEY** still enables a separate Google Jobs fetch in code, but the UI is built around the human-in-the-loop flow.
- **Cold outreach** — Company “research” is LLM text from your profile + company name/URL only; there is **no live web crawl**. Verify facts before sending mail.
- **Single machine / SQLite** — not suitable for concurrent multi-user production hosting.
- **No authentication** — sidebar profiles are for convenience, not security.
- **OpenAI dependency** — JSON-shaped responses can occasionally fail parsing; retry or simplify inputs.
- **Resume export** is plain/ATS-oriented, not designer-styled.
- **Compensation math** is heuristic, not tax or legal advice.

## Future improvements

- Optional cloud DB and real auth.
- Attachments (PDF JD upload) and parsing.
- Calendar sync for follow-ups.
- Email send integration (manual copy-paste for v1 is intentional).

## License

Use for personal/friends projects at your own discretion.
