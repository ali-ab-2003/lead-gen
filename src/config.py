"""Load run configuration from config.yaml and environment variables."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG_PATH = ROOT / "config.yaml"


@dataclass
class Settings:
    """Resolved configuration for one pipeline run."""
    categories: list[str]
    areas: list[str]
    max_results_per_query: int
    language: str
    require_no_website: bool
    require_some_contact: bool
    enrich_enabled: bool
    ai_enabled: bool
    outreach_persona: str

    @property
    def queries(self) -> list[tuple[str, str, str]]:
        """All (search_string, category, area) combinations to scrape."""
        out: list[tuple[str, str, str]] = []
        for area in self.areas:
            for cat in self.categories:
                out.append((f"{cat} in {area}", cat, area))
        return out


def _env_flag(name: str, default: bool = False) -> bool:
    val = os.getenv(name)
    if val is None:
        return default
    return val.strip() not in ("0", "", "false", "False", "no")


def load_settings(path: str | Path = DEFAULT_CONFIG_PATH) -> Settings:
    with open(path, "r", encoding="utf-8") as fh:
        raw: dict[str, Any] = yaml.safe_load(fh) or {}

    flt = raw.get("filter", {}) or {}
    enrich = raw.get("enrich", {}) or {}
    ai = raw.get("ai", {}) or {}

    # Environment toggles override config-file values when set.
    enrich_enabled = enrich.get("enabled", True) and not _env_flag("DISABLE_ENRICH")
    ai_enabled = ai.get("enabled", True) and not _env_flag("DISABLE_AI")

    return Settings(
        categories=list(raw.get("categories", [])),
        areas=list(raw.get("areas", [])),
        max_results_per_query=int(raw.get("max_results_per_query", 50)),
        language=str(raw.get("language", "en")),
        require_no_website=bool(flt.get("require_no_website", True)),
        require_some_contact=bool(flt.get("require_some_contact", True)),
        enrich_enabled=enrich_enabled,
        ai_enabled=ai_enabled,
        outreach_persona=str(ai.get("outreach_persona", "")).strip(),
    )


def env(name: str, default: str = "") -> str:
    return os.getenv(name, default)
