from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from core.llm.brand_context import load_personal_brand
from core.llm.gemini_client import generate_json
from core.models.idea import BrandFit, Idea, ScriptAngle
from core.models.run import RunContext, RunResult
from core.storage.sqlite_store import SqliteStore

logger = logging.getLogger(__name__)


ANGLES_SYSTEM = """You are the brand angles agent for Idea Angles Pipeline.
Given any raw capture and brand context, suggest 2-3 short-form content angles.
Return JSON only:
{
  "title": "working title",
  "lane": "build" | "create" | "reflect",
  "brand_fit": 0.0-1.0,
  "brand_fit_note": "one sentence — why this score, advisory only",
  "angles": [
    {
      "framework": "PAS | HSO | Learn in Public | Bridge",
      "hook": "opening line",
      "angle": "2-3 sentence angle",
      "tone": "direct, peer-level, etc.",
      "estimated_length": "60s",
      "confidence": 0.0-1.0,
      "delivery_format": "talking head | silent film | carousel | voiceover",
      "hook_family": "promise | moment",
      "hook_mechanism": "which mechanism(s) the hook uses — see list below",
      "stage": "reach | trust | proof | resonance"
    }
  ]
}

Rules:
- Always return at least 2 angles — never refuse an idea
- brand_fit = how naturally the raw capture matches personal_brand.md (0=off-brand, 1=perfect fit)
- brand_fit_note is informational only — do not tell the user to skip the idea
- If the capture is not obviously on-brand, use Bridge angles AND reflect a lower brand_fit honestly
- Narrate as a learner (Learn in Public), not an expert lecturer
- Hooks must be concrete, not hype
- Pick the best-fit lane for the strongest angle

## Hooks

THE GOVERNING RULE: **the story is hers, the hook is about them.** Open on the universal pain
inside her experience, then arrive at her specific version. A hook that opens on "I" is weaker
than the same hook opening on "you" or on the shared problem.

A hook must leave the viewer with MORE unresolved than before, not less. Two ways to do that:
- **withhold** — state a gap, don't fill it ("None of them ask what you've actually done.")
- **reframe** — replace their explanation with a mechanism ("You're not lazy, you're
  overstimulated." / "You're not scattered, your system has no read path.")
  For a reframe, the replacement must be a DIFFERENT CATEGORY, not a synonym. "You're not lazy,
  you're unmotivated" is a rename and fails.

NEVER end a hook with a purpose clause ("...so you can X", "...which means Y", "...because it
helps you Z"). Purpose clauses resolve tension and create none. They belong in the body.

CHOOSING THE MECHANISM: do not pick from the menu. Find the tension already in the capture and
name its shape. The mechanism is a label for something present, not an ingredient added.
- viewer holds a wrong self-label            -> reframe
- she did the opposite of the expected advice -> negation
- a countable set genuinely exists            -> number
- they may not know it applies to them        -> diagnostic
- a private feeling nobody says out loud      -> validation
- two true things that shouldn't coexist      -> contradiction
- surprisingly much or little time            -> timeframe
- insider knowledge with a gatekeeper         -> authority
- a scene they have literally been in         -> POV-as-advice

When returning 2-3 angles for one capture, each angle must use a DIFFERENT mechanism — they are
alternative reads of the same material, not the same hook reworded. If every angle you produce
uses negation, you are defaulting; go back to the capture and find the other tensions in it.

Mechanisms for hook_mechanism (name one or two, never more):
number · negation · diagnostic · validation · authority · contradiction · timeframe ·
POV-as-advice · hyper-specificity · open-loop · reframe

If a hook opens a loop, the angle must say how the body closes it. An unpaid tease is the one
failure with no upside.

## hook_family
- "promise" — numbered/contrarian/diagnostic opener. Job: REACH. Note that promise hooks are
  expert-register by construction; the body must still be scenes and specifics.
- "moment" — opens mid-scene on a specific instant. Job: CONNECTION.

## delivery_format — pick by what actually carries the story
- "silent film" — the emotional beat is tied to a place, object, or physical moment (b-roll +
  music, no talking). Use when the thing can be SHOWN.
- "carousel" — the idea is an argument with discrete steps, or a list worth re-reading. Also the
  right call for days with no energy to film.
- "voiceover" — the visual is a screen, terminal, or hands. Her face would add nothing.
- "talking head" — confession, nuance, tone, or anything where her face IS the evidence.
DEFAULT BIAS: she over-uses talking head. If another format genuinely fits, choose it. Do not
choose talking head just because it's easiest.

## stage — what job this video does
- "reach" — a stranger stops. Pain-first hooks, tech metaphors.
- "trust" — they believe she's real. Journey, build-in-public, vlogs.
- "proof" — a hiring manager acts. Technical depth, receipts, live demos.
- "resonance" — they adopt her way of seeing. Code-to-Consciousness: human symptom → system
  analogy → question.
Her mix is heavily over-weighted to "trust". When an idea could plausibly be reach or resonance,
prefer that read and say why in the angle.
"""


@dataclass
class AnglesRunResult:
    idea: Idea


def _clamp_fit(value: object) -> float | None:
    if value is None:
        return None
    try:
        fit = float(value)
    except (TypeError, ValueError):
        return None
    return max(0.0, min(1.0, fit))


def _enum_or_none(value: object, allowed: tuple[str, ...]) -> str | None:
    """Normalise an LLM string to a known enum value, or drop it.

    The fields these feed are advisory, so a bad value is discarded rather than
    raising — a missing suggestion is better than a failed run.
    """
    if not isinstance(value, str):
        return None
    normalised = value.strip().lower()
    return normalised if normalised in allowed else None


def run_script_angles(idea: Idea, *, brand_md: str | None = None) -> AnglesRunResult:
    brand_md = brand_md or load_personal_brand()
    user = (
        f"## Personal brand\n{brand_md}\n\n"
        f"## Raw capture\n{idea.content.raw_text}\n"
    )
    if idea.content.context:
        user += f"\nContext: {idea.content.context}\n"
    if idea.content.tags:
        user += f"\nTags: {', '.join(idea.content.tags)}\n"

    payload = generate_json("script_angles", system=ANGLES_SYSTEM, user=user)
    title = payload.get("title")
    if title:
        idea.content.title = str(title)[:200]

    lane = payload.get("lane")
    lane_value = lane if lane in ("build", "create", "reflect") else None
    fit = _clamp_fit(payload.get("brand_fit"))
    note = payload.get("brand_fit_note")
    idea.brand_fit = BrandFit(
        fit=fit,
        note=str(note)[:500] if note else None,
        lane=lane_value,
    )
    if fit is not None:
        idea.classification.audience_fit = fit
        idea.classification.noise_score = round(1.0 - fit, 2)

    angles: list[ScriptAngle] = []
    for raw in payload.get("angles", [])[:3]:
        confidence = _clamp_fit(raw.get("confidence"))
        mechanism = raw.get("hook_mechanism")
        angles.append(
            ScriptAngle(
                framework=str(raw.get("framework", "Learn in Public")),
                hook=str(raw.get("hook", "")),
                angle=str(raw.get("angle", "")),
                tone=raw.get("tone"),
                estimated_length=raw.get("estimated_length"),
                confidence=confidence,
                delivery_format=_enum_or_none(
                    raw.get("delivery_format"),
                    ("talking head", "silent film", "carousel", "voiceover"),
                ),
                hook_family=_enum_or_none(raw.get("hook_family"), ("promise", "moment")),
                hook_mechanism=str(mechanism)[:120] if mechanism else None,
                stage=_enum_or_none(
                    raw.get("stage"), ("reach", "trust", "proof", "resonance")
                ),
            )
        )
    idea.script_angles = angles
    idea.processing.status = "angled"
    idea.processing.agent_runs.append(
        {
            "agent": "script_angles_agent",
            "model": "gemini",
            "output": {"angle_count": len(angles), "brand_fit": fit},
            "ran_at": datetime.now(timezone.utc).isoformat(),
        }
    )
    idea.touch()
    return AnglesRunResult(idea=idea)


def angles_for_idea(
    idea_id: str,
    *,
    db_path: Path | None = None,
    store: bool = True,
) -> AnglesRunResult:
    sqlite = SqliteStore(db_path)
    idea = sqlite.get_idea(idea_id)
    if idea is None:
        raise ValueError(f"Idea not found: {idea_id}")
    result = run_script_angles(idea)
    if store:
        sqlite.upsert_idea(result.idea)
    return result


def run(ctx: RunContext) -> RunResult:
    """Orchestrator step `angles`: drain the queue of `captured` ideas → `angled`.

    Idempotent — already-angled ideas are not picked up again; a failed idea
    stays `captured` and is retried on the next run.
    """
    started = time.monotonic()
    store = SqliteStore(ctx.db_path)
    pending = store.list_ideas_by_status("captured")

    if ctx.dry_run:
        return RunResult(
            module="script_angles_agent",
            counts={"pending": len(pending), "angled": 0},
            duration_s=time.monotonic() - started,
        )

    brand_md = load_personal_brand()
    angled = 0
    errors: list[str] = []
    for idea in pending:
        try:
            result = run_script_angles(idea, brand_md=brand_md)
            store.upsert_idea(result.idea)
            angled += 1
        except Exception as exc:
            logger.exception("Angles failed for idea %s", idea.id)
            errors.append(f"{idea.id}: {exc}")

    return RunResult(
        module="script_angles_agent",
        ok=not errors,
        counts={"pending": len(pending), "angled": angled},
        errors=errors,
        duration_s=time.monotonic() - started,
    )
