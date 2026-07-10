from __future__ import annotations

import hashlib
import logging
import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from html import unescape
from typing import Any

import feedparser

from agents.news_scraper.config_loader import FeedConfig, NewsSourcesConfig
from core.models.news_item import Classification, Content, NewsItem, Processing, Source

logger = logging.getLogger(__name__)

_TAG_RE = re.compile(r"<[^>]+>")


def normalize_url(url: str) -> str:
    cleaned = url.strip().split("#", 1)[0].rstrip("/")
    return cleaned.lower()


def url_hash(url: str) -> str:
    return hashlib.sha256(normalize_url(url).encode("utf-8")).hexdigest()


def _strip_html(text: str | None) -> str | None:
    if not text:
        return None
    plain = unescape(_TAG_RE.sub(" ", text))
    return re.sub(r"\s+", " ", plain).strip() or None


def _parse_published(entry: dict[str, Any]) -> datetime | None:
    for key in ("published_parsed", "updated_parsed"):
        parsed = entry.get(key)
        if parsed:
            try:
                return datetime(*parsed[:6], tzinfo=timezone.utc)
            except (TypeError, ValueError):
                pass
    for key in ("published", "updated"):
        raw = entry.get(key)
        if raw:
            try:
                dt = parsedate_to_datetime(raw)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt.astimezone(timezone.utc)
            except (TypeError, ValueError, IndexError):
                pass
    return None


def _entry_url(entry: dict[str, Any]) -> str | None:
    link = entry.get("link")
    if link:
        return str(link).strip()
    entry_id = entry.get("id")
    if entry_id and str(entry_id).startswith("http"):
        return str(entry_id).strip()
    return None


def _entry_title(entry: dict[str, Any]) -> str | None:
    title = _strip_html(entry.get("title"))
    return title if title else None


def _entry_summary(entry: dict[str, Any]) -> str | None:
    for key in ("summary", "description", "content"):
        value = entry.get(key)
        if isinstance(value, list) and value:
            value = value[0].get("value")
        text = _strip_html(str(value) if value is not None else None)
        if text:
            return text[:2000]
    return None


def _entry_external_id(entry: dict[str, Any], article_url: str) -> str:
    entry_id = entry.get("id")
    if entry_id:
        return str(entry_id)
    return article_url


def fetch_feed(feed: FeedConfig, config: NewsSourcesConfig) -> list[NewsItem]:
    logger.info("Fetching feed: %s", feed.name)
    parsed = feedparser.parse(feed.url, agent=config.user_agent)

    if getattr(parsed, "bozo", False) and not parsed.entries:
        exc = getattr(parsed, "bozo_exception", None)
        logger.warning("Feed parse issue for %s: %s", feed.name, exc)
        return []

    items: list[NewsItem] = []
    for entry in parsed.entries[: config.max_items_per_feed]:
        article_url = _entry_url(entry)
        title = _entry_title(entry)
        if not article_url or not title:
            continue

        summary = _entry_summary(entry)
        now = datetime.now(timezone.utc)
        category = feed.category if feed.category in {"ai_tech", "macro", "markets", "geopolitics", "other"} else "other"

        items.append(
            NewsItem(
                created_at=now,
                updated_at=now,
                source=Source(
                    type="rss",
                    name=feed.name,
                    url=feed.url,
                    external_id=_entry_external_id(entry, article_url),
                ),
                content=Content(
                    title=title,
                    summary=summary,
                    body_excerpt=summary[:500] if summary else None,
                    url=article_url,
                    published_at=_parse_published(entry),
                ),
                classification=Classification(
                    category=category,
                    tags=[],
                    relevance_score=0.0,
                    noise_score=1.0,
                ),
                processing=Processing(status="raw"),
            )
        )

    logger.info("Fetched %d items from %s", len(items), feed.name)
    return items


def fetch_all(config: NewsSourcesConfig) -> list[NewsItem]:
    all_items: list[NewsItem] = []
    for feed in config.feeds:
        if not feed.enabled:
            logger.debug("Skipping disabled feed: %s", feed.name)
            continue
        try:
            all_items.extend(fetch_feed(feed, config))
        except Exception:
            logger.exception("Failed to fetch feed: %s", feed.name)
    return all_items
