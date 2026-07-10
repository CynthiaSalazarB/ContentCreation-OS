from __future__ import annotations

import argparse
import logging
import sys
from dataclasses import dataclass
from pathlib import Path

from core.models.idea import Idea, IdeaContent
from core.models.news_item import Source
from core.storage.sqlite_store import SqliteStore

logger = logging.getLogger(__name__)


@dataclass
class CaptureResult:
    idea: Idea
    created: bool


def _parse_tags(raw: str | None) -> list[str]:
    if not raw:
        return []
    return [tag.strip().lower() for tag in raw.split(",") if tag.strip()]


def capture_idea(
    text: str,
    *,
    context: str | None = None,
    tags: list[str] | None = None,
    source: Source | None = None,
    related_idea_ids: list[str] | None = None,
    db_path: Path | None = None,
) -> CaptureResult:
    text = text.strip()
    if not text:
        raise ValueError("Idea text cannot be empty")

    idea = Idea(
        source=source or Source(type="manual", name="cli_capture", url=None),
        content=IdeaContent(
            raw_text=text,
            context=context.strip() if context else None,
            tags=tags or [],
        ),
    )
    if related_idea_ids:
        idea.links.related_idea_ids = related_idea_ids

    store = SqliteStore(db_path)
    store.upsert_idea(idea)
    logger.info("Captured idea %s", idea.id)
    return CaptureResult(idea=idea, created=True)


def list_recent(*, limit: int = 20, db_path: Path | None = None) -> list[Idea]:
    return SqliteStore(db_path).list_ideas(limit=limit)


def _print_pipeline_result(result) -> int:
    idea = result.idea
    print(f"Idea: {idea.id}")
    if idea.content.title:
        print(f"Title: {idea.content.title}")
    if idea.brand_fit.lane:
        print(f"Lane: {idea.brand_fit.lane}")
    if idea.brand_fit.fit is not None:
        print(f"Brand fit: {round(idea.brand_fit.fit * 100)}%")
    if idea.brand_fit.note:
        print(f"Note: {idea.brand_fit.note}")
    for index, angle in enumerate(idea.script_angles, start=1):
        print(f"\nAngle {index} [{angle.framework}]: {angle.hook}")
        print(f"  {angle.angle}")
    if result.synced_to_notion:
        print(f"\nNotion Idea Bank: {result.notion_page_id}")
        print("Status: Inbox — approve or reject in Notion.")
    else:
        print("\nNot synced to Notion (dry-run or --no-notion).")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="ContentCreation-OS capture agent — frictionless raw idea inbox (Phase 2a)"
    )
    subparsers = parser.add_subparsers(dest="command")

    capture_parser = subparsers.add_parser("capture", help="Save a raw idea to SQLite")
    capture_parser.add_argument("text", help="One-line idea or reaction")
    capture_parser.add_argument("--context", help="Optional context (class, project, mood)")
    capture_parser.add_argument("--tags", help="Comma-separated tags")
    capture_parser.add_argument(
        "--link",
        action="append",
        dest="related_idea_ids",
        metavar="IDEA_ID",
        help="Related idea UUID (repeatable)",
    )

    list_parser = subparsers.add_parser("list", help="Show recent captured ideas")
    list_parser.add_argument("--limit", type=int, default=20)

    process_parser = subparsers.add_parser(
        "process",
        help="Capture + on-brand angles → Notion Idea Bank (Inbox)",
    )
    process_parser.add_argument("text", help="One-line idea or reaction")
    process_parser.add_argument("--context", help="Optional context")
    process_parser.add_argument("--tags", help="Comma-separated tags")
    process_parser.add_argument(
        "--no-notion",
        action="store_true",
        help="Skip Notion Idea Bank sync",
    )
    process_parser.add_argument("--dry-run", action="store_true")

    process_id_parser = subparsers.add_parser(
        "process-id",
        help="Run angles on an existing capture and sync to Idea Bank",
    )
    process_id_parser.add_argument("idea_id")
    process_id_parser.add_argument("--no-notion", action="store_true")
    process_id_parser.add_argument("--dry-run", action="store_true")

    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.WARNING,
        format="%(levelname)s %(name)s: %(message)s",
    )

    if args.command == "list":
        ideas = list_recent(limit=args.limit)
        if not ideas:
            print("No ideas captured yet.")
            return 0
        for idea in ideas:
            preview = idea.content.raw_text.replace("\n", " ")
            if len(preview) > 80:
                preview = preview[:77] + "..."
            tags = f" [{', '.join(idea.content.tags)}]" if idea.content.tags else ""
            status = ""
            if idea.processing.status != "captured":
                status = f" ({idea.processing.status})"
            print(f"{idea.id}  {preview}{tags}{status}")
        return 0

    if args.command == "process":
        # Entry-point exception: CLI commands may compose via the top-level
        # pipelines package; library functions in this module may not.
        from pipelines.idea_pipeline import capture_and_process

        try:
            result = capture_and_process(
                args.text,
                context=args.context,
                tags=_parse_tags(args.tags),
                sync_notion=not args.no_notion,
                dry_run=args.dry_run,
            )
        except ValueError as exc:
            print(exc, file=sys.stderr)
            return 1
        return _print_pipeline_result(result)

    if args.command == "process-id":
        from pipelines.idea_pipeline import process_idea_id

        try:
            result = process_idea_id(
                args.idea_id,
                sync_notion=not args.no_notion,
                dry_run=args.dry_run,
            )
        except ValueError as exc:
            print(exc, file=sys.stderr)
            return 1
        return _print_pipeline_result(result)

    if args.command != "capture":
        parser.print_help()
        return 1

    try:
        result = capture_idea(
            args.text,
            context=args.context,
            tags=_parse_tags(args.tags),
            related_idea_ids=args.related_idea_ids,
        )
    except ValueError as exc:
        print(exc, file=sys.stderr)
        return 1

    idea = result.idea
    print(f"Captured: {idea.id}")
    print(f"Text: {idea.content.raw_text}")
    if idea.content.context:
        print(f"Context: {idea.content.context}")
    if idea.content.tags:
        print(f"Tags: {', '.join(idea.content.tags)}")
    if idea.links.related_idea_ids:
        print(f"Linked ideas: {', '.join(idea.links.related_idea_ids)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
