from __future__ import annotations

import argparse
import logging
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from agents.sync_agent.notion_ideas_sync import NotionIdeaSync
from core.models.run import RunContext, RunResult
from core.storage.sqlite_store import SqliteStore

logger = logging.getLogger(__name__)


def push_ideas(*, db_path: Path | None = None, dry_run: bool = False) -> tuple[int, int]:
    store = SqliteStore(db_path)
    candidates = store.list_ideas_unsynced_angled()
    if dry_run:
        return len(candidates), 0

    notion = NotionIdeaSync()
    created = 0
    updated = 0
    for idea in candidates:
        page_id, was_created = notion.sync_idea(idea)
        idea.sync.notion_page_id = page_id
        idea.sync.last_synced_at = datetime.now(timezone.utc)
        idea.processing.status = "synced"
        idea.touch()
        store.upsert_idea(idea)
        if was_created:
            created += 1
        else:
            updated += 1
        logger.info("Synced idea %s -> %s", idea.id, page_id)
    return len(candidates), created + updated


def pull_ideas(*, db_path: Path | None = None, dry_run: bool = False) -> int:
    store = SqliteStore(db_path)
    notion = NotionIdeaSync()
    updates = notion.pull_human_decisions()
    changed = 0
    for idea_id, decision in updates:
        idea = store.get_idea(idea_id)
        if idea is None:
            continue
        if idea.human.decision == decision:
            continue
        if dry_run:
            changed += 1
            continue
        idea.human.decision = decision
        idea.human.decided_at = datetime.now(timezone.utc)
        idea.touch()
        store.upsert_idea(idea)
        changed += 1
        logger.info("Updated idea %s decision -> %s", idea_id, decision)
    return changed


def pull_remote_ideas(
    source_db: Path, *, db_path: Path | None = None, dry_run: bool = False
) -> tuple[int, int, int]:
    """Drain a fetched copy of the remote (VM) ideas DB into the canonical local DB.

    One-way by design: the VM is a capture inbox, local data/cynthia.db is canonical.
    CLI-only (not an orchestrator step) — fetching the file needs gcloud/ssh auth.
    Returns (imported, updated, skipped).
    """
    if not source_db.is_file():
        raise FileNotFoundError(
            f"Remote DB copy not found: {source_db}. Fetch it first, e.g. "
            "gcloud compute scp <vm>:~/idea-angles-pipeline/data/cynthia.db data/remote/cynthia-vm.db"
        )
    store = SqliteStore(db_path)
    return store.merge_ideas_from(SqliteStore(source_db), dry_run=dry_run)


def run_push(ctx: RunContext) -> RunResult:
    """Orchestrator step `ideas-push`: angled ideas → Notion Idea Bank (→ `synced`)."""
    started = time.monotonic()
    candidates, synced = push_ideas(db_path=ctx.db_path, dry_run=ctx.dry_run)
    return RunResult(
        module="sync_agent.ideas_push",
        counts={"candidates": candidates, "synced": synced},
        duration_s=time.monotonic() - started,
    )


def run_pull(ctx: RunContext) -> RunResult:
    """Orchestrator step `ideas-pull`: human Approve/Reject in Notion → SQLite."""
    started = time.monotonic()
    changed = pull_ideas(db_path=ctx.db_path, dry_run=ctx.dry_run)
    return RunResult(
        module="sync_agent.ideas_pull",
        counts={"changed": changed},
        duration_s=time.monotonic() - started,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Idea Angles Pipeline Idea Bank Notion sync (Phase 2b)")
    sub = parser.add_subparsers(dest="command", required=True)
    push_parser = sub.add_parser("push", help="Push angled ideas to Notion Idea Bank")
    push_parser.add_argument("--dry-run", action="store_true")
    sub.add_parser("pull", help="Pull Approved/Rejected status from Notion to SQLite")
    remote_parser = sub.add_parser(
        "pull-remote", help="Merge a fetched copy of the VM capture DB into the local DB"
    )
    remote_parser.add_argument(
        "--from",
        dest="source_db",
        type=Path,
        required=True,
        help="Path to the fetched remote cynthia.db copy",
    )
    remote_parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )

    if args.command == "push":
        candidates, synced = push_ideas(dry_run=args.dry_run)
        print(f"Candidates: {candidates}")
        if args.dry_run:
            print("Dry run — nothing pushed")
        else:
            print(f"Synced to Notion: {synced}")
        return 0

    if args.command == "pull":
        changed = pull_ideas()
        print(f"Updated from Notion: {changed}")
        return 0

    if args.command == "pull-remote":
        try:
            imported, updated, skipped = pull_remote_ideas(args.source_db, dry_run=args.dry_run)
        except FileNotFoundError as exc:
            print(exc)
            return 1
        prefix = "Would import" if args.dry_run else "Imported"
        print(f"{prefix}: {imported} new, {updated} updated ({skipped} already up to date)")
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main())
