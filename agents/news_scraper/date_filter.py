from __future__ import annotations

import logging
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

from core.models.news_item import NewsItem

logger = logging.getLogger(__name__)


def _published_local_date(published_at: datetime, tz: ZoneInfo) -> date:
    if published_at.tzinfo is None:
        published_at = published_at.replace(tzinfo=timezone.utc)
    return published_at.astimezone(tz).date()


def filter_published_on_date(
    items: list[NewsItem],
    run_date: date,
    tz_name: str,
) -> tuple[list[NewsItem], list[NewsItem]]:
    """Keep items whose published_at falls on run_date in the given timezone."""
    tz = ZoneInfo(tz_name)
    kept: list[NewsItem] = []
    skipped: list[NewsItem] = []

    for item in items:
        published = item.content.published_at
        if published is None:
            skipped.append(item)
            continue
        if _published_local_date(published, tz) == run_date:
            kept.append(item)
        else:
            skipped.append(item)

    logger.info(
        "Date filter (%s on %s): %d kept, %d skipped",
        tz_name,
        run_date.isoformat(),
        len(kept),
        len(skipped),
    )
    return kept, skipped
