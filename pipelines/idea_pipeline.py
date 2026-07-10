"""Orchestration-layer composition: capture → angles → Notion Idea Bank.

This package sits at the top level (like orchestrator.py) — the only layer
allowed to import multiple agents. Library code under agents/ must never
import it; CLI/bot entry points may (see ARCHITECTURE.md, entry-point rule).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from agents.capture_agent.run import capture_idea
from agents.script_angles_agent.run import run_script_angles
from agents.sync_agent.notion_ideas_sync import NotionIdeaSync
from core.models.idea import Idea
from core.models.news_item import Source
from core.storage.sqlite_store import SqliteStore


@dataclass
class IdeaPipelineResult:
    idea: Idea
    synced_to_notion: bool
    notion_page_id: str | None = None


def process_idea(
    idea: Idea,
    *,
    db_path: Path | None = None,
    sync_notion: bool = True,
    dry_run: bool = False,
) -> IdeaPipelineResult:
    store = SqliteStore(db_path)

    angles = run_script_angles(idea)
    idea = angles.idea
    store.upsert_idea(idea)

    if not sync_notion or dry_run:
        return IdeaPipelineResult(idea=idea, synced_to_notion=False)

    notion = NotionIdeaSync()
    page_id, created = notion.sync_idea(idea)
    idea.sync.notion_page_id = page_id
    idea.sync.last_synced_at = datetime.now(timezone.utc)
    idea.processing.status = "synced"
    idea.touch()
    store.upsert_idea(idea)
    return IdeaPipelineResult(
        idea=idea,
        synced_to_notion=created or bool(page_id),
        notion_page_id=page_id,
    )


def process_idea_id(
    idea_id: str,
    *,
    db_path: Path | None = None,
    sync_notion: bool = True,
    dry_run: bool = False,
) -> IdeaPipelineResult:
    store = SqliteStore(db_path)
    idea = store.get_idea(idea_id)
    if idea is None:
        raise ValueError(f"Idea not found: {idea_id}")
    return process_idea(idea, db_path=db_path, sync_notion=sync_notion, dry_run=dry_run)


def capture_and_process(
    text: str,
    *,
    context: str | None = None,
    tags: list[str] | None = None,
    source: Source | None = None,
    db_path: Path | None = None,
    sync_notion: bool = True,
    dry_run: bool = False,
) -> IdeaPipelineResult:
    captured = capture_idea(
        text,
        context=context,
        tags=tags,
        source=source,
        db_path=db_path,
    )
    return process_idea(
        captured.idea,
        db_path=db_path,
        sync_notion=sync_notion,
        dry_run=dry_run,
    )
