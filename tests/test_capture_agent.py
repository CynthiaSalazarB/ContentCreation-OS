from core.models.idea import Idea, IdeaContent
from core.models.news_item import Source
from core.storage.sqlite_store import SqliteStore


def test_upsert_and_get_idea(tmp_path):
    db_path = tmp_path / "cynthia.db"
    store = SqliteStore(db_path)
    idea = Idea(
        source=Source(type="manual", name="cli_capture"),
        content=IdeaContent(raw_text="Docker boundaries finally clicked", tags=["docker"]),
    )
    store.upsert_idea(idea)

    loaded = store.get_idea(idea.id)
    assert loaded is not None
    assert loaded.content.raw_text == "Docker boundaries finally clicked"
    assert loaded.content.tags == ["docker"]
    assert loaded.processing.status == "captured"


def test_list_ideas_newest_first(tmp_path):
    db_path = tmp_path / "cynthia.db"
    store = SqliteStore(db_path)
    first = Idea(
        source=Source(type="manual", name="cli_capture"),
        content=IdeaContent(raw_text="First"),
    )
    second = Idea(
        source=Source(type="manual", name="cli_capture"),
        content=IdeaContent(raw_text="Second"),
    )
    store.upsert_idea(first)
    store.upsert_idea(second)

    ideas = store.list_ideas(limit=10)
    assert len(ideas) == 2
    assert ideas[0].content.raw_text == "Second"


def test_idea_related_links():
    idea = Idea(
        source=Source(type="manual", name="cli_capture"),
        content=IdeaContent(raw_text="Part two"),
        links={"related_idea_ids": ["abc-123"]},
    )
    assert idea.links.related_idea_ids == ["abc-123"]
