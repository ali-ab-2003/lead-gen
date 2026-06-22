"""Persist leads to Supabase Postgres with dedupe across daily runs.

Dedupe key is `place_id`. Existing rows get `last_seen` bumped (and any newly
discovered email/owner/AI fields filled in) but are NOT reported as new.
Genuinely new leads are returned so the caller can export just those.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from supabase import create_client, Client

from .config import env
from .models import Lead

log = logging.getLogger(__name__)

# Fields we allow an existing row to have *backfilled* if it was previously blank.
_BACKFILL_FIELDS = (
    "email", "owner_name", "source_of_contact",
    "lead_score", "score_reason", "outreach_draft",
)


def _client() -> Client:
    url, key = env("SUPABASE_URL"), env("SUPABASE_KEY")
    if not url or not key:
        raise RuntimeError("SUPABASE_URL / SUPABASE_KEY not set (see .env.example).")
    return create_client(url, key)


def upsert_leads(leads: list[Lead]) -> list[Lead]:
    """Insert new leads, refresh existing ones. Returns only the new leads."""
    if not leads:
        return []

    client = _client()
    place_ids = [l.place_id for l in leads]

    # Which place_ids already exist?
    existing_rows = (
        client.table("leads")
        .select("place_id")
        .in_("place_id", place_ids)
        .execute()
        .data
    )
    existing_ids = {row["place_id"] for row in existing_rows}

    now = datetime.now(timezone.utc).isoformat()
    new_leads = [l for l in leads if l.place_id not in existing_ids]

    # Insert new leads.
    if new_leads:
        client.table("leads").upsert(
            [l.to_dict() for l in new_leads], on_conflict="place_id"
        ).execute()

    # Refresh existing leads: bump last_seen + backfill blanks.
    for lead in leads:
        if lead.place_id in existing_ids:
            patch = {"last_seen": now}
            for f in _BACKFILL_FIELDS:
                val = getattr(lead, f)
                if val not in (None, ""):
                    patch[f] = val
            client.table("leads").update(patch).eq("place_id", lead.place_id).execute()

    log.info("Stored %d leads (%d new, %d existing refreshed).",
             len(leads), len(new_leads), len(existing_ids))
    return new_leads
