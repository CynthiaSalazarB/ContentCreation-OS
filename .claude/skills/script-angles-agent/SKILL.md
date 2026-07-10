---
name: script-angles-agent
description: Generate on-brand script angles for a captured idea via Gemini. Use when debugging angle output or re-running angles on an existing idea.
---

# Script Angles Agent (Phase 2)

Generates 2–3 short-form content angles using `config/personal_brand.md`. Uses Bridge framework for off-brand captures.

## Prerequisites

- `GOOGLE_API_KEY` or `GEMINI_API_KEY` in `.env`

## Commands

```powershell
python -m agents.script_angles_agent.cli <idea_id>
```

## Full pipeline (preferred)

```powershell
python -m agents.capture_agent.run process "your idea"
```

Angles sync to Notion **Angles** property on Idea Bank push.
