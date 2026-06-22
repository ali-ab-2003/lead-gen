"""Best-effort contact enrichment for no-website leads.

These businesses have no site, so public emails are scarce. We make a light,
polite attempt: fetch the business's DuckDuckGo HTML result page and look for
an email address or a Facebook page (FB pages often expose a contact email).
We never fabricate data — if nothing is found, fields stay blank.

This is intentionally low-tech and dependency-light. If you want higher
coverage later, swap in a dedicated enrichment API here.
"""
from __future__ import annotations

import logging
import re
import time

import requests

from .models import Lead

log = logging.getLogger(__name__)

_EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")
_FB_RE = re.compile(r"https?://(?:www\.)?facebook\.com/[^\s\"'<>]+", re.I)

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )
}
_TIMEOUT = 12
_SLEEP_BETWEEN = 1.0  # be polite

# Emails that are almost certainly not the business's own contact.
# Domains/strings that are never a real business contact — usually scraped from
# the search engine's own page markup, CDNs, analytics, or image filenames.
_JUNK_EMAIL = (
    "duckduckgo.com", "google.com", "gstatic.com", "googleapis.com",
    "schema.org", "w3.org", "sentry.io", "wixpress.com", "example.com",
    "cloudflare", "jsdelivr", "fontawesome", "@2x", ".png", ".jpg", ".gif",
    ".svg", ".webp", "youremail", "email@", "name@", "user@", "domain.com",
)


def _search_html(query: str) -> str:
    try:
        resp = requests.get(
            "https://html.duckduckgo.com/html/",
            params={"q": query},
            headers=_HEADERS,
            timeout=_TIMEOUT,
        )
        resp.raise_for_status()
        return resp.text
    except requests.RequestException as exc:
        log.debug("Search failed for %r: %s", query, exc)
        return ""


def _first_clean_email(text: str) -> str:
    for match in _EMAIL_RE.findall(text):
        low = match.lower()
        if not any(j in low for j in _JUNK_EMAIL):
            return match
    return ""


def _enrich_one(lead: Lead) -> Lead:
    if lead.email and lead.owner_name:
        return lead

    query = f'"{lead.name}" {lead.area} email contact'
    html = _search_html(query)
    if not html:
        return lead

    if not lead.email:
        email = _first_clean_email(html)
        if email:
            lead.email = email
            lead.source_of_contact = lead.source_of_contact or "web_search"

    # Note presence of a Facebook page; the AI stage can mine it for an owner.
    if "facebook.com" not in (lead.source_of_contact or ""):
        fb = _FB_RE.search(html)
        if fb and not lead.source_of_contact:
            lead.source_of_contact = "facebook"

    return lead


def enrich_leads(leads: list[Lead]) -> list[Lead]:
    log.info("Enriching %d leads (best-effort)...", len(leads))
    found = 0
    for lead in leads:
        had_email = bool(lead.email)
        _enrich_one(lead)
        if lead.email and not had_email:
            found += 1
        time.sleep(_SLEEP_BETWEEN)
    log.info("Enrichment found %d new emails.", found)
    return leads
