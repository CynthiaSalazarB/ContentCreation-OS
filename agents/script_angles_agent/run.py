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


ANGLES_SYSTEM = """You are the brand angles agent for ContentCreation-OS.
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
      "confidence": 0.0-1.0
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
        angles.append(
            ScriptAngle(
                framework=str(raw.get("framework", "Learn in Public")),
                hook=str(raw.get("hook", "")),
                angle=str(raw.get("angle", "")),
                tone=raw.get("tone"),
                estimated_length=raw.get("estimated_length"),
                confidence=confidence,
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
