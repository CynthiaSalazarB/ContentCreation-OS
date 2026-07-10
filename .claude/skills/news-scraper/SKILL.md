---
name: news-scraper
description: Runs and extends the ContentCreation-OS RSS news scraper. Use when adding RSS feeds, tuning keyword filters, running the daily digest, or debugging news JSON output.
---

# News Scraper

## Run

```powershell
cd ContentCreation-OS
python -m agents.news_scraper.run
python -m agents.news_scraper.run --dry-run
python -m agents.news_scraper.run -v

# HTML digest for browser review
python -m agents.news_scraper.view
```

Open `data/news/digest.html` in a browser after generating.

## Add a feed

Edit [config/news_sources.yaml](../../config/news_sources.yaml):

```yaml
  - name: my-feed
    url: https://example.com/feed/
    category: ai_tech   # or macro
    tier: journalism
    enabled: true
```

## Tune filters

Edit `filters.ai_tech` or `filters.macro` in the same config file. Adjust `settings.min_relevance_score` if too much noise gets through.

**Published today only** (default on): `settings.published_on_run_date_only: true` + `digest_timezone: America/New_York`. Only articles whose RSS `published_at` falls on the digest date are kept.

## Output locations

- Daily digest: `data/news/YYYY-MM-DD.json`
- HTML viewer: `data/news/digest.html` (run `python -m agents.news_scraper.view`)
- Dedup index: `data/news/seen.json`

## Schema

- Model: [core/models/news_item.py](../../core/models/news_item.py)
- Full spec: [docs/ARCHITECTURE.md](../../docs/ARCHITECTURE.md)

## Do not (Phase 0)

- Add Notion sync or SQLite here
- Add LLM filtering without user request (Phase 0b)
