# Capture agent (Phase 2a/2b)

Frictionless raw idea inbox — every capture saved locally in SQLite.

## Run

```powershell
# Raw capture only (no LLM)
python -m agents.capture_agent.run capture "What confused me about Docker today"
python -m agents.capture_agent.run capture "Modular beats microservices" --context "system design class" --tags docker,learning
python -m agents.capture_agent.run list

# Full pipeline: capture → angles → Notion Idea Bank
python -m agents.capture_agent.run process "Docker boundaries finally clicked"
python -m agents.capture_agent.run process-id <idea-uuid> --no-notion
```

## Storage

- Table: `ideas` in `data/cynthia.db`
- **process** → angles generated → Notion Idea Bank (unless `--no-notion`)
- Human approval happens in Notion **Status**

## Env

- `GEMINI_API_KEY` or `GOOGLE_API_KEY`
- `NOTION_IDEA_BANK_DATABASE_ID`

## Related

- `config/personal_brand.md` — your brand definition (gitignored; copy `config/personal_brand.example.md`)
- [`agents/sync_agent/README.md`](../sync_agent/README.md) — Idea Bank database schema + push/pull
