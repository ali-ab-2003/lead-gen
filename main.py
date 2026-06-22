"""Pipeline entrypoint for the Google Maps no-website lead generator.

Usage:
    python main.py --dry-run          # scrape + filter, write a local CSV only
    python main.py                    # full run: + enrich + AI + store + export
    python main.py --no-ai            # skip the Groq AI stage
    python main.py --config other.yaml
"""
from __future__ import annotations

import argparse
import csv
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from src.config import load_settings
from src.models import LEAD_COLUMNS, Lead

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
log = logging.getLogger("leadgen")

OUTPUT_DIR = Path(__file__).resolve().parent / "output"


def write_csv(leads: list[Lead], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=LEAD_COLUMNS)
        writer.writeheader()
        for lead in leads:
            writer.writerow(lead.to_dict())
    log.info("Wrote %d leads -> %s", len(leads), path)


def parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Google Maps no-website lead generator")
    p.add_argument("--config", default=None, help="Path to config.yaml")
    p.add_argument("--dry-run", action="store_true",
                   help="Scrape + filter only; write a local CSV, no storage/AI.")
    p.add_argument("--no-ai", action="store_true", help="Skip the Groq AI stage.")
    p.add_argument("--no-enrich", action="store_true", help="Skip contact enrichment.")
    return p.parse_args(argv)


def run(argv: list[str]) -> int:
    args = parse_args(argv)
    settings = load_settings(args.config) if args.config else load_settings()

    if args.no_ai:
        settings.ai_enabled = False
    if args.no_enrich:
        settings.enrich_enabled = False

    # 1. Scrape ----------------------------------------------------------
    from src.scrape import scrape
    leads = scrape(settings)

    # 2. Filter to no-website actionable leads ---------------------------
    from src.filter import filter_leads
    leads = filter_leads(leads, settings)

    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    if args.dry_run:
        write_csv(leads, OUTPUT_DIR / f"leads-{stamp}-dryrun.csv")
        log.info("Dry run complete: %d leads.", len(leads))
        return 0

    # 3. Best-effort contact enrichment ----------------------------------
    if settings.enrich_enabled:
        from src.enrich import enrich_leads
        leads = enrich_leads(leads)

    # 4. AI scoring + outreach drafting (Groq) ---------------------------
    if settings.ai_enabled:
        from src.ai_enrich import ai_enrich_leads
        leads = ai_enrich_leads(leads, settings)

    # 5. Store + dedupe across days; keep only newly added ---------------
    from src.store import upsert_leads
    new_leads = upsert_leads(leads)

    # 6. Export deliverables ---------------------------------------------
    from src.export import export_to_sheet
    write_csv(new_leads, OUTPUT_DIR / f"leads-{stamp}.csv")
    export_to_sheet(new_leads)

    log.info("Run complete: %d total kept, %d new this run.", len(leads), len(new_leads))
    return 0


if __name__ == "__main__":
    sys.exit(run(sys.argv[1:]))
