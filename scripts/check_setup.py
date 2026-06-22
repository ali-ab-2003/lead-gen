"""Validate all credentials/services connect before a real run.

Run: python scripts/check_setup.py
Does NOT scrape (no Apify credits used) — only checks auth/reachability.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import env  # noqa: E402

OK, FAIL = "[ OK ]", "[FAIL]"
results: list[tuple[str, bool, str]] = []


def record(name: str, ok: bool, detail: str = "") -> None:
    results.append((name, ok, detail))
    print(f"{OK if ok else FAIL} {name}" + (f" — {detail}" if detail else ""))


# 1. Apify: validate token by fetching the current user (no actor run).
def check_apify() -> None:
    try:
        from apify_client import ApifyClient
        token = env("APIFY_TOKEN")
        if not token:
            return record("Apify token", False, "APIFY_TOKEN not set")
        user = ApifyClient(token).user("me").get()
        username = user.get("username", "?") if isinstance(user, dict) else getattr(user, "username", "ok")
        record("Apify token", True, f"user: {username}")
    except Exception as e:  # noqa: BLE001
        record("Apify token", False, str(e)[:120])


# 2. Supabase: select against the leads table.
def check_supabase() -> None:
    try:
        from supabase import create_client
        url, key = env("SUPABASE_URL"), env("SUPABASE_KEY")
        if not url or not key:
            return record("Supabase", False, "SUPABASE_URL/KEY not set")
        client = create_client(url, key)
        res = client.table("leads").select("place_id").limit(1).execute()
        record("Supabase + leads table", True, f"reachable ({len(res.data)} sample rows)")
    except Exception as e:  # noqa: BLE001
        record("Supabase + leads table", False, str(e)[:160])


# 3. Groq: tiny completion.
def check_groq() -> None:
    try:
        key = env("GROQ_API_KEY")
        if not key:
            return record("Groq", False, "GROQ_API_KEY not set (AI stage will be skipped)")
        from groq import Groq
        model = env("GROQ_MODEL", "llama-3.3-70b-versatile")
        r = Groq(api_key=key).chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "reply with the single word: ok"}],
            max_tokens=5,
        )
        record("Groq", True, f"model {model} -> {r.choices[0].message.content.strip()!r}")
    except Exception as e:  # noqa: BLE001
        record("Groq", False, str(e)[:160])


# 4. Google Sheets: open the sheet + read header.
def check_sheets() -> None:
    try:
        sa, sheet_id = env("GOOGLE_SERVICE_ACCOUNT_JSON"), env("GOOGLE_SHEET_ID")
        if not sa or not sheet_id:
            return record("Google Sheets", False, "GOOGLE_SERVICE_ACCOUNT_JSON/SHEET_ID not set")
        if not Path(sa).exists():
            return record("Google Sheets", False, f"key file not found: {sa}")
        import gspread
        from google.oauth2.service_account import Credentials
        creds = Credentials.from_service_account_file(
            sa, scopes=["https://www.googleapis.com/auth/spreadsheets"]
        )
        sh = gspread.authorize(creds).open_by_key(sheet_id)
        record("Google Sheets access", True, f"opened '{sh.title}'")
    except Exception as e:  # noqa: BLE001
        record("Google Sheets access", False, f"{type(e).__name__}: {str(e)[:200]}")


if __name__ == "__main__":
    print("Checking setup (no Apify credits used)...\n")
    check_apify()
    check_supabase()
    check_groq()
    check_sheets()
    failed = [n for n, ok, _ in results if not ok]
    print("\n" + ("All checks passed!" if not failed else f"{len(failed)} check(s) failed: {failed}"))
    sys.exit(1 if failed else 0)
