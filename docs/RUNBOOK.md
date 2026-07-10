# Runbook — which command, when

> The "how do I operate it" doc — organized by **what you want to do**, not by agent.
> For *what & why* see [VISION.md](VISION.md) · *what's coming* [WHATS-NEXT.md](WHATS-NEXT.md) · *how it's built* [ARCHITECTURE.md](ARCHITECTURE.md).

Every command below assumes you're in the project root with the venv active:

```powershell
.venv\Scripts\Activate.ps1
```

Almost every command accepts `--dry-run` (preview, writes nothing) and `-v` (verbose logs).

---

## Cheat sheet

| I want to… | Run | How often |
|------------|-----|-----------|
| Get today's news into Notion | *nothing* — GitHub Action does it every morning | automatic |
| Re-run news manually (Action failed / PC testing) | `python orchestrator.py --steps news,sync` | rarely |
| Read today's digest without Notion | `python -m agents.news_scraper.view` | optional |
| Capture an idea from my phone | *nothing* — Telegram bot on the VM does capture → angles → Notion | automatic |
| Capture + fully process an idea from my PC | `python -m agents.capture_agent.run process "idea text"` | whenever |
| Quick-capture only (no AI, no Notion yet) | `python -m agents.capture_agent.run capture "idea text"` | whenever |
| Process everything sitting in the queue | `python orchestrator.py --steps angles,ideas-push,ideas-pull` | when reviewing ideas |
| Get my Approve/Reject decisions from Notion into the local DB | `python orchestrator.py --steps ideas-pull` | when reviewing ideas |
| Bring phone captures into my local (canonical) DB | fetch + `ideas pull-remote` (see below) | ~weekly |
| See what's in the local ideas DB | `python -m agents.capture_agent.run list` | whenever |
| Check everything still works | `pytest` | after changes |

---

## Daily news (usually zero commands)

The GitHub Action (`.github/workflows/daily-news.yml`) runs every morning with your PC off: scrape → filter → push new articles to the Notion News Dashboard → delete pages older than 30 days. You just open Notion's **Today** view.

Manual equivalents, when you need them:

```powershell
# Full pipeline locally (same as the Action)
python orchestrator.py --steps news,sync

# Scraper only → data/news/YYYY-MM-DD.json
python -m agents.news_scraper.run

# Sync only (today's JSON → Notion, + 30-day retention delete)
python -m agents.sync_agent.run
python -m agents.sync_agent.run --date 2026-07-08      # a specific day's JSON
python -m agents.sync_agent.run --retention-days 60    # custom window (0 = keep everything)

# Local HTML digest (no Notion needed)
python -m agents.news_scraper.view                      # then open data/news/digest.html
```

**When to use which:** you almost never run these. Use `orchestrator --steps news,sync` if the Action failed or you want news *now*; use `view` if you want to read the digest without opening Notion.

---

## Capturing ideas

Three doors into the same pipeline (`captured → angled → synced`):

**Phone (Telegram)** — send a message to the bot. The VM handles everything; the idea appears in the Notion Idea Bank on its own. No commands.

**PC, one-shot** — when you want the idea fully processed immediately (capture → Gemini angles → Notion):

```powershell
python -m agents.capture_agent.run process "System design maps to identity building"
```

**PC, quick capture** — when you just want the thought saved (no LLM call, no Notion) and will process later:

```powershell
python -m agents.capture_agent.run capture "raw thought" --context "why it matters" --tags brand,ai
```

Quick-captured ideas sit at `captured` until you drain the queue (next section).

Useful extras:

```powershell
python -m agents.capture_agent.run list                       # recent ideas + status
python -m agents.capture_agent.run process-id <idea_id>      # process one specific captured idea
python -m agents.script_angles_agent.cli <idea_id>           # re-generate angles for one idea
```

---

## The ideas review loop (manual, human-in-the-loop by design)

Nothing on your PC runs on a schedule. When you sit down to work with ideas, run:

```powershell
python orchestrator.py --steps angles,ideas-push,ideas-pull
```

which drains the whole queue in order:

1. **angles** — every `captured` idea gets Gemini script angles + brand fit % (→ `angled`)
2. **ideas-push** — every angled-but-unsynced idea becomes a Notion Idea Bank page (→ `synced`)
3. **ideas-pull** — your Approve/Reject decisions in Notion flow back into the local DB

Then do the human part in Notion: set **Status** on the ideas. Run `--steps ideas-pull` again afterwards (or just include it next session — decisions are picked up whenever it runs).

---

## Draining phone captures into the canonical local DB (~weekly)

The VM's DB is only a capture inbox — local `data/cynthia.db` is the one true store. Two commands, run on your PC:

```powershell
gcloud compute scp <vm-user>@<vm-instance>:/path/to/repo/data/cynthia.db .\data\remote\cynthia-vm.db --zone=<zone>
python -m agents.sync_agent.run ideas pull-remote --from data\remote\cynthia-vm.db
```

*(Fill in your own VM identity — machine-specific values live in the gitignored `docs/local-notes.md`.)*

Safe to re-run anytime (already-imported ideas are skipped). Strictly one-way: nothing is ever pushed back to the VM. There's no urgency — phone captures already reach Notion without this; the drain is for keeping your canonical DB complete (future notes/memory modules read it).

---

## Maintenance & checks

```powershell
pytest                                          # test suite — run after any code change
python orchestrator.py --steps news,sync --dry-run    # preview any step without writing
git pull                                        # on the VM, after pushing changes (then restart the bot)
```

Retention needs no attention: news pages older than 30 days are deleted by every sync run (to Notion trash — empty it in the Notion UI if you ever care).

## Something's broken?

- Sync/Notion errors → [.claude/skills/sync-agent/SKILL.md](../.claude/skills/sync-agent/SKILL.md) troubleshooting table
- Scraper/feeds → [.claude/skills/news-scraper/SKILL.md](../.claude/skills/news-scraper/SKILL.md)
- Capture/pipeline → [.claude/skills/capture-agent/SKILL.md](../.claude/skills/capture-agent/SKILL.md)
- Angles/Gemini → [.claude/skills/script-angles-agent/SKILL.md](../.claude/skills/script-angles-agent/SKILL.md)
