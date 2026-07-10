from unittest.mock import MagicMock, patch

from datetime import datetime, timezone

from agents.sync_agent.notion_sync import NOTION_CATEGORY, NOTION_SCORE, NOTION_TITLE, NotionNewsSync, item_to_properties
from agents.sync_agent.run import run_sync
from core.models.news_item import Classification, Content, NewsItem, Processing, Source


def _sample_item(url: str = "https://example.com/article") -> NewsItem:
    return NewsItem(
        source=Source(name="techcrunch-ai", url="https://example.com/feed"),
        content=Content(
            title="OpenAI update",
            summary="AI news",
            url=url,
            published_at=datetime(2026, 6, 4, 12, 0, tzinfo=timezone.utc),
        ),
        classification=Classification(
            category="ai_tech",
            relevance_score=0.82,
            noise_score=0.1,
        ),
        processing=Processing(status="filtered"),
    )


def test_item_to_notion_properties():
    item = _sample_item()
    props = item_to_properties(item, synced_at=datetime(2026, 6, 4, 15, 0, tzinfo=timezone.utc))

    assert NOTION_TITLE in props
    assert props[NOTION_TITLE]["title"][0]["text"]["content"] == "OpenAI update"
    assert props[NOTION_CATEGORY]["select"]["name"] == "ai_tech"
    assert props[NOTION_SCORE]["number"] == 0.82


def test_push_items_skips_existing_urls():
    notion = NotionNewsSync.__new__(NotionNewsSync)
    notion.find_page_by_url = MagicMock(side_effect=[None, "page-existing"])
    notion.create_page = MagicMock(return_value="page-new")

    items = [_sample_item("https://a.com"), _sample_item("https://b.com")]
    created, skipped = notion.push_items(items)

    assert created == 1
    assert skipped == 1
    notion.create_page.assert_called_once()


def test_delete_older_than_trashes_only_old_pages():
    old_page = {
        "id": "page-old",
        "properties": {"Synced": {"type": "date", "date": {"start": "2026-05-01T08:00:00+00:00"}}},
    }
    fresh_page = {
        "id": "page-fresh",
        "properties": {"Synced": {"type": "date", "date": {"start": datetime.now(timezone.utc).isoformat()}}},
    }
    no_synced_page = {
        "id": "page-created-old",
        "properties": {},
        "created_time": "2026-04-20T08:00:00.000Z",
    }
    notion = NotionNewsSync.__new__(NotionNewsSync)
    notion.db = MagicMock()
    notion.db.query_all_pages.return_value = [old_page, fresh_page, no_synced_page]

    deleted = notion.delete_older_than(30)

    assert deleted == 2
    trashed_ids = [call.args[0] for call in notion.db.trash_page.call_args_list]
    assert trashed_ids == ["page-old", "page-created-old"]


def test_run_sync_dry_run_json(tmp_path):
    digest = tmp_path / "2026-06-16.json"
    item = _sample_item()
    digest.write_text(
        '{"date":"2026-06-16","items":[' + item.model_dump_json() + "]}",
        encoding="utf-8",
    )

    with patch("agents.sync_agent.run.NotionNewsSync") as mock_cls:
        mock_cls.return_value.list_pages_older_than.return_value = [1, 2, 3]
        result = run_sync(
            run_date=__import__("datetime").date(2026, 6, 16),
            data_dir=tmp_path,
            dry_run=True,
        )

    assert result.candidates == 1
    assert result.deleted == 3
    assert result.created == 0
    assert result.dry_run is True
