from unittest.mock import patch

from agents.sync_agent.notion_ideas_sync import idea_to_properties
from core.models.idea import BrandFit, Idea, IdeaContent
from core.models.news_item import Source
from pipelines.idea_pipeline import process_idea
from core.storage.sqlite_store import SqliteStore


def _sample_idea(text: str = "Docker boundaries finally clicked") -> Idea:
    return Idea(
        source=Source(type="manual", name="cli_capture"),
        content=IdeaContent(raw_text=text),
    )


def _angles_payload(
    *,
    title: str = "Docker clicked for me",
    lane: str = "build",
    brand_fit: float = 0.85,
):
    return {
        "title": title,
        "lane": lane,
        "brand_fit": brand_fit,
        "brand_fit_note": "Build lane learn-in-public fit",
        "angles": [
            {
                "framework": "Bridge",
                "hook": "I thought Docker was overkill",
                "angle": "Here's what changed",
                "tone": "peer",
                "estimated_length": "60s",
                "confidence": 0.8,
            }
        ],
    }


def test_process_idea_sets_brand_fit():
    idea = _sample_idea("unboxing of my standing desk")
    with (
        patch(
            "agents.script_angles_agent.run.load_personal_brand",
            return_value="# Test brand",
        ),
        patch(
            "agents.script_angles_agent.run.generate_json",
            return_value=_angles_payload(title="My dev setup upgrade", brand_fit=0.42),
        ),
    ):
        result = process_idea(idea, sync_notion=False)
    assert len(result.idea.script_angles) == 1
    assert result.idea.brand_fit.fit == 0.42
    assert result.idea.brand_fit.lane == "build"
    assert result.idea.brand_fit.note is not None


def test_process_idea_off_brand_still_gets_angles():
    idea = _sample_idea("random personal diary entry")
    with (
        patch(
            "agents.script_angles_agent.run.load_personal_brand",
            return_value="# Test brand",
        ),
        patch(
            "agents.script_angles_agent.run.generate_json",
            return_value=_angles_payload(title="A reflect angle", lane="reflect", brand_fit=0.25),
        ),
    ):
        result = process_idea(idea, sync_notion=False)
    assert result.idea.script_angles
    assert result.idea.brand_fit.lane == "reflect"
    assert result.idea.brand_fit.fit == 0.25


def test_idea_to_notion_properties_brand_fit():
    idea = _sample_idea()
    idea.brand_fit = BrandFit(fit=0.72, note="Fits Build if framed as setup", lane="build")
    props = idea_to_properties(idea)
    assert "Title" in props
    assert props["Brand fit %"]["number"] == 72.0
    assert "Brand fit note" in props
    assert props["Status"]["select"]["name"] == "Inbox"


def test_list_unsynced_angled(tmp_path):
    store = SqliteStore(tmp_path / "db.sqlite")
    idea = _sample_idea()
    idea.processing.status = "angled"
    store.upsert_idea(idea)
    unsynced = store.list_ideas_unsynced_angled()
    assert len(unsynced) == 1
