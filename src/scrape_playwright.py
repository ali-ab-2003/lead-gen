"""OPTIONAL zero-cost fallback scraper using Playwright.

WARNING: This drives a real browser against Google Maps. It is fragile, against
Google's Terms of Service, and will get rate-limited / captcha'd, especially
from datacenter IPs. Prefer the Apify path in `scrape.py`. This exists only as
a no-API-key option for very low volume / experimentation.

Usage: set USE_PLAYWRIGHT=1 and call scrape_playwright(settings) yourself, or
wire it into main.py as an alternative to src.scrape.scrape.
"""
from __future__ import annotations

import logging
import re
import time
from urllib.parse import quote_plus

from .config import Settings
from .models import Lead

log = logging.getLogger(__name__)


def _scrape_query(page, search: str, category: str, area: str, cap: int) -> list[Lead]:
    page.goto(f"https://www.google.com/maps/search/{quote_plus(search)}", timeout=60000)
    page.wait_for_timeout(3000)

    # Scroll the results feed to load more listings.
    feed_sel = 'div[role="feed"]'
    try:
        page.wait_for_selector(feed_sel, timeout=15000)
    except Exception:  # noqa: BLE001
        log.warning("No results feed for %r (maps layout change or captcha).", search)
        return []

    for _ in range(8):
        page.eval_on_selector(feed_sel, "el => el.scrollBy(0, el.scrollHeight)")
        page.wait_for_timeout(1500)

    cards = page.query_selector_all(f'{feed_sel} a[href*="/maps/place/"]')
    leads: list[Lead] = []
    seen: set[str] = set()

    for card in cards[:cap]:
        href = card.get_attribute("href") or ""
        m = re.search(r"!1s([^!?]+)", href)
        place_id = m.group(1) if m else href
        if not place_id or place_id in seen:
            continue
        seen.add(place_id)
        name = card.get_attribute("aria-label") or ""
        leads.append(Lead(
            place_id=place_id, name=name, category=category, area=area,
            google_maps_url=href,
        ))
    # NOTE: phone/website require visiting each detail page; left as an exercise
    # to keep this fallback minimal. Apify returns these directly.
    log.info("Playwright scraped %d cards for %r", len(leads), search)
    return leads


def scrape_playwright(settings: Settings) -> list[Lead]:
    from playwright.sync_api import sync_playwright

    leads: list[Lead] = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        for search, category, area in settings.queries:
            leads.extend(_scrape_query(page, search, category, area,
                                       settings.max_results_per_query))
            time.sleep(2)
        browser.close()
    return leads
