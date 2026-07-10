"""Shared Notion plumbing for sync_agent — config, property builders, base client."""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timezone

from dotenv import load_dotenv
from notion_client import Client

from core.paths import ENV_PATH


@dataclass
class NotionDatabaseConfig:
    api_key: str
    database_id: str
    data_source_id: str | None = None


def load_database_config(
    database_id_env: str,
    data_source_id_env: str,
    *,
    missing_hint: str = "",
) -> NotionDatabaseConfig:
    load_dotenv(ENV_PATH)
    api_key = os.getenv("NOTION_API_KEY", "").strip()
    database_id = os.getenv(database_id_env, "").strip()
    data_source_id = os.getenv(data_source_id_env, "").strip() or None
    if not api_key:
        raise ValueError("NOTION_API_KEY is not set. Add it to .env in the project root.")
    if not database_id:
        raise ValueError(f"{database_id_env} is not set. {missing_hint}".strip())
    return NotionDatabaseConfig(
        api_key=api_key,
        database_id=database_id.replace("-", ""),
        data_source_id=data_source_id.replace("-", "") if data_source_id else None,
    )


def title_property(value: str) -> dict:
    return {"title": [{"text": {"content": value[:2000]}}]}


def rich_text_property(value: str) -> dict:
    return {"rich_text": [{"text": {"content": value[:2000]}}]}


def select_property(value: str) -> dict:
    return {"select": {"name": value}}


def number_property(value: float) -> dict:
    return {"number": round(value, 4)}


def date_property(value: datetime | None) -> dict | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return {"date": {"start": value.astimezone(timezone.utc).isoformat()}}


class NotionDatabaseClient:
    """Wraps one Notion database: data-source resolution + paginated queries."""

    def __init__(self, config: NotionDatabaseConfig, *, data_source_id_env: str) -> None:
        self.config = config
        self.client = Client(auth=config.api_key)
        self._data_source_id_env = data_source_id_env
        self._data_source_id = config.data_source_id or self._resolve_data_source_id()

    def _resolve_data_source_id(self) -> str:
        database = self.client.databases.retrieve(database_id=self.config.database_id)
        data_sources = database.get("data_sources", [])
        if not data_sources:
            raise ValueError(
                "No data sources found for the configured Notion database. "
                f"Set {self._data_source_id_env} in .env if needed."
            )
        return data_sources[0]["id"].replace("-", "")

    def query_first_page_id(self, filter_: dict) -> str | None:
        response = self.client.data_sources.query(
            data_source_id=self._data_source_id,
            filter=filter_,
            page_size=1,
        )
        results = response.get("results", [])
        if not results:
            return None
        return results[0]["id"]

    def query_all_pages(self) -> list[dict]:
        pages: list[dict] = []
        cursor: str | None = None
        while True:
            kwargs: dict = {"data_source_id": self._data_source_id, "page_size": 100}
            if cursor:
                kwargs["start_cursor"] = cursor
            response = self.client.data_sources.query(**kwargs)
            pages.extend(response.get("results", []))
            if not response.get("has_more"):
                break
            cursor = response.get("next_cursor")
        return pages

    def create_page(self, properties: dict) -> str:
        page = self.client.pages.create(
            parent={"data_source_id": self._data_source_id},
            properties=properties,
        )
        return page["id"]

    def update_page(self, page_id: str, properties: dict) -> None:
        self.client.pages.update(page_id=page_id, properties=properties)

    def trash_page(self, page_id: str) -> None:
        # Notion's public API has no hard-delete endpoint; in_trash=True is the
        # strongest removal it offers (page leaves the database, lands in trash).
        self.client.pages.update(page_id=page_id, in_trash=True)
