from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from core.paths import CONFIG_DIR


@dataclass
class FeedConfig:
    name: str
    url: str
    category: str
    tier: str = "journalism"
    enabled: bool = True


@dataclass
class FilterRules:
    allow: list[str] = field(default_factory=list)
    block: list[str] = field(default_factory=list)


@dataclass
class NewsSourcesConfig:
    feeds: list[FeedConfig]
    filters: dict[str, FilterRules]
    min_relevance_score: float = 0.3
    max_items_per_feed: int = 20
    user_agent: str = "ContentCreation-OS-NewsBot/0.1 (personal RSS reader)"
    published_on_run_date_only: bool = False
    digest_timezone: str = "UTC"


def load_config(path: Path | None = None) -> NewsSourcesConfig:
    config_path = path or (CONFIG_DIR / "news_sources.yaml")
    with config_path.open(encoding="utf-8") as handle:
        raw: dict[str, Any] = yaml.safe_load(handle)

    feeds = [
        FeedConfig(
            name=item["name"],
            url=item["url"],
            category=item["category"],
            tier=item.get("tier", "journalism"),
            enabled=item.get("enabled", True),
        )
        for item in raw.get("feeds", [])
    ]

    filters: dict[str, FilterRules] = {}
    for category, rules in raw.get("filters", {}).items():
        filters[category] = FilterRules(
            allow=[k.lower() for k in rules.get("allow", [])],
            block=[k.lower() for k in rules.get("block", [])],
        )

    settings = raw.get("settings", {})
    return NewsSourcesConfig(
        feeds=feeds,
        filters=filters,
        min_relevance_score=float(settings.get("min_relevance_score", 0.3)),
        max_items_per_feed=int(settings.get("max_items_per_feed", 20)),
        user_agent=str(settings.get("user_agent", "ContentCreation-OS-NewsBot/0.1")),
        published_on_run_date_only=bool(settings.get("published_on_run_date_only", False)),
        digest_timezone=str(settings.get("digest_timezone", "UTC")),
    )
