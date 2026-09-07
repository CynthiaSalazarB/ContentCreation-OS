from __future__ import annotations

import argparse
import logging
import sys
import time
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from agents.sync_agent.notion_sync import NotionNewsSync
from core.models.run import RunContext, RunResult
from core.paths import NEWS_DATA_DIR
from core.storage.json_store import daily_output_path, latest_daily_date, load_daily_items

logger = logging.getLogger(__name__)

DEFAULT_RETENTION_DAYS = 30


@dataclass
class SyncResult:
    candidates: int
    created: int
    skipped_existing: int
    deleted: int
    dry_run: bool


def _items_from_date(run_date: date, data_dir: Path) -> list:
    path = daily_output_path(run_date, data_dir)
    items = load_daily_items(path)
    return [item for item in items if item.processing.status == "filtered"]


def run_sync(
    *,
    run_date: date | None = None,
    data_dir: Path | None = None,
    retention_days: int = DEFAULT_RETENTION_DAYS,
    dry_run: bool = False,
) -> SyncResult:
    """Incremental push of the daily digest + rolling retention delete.

    New URLs become Notion pages (Synced = arrival date, drives the Today view);
    already-present URLs are skipped; pages older than retention_days are deleted
    (moved to Notion trash — the API offers no hard delete).
    """
    data_dir = data_dir or NEWS_DATA_DIR
    if run_date is None:
        run_date = latest_daily_date(data_dir) or date.today()
    items = _items_from_date(run_date, data_dir)

    if dry_run:
        deletable = 0
        try:
            notion = NotionNewsSync()
            if retention_days > 0:
                deletable = len(notion.list_pages_older_than(retention_days))
        except Exception:
            logger.debug("Could not count deletable Notion pages for dry run", exc_info=True)
        return SyncResult(
            candidates=len(items),
            created=0,
            skipped_existing=0,
            deleted=deletable,
            dry_run=True,
        )

    notion = NotionNewsSync()
    created, skipped = notion.push_items(items)
    deleted = notion.delete_older_than(retention_days) if retention_days > 0 else 0
    return SyncResult(
        candidates=len(items),
        created=created,
        skipped_existing=skipped,
        deleted=deleted,
        dry_run=False,
    )


def run(ctx: RunContext) -> RunResult:
    """Orchestrator step `sync`: daily digest → Notion (incremental, 30-day rolling retention)."""
    started = time.monotonic()
    result = run_sync(data_dir=ctx.data_dir, dry_run=ctx.dry_run)
    return RunResult(
        module="sync_agent",
        counts={
            "candidates": result.candidates,
            "created": result.created,
            "skipped": result.skipped_existing,
            "deleted": result.deleted,
        },
        duration_s=time.monotonic() - started,
    )


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] == "ideas":
        from agents.sync_agent.ideas_run import main as ideas_main

        return ideas_main(argv[1:])

    parser = argparse.ArgumentParser(description="Idea Angles Pipeline Notion sync (Phase 1)")
    parser.add_argument("--date", type=date.fromisoformat, help="Daily JSON date (YYYY-MM-DD)")
    parser.add_argument(
        "--retention-days",
        type=int,
        default=DEFAULT_RETENTION_DAYS,
        help=f"Delete Notion pages older than this many days (default {DEFAULT_RETENTION_DAYS}; 0 disables deletion)",
    )
    parser.add_argument("--dry-run", action="store_true", help="Preview without pushing to Notion")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )

    result = run_sync(
        run_date=args.date,
        retention_days=args.retention_days,
        dry_run=args.dry_run,
    )

    print(f"Candidates: {result.candidates}")
    if result.dry_run:
        if result.deleted:
            print(f"Would delete (older than {args.retention_days}d): {result.deleted}")
        print("Dry run — nothing pushed to Notion")
    else:
        print(f"Created: {result.created}")
        if result.skipped_existing:
            print(f"Already in Notion: {result.skipped_existing}")
        if result.deleted:
            print(f"Deleted (older than {args.retention_days}d): {result.deleted}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
