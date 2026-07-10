from __future__ import annotations

import argparse
import logging
import sys
import time
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from agents.news_scraper.config_loader import load_config
from agents.news_scraper.date_filter import filter_published_on_date
from agents.news_scraper.dedup import dedup_items, load_seen, save_seen
from agents.news_scraper.fetcher import fetch_all
from agents.news_scraper.filter import filter_items
from core.models.run import RunContext, RunResult
from core.paths import NEWS_DATA_DIR
from core.storage.json_store import prune_old_daily_json, write_daily_items

logger = logging.getLogger(__name__)


@dataclass
class PipelineResult:
    fetched: int
    new_after_dedup: int
    date_skipped: int
    kept: int
    discarded: int
    output_path: Path | None
    dry_run: bool


def digest_run_date(
    run_date: date | None = None,
    config_path: Path | None = None,
) -> date:
    """Calendar date for today's digest file (respects digest_timezone when configured)."""
    if run_date is not None:
        return run_date
    config = load_config(config_path)
    if config.published_on_run_date_only:
        return datetime.now(ZoneInfo(config.digest_timezone)).date()
    return date.today()


def run_pipeline(
    *,
    run_date: date | None = None,
    data_dir: Path | None = None,
    config_path: Path | None = None,
    dry_run: bool = False,
) -> PipelineResult:
    data_dir = data_dir or NEWS_DATA_DIR
    config = load_config(config_path)
    run_date = digest_run_date(run_date, config_path)

    fetched_items = fetch_all(config)
    seen = load_seen(data_dir)
    new_items, new_hashes = dedup_items(fetched_items, seen)

    date_skipped = 0
    candidates = new_items
    if config.published_on_run_date_only:
        candidates, skipped_by_date = filter_published_on_date(
            new_items, run_date, config.digest_timezone
        )
        date_skipped = len(skipped_by_date)

    kept, discarded = filter_items(candidates, config)

    output_path: Path | None = None
    if not dry_run:
        prune_old_daily_json(data_dir, run_date)
        if kept:
            output_path = write_daily_items(kept, run_date, data_dir, merge=False)
        if new_hashes:
            seen.update(new_hashes)
            save_seen(seen, data_dir)

    return PipelineResult(
        fetched=len(fetched_items),
        new_after_dedup=len(new_items),
        date_skipped=date_skipped,
        kept=len(kept),
        discarded=len(discarded),
        output_path=output_path,
        dry_run=dry_run,
    )


def run(ctx: RunContext) -> RunResult:
    """Orchestrator step `news`: RSS fetch → dedup → filter → daily JSON."""
    started = time.monotonic()
    result = run_pipeline(
        data_dir=ctx.data_dir,
        config_path=ctx.config_path,
        dry_run=ctx.dry_run,
    )
    return RunResult(
        module="news_scraper",
        counts={
            "fetched": result.fetched,
            "new": result.new_after_dedup,
            "kept": result.kept,
            "discarded": result.discarded,
        },
        duration_s=time.monotonic() - started,
    )


def _parse_date(value: str) -> date:
    return date.fromisoformat(value)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="ContentCreation-OS news scraper (Phase 0)")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing files")
    parser.add_argument("--date", type=_parse_date, help="Output date file (YYYY-MM-DD)")
    parser.add_argument("--config", type=Path, help="Path to news_sources.yaml")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose logging")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )

    result = run_pipeline(
        run_date=args.date,
        config_path=args.config,
        dry_run=args.dry_run,
    )

    print(f"Fetched: {result.fetched}")
    print(f"New (after dedup): {result.new_after_dedup}")
    if result.date_skipped:
        print(f"Skipped (not published today): {result.date_skipped}")
    print(f"Kept: {result.kept}")
    print(f"Discarded: {result.discarded}")
    if result.dry_run:
        print("Dry run — no files written")
    elif result.output_path:
        print(f"Written: {result.output_path}")
    elif result.kept == 0:
        print("No new items to write")

    return 0


if __name__ == "__main__":
    sys.exit(main())
