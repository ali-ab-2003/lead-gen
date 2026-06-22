"""Export new leads to a Google Sheet (the daily deliverable).

Appends rows to a master worksheet, creating the header row on first use.
CSV output is handled by main.py (write_csv); this module is Sheets-only.
"""
from __future__ import annotations

import logging

import gspread
from google.oauth2.service_account import Credentials

from .config import env
from .models import LEAD_COLUMNS, Lead

log = logging.getLogger(__name__)

_SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
_WORKSHEET = "leads"


def _open_worksheet():
    sa_path = env("GOOGLE_SERVICE_ACCOUNT_JSON")
    sheet_id = env("GOOGLE_SHEET_ID")
    if not sa_path or not sheet_id:
        raise RuntimeError(
            "GOOGLE_SERVICE_ACCOUNT_JSON / GOOGLE_SHEET_ID not set (see .env.example)."
        )

    creds = Credentials.from_service_account_file(sa_path, scopes=_SCOPES)
    gc = gspread.authorize(creds)
    sh = gc.open_by_key(sheet_id)

    try:
        ws = sh.worksheet(_WORKSHEET)
    except gspread.WorksheetNotFound:
        ws = sh.add_worksheet(title=_WORKSHEET, rows=1, cols=len(LEAD_COLUMNS))
        ws.append_row(LEAD_COLUMNS, value_input_option="RAW")
    return ws


def export_to_sheet(leads: list[Lead]) -> None:
    if not leads:
        log.info("No new leads to export to Google Sheets.")
        return

    ws = _open_worksheet()

    # Ensure header exists (in case the sheet was created/emptied manually).
    if not ws.row_values(1):
        ws.append_row(LEAD_COLUMNS, value_input_option="RAW")

    rows = [[_cell(getattr(l, c)) for c in LEAD_COLUMNS] for l in leads]
    ws.append_rows(rows, value_input_option="RAW")
    log.info("Appended %d new leads to Google Sheet worksheet '%s'.", len(rows), _WORKSHEET)


def _cell(value) -> str:
    return "" if value is None else str(value)
