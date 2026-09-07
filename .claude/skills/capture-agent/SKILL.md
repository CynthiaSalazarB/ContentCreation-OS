---
name: capture-agent
description: Capture and process ideas in Idea Angles Pipeline. Use for CLI capture, process pipeline (angles + Notion Idea Bank), or listing recent ideas.
---

# Capture Agent (Phase 2)

## Commands

```powershell
.venv\Scripts\Activate.ps1

# Raw capture (SQLite only, no LLM)
python -m agents.capture_agent.run capture "one line after class"
python -m agents.capture_agent.run capture "thought" --context "AWS week 3" --tags aws,learning
python -m agents.capture_agent.run list

# Full pipeline → angles → Notion Idea Bank
python -m agents.capture_agent.run process "Docker finally clicked for me"
python -m agents.capture_agent.run process-id <idea-uuid> --no-notion
```

## Env

- `GOOGLE_API_KEY` or `GEMINI_API_KEY`
- `NOTION_IDEA_BANK_DATABASE_ID`

## Related

- [agents/capture_agent/README.md](../../agents/capture_agent/README.md)
- [agents/sync_agent/README.md](../../agents/sync_agent/README.md) — Idea Bank schema
