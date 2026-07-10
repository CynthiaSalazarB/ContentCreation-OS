from __future__ import annotations

import json
from datetime import date, datetime, timezone
from pathlib import Path

from core.models.news_item import NewsItem
from core.paths import NEWS_DATA_DIR

SEEN_FILENAME = "seen.json"


def daily_output_path(run_date: date, data_dir: Path | None = None) -> Path:
    return (data_dir or NEWS_DATA_DIR) / f"{run_date.isoformat()}.json"


def latest_daily_date(data_dir: Path | None = None) -> date | None:
    """Date of the newest daily digest file, or None if none exist."""
    directory = data_dir or NEWS_DATA_DIR
    dates: list[date] = []
    for path in directory.glob("*.json"):
        try:
            dates.append(date.fromisoformat(path.stem))
        except ValueError:
            continue
    return max(dates) if dates else None


def load_daily_items(path: Path) -> list[NewsItem]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    raw_items = payload.get("items", payload if isinstance(payload, list) else [])
    return [NewsItem.model_validate(item) for item in raw_items]


def write_daily_items(
    items: list[NewsItem],
    run_date: date,
    data_dir: Path | None = None,
    *,
    merge: bool = True,
) -> Path:
    output_dir = data_dir or NEWS_DATA_DIR
    output_dir.mkdir(parents=True, exist_ok=True)
    path = daily_output_path(run_date, output_dir)

    existing: list[NewsItem] = load_daily_items(path) if merge else []
    by_url = {item.content.url: item for item in existing}
    for item in items:
        by_url[item.content.url] = item

    merged = sorted(
        by_url.values(),
        key=lambda i: i.content.published_at or i.created_at,
        reverse=True,
    )

    payload = {
        "date": run_date.isoformat(),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "count": len(merged),
        "items": [item.model_dump(mode="json") for item in merged],
    }
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
    return path


def prune_old_daily_json(data_dir: Path, keep_date: date) -> int:
    """Remove dated digest files except keep_date. Never touches seen.json."""
    removed = 0
    for path in data_dir.glob("*.json"):
        if path.name == SEEN_FILENAME:
            continue
        try:
            file_date = date.fromisoformat(path.stem)
        except ValueError:
            continue
        if file_date != keep_date:
            path.unlink(missing_ok=True)
            removed += 1
    return removed
