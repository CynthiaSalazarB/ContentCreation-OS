# CLAUDE.md — Idea Angles Pipeline

A local-first, modular, human-in-the-loop Python pipeline: a raw idea goes in, on-brand script angles come back in Notion.

## System Context & Philosophy

- **Human-in-the-loop** — AI scores, tags, and suggests angles; it never auto-publishes, auto-approves, or makes irreversible decisions. Brand fit % is advisory only; the human **Status** in Notion is the only gate.
- **Local-first** — Python runs on the user's machine; the local store (SQLite/JSON) is canonical. Notion is a human review dashboard, never the source of truth.
- **Modular, loosely coupled** — independent modules in `agents/`, talking only through shared `core/storage`, never importing each other directly.
- **Progressive complexity** — JSON before SQLite, rules before LLM, one module at a time.
- **Data policy — rolling vs. persistent**: daily news is *short-lived* (today-only JSON locally, never written to SQLite; Notion News Dashboard keeps a **rolling 30-day window** — incremental push deduped by URL, pages older than 30 days deleted on each sync (moved to Notion trash; the API has no hard delete); "Today" and "Archive" are filtered Notion views on the `Synced` date). Captured ideas are *persistent* (SQLite `data/cynthia.db`, append-only, survive indefinitely, drive the angles → Notion Idea Bank pipeline).

## Living Documentation (read on demand — do not summarize from memory)

- **[docs/VISION.md](docs/VISION.md)** — canonical source for *what & why*: philosophy, principles, non-goals. Changes rarely.
- **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)** — canonical source for *how*: module inventory, data schemas, folder structure, orchestrator contract.
- **[docs/RUNBOOK.md](docs/RUNBOOK.md)** — canonical source for *operating it*: which command to run for which task, what's automatic vs. manual. Update it whenever a CLI command or automation changes.
- **[docs/WHATS-NEXT.md](docs/WHATS-NEXT.md)** — public roadmap: what's shipped, what's coming.

**Private, local-only docs** (gitignored in the public repo — they exist on the owner's machine but not on GitHub; skip them if absent): `docs/ROADMAP.md` (phase status board, decisions log, backlog — check it before assuming what phase/feature is active, when present), `docs/GLOSSARY.md`, `docs/plans/` (historical per-phase plans), `docs/brand/` + `config/personal_brand.md` (personal brand content), `docs/local-notes.md` (machine-specific values).

Always re-read the relevant doc rather than relying on a prior summary — these files are living and updated per phase.

## Essential Commands

```powershell
.venv\Scripts\Activate.ps1

# Orchestrator (steps: news, sync, angles, ideas-push, ideas-pull)
python orchestrator.py --steps news,sync
python orchestrator.py --steps angles,ideas-push,ideas-pull
python orchestrator.py --steps news,sync --dry-run

# Individual agents
python -m agents.news_scraper.run [--dry-run | -v]
python -m agents.news_scraper.view                 # build HTML digest
python -m agents.sync_agent.run [--dry-run] [--retention-days N]   # incremental + 30-day delete
python -m agents.sync_agent.run ideas push|pull [--dry-run]
python -m agents.sync_agent.run ideas pull-remote --from data/remote/cynthia-vm.db [--dry-run]  # drain VM captures into local DB
python -m agents.capture_agent.run capture "thought" [--context "..."] [--tags a,b] [--link <uuid>]
python -m agents.capture_agent.run list
python -m agents.capture_agent.run process "idea text"        # capture + angles + Notion
python -m agents.capture_agent.run process-id <idea_id> [--no-notion]
python -m agents.capture_agent.telegram_run                   # Telegram capture bot (long-polling)
python -m agents.script_angles_agent.cli <idea_id>

# Tests
pytest
```

## Code Style & Architecture Constraints

- **Pydantic v2**, `from __future__ import annotations`, `str | None` unions, `Literal[...]` for closed enums, `Field(default_factory=...)` for mutable/derived defaults (uuid4 ids, UTC `datetime.now(timezone.utc)`).
- Every top-level entity (`NewsItem`, `Idea`) extends the same **shared envelope**: `id`, `type` (Literal tag), `created_at`, `updated_at`, `source`. Persistent entities (`Idea`) also carry a `sync` block (`notion_page_id`, `last_synced_at`); disposable entities (`NewsItem`) deliberately omit it — see `core/models/news_item.py` and `core/models/idea.py`.
- Nest related fields into sub-models (`Source`, `Content`, `Classification`, `Processing`, `human`, `brand_fit`, etc.) rather than flattening — mirrors the schemas documented in ARCHITECTURE.md.
- Give models a `touch()` method to bump `updated_at`; never mutate timestamps inline.
- **Layering rules** (blackboard pattern):
  - `core/` is the foundation — it must never import from `agents/` or `pipelines/`.
  - **Modules never import each other** — only `core/` (`core/models`, `core/storage`, `core/llm`, `core/paths`). Cross-module handoffs happen through shared storage, keyed on `processing.status` (`captured → angled → synced`).
  - `pipelines/` and `orchestrator.py` are the top orchestration layer — the only code allowed to import multiple agents.
  - **Entry-point exception**: CLI command handlers and the Telegram bot may import `pipelines/` (lazily) to run one-shot end-to-end flows; module *library* functions may not.
- **Module contract**: every orchestrator step is a module-level `run(ctx: RunContext) -> RunResult` (see `core/models/run.py`) and must be **idempotent** — safe to re-run without corrupting data. Register new steps in `STEP_REGISTRY` in `orchestrator.py`.
- SQLite access goes through `core/storage/sqlite_store.py` (`SqliteStore`) — **ideas only** (daily news never touches SQLite): payload stored as JSON column, validated back into the Pydantic model via `model_validate(json.loads(...))`. Use `INSERT ... ON CONFLICT DO UPDATE` upserts, not delete+insert. Daily news JSON goes through `core/storage/json_store.py`.
- **Notion MCP is development-only** (designing DB schema/views from chat). Production/unattended sync always uses the Python `notion-client` API via `sync_agent` — keep MCP servers out of the runtime pipeline. Shared Notion plumbing lives in `agents/sync_agent/notion_common.py`.
- Scrapers (deterministic, no LLM — e.g. `news_scraper`) vs. agents (LLM/decision logic — e.g. `script_angles_agent`) is a meaningful naming distinction; keep it consistent for new modules.
- Avoid over-engineering: heavier tooling (Docker, FireCrawl, vector DB, agent frameworks) is adopted only when a phase hits real pain a simpler tool can't solve (see ARCHITECTURE.md "Anti Over-Engineering Principles").

## Reference Router — Localized Skills

When debugging or extending a specific module, read its skill file first:

- `.claude/skills/news-scraper/SKILL.md`
- `.claude/skills/sync-agent/SKILL.md`
- `.claude/skills/capture-agent/SKILL.md`
- `.claude/skills/script-angles-agent/SKILL.md`
