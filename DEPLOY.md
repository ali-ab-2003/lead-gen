# Deployment

Two things run on a schedule / always-on:

1. **Daily pipeline** → Windows Task Scheduler (local)
2. **Dashboard** → Streamlit Community Cloud (free, always-on URL)

---

## 1. Daily pipeline (Windows Task Scheduler)

Already set up by [run_daily.bat](run_daily.bat) + a scheduled task named **`LeadGenDaily`**
that runs daily at **08:00** local time.

**Useful commands** (PowerShell):
```powershell
# Run it right now (manual test)
Start-ScheduledTask -TaskName "LeadGenDaily"

# See status / last result
Get-ScheduledTaskInfo -TaskName "LeadGenDaily"

# Change the time to e.g. 06:30
Set-ScheduledTask -TaskName "LeadGenDaily" `
  -Trigger (New-ScheduledTaskTrigger -Daily -At 6:30am)

# Disable / re-enable / remove
Disable-ScheduledTask -TaskName "LeadGenDaily"
Enable-ScheduledTask  -TaskName "LeadGenDaily"
Unregister-ScheduledTask -TaskName "LeadGenDaily" -Confirm:$false
```
Logs from each run are appended to `output\run.log`.

> The job only runs while the PC is on. `-StartWhenAvailable` means a missed run
> (PC off at 08:00) fires at the next opportunity.

---

## 2. Dashboard (Streamlit Community Cloud)

The repo is already on GitHub (`ali-ab-2003/lead-gen`). To publish the dashboard:

1. Go to **https://share.streamlit.io** and sign in with GitHub.
2. **Create app** → **Deploy a public app from GitHub** (or pick the repo).
   - Repository: `ali-ab-2003/lead-gen`
   - Branch: `main`
   - **Main file path:** `dashboard/app.py`
3. Click **Advanced settings → Secrets** and paste (with your real values):
   ```toml
   SUPABASE_URL = "https://xxxx.supabase.co"
   SUPABASE_KEY = "your-supabase-key"
   ```
   (Template: [.streamlit/secrets.toml.example](.streamlit/secrets.toml.example).
   The dashboard only needs Supabase — no Apify/Groq/Google keys.)
4. **Deploy.** You'll get a permanent URL like `https://lead-gen-xxxx.streamlit.app`
   that reads your leads live from Supabase — open it from any browser or phone.

Whenever you push changes to `main`, Streamlit Cloud auto-redeploys.

### Run the dashboard locally instead (optional)
```bash
streamlit run dashboard/app.py
```
Uses `SUPABASE_URL` / `SUPABASE_KEY` from your `.env`.
