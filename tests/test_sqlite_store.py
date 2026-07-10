from core.models.idea import Idea, IdeaContent
from core.models.news_item import Source
from core.storage.sqlite_store import SqliteStore


def _idea(text: str, *, source: Source | None = None) -> Idea:
    return Idea(
        source=source or Source(type="manual", name="cli_capture"),
        content=IdeaContent(raw_text=text),
    )


def test_list_ideas_by_status_oldest_first(tmp_path):
    store = SqliteStore(tmp_path / "cynthia.db")
    first = _idea("First")
    second = _idea("Second")
    angled = _idea("Angled")
    angled.processing.status = "angled"
    for idea in (first, second, angled):
        store.upsert_idea(idea)

    captured = store.list_ideas_by_status("captured")
    assert [idea.content.raw_text for idea in captured] == ["First", "Second"]
    assert [idea.id for idea in store.list_ideas_by_status("angled")] == [angled.id]


def test_list_ideas_unsynced_angled_excludes_synced(tmp_path):
    store = SqliteStore(tmp_path / "cynthia.db")
    unsynced = _idea("Unsynced")
    unsynced.processing.status = "angled"
    synced = _idea("Synced")
    synced.processing.status = "angled"
    synced.sync.notion_page_id = "page-123"
    store.upsert_idea(unsynced)
    store.upsert_idea(synced)

    result = store.list_ideas_unsynced_angled()
    assert [idea.id for idea in result] == [unsynced.id]


def test_merge_ideas_from_imports_and_skips(tmp_path):
    local = SqliteStore(tmp_path / "local.db")
    remote = SqliteStore(tmp_path / "remote.db")
    shared = _idea("Captured on both")
    local.upsert_idea(shared)
    remote.upsert_idea(shared)
    vm_only = _idea("Captured on the VM")
    remote.upsert_idea(vm_only)

    imported, updated, skipped = local.merge_ideas_from(remote)

    assert (imported, updated, skipped) == (1, 0, 1)
    assert local.get_idea(vm_only.id) is not None
    # Idempotent: draining again changes nothing
    assert local.merge_ideas_from(remote) == (0, 0, 2)


def test_merge_ideas_from_newer_source_wins_and_keeps_local_sync(tmp_path):
    local = SqliteStore(tmp_path / "local.db")
    remote = SqliteStore(tmp_path / "remote.db")
    idea = _idea("Progressed on the VM")
    local.upsert_idea(idea)
    synced_locally = _idea("Already in Notion locally")
    synced_locally.sync.notion_page_id = "page-local"
    local.upsert_idea(synced_locally)
    remote.upsert_idea(synced_locally)

    remote_copy = idea.model_copy(deep=True)
    remote_copy.processing.status = "angled"
    remote_copy.touch()
    remote.upsert_idea(remote_copy)

    imported, updated, skipped = local.merge_ideas_from(remote)

    assert (imported, updated, skipped) == (0, 1, 1)
    assert local.get_idea(idea.id).processing.status == "angled"
    assert local.get_idea(synced_locally.id).sync.notion_page_id == "page-local"


def test_merge_ideas_from_dry_run_writes_nothing(tmp_path):
    local = SqliteStore(tmp_path / "local.db")
    remote = SqliteStore(tmp_path / "remote.db")
    remote.upsert_idea(_idea("VM capture"))

    imported, updated, skipped = local.merge_ideas_from(remote, dry_run=True)

    assert (imported, updated, skipped) == (1, 0, 0)
    assert local.list_all_ideas() == []


def test_find_idea_by_external_id(tmp_path):
    store = SqliteStore(tmp_path / "cynthia.db")
    telegram_idea = _idea(
        "From my phone",
        source=Source(type="telegram", name="telegram", external_id="42:100"),
    )
    store.upsert_idea(telegram_idea)
    store.upsert_idea(_idea("Plain CLI idea"))

    found = store.find_idea_by_external_id("telegram", "42:100")
    assert found is not None
    assert found.id == telegram_idea.id
    assert store.find_idea_by_external_id("telegram", "42:999") is None
