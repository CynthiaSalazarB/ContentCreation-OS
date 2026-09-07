from __future__ import annotations

import argparse
import logging
import sys

from agents.script_angles_agent.run import angles_for_idea


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Idea Angles Pipeline script angles agent (Phase 2a/2b)")
    parser.add_argument("idea_id", help="Idea UUID")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )

    result = angles_for_idea(args.idea_id)
    idea = result.idea
    if idea.content.title:
        print(f"Title: {idea.content.title}")
    for index, angle in enumerate(idea.script_angles, start=1):
        print(f"\n--- Angle {index} [{angle.framework}] ---")
        print(f"Hook: {angle.hook}")
        print(f"Angle: {angle.angle}")
        if angle.tone:
            print(f"Tone: {angle.tone}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
