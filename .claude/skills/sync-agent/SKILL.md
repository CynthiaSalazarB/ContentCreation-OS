---
name: sync-agent
description: Run Idea Angles Pipeline Notion sync for News Dashboard and Idea Bank. Use when pushing news or ideas to Notion, fixing sync errors, or configuring NOTION_API_KEY and database IDs.
---

# Sync Agent (Phase 1 + 2b)

## News Dashboard (Phase 1)

## Prerequisites

- News Dashboard database exists in Notion
- Integration connected to that database
- `.env` in project root (see `.env.example`)

## Commands

```powershell
.venv\Scripts\Activate.ps1

# Full local pipeline (today's JSON → incremental Notion push + 30-day delete)
python orchestrator.py --steps news,sync

# Sync only
python -m agents.sync_agent.run

# Dry run (shows candidate count + how many pages the 30-day retention would delete)
python -m agents.sync_agent.run --dry-run

# Custom retention window (0 disables deletion)
python -m agents.sync_agent.run --retention-days 60
```

## Idea Bank (Phase 2b)

Separate database — schema in [agents/sync_agent/README.md](../../agents/sync_agent/README.md).

```powershell
python -m agents.sync_agent.run ideas push
python -m agents.sync_agent.run ideas pull
python -m agents.sync_agent.run ideas push --dry-run

# Drain GCP Telegram-bot captures into the canonical local DB (one-way, idempotent)
gcloud compute scp <vm-name>:~/idea-angles-pipeline/data/cynthia.db data/remote/cynthia-vm.db
python -m agents.sync_agent.run ideas pull-remote --from data/remote/cynthia-vm.db
```

Requires `NOTION_IDEA_BANK_DATABASE_ID` in `.env`.

## Storage policy

- **Notion = rolling 30-day news window** — incremental push deduped by URL; pages older than 30 days deleted each sync (moved to Notion trash — the API has no hard-delete endpoint; empty trash in the Notion UI if desired). "Today" and "Archive" are filtered Notion views on the `Synced` date.
- **Local JSON is today-only** — older digest files pruned on scrape
- **`seen.json`** kept for dedup (URL hashes, not full articles)
- **SQLite** not used for daily news (ideas only)

## GitHub Actions

Workflow: `.github/workflows/daily-news.yml`

Required repo secrets:
- `NOTION_API_KEY`
- `NOTION_NEWS_DATABASE_ID`

## Notion property map

| Notion | NewsItem field |
|--------|----------------|
| Title | content.title |
| URL | content.url |
| Source | source.name |
| Category | classification.category |
| Score | classification.relevance_score |
| Published | content.published_at |
| Status | processing.status |
| Synced | sync timestamp |

## Troubleshooting

- **401 / invalid token**: use the **Internal Integration Token** from [notion.so/my-integrations](https://www.notion.so/my-integrations) — starts with `secret_` or `ntn_`. MCP OAuth does not replace this for Python sync.
- **401 / unauthorized**: integration not connected to News Dashboard
- **No data sources found**: set `NOTION_NEWS_DATA_SOURCE_ID` in `.env` (from database URL or MCP create response)
- **Select option missing**: add feed name to Source select in Notion, or match `config/news_sources.yaml` feed names
- **Empty dashboard after sync**: scraper had 0 kept items today — expected if no new relevant news

## Related

- [agents/sync_agent/README.md](../../agents/sync_agent/README.md)
- [docs/ARCHITECTURE.md](../../docs/ARCHITECTURE.md) — Phase 1 design
