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




## Next: maintenance, not a new phase

The pipeline covers the job it was scoped to do. Expect small improvements to angle quality, dependency upkeep, and fixes — not new subsystems.

- **Angle quality** — tighten the hook seed so it stays anchored to the raw capture instead of drifting.
- **News → angles helper** — run a news item through the brand filter, the one Phase 2a item still open.



## Phase 3 moved out of this repo

The earlier plan put a knowledge and memory layer here: notes ingestion, a connection-finder across notes and ideas, embeddings, and a script-writer agent. That scope now lives in the surrounding personal system instead. Short version of why:

- **Wrong input.** A connection-finder reads a personal knowledge base, not this pipeline's data. What a system reads decides where it belongs.
- **No real pain yet.** The corpus is a few thousand lines of markdown that plain text search handles instantly. Embeddings would be infrastructure bought ahead of the need.
- **The script-writer is cancelled, not deferred.** A script worth filming comes out of an interview with the person whose story it is. See [VISION.md](VISION.md).

Other parts of the workflow ship as their own repos rather than accumulating here, so each piece stays explainable on its own terms.



## Guiding rules

- **Human-in-the-loop** — nothing publishes or decides without human approval.
- **Anti-over-engineering** — complexity is added when a phase actually needs it, not before. 
- Ideas graduate from a private backlog only when they survive the "worth building, or scope creep?" check.
