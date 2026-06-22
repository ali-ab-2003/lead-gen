"""Shared data model for a lead.

A single `Lead` record flows through the whole pipeline (scrape -> filter ->
enrich -> ai_enrich -> store -> export). Keeping it one flat dataclass keeps
serialization to CSV / Sheets / Postgres trivial.
"""
from __future__ import annotations

from dataclasses import dataclass, field, fields, asdict
from datetime import datetime, timezone
from typing import Any, Optional


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class Lead:
    # ── Core identity / scraped fields ───────────────────────────────────
    place_id: str
    name: str = ""
    category: str = ""
    address: str = ""
    area: str = ""              # the search-area tag this lead came from
    phone: str = ""
    website: str = ""          # expected empty for our targets
    google_maps_url: str = ""
    rating: Optional[float] = None
    reviews_count: Optional[int] = None

    # ── Best-effort enrichment ───────────────────────────────────────────
    email: str = ""
    owner_name: str = ""
    source_of_contact: str = ""   # e.g. "facebook", "web_search", "apify"

    # ── AI enrichment (Groq) ─────────────────────────────────────────────
    lead_score: Optional[int] = None      # 0-100
    score_reason: str = ""
    outreach_draft: str = ""

    # ── Lifecycle ────────────────────────────────────────────────────────
    status: str = "new"
    first_seen: str = field(default_factory=_now_iso)
    last_seen: str = field(default_factory=_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Lead":
        known = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in data.items() if k in known})


# Column order used for CSV / Google Sheets headers.
LEAD_COLUMNS = [f.name for f in fields(Lead)]
