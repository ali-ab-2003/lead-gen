# Lead Generator

Automatically finds local businesses **without a website** in chosen categories
and areas, scrapes their contact details, makes a best-effort attempt at the
owner/decision-maker contact, scores each lead with AI, and delivers the results
to a **Google Sheet**, a **CSV**, and a **Streamlit dashboard** — on a daily
schedule.

> **Honest caveat:** businesses with no website rarely expose a public email.
> Phone + business data is reliable; **email and owner name are best-effort** and
> will not be 100% covered. We never fabricate contact data.

> **Legal/ToS:** scraping Google Maps is contrary to Google's Terms of Service.
> This is a common B2B lead-gen practice but is your responsibility. Keep volumes
> modest and respect rate limits.

## Pipeline

```
config.yaml → scrape (Apify) → filter (no website) → enrich (email/owner)
            → ai_enrich (Groq score + outreach) → store (Supabase, dedupe)
            → export (Google Sheet + CSV)
```

Everything runs on free tiers: **Apify** (scraping), **Groq** (AI),
**Supabase** (storage), **Google Sheets** (output), **Streamlit** (dashboard).
The daily run is scheduled locally (Windows Task Scheduler); an optional
containerized path (Docker + Jenkins) is included for always-on hosting.

## Setup

1. **Python deps**
   ```bash
   python -m venv .venv && . .venv/Scripts/activate   # Windows
   pip install -r requirements.txt
   ```
2. **Secrets** — copy `.env.example` to `.env` and fill in:
   - `APIFY_TOKEN` — https://console.apify.com
   - `SUPABASE_URL` / `SUPABASE_KEY` — your Supabase project (service_role key)
   - `GROQ_API_KEY` — https://console.groq.com/keys (free)
   - `GOOGLE_SERVICE_ACCOUNT_JSON` — path to a Google service-account key with
     the Sheets API enabled; share your target sheet with the SA's email
   - `GOOGLE_SHEET_ID` — id from the sheet URL
3. **Database** — run [`db/schema.sql`](db/schema.sql) in the Supabase SQL editor.
4. **What to search** — edit [`config.yaml`](config.yaml): `categories` + `areas`.

## Running

```bash
python main.py --dry-run     # scrape + filter only → output/leads-YYYY-MM-DD-dryrun.csv
python main.py               # full run (enrich + AI + store + export)
python main.py --no-ai       # skip Groq stage (fully free, faster)
python main.py --no-enrich   # skip contact enrichment
```

## Dashboard

```bash
streamlit run dashboard/app.py
```
Filter by area/category/status/score, view AI outreach drafts, export CSV.
Deploy free on Streamlit Community Cloud with the same Supabase secrets.

## Daily schedule

The default scheduler is **Windows Task Scheduler**, which runs
[`run_daily.bat`](run_daily.bat) once a day. Register it (PowerShell):

```powershell
$action  = New-ScheduledTaskAction  -Execute "C:\path\to\lead-gen\run_daily.bat"
$trigger = New-ScheduledTaskTrigger -Daily -At 8:00pm
Register-ScheduledTask -TaskName "LeadGenDaily" -Action $action -Trigger $trigger `
  -Settings (New-ScheduledTaskSettingsSet -StartWhenAvailable) -Force
```

See [DEPLOY.md](DEPLOY.md) for managing/changing the schedule. The job only fires
while the PC is on.

**Optional — Docker + Jenkins:** [`Dockerfile`](Dockerfile) and
[`Jenkinsfile`](Jenkinsfile) provide a containerized pipeline you can run on an
always-on host (cron `H 7 * * *`, credentials via the Jenkins credentials store).
Use this if you'd rather not depend on a local machine being awake.

## Project layout

| Path | Purpose |
|---|---|
| `config.yaml` | What to search for and where |
| `src/scrape.py` | Apify Google Maps scraper |
| `src/scrape_playwright.py` | Optional zero-cost fallback scraper |
| `src/filter.py` | Keep only no-website, contactable leads |
| `src/enrich.py` | Best-effort email/owner lookup |
| `src/ai_enrich.py` | Groq scoring + owner inference + outreach draft |
| `src/store.py` | Supabase upsert + cross-day dedupe |
| `src/export.py` | Append new leads to Google Sheet |
| `main.py` | Pipeline orchestrator |
| `dashboard/app.py` | Streamlit dashboard |
| `run_daily.bat` | Daily run launcher (Windows Task Scheduler) |
| `Dockerfile` / `Jenkinsfile` | Optional containerized daily run |
| `db/schema.sql` | `leads` table |
