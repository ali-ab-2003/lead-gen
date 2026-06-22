"""Filter scraped places down to actionable no-website leads."""
from __future__ import annotations

import logging

from .config import Settings
from .models import Lead

log = logging.getLogger(__name__)


def _has_website(lead: Lead) -> bool:
    site = (lead.website or "").strip().lower()
    if not site:
        return False
    # Treat obvious non-sites as "no website".
    junk = ("facebook.com", "instagram.com", "google.com", "business.site",
            "linktr.ee", "wa.me", "t.me")
    return not any(j in site for j in junk)


def _has_contact(lead: Lead) -> bool:
    return bool((lead.phone or "").strip() or (lead.email or "").strip())


def filter_leads(leads: list[Lead], settings: Settings) -> list[Lead]:
    """Keep only leads matching the configured filters, de-duped by place_id."""
    seen: set[str] = set()
    kept: list[Lead] = []
    dropped_site = dropped_contact = dropped_dupe = 0

    for lead in leads:
        if lead.place_id in seen:
            dropped_dupe += 1
            continue

        if settings.require_no_website and _has_website(lead):
            dropped_site += 1
            continue

        if settings.require_some_contact and not _has_contact(lead):
            dropped_contact += 1
            continue

        seen.add(lead.place_id)
        kept.append(lead)

    log.info(
        "Filtered: kept %d (dropped %d has-website, %d no-contact, %d dupes)",
        len(kept), dropped_site, dropped_contact, dropped_dupe,
    )
    return kept
