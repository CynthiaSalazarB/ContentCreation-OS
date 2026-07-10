from datetime import date
from pathlib import Path

from agents.news_scraper.view import build_digest, render_digest_html
from core.models.news_item import Classification, Content, NewsItem, Source


def _item(title: str, category: str = "ai_tech") -> NewsItem:
    return NewsItem(
        source=Source(name="test-feed", url="https://example.com/feed"),
        content=Content(
            title=title,
            summary="Summary text",
            url="https://example.com/article",
        ),
        classification=Classification(
            category=category,
            tags=["ai"],
            relevance_score=0.8,
            noise_score=0.2,
        ),
    )


def test_render_digest_html_contains_items():
    html_out = render_digest_html(
        [_item("OpenAI update"), _item("Fed rates", "macro")],
        digest_date="2026-06-03",
    )
    assert "OpenAI update" in html_out
    assert "Fed rates" in html_out
    assert "AI &amp; Tech" in html_out or "AI & Tech" in html_out
    assert "<!DOCTYPE html>" in html_out


def test_build_digest_from_json(tmp_path):
    json_path = tmp_path / "2026-06-03.json"
    json_path.write_text(
        """{
  "date": "2026-06-03",
  "generated_at": "2026-06-03T12:00:00Z",
  "count": 1,
  "items": [{
    "id": "1",
    "type": "news_item",
    "created_at": "2026-06-03T12:00:00Z",
    "updated_at": "2026-06-03T12:00:00Z",
    "source": {"type": "rss", "name": "test", "url": "https://x.com/feed"},
    "content": {
      "title": "Test headline",
      "summary": "Test summary",
      "url": "https://example.com/1",
      "language": "en"
    },
    "classification": {
      "category": "ai_tech",
      "tags": ["ai"],
      "relevance_score": 0.7,
      "noise_score": 0.3
    },
    "processing": {"status": "filtered", "pipeline_version": "0.1"}
  }]
}""",
        encoding="utf-8",
    )

    out = build_digest(run_date=date(2026, 6, 3), data_dir=tmp_path)
    assert out.exists()
    text = out.read_text(encoding="utf-8")
    assert "Test headline" in text
