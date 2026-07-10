from __future__ import annotations

import logging
import re

from agents.news_scraper.config_loader import FilterRules, NewsSourcesConfig
from core.models.news_item import NewsItem

logger = logging.getLogger(__name__)


def _contains_keyword(text: str, keyword: str) -> bool:
    if " " in keyword:
        return keyword in text
    pattern = re.compile(r"\b" + re.escape(keyword) + r"\b")
    return pattern.search(text) is not None


def _match_keywords(text: str, keywords: list[str]) -> list[str]:
    return [kw for kw in keywords if _contains_keyword(text, kw)]


def score_item(item: NewsItem, rules: FilterRules) -> tuple[float, list[str]]:
    text = " ".join(
        part for part in (item.content.title, item.content.summary) if part
    ).lower()

    allow_hits = _match_keywords(text, rules.allow)
    block_hits = _match_keywords(text, rules.block)

    if allow_hits:
        score = 0.35 + min(len(allow_hits) * 0.15, 0.55)
    else:
        score = 0.25

    score -= len(block_hits) * 0.25
    score = max(0.0, min(1.0, score))

    return score, allow_hits


def filter_items(items: list[NewsItem], config: NewsSourcesConfig) -> tuple[list[NewsItem], list[NewsItem]]:
    kept: list[NewsItem] = []
    discarded: list[NewsItem] = []

    for item in items:
        rules = config.filters.get(item.classification.category, FilterRules())
        score, tags = score_item(item, rules)

        item.classification.relevance_score = round(score, 2)
        item.classification.noise_score = round(1.0 - score, 2)
        item.classification.tags = tags
        item.touch()

        if score >= config.min_relevance_score:
            item.processing.status = "filtered"
            kept.append(item)
        else:
            item.processing.status = "discarded"
            discarded.append(item)

    logger.info("Filter: %d kept, %d discarded", len(kept), len(discarded))
    return kept, discarded
