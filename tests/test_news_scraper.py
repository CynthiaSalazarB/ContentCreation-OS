from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

import pytest

from agents.news_scraper.dedup import dedup_items, load_seen, save_seen
from agents.news_scraper.fetcher import url_hash
from agents.news_scraper.filter import filter_items
from agents.news_scraper.config_loader import FilterRules, NewsSourcesConfig
from agents.news_scraper.date_filter import filter_published_on_date
from core.storage.json_store import prune_old_daily_json, write_daily_items
from core.models.news_item import Classification, Content, NewsItem, Processing, Source


def _sample_item(title: str, summary: str, url: str, category: str = "ai_tech") -> NewsItem:
    return NewsItem(
        source=Source(name="test", url="https://example.com/feed"),
        content=Content(title=title, summary=summary, url=url),
        classification=Classification(
            category=category,
            tags=[],
            relevance_score=0.0,
            noise_score=1.0,
        ),
    )


def test_url_hash_normalizes_trailing_slash():
    assert url_hash("https://Example.com/a/") == url_hash("https://example.com/a")


def test_dedup_skips_seen_urls(tmp_path):
    item = _sample_item("AI news", "OpenAI update", "https://example.com/1")
    seen = {url_hash(item.content.url)}
    new_items, new_hashes = dedup_items([item], seen)
    assert new_items == []
    assert new_hashes == []


def test_filter_keeps_relevant_ai_item():
    config = NewsSourcesConfig(
        feeds=[],
        filters={"ai_tech": FilterRules(allow=["openai", "ai"], block=["gaming"])},
        min_relevance_score=0.3,
    )
    item = _sample_item("OpenAI launches new model", "AI breakthrough", "https://example.com/2")
    kept, discarded = filter_items([item], config)
    assert len(kept) == 1
    assert kept[0].processing.status == "filtered"
    assert kept[0].classification.relevance_score >= 0.3


def test_filter_discards_blocked_item():
    config = NewsSourcesConfig(
        feeds=[],
        filters={"ai_tech": FilterRules(allow=["quantum"], block=["gaming", "sports"])},
        min_relevance_score=0.3,
    )
    item = _sample_item("Gaming tournament recap", "sports highlights", "https://example.com/3")
    kept, discarded = filter_items([item], config)
    assert len(discarded) == 1
    assert discarded[0].processing.status == "discarded"


def test_seen_roundtrip(tmp_path):
    save_seen({"abc", "def"}, tmp_path)
    loaded = load_seen(tmp_path)
    assert loaded == {"abc", "def"}


def test_prune_old_daily_json_keeps_today_and_seen(tmp_path):
    (tmp_path / "seen.json").write_text("{}", encoding="utf-8")
    (tmp_path / "2026-06-15.json").write_text("{}", encoding="utf-8")
    (tmp_path / "2026-06-16.json").write_text("{}", encoding="utf-8")

    removed = prune_old_daily_json(tmp_path, date(2026, 6, 16))

    assert removed == 1
    assert (tmp_path / "2026-06-15.json").exists() is False
    assert (tmp_path / "2026-06-16.json").exists()
    assert (tmp_path / "seen.json").exists()


def test_write_daily_items_replaces_same_day(tmp_path):
    item_a = _sample_item("First", "summary", "https://example.com/a")
    item_b = _sample_item("Second", "summary", "https://example.com/b")
    run_date = date(2026, 6, 16)

    write_daily_items([item_a], run_date, tmp_path, merge=False)
    write_daily_items([item_b], run_date, tmp_path, merge=False)

    from core.storage.json_store import load_daily_items, daily_output_path

    loaded = load_daily_items(daily_output_path(run_date, tmp_path))
    assert len(loaded) == 1
    assert loaded[0].content.url == "https://example.com/b"


def test_filter_published_on_date_keeps_today_only():
    tz = "America/New_York"
    run_date = date(2026, 6, 16)
    today_item = NewsItem(
        source=Source(name="test", url="https://example.com/feed"),
        content=Content(
            title="Today",
            url="https://example.com/today",
            published_at=datetime(2026, 6, 16, 15, 0, tzinfo=ZoneInfo(tz)),
        ),
        classification=Classification(category="ai_tech", relevance_score=0.0, noise_score=1.0),
    )
    old_item = NewsItem(
        source=Source(name="test", url="https://example.com/feed"),
        content=Content(
            title="Old",
            url="https://example.com/old",
            published_at=datetime(2026, 5, 20, 12, 0, tzinfo=ZoneInfo(tz)),
        ),
        classification=Classification(category="ai_tech", relevance_score=0.0, noise_score=1.0),
    )

    kept, skipped = filter_published_on_date([today_item, old_item], run_date, tz)

    assert len(kept) == 1
    assert kept[0].content.url == "https://example.com/today"
    assert len(skipped) == 1


def test_filter_published_on_date_drops_missing_date():
    run_date = date(2026, 6, 16)
    item = NewsItem(
        source=Source(name="test", url="https://example.com/feed"),
        content=Content(title="No date", url="https://example.com/nodate"),
        classification=Classification(category="ai_tech", relevance_score=0.0, noise_score=1.0),
    )

    kept, skipped = filter_published_on_date([item], run_date, "UTC")

    assert kept == []
    assert len(skipped) == 1
