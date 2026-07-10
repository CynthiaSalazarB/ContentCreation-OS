# What's Next

> The public "where is this going" doc. For what's already built, see [ARCHITECTURE.md](ARCHITECTURE.md); for how to run it, see [RUNBOOK.md](RUNBOOK.md).

## Shipped so far


| Phase | What it added                                                                       |
| ----- | ----------------------------------------------------------------------------------- |
| 0     | RSS news scraper — fetch → dedup → keyword filter → daily JSON digest               |
| 1     | Notion News Dashboard + daily GitHub Action (rolling 30-day window)                 |
| 2a    | Brand config + Gemini script-angles agent + CLI idea capture                        |
| 2b    | Notion Idea Bank pipeline with advisory brand-fit % (human Status is the only gate) |
| 2c    | Telegram capture bot on a GCP VM + one-way drain into the canonical local DB        |




## Next: the knowledge & memory layer (Phase 3 — in design)

> This phase is still being designed. The items below are the current candidates, not commitments — scope may change, and some pieces may end up as a companion system rather than inside this repo.

The captured-ideas store was deliberately designed as one canonical local SQLite DB — the substrate for this phase:

- **Notes ingestion** — connect a static knowledge vault (Obsidian: theory, concepts, books) and dynamic notes (Notion: fleeting thoughts from phone/laptop) to the system.
- **Connection-finder agent** — reads notes + captured ideas and surfaces patterns, repetitions, and links between them ("you've circled this theme four times") as fuel for content. Likely the first real use for vector embeddings in the stack.
- **Memory** — the orchestrator gets long-term context: what was already made, what resonated, what keeps coming back.
- **Market/trend research agent** — what's moving in the niche and what admired creators are publishing, as extra fuel for angle quality (the original Phase 3 sketch in [ARCHITECTURE.md](ARCHITECTURE.md)).



## After that (exploring)

- **Script-writer agent** — turns an approved angle into a platform-specific script in the author's voice, driven by the brand config and voice examples.



## Guiding rules

- **Human-in-the-loop** — nothing publishes or decides without human approval.
- **Anti-over-engineering** — complexity is added when a phase actually needs it, not before. 
- Ideas graduate from a private backlog only when they survive the "worth building, or scope creep?" check.

