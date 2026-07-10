from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from agents.news_scraper.fetcher import url_hash
from core.models.news_item import NewsItem
from core.paths import NEWS_DATA_DIR

logger = logging.getLogger(__name__)

SEEN_FILENAME = "seen.json"


def seen_path(data_dir: Path | None = None) -> Path:
    return (data_dir or NEWS_DATA_DIR) / SEEN_FILENAME


def load_seen(data_dir: Path | None = None) -> set[str]:
    path = seen_path(data_dir)
    if not path.exists():
        return set()
    with path.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    hashes = payload.get("url_hashes", [])
    return set(hashes)


def save_seen(hashes: set[str], data_dir: Path | None = None) -> None:
    path = seen_path(data_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "url_hashes": sorted(hashes),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "count": len(hashes),
    }
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)


def dedup_items(items: list[NewsItem], seen: set[str]) -> tuple[list[NewsItem], list[str]]:
    new_items: list[NewsItem] = []
    new_hashes: list[str] = []

    for item in items:
        digest = url_hash(item.content.url)
        if digest in seen:
            continue
        new_items.append(item)
        new_hashes.append(digest)

    logger.info("Dedup: %d new of %d fetched", len(new_items), len(items))
    return new_items, new_hashes
