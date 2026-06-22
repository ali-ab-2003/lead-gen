"""Scrape Google Maps business listings via the Apify Google Maps Scraper actor.

We use Apify because it handles proxies + Google's anti-bot, returns rich
structured data (including emails when discoverable), and stays effectively
free at low daily volume on the free plan. A fragile DIY fallback lives in
`scrape_playwright.py`.
"""
from __future__ import annotations

import logging

from apify_client import ApifyClient

from .config import Settings, env
from .models import Lead

log = logging.getLogger(__name__)


def _to_float(val) -> float | None:
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


def _to_int(val) -> int | None:
    try:
        return int(val)
    except (TypeError, ValueError):
        return None


def _item_to_lead(item: dict, category: str, area: str) -> Lead | None:
    """Map one Apify result item to a Lead. Returns None if no usable id."""
    place_id = (
        item.get("placeId")
        or item.get("placeID")
        or item.get("cid")
        or item.get("fid")
        or item.get("url")  # last resort; URL is stable per place
    )
    if not place_id:
        return None

    # Apify sometimes returns a list of emails; take the first.
    emails = item.get("emails") or []
    email = emails[0] if isinstance(emails, list) and emails else (item.get("email") or "")

    return Lead(
        place_id=str(place_id),
        name=item.get("title") or item.get("name") or "",
        category=category,
        address=item.get("address") or item.get("street") or "",
        area=area,
        phone=item.get("phone") or item.get("phoneUnformatted") or "",
        website=item.get("website") or item.get("webSite") or "",
        google_maps_url=item.get("url") or "",
        rating=_to_float(item.get("totalScore") or item.get("rating")),
        reviews_count=_to_int(item.get("reviewsCount") or item.get("reviews")),
        email=email,
        source_of_contact="apify" if email else "",
    )


def scrape(settings: Settings) -> list[Lead]:
    """Run the Apify actor for every query in settings and return Leads."""
    token = env("APIFY_TOKEN")
    if not token:
        raise RuntimeError(
            "APIFY_TOKEN is not set. Add it to your .env (see .env.example) "
            "or run with the Playwright fallback scraper."
        )
    actor_id = env("APIFY_GMAPS_ACTOR", "nwua9Gu5YrADL7ZDj")
    client = ApifyClient(token)

    search_strings = [q[0] for q in settings.queries]
    log.info("Scraping %d queries via Apify actor %s", len(search_strings), actor_id)

    # One actor run covers all search strings; cheaper than one run per query.
    run_input = {
        "searchStringsArray": search_strings,
        "maxCrawledPlacesPerSearch": settings.max_results_per_query,
        "language": settings.language,
        "scrapeContacts": True,   # ask the actor to dig for emails/socials
        "skipClosedPlaces": True,
    }

    run = client.actor(actor_id).call(run_input=run_input)
    # apify-client 3.x returns a typed Run object; older versions a dict.
    dataset_id = (
        run.get("defaultDatasetId") if isinstance(run, dict)
        else run.default_dataset_id
    )

    # Map results back to their (category, area) using the search string.
    by_search: dict[str, tuple[str, str]] = {
        q[0]: (q[1], q[2]) for q in settings.queries
    }

    leads: list[Lead] = []
    for item in client.dataset(dataset_id).iterate_items():
        search = item.get("searchString") or item.get("searchQuery") or ""
        category, area = by_search.get(search, ("", ""))
        lead = _item_to_lead(item, category, area)
        if lead:
            leads.append(lead)

    log.info("Scraped %d raw places", len(leads))
    return leads
