from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field

ProcessingStatus = Literal["raw", "filtered", "discarded"]
NewsCategory = Literal["ai_tech", "macro", "markets", "geopolitics", "other"]


class Source(BaseModel):
    type: Literal["rss", "manual", "notion", "telegram", "scraper"] = "rss"
    name: str
    url: str | None = None
    external_id: str | None = None


class Content(BaseModel):
    title: str
    summary: str | None = None
    body_excerpt: str | None = None
    url: str
    published_at: datetime | None = None
    language: str = "en"


class Classification(BaseModel):
    category: NewsCategory
    tags: list[str] = Field(default_factory=list)
    relevance_score: float = Field(ge=0.0, le=1.0)
    noise_score: float = Field(ge=0.0, le=1.0)


class Processing(BaseModel):
    status: ProcessingStatus = "raw"
    pipeline_version: str = "0.1"
    agent_runs: list[dict] = Field(default_factory=list)


class NewsItem(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    type: Literal["news_item"] = "news_item"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    source: Source
    content: Content
    classification: Classification
    processing: Processing = Field(default_factory=Processing)

    def touch(self) -> None:
        self.updated_at = datetime.now(timezone.utc)
