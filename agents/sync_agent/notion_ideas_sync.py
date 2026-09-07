from __future__ import annotations

from datetime import datetime, timezone

from agents.sync_agent.notion_common import (
    NotionDatabaseClient,
    NotionDatabaseConfig,
    date_property,
    load_database_config,
    number_property,
    rich_text_property,
    select_property,
    title_property,
)
from core.models.idea import Idea

IDEA_TITLE = "Title"
IDEA_ID = "Idea ID"
IDEA_BRAND_FIT = "Brand fit %"
IDEA_BRAND_FIT_NOTE = "Brand fit note"
IDEA_LANE = "Lane"
IDEA_STATUS = "Status"
IDEA_SOURCE = "Source"
IDEA_ANGLES = "Angles"
IDEA_SYNCED = "Synced"

DATA_SOURCE_ID_ENV = "NOTION_IDEA_BANK_DATA_SOURCE_ID"

NOTION_HUMAN_STATUS = {
    "approved": "Approved",
    "rejected": "Rejected",
    "edit_requested": "Edit requested",
    "pending": "Inbox",
}

PULL_STATUS_MAP = {
    "Approved": "approved",
    "Rejected": "rejected",
    "Edit requested": "edit_requested",
    "Inbox": "pending",
}

LANE_LABELS = {"build": "Build", "create": "Create", "reflect": "Reflect"}


def load_notion_idea_config() -> NotionDatabaseConfig:
    return load_database_config(
        "NOTION_IDEA_BANK_DATABASE_ID",
        DATA_SOURCE_ID_ENV,
        missing_hint="Create an Idea Bank database in Notion.",
    )


def _brand_fit_percent(idea: Idea) -> float | None:
    if idea.brand_fit.fit is None:
        return None
    return round(idea.brand_fit.fit * 100, 1)


def _angle_tags(angle) -> str:
    """Advisory suggestion tags, e.g. `carousel · reach · promise/negation`.

    Every field is optional, so older angles render exactly as before.
    """
    tags = [t for t in (angle.delivery_format, angle.stage) if t]
    if angle.hook_family:
        family = angle.hook_family
        tags.append(f"{family}/{angle.hook_mechanism}" if angle.hook_mechanism else family)
    return f"  ({' · '.join(tags)})" if tags else ""


def _angles_summary(idea: Idea) -> str:
    if not idea.script_angles:
        return ""
    parts: list[str] = []
    for index, angle in enumerate(idea.script_angles, start=1):
        parts.append(
            f"{index}. [{angle.framework}]{_angle_tags(angle)} {angle.hook}\n   {angle.angle}"
        )
    return "\n".join(parts)[:2000]


def _display_title(idea: Idea) -> str:
    if idea.content.title:
        return idea.content.title
    text = idea.content.raw_text.strip()
    return text[:80] + ("..." if len(text) > 80 else "")


def idea_to_properties(idea: Idea, *, synced_at: datetime | None = None) -> dict:
    synced_at = synced_at or datetime.now(timezone.utc)
    status = NOTION_HUMAN_STATUS.get(idea.human.decision, "Inbox")
    properties: dict = {
        IDEA_TITLE: title_property(_display_title(idea)),
        IDEA_ID: rich_text_property(idea.id),
        IDEA_LANE: select_property(LANE_LABELS.get(idea.brand_fit.lane or "", "Build")),
        IDEA_SOURCE: select_property(idea.source.name),
        IDEA_STATUS: select_property(status),
        IDEA_SYNCED: date_property(synced_at),
    }
    brand_fit_pct = _brand_fit_percent(idea)
    if brand_fit_pct is not None:
        properties[IDEA_BRAND_FIT] = number_property(brand_fit_pct)
    if idea.brand_fit.note:
        properties[IDEA_BRAND_FIT_NOTE] = rich_text_property(idea.brand_fit.note)
    summary = _angles_summary(idea)
    if summary:
        properties[IDEA_ANGLES] = rich_text_property(summary)
    return properties


class NotionIdeaSync:
    def __init__(self, config: NotionDatabaseConfig | None = None) -> None:
        self.db = NotionDatabaseClient(
            config or load_notion_idea_config(),
            data_source_id_env=DATA_SOURCE_ID_ENV,
        )

    def find_page_by_idea_id(self, idea_id: str) -> str | None:
        return self.db.query_first_page_id(
            {"property": IDEA_ID, "rich_text": {"equals": idea_id}}
        )

    def sync_idea(self, idea: Idea) -> tuple[str, bool]:
        existing_id = idea.sync.notion_page_id or self.find_page_by_idea_id(idea.id)
        if existing_id:
            self.db.update_page(existing_id, idea_to_properties(idea))
            return existing_id, False
        page_id = self.db.create_page(idea_to_properties(idea))
        return page_id, True

    @staticmethod
    def _prop_text(prop: dict | None) -> str:
        if not prop:
            return ""
        if prop.get("type") == "rich_text":
            parts = prop.get("rich_text", [])
            return "".join(part.get("plain_text", "") for part in parts)
        return ""

    @staticmethod
    def _prop_select(prop: dict | None) -> str | None:
        if not prop or prop.get("type") != "select":
            return None
        select = prop.get("select")
        if not select:
            return None
        return select.get("name")

    def pull_human_decisions(self) -> list[tuple[str, str]]:
        """Return (idea_id, human_decision) pairs from Notion Status changes."""
        updates: list[tuple[str, str]] = []
        for page in self.db.query_all_pages():
            props = page.get("properties", {})
            idea_id = self._prop_text(props.get(IDEA_ID))
            if not idea_id:
                continue
            status_name = self._prop_select(props.get(IDEA_STATUS))
            if not status_name:
                continue
            decision = PULL_STATUS_MAP.get(status_name)
            if decision:
                updates.append((idea_id, decision))
        return updates
