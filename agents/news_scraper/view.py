from __future__ import annotations

import argparse
import html
import json
import sys
from datetime import date, datetime
from pathlib import Path

from core.models.news_item import NewsItem
from core.paths import NEWS_DATA_DIR
from core.storage.json_store import daily_output_path, load_daily_items

DIGEST_FILENAME = "digest.html"
CATEGORY_ORDER = ("ai_tech", "macro", "markets", "geopolitics", "other")
CATEGORY_LABELS = {
    "ai_tech": "AI & Tech",
    "macro": "Macro & Markets",
    "markets": "Markets",
    "geopolitics": "Geopolitics",
    "other": "Other",
}


def resolve_json_path(run_date: date | None, data_dir: Path) -> Path:
    if run_date:
        path = daily_output_path(run_date, data_dir)
        if not path.exists():
            raise FileNotFoundError(f"No digest JSON for {run_date.isoformat()}: {path}")
        return path

    candidates = sorted(data_dir.glob("????-??-??.json"), reverse=True)
    if not candidates:
        raise FileNotFoundError(f"No daily JSON files in {data_dir}")
    return candidates[0]


def digest_html_path(data_dir: Path | None = None) -> Path:
    return (data_dir or NEWS_DATA_DIR) / DIGEST_FILENAME


def _format_published(item: NewsItem) -> str:
    published = item.content.published_at
    if not published:
        return ""
    if isinstance(published, datetime):
        return published.strftime("%Y-%m-%d %H:%M UTC")
    return str(published)


def _render_item(item: NewsItem) -> str:
    title = html.escape(item.content.title)
    url = html.escape(item.content.url, quote=True)
    summary = html.escape(item.content.summary or "")
    source = html.escape(item.source.name)
    score = item.classification.relevance_score
    tags = ", ".join(html.escape(t) for t in item.classification.tags)
    published = html.escape(_format_published(item))

    tags_html = f'<span class="tags">{tags}</span>' if tags else ""
    published_html = f'<time>{published}</time>' if published else ""

    return f"""
    <article class="item">
      <header>
        <h3><a href="{url}" target="_blank" rel="noopener">{title}</a></h3>
        <div class="meta">
          <span class="source">{source}</span>
          <span class="score" title="Relevance score">{score:.0%}</span>
          {published_html}
        </div>
      </header>
      {f'<p class="summary">{summary}</p>' if summary else ''}
      {tags_html}
    </article>
    """


def _group_items(items: list[NewsItem]) -> dict[str, list[NewsItem]]:
    groups: dict[str, list[NewsItem]] = {key: [] for key in CATEGORY_ORDER}
    groups.setdefault("other", [])
    for item in items:
        category = item.classification.category
        if category not in groups:
            groups[category] = []
        groups[category].append(item)
    return groups


def render_digest_html(
    items: list[NewsItem],
    *,
    digest_date: str,
    generated_at: str | None = None,
    source_json: str | None = None,
) -> str:
    groups = _group_items(items)
    sections: list[str] = []

    for category in CATEGORY_ORDER:
        group_items = groups.get(category, [])
        if not group_items:
            continue
        label = CATEGORY_LABELS.get(category, category)
        articles = "".join(_render_item(item) for item in group_items)
        sections.append(
            f"""
        <section class="category">
          <h2>{html.escape(label)} <span class="count">({len(group_items)})</span></h2>
          <div class="items">{articles}</div>
        </section>
        """
        )

    for category, group_items in groups.items():
        if category in CATEGORY_ORDER or not group_items:
            continue
        label = CATEGORY_LABELS.get(category, category)
        articles = "".join(_render_item(item) for item in group_items)
        sections.append(
            f"""
        <section class="category">
          <h2>{html.escape(label)} <span class="count">({len(group_items)})</span></h2>
          <div class="items">{articles}</div>
        </section>
        """
        )

    meta_parts = [
        f"<span>{html.escape(digest_date)}</span>",
        f"<span>{len(items)} articles</span>",
    ]
    if generated_at:
        meta_parts.append(f"<span>Data from {html.escape(generated_at)}</span>")
    if source_json:
        meta_parts.append(f'<span class="file">{html.escape(source_json)}</span>')

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Idea Angles Pipeline News — {html.escape(digest_date)}</title>
  <style>
    :root {{
      --bg: #0f1117;
      --surface: #1a1d27;
      --text: #e8eaed;
      --muted: #9aa0a6;
      --accent: #7c9cff;
      --border: #2d3142;
      --ai: #5b8def;
      --macro: #6bc9a8;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      font-family: "Segoe UI", system-ui, sans-serif;
      background: var(--bg);
      color: var(--text);
      line-height: 1.5;
      margin: 0;
      padding: 1.5rem;
      max-width: 52rem;
      margin-inline: auto;
    }}
    header.page {{
      margin-bottom: 2rem;
      padding-bottom: 1rem;
      border-bottom: 1px solid var(--border);
    }}
    header.page h1 {{
      font-size: 1.5rem;
      font-weight: 600;
      margin: 0 0 0.5rem;
    }}
    .page-meta {{
      display: flex;
      flex-wrap: wrap;
      gap: 0.75rem 1.25rem;
      font-size: 0.875rem;
      color: var(--muted);
    }}
    .page-meta .file {{ font-family: ui-monospace, monospace; font-size: 0.8rem; }}
    section.category {{
      margin-bottom: 2rem;
    }}
    section.category h2 {{
      font-size: 1.1rem;
      font-weight: 600;
      margin: 0 0 1rem;
      color: var(--accent);
    }}
    section.category h2 .count {{
      font-weight: 400;
      color: var(--muted);
    }}
    article.item {{
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 1rem 1.25rem;
      margin-bottom: 0.75rem;
    }}
    article.item h3 {{
      font-size: 1rem;
      font-weight: 600;
      margin: 0 0 0.5rem;
      line-height: 1.35;
    }}
    article.item h3 a {{
      color: var(--text);
      text-decoration: none;
    }}
    article.item h3 a:hover {{
      color: var(--accent);
      text-decoration: underline;
    }}
    .meta {{
      display: flex;
      flex-wrap: wrap;
      gap: 0.5rem 1rem;
      font-size: 0.8rem;
      color: var(--muted);
    }}
    .source {{
      font-weight: 500;
      color: var(--accent);
    }}
    .score {{
      background: var(--border);
      padding: 0.1rem 0.4rem;
      border-radius: 4px;
    }}
    .summary {{
      margin: 0.5rem 0 0;
      font-size: 0.9rem;
      color: var(--muted);
    }}
    .tags {{
      display: inline-block;
      margin-top: 0.5rem;
      font-size: 0.75rem;
      color: var(--muted);
    }}
    .empty {{
      color: var(--muted);
      font-style: italic;
    }}
  </style>
</head>
<body>
  <header class="page">
    <h1>Idea Angles Pipeline News Digest</h1>
    <div class="page-meta">{"".join(meta_parts)}</div>
  </header>
  <main>
    {"".join(sections) if sections else '<p class="empty">No articles in this digest.</p>'}
  </main>
</body>
</html>
"""


def build_digest(
    *,
    run_date: date | None = None,
    data_dir: Path | None = None,
    output_path: Path | None = None,
) -> Path:
    data_dir = data_dir or NEWS_DATA_DIR
    json_path = resolve_json_path(run_date, data_dir)

    with json_path.open(encoding="utf-8") as handle:
        payload = json.load(handle)

    items = load_daily_items(json_path)
    digest_date = payload.get("date", json_path.stem)
    generated_at = payload.get("generated_at")

    html_content = render_digest_html(
        items,
        digest_date=str(digest_date),
        generated_at=str(generated_at) if generated_at else None,
        source_json=json_path.name,
    )

    out = output_path or digest_html_path(data_dir)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html_content, encoding="utf-8")
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate static HTML digest from news JSON"
    )
    parser.add_argument(
        "--date",
        type=date.fromisoformat,
        help="Digest date (YYYY-MM-DD). Default: latest JSON in data/news/",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help=f"Output HTML path (default: data/news/{DIGEST_FILENAME})",
    )
    args = parser.parse_args(argv)

    try:
        out = build_digest(run_date=args.date, output_path=args.output)
    except FileNotFoundError as exc:
        print(exc, file=sys.stderr)
        return 1

    print(f"Written: {out}")
    print("Open in browser: file:///" + str(out.resolve()).replace("\\", "/"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
