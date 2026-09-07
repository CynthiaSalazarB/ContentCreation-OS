"""Idea Angles Pipeline orchestrator — knows execution order only, no business logic.

Every step is a module-level `run(ctx: RunContext) -> RunResult`. Modules hand
off work through shared storage (daily JSON, SQLite idea statuses), never by
calling each other. Adding a module = one entry in STEP_REGISTRY.
"""

from __future__ import annotations

import argparse
import logging
import sys
import time
from typing import Callable

from core.models.run import RunContext, RunResult


def _news(ctx: RunContext) -> RunResult:
    from agents.news_scraper.run import run

    return run(ctx)


def _sync(ctx: RunContext) -> RunResult:
    from agents.sync_agent.run import run

    return run(ctx)


def _angles(ctx: RunContext) -> RunResult:
    from agents.script_angles_agent.run import run

    return run(ctx)


def _ideas_push(ctx: RunContext) -> RunResult:
    from agents.sync_agent.ideas_run import run_push

    return run_push(ctx)


def _ideas_pull(ctx: RunContext) -> RunResult:
    from agents.sync_agent.ideas_run import run_pull

    return run_pull(ctx)


STEP_REGISTRY: dict[str, Callable[[RunContext], RunResult]] = {
    "news": _news,
    "sync": _sync,
    "angles": _angles,
    "ideas-push": _ideas_push,
    "ideas-pull": _ideas_pull,
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Idea Angles Pipeline orchestrator")
    parser.add_argument(
        "--steps",
        required=True,
        help=f"Comma-separated steps: {','.join(STEP_REGISTRY)}",
    )
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing/pushing")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args(argv)

    steps = [step.strip() for step in args.steps.split(",") if step.strip()]
    unknown = [step for step in steps if step not in STEP_REGISTRY]
    if unknown:
        print(
            f"Unknown steps: {', '.join(unknown)}. Available: {', '.join(STEP_REGISTRY)}",
            file=sys.stderr,
        )
        return 1

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )

    ctx = RunContext(dry_run=args.dry_run, verbose=args.verbose)
    failed = False
    for step in steps:
        started = time.monotonic()
        try:
            result = STEP_REGISTRY[step](ctx)
        except Exception as exc:
            logging.getLogger("orchestrator").exception("Step %s failed", step)
            result = RunResult(
                module=step,
                ok=False,
                errors=[str(exc)],
                duration_s=time.monotonic() - started,
            )
        print(result.summary())
        if not result.ok:
            failed = True

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
