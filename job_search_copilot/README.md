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

5. **Run the app**

   From the `job_search_copilot` folder:

   ```bash
   streamlit run app.py
   ```

   Or from the repository root:

   ```bash
   streamlit run job_search_copilot/app.py
   ```

## First run

- The SQLite database file is created automatically at `data/app.db` on first launch.
- If **no users** exist, create a profile under **User Profile**. Use the sidebar selector to switch between friends sharing the same instance.

## How to use (short)

1. **User Profile** — Save identity, CTC fields, notice period, and long-form career content (experience, projects, etc.).
2. **Add / Analyze Job** — Paste a JD and run **Analyze Job Fit** to extract skills, fit score, and recommendations.
3. **Resume Tailor** — Pick a job, generate a tailored resume (no invented facts), then **Export DOCX**.
4. **Outreach Generator** — Short India-context messages; LinkedIn drafts are kept under 900 characters when the model obeys the prompt (verify before sending).
5. **Interview Prep** — Structured pack grounded in JD + profile; company deep-dive may note when external research is needed.
6. **Application Tracker** — Filter and edit status, priority, follow-up date, and notes; save changes with the button.
7. **Compensation Comparator** — Deterministic LPA math plus optional AI negotiation brief.

## Database reset

Stop the app, then delete the SQLite file:

```bash
rm job_search_copilot/data/app.db
```

On next run, tables are recreated empty.

## Limitations (MVP)

- **Single machine / SQLite** — not suitable for concurrent multi-user production hosting.
- **No authentication** — anyone with access to the machine can open the app; the sidebar profile switcher is for convenience, not security.
- **OpenAI dependency** — analysis quality and JSON shape depend on the model; invalid JSON is retried client-side but can still fail on unusual outputs.
- **Resume export** is intentionally plain/ATS-friendly, not designer-styled.
- **Compensation math** uses simple heuristics (e.g. risk-adjusted weighting); not tax or legal advice.

## Future improvements

- Optional cloud DB and real auth.
- Attachments (PDF JD upload) and parsing.
- Calendar sync for follow-ups.
- Email send integration (manual copy-paste for v1 is intentional).

## License

Use for personal/friends projects at your own discretion.
