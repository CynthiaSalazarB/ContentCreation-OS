from __future__ import annotations

from datetime import datetime, timedelta, timezone

from agents.sync_agent.notion_common import (
    NotionDatabaseClient,
    NotionDatabaseConfig,
    date_property,
    load_database_config,
    number_property,
    select_property,
    title_property,
)
from core.models.news_item import NewsItem

NOTION_TITLE = "Title"
NOTION_URL = "URL"
NOTION_SOURCE = "Source"
NOTION_CATEGORY = "Category"
NOTION_SCORE = "Score"
NOTION_PUBLISHED = "Published"
NOTION_STATUS = "Status"
NOTION_SYNCED = "Synced"

DATA_SOURCE_ID_ENV = "NOTION_NEWS_DATA_SOURCE_ID"


def load_notion_config() -> NotionDatabaseConfig:
    return load_database_config(
        "NOTION_NEWS_DATABASE_ID",
        DATA_SOURCE_ID_ENV,
        missing_hint="Add it to .env in the project root.",
    )


def item_to_properties(item: NewsItem, *, synced_at: datetime | None = None) -> dict:
    synced_at = synced_at or datetime.now(timezone.utc)
    properties: dict = {
        NOTION_TITLE: title_property(item.content.title),
        NOTION_URL: {"url": item.content.url},
        NOTION_SOURCE: select_property(item.source.name),
        NOTION_CATEGORY: select_property(item.classification.category),
        NOTION_SCORE: number_property(item.classification.relevance_score),
        NOTION_STATUS: select_property(item.processing.status),
        NOTION_SYNCED: date_property(synced_at),
    }
    published = date_property(item.content.published_at)
    if published is not None:
        properties[NOTION_PUBLISHED] = published
    return properties


class NotionNewsSync:
    def __init__(self, config: NotionDatabaseConfig | None = None) -> None:
        self.db = NotionDatabaseClient(
            config or load_notion_config(),
            data_source_id_env=DATA_SOURCE_ID_ENV,
        )

    def find_page_by_url(self, url: str) -> str | None:
        return self.db.query_first_page_id({"property": NOTION_URL, "url": {"equals": url}})

    def create_page(self, item: NewsItem) -> str:
        return self.db.create_page(item_to_properties(item))

    def list_page_ids(self) -> list[str]:
        return [page["id"] for page in self.db.query_all_pages()]

    def trash_page(self, page_id: str) -> None:
        self.db.trash_page(page_id)

    def sync_item(self, item: NewsItem) -> tuple[str, bool]:
        existing_id = self.find_page_by_url(item.content.url)
        if existing_id:
            return existing_id, False
        page_id = self.create_page(item)
        return page_id, True

    def push_items(self, items: list[NewsItem]) -> tuple[int, int]:
        """Incremental push: create pages for new URLs only (dedup against Notion itself)."""
        created = 0
        skipped = 0
        for item in items:
            _, was_created = self.sync_item(item)
            if was_created:
                created += 1
            else:
                skipped += 1
        return created, skipped

    @staticmethod
    def _page_synced_at(page: dict) -> datetime | None:
        """When the page entered the dashboard: Synced property, else Notion created_time."""
        prop = page.get("properties", {}).get(NOTION_SYNCED, {})
        raw = (prop.get("date") or {}).get("start") if prop.get("type") == "date" else None
        if not raw:
            raw = page.get("created_time")
        if not raw:
            return None
        try:
            parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError:
            return None
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed

    def list_pages_older_than(self, retention_days: int) -> list[str]:
        cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)
        page_ids: list[str] = []
        for page in self.db.query_all_pages():
            synced_at = self._page_synced_at(page)
            if synced_at is not None and synced_at < cutoff:
                page_ids.append(page["id"])
        return page_ids

    def delete_older_than(self, retention_days: int) -> int:
        """Rolling retention: delete pages that entered the dashboard > retention_days ago.

        Deletion = Notion trash (the API cannot hard-delete); pages leave the
        active database immediately and can be purged from trash in the Notion UI.
        """
        page_ids = self.list_pages_older_than(retention_days)
        for page_id in page_ids:
            self.trash_page(page_id)
        return len(page_ids)
