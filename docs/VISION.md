# Idea Angles Pipeline — Vision (Source of Truth)

> The stable "what & why." Changes rarely. For *how it's built* see [ARCHITECTURE.md](ARCHITECTURE.md); for *what's coming* see [WHATS-NEXT.md](WHATS-NEXT.md).

---

## One-liner

A local-first, modular pipeline that helps me capture ideas and turn the right ones into on-brand content angles. **AI curates, I decide.**

---

## The deeper why

I keep things that seem separate and make them whole. This pipeline is that philosophy as software: independent modules integrated into one coherent system, the same way I'm integrating my logical and creative selves into one person, in public.

So this project is two things at once:

1. A **real tool** for the job it's good at: unsticking an idea I want to post but can't find my own angle into.
2. A **portfolio piece** that proves how I think (systems, architecture, boundaries, and when *not* to write code).

---



## Who it's for

- **Primarily me.** Optimize for simplicity and one person's use.
- Designed cleanly enough that it *could* work for others: swap in your own brand config (`config/personal_brand.example.md`) and feeds, and the same engine runs on your voice instead of mine. An invitation to read and fork, not a product with a support inbox.

---



## What it does

- **Awareness.** A daily dashboard of AI + world news (a living feed, not an archive).
- **Content radar.** Scores ideas against a brand definition and flags what's worth a video, with angles.
- **Capture.** Quick inbox for raw thoughts from anywhere (CLI or Telegram).
- **Curate.** AI scores and suggests; the human approves, rejects, or reframes.
- **Connect.** Modules feed each other through shared storage, orchestrated into one flow.



## What it doesn't do, and why

This is the automated half of a larger content workflow: the part that runs without me. Three capabilities are deliberately outside it.

- **Writing the script.** A script worth filming comes out of an interview, not an angle. Generating it produces a fluent, empty draft.
- **Hooks and creator teardowns.** Same reason. They run as conversational playbooks against a private voice profile, not as code.
- **Notes, memory, connection-finding.** Its input is a personal knowledge base, not this pipeline's data. What a system reads decides where it lives.

---



## Core principles

- **Human-in-the-loop.** AI suggests; I make the final call.
- **Local-first.** My data stays on my machine; Notion is the dashboard.
- **Modular.** Independent modules connected via shared storage.
- **Progressive.** JSON before SQLite, rules before LLM, one module at a time.
- **Integration over fragmentation.** Every module earns its place by connecting, not sprawling.

---



## Non-goals (what this is NOT)

- **Not a news archive.** News is disposable daily awareness, not a filing cabinet.
- **Not fully autonomous.** No agent acts without my approval on what matters.
- **Not a script writer.** A deliberate limit, not a gap. See above.
- **Not over-engineered.** No Docker, no vector store, no infra I don't need yet.
- **Not a rebrand machine.** New interests get *placed*, not chased.

---



## Success criteria

- I read my world+AI dashboard each morning without thinking about it.
- When an idea's angle isn't obvious to me, the system gives me one I can actually film.
- Capture is frictionless enough from a phone that no idea is lost to not having a laptop open.
- My content feels like **one voice**, not fragments.
- The system itself becomes a portfolio piece that attracts opportunities.

---



## Related

- [Architecture](ARCHITECTURE.md) · [What's next](WHATS-NEXT.md) · [Runbook](RUNBOOK.md)
- [Brand config template](../config/personal_brand.example.md) — the file the angles agent reads (your real one stays local)

