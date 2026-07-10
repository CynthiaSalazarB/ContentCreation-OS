from unittest.mock import patch

from core.models.idea import Idea, IdeaContent
from core.models.news_item import Source
from core.models.run import RunContext, RunResult
from core.storage.sqlite_store import SqliteStore
from orchestrator import STEP_REGISTRY, main


def test_unknown_step_fails():
    assert main(["--steps", "news,bogus"]) == 1


def test_registry_has_documented_steps():
    assert set(STEP_REGISTRY) == {"news", "sync", "angles", "ideas-push", "ideas-pull"}


def test_angles_step_drains_captured_queue(tmp_path):
    store = SqliteStore(tmp_path / "cynthia.db")
    idea = Idea(
        source=Source(type="manual", name="cli_capture"),
        content=IdeaContent(raw_text="Docker boundaries finally clicked"),
    )
    store.upsert_idea(idea)

    from agents.script_angles_agent.run import run as angles_run

    payload = {
        "title": "Docker clicked",
        "lane": "build",
        "brand_fit": 0.8,
        "brand_fit_note": "fits",
        "angles": [
            {"framework": "PAS", "hook": "hook", "angle": "angle", "confidence": 0.9}
        ],
    }
    with (
        patch("agents.script_angles_agent.run.generate_json", return_value=payload),
        patch("agents.script_angles_agent.run.load_personal_brand", return_value="brand"),
    ):
        result = angles_run(RunContext(db_path=tmp_path / "cynthia.db"))

    assert isinstance(result, RunResult)
    assert result.ok
    assert result.counts == {"pending": 1, "angled": 1}
    refreshed = store.get_idea(idea.id)
    assert refreshed.processing.status == "angled"
    # Second run: queue is drained — idempotent.
    with (
        patch("agents.script_angles_agent.run.generate_json", return_value=payload),
        patch("agents.script_angles_agent.run.load_personal_brand", return_value="brand"),
    ):
        again = angles_run(RunContext(db_path=tmp_path / "cynthia.db"))
    assert again.counts == {"pending": 0, "angled": 0}


def test_angles_step_dry_run_touches_nothing(tmp_path):
    store = SqliteStore(tmp_path / "cynthia.db")
    idea = Idea(
        source=Source(type="manual", name="cli_capture"),
        content=IdeaContent(raw_text="An idea"),
    )
    store.upsert_idea(idea)

    from agents.script_angles_agent.run import run as angles_run

    result = angles_run(RunContext(db_path=tmp_path / "cynthia.db", dry_run=True))
    assert result.counts == {"pending": 1, "angled": 0}
    assert store.get_idea(idea.id).processing.status == "captured"
