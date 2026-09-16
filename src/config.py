"""Central configuration loaded from environment / .env."""
from __future__ import annotations

import os
from pathlib import Path
from typing import List

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DOCUMENTS_DIR = DATA_DIR / "documents"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"

for _dir in (DATA_DIR, DOCUMENTS_DIR, RAW_DIR, PROCESSED_DIR):
    _dir.mkdir(parents=True, exist_ok=True)


def _get_groq_api_key() -> str | None:
    return os.getenv("groq_api_key") or os.getenv("GROQ_API_KEY")


def _get_bool(name: str, default: bool) -> bool:
    val = os.getenv(name)
    if val is None:
        return default
    return val.strip().lower() in ("1", "true", "yes", "on")


def _get_list(name: str, default: List[str]) -> List[str]:
    val = os.getenv(name)
    if not val:
        return default
    return [item.strip() for item in val.split(",") if item.strip()]


class Settings:
    """Application settings. Values are read once at import time."""

    groq_api_key: str | None = _get_groq_api_key()
    groq_model: str = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

    database_url: str = os.getenv("DATABASE_URL", f"sqlite:///{DATA_DIR / 'govbid.db'}")

    enabled_sources: List[str] = _get_list("ENABLED_SOURCES", ["gem"])
    # Not a fixed page size - GeM search already stops once it has no more
    # results. This is a safety ceiling so a very broad/generic query (tens
    # of thousands of matches) can't turn into thousands of sequential
    # requests in one search, which would be aggressive scraping.
    max_pages_per_source: int = int(os.getenv("MAX_PAGES_PER_SOURCE", "100"))
    request_delay_seconds: float = float(os.getenv("REQUEST_DELAY_SECONDS", "0.2"))
    request_timeout_seconds: int = int(os.getenv("REQUEST_TIMEOUT_SECONDS", "15"))
    max_download_size_mb: int = int(os.getenv("MAX_DOWNLOAD_SIZE_MB", "25"))

    user_agent: str = os.getenv(
        "USER_AGENT",
        "GovBidIntelligence/0.1 (public-data-research; contact=admin@example.com)",
    )

    @property
    def has_groq_key(self) -> bool:
        return bool(self.groq_api_key)


settings = Settings()
