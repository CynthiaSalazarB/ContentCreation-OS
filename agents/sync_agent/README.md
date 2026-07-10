# ContentCreation-OS sync agent (Phase 1)

Pushes today's filtered `NewsItem` rows to the Notion **News Dashboard**.

**Storage policy (rolling 30-day window):** each run pushes only *new* articles (deduped by URL against Notion itself) and deletes pages older than 30 days. Deletion moves pages to Notion trash — the public API has no hard-delete endpoint, so emptying the trash for good is a manual Notion-UI action (rarely needed; trash doesn't clutter the database). The dashboard is browsed through two filtered views on the `Synced` date:

- **Today** — filter: `Synced` is *Today* → your fresh morning feed
- **Archive** — sort: `Synced` descending → the last 30 days, with dates, for catching up on missed days

News is never written to SQLite (SQLite is reserved for ideas).

## Prerequisites

1. Notion integration connected to the News Dashboard database
2. `.env` in project root:

```env
NOTION_API_KEY=secret_...
NOTION_NEWS_DATABASE_ID=...
```

3. In Notion, create the two views above (one-time, in the Notion UI).

## Run

Full daily pipeline (scrape + incremental Notion sync + retention delete):

```powershell
python orchestrator.py --steps news,sync
```

Sync only:

```powershell
python -m agents.sync_agent.run
```

Dry run (counts candidates and deletable pages):

```powershell
python -m agents.sync_agent.run --dry-run
```

Specific date JSON:

```powershell
python -m agents.sync_agent.run --date 2026-06-16
```

Custom retention (0 disables deletion):

```powershell
python -m agents.sync_agent.run --retention-days 60
```

## Idea Bank (Phase 2b)

Separate Notion database from the News Dashboard, with these properties (one-time manual setup; connect your integration to it):

| Property | Type | Options / notes |
|----------|------|-----------------|
| Title | title | Working title from angles agent |
| Idea ID | rich_text | ContentCreation-OS UUID — required for pull sync |
| Brand fit % | number | 0–100 advisory score (not a gate) |
| Brand fit note | rich_text | One-line why |
| Lane | select | Your brand lanes (e.g. `Build`, `Create`, `Reflect`) |
| Status | select | `Inbox`, `Approved`, `Rejected`, `Edit requested` |
| Source | select | `cli_capture`, `telegram` |
| Angles | rich_text | Formatted angle summary |
| Synced | date | Last push time |

```powershell
# Push angled ideas to Notion (or: python orchestrator.py --steps ideas-push)
python -m agents.sync_agent.run ideas push

# Pull Approved/Rejected status from Notion (or: --steps ideas-pull)
python -m agents.sync_agent.run ideas pull
```

Requires `NOTION_IDEA_BANK_DATABASE_ID` in `.env`.

### Remote capture drain (GCP Telegram bot)

The VM's SQLite is a **capture inbox, never canonical** — local `data/cynthia.db` is the one true ideas store (future notes/embedding/memory modules index it). Drain the inbox whenever you like:

```powershell
# 1. Fetch a copy of the VM's DB
gcloud compute scp <vm-name>:~/ContentCreation-OS/data/cynthia.db data/remote/cynthia-vm.db

# 2. Merge it into the local DB (upsert by UUID, newer updated_at wins, idempotent)
python -m agents.sync_agent.run ideas pull-remote --from data/remote/cynthia-vm.db
```

Strictly one-way: local never pushes ideas back to the VM. Re-running is always safe.

## What persists

| Layer | Keeps history? |
|-------|----------------|
| `seen.json` | Yes — URL hashes for dedup only (~KB) |
| `data/news/YYYY-MM-DD.json` | Today only — older digest files deleted on scrape |
| Notion News Dashboard | Rolling 30 days — older pages deleted (to Notion trash) on each sync |
| SQLite `data/cynthia.db` | Ideas only — news never touches SQLite |

## Idempotency

Safe to re-run: URLs already in Notion are skipped (queried by URL property), and retention deletion only touches pages past the retention window. A page's `Synced` date is its arrival day (fallback: Notion `created_time`) — that drives both the Today view and retention.

Note: deleted pages no longer match the URL dedup query, so an article older than 30 days that is *still* in a feed could re-enter the dashboard. Locally `seen.json` prevents this; in practice RSS feeds rarely carry month-old items.
