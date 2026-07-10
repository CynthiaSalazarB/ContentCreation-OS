from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from core.models.idea import Idea, IdeaProcessingStatus
from core.paths import DB_PATH


class SqliteStore:
    """Canonical store for persistent ideas.

    Daily news is disposable (today-only JSON via core/storage/json_store.py)
    and is never written here.
    """

    def __init__(self, db_path: Path | None = None) -> None:
        self.db_path = db_path or DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS ideas (
                    id TEXT PRIMARY KEY,
                    payload TEXT NOT NULL,
                    notion_page_id TEXT,
                    last_synced_at TEXT,
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_ideas_notion ON ideas(notion_page_id)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_ideas_created ON ideas(created_at DESC)"
            )

    def upsert_idea(self, idea: Idea) -> None:
        payload = idea.model_dump(mode="json")
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO ideas (id, payload, notion_page_id, last_synced_at, created_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    payload = excluded.payload,
                    notion_page_id = COALESCE(excluded.notion_page_id, ideas.notion_page_id),
                    last_synced_at = COALESCE(excluded.last_synced_at, ideas.last_synced_at)
                """,
                (
                    idea.id,
                    json.dumps(payload),
                    idea.sync.notion_page_id,
                    idea.sync.last_synced_at.isoformat() if idea.sync.last_synced_at else None,
                    idea.created_at.isoformat(),
                ),
            )

    def get_idea(self, idea_id: str) -> Idea | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT payload FROM ideas WHERE id = ?",
                (idea_id,),
            ).fetchone()
        if row is None:
            return None
        return Idea.model_validate(json.loads(row["payload"]))

    def find_idea_by_external_id(self, source_name: str, external_id: str) -> Idea | None:
        """Look up an idea by its upstream id (e.g. a Telegram message) for idempotent capture."""
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT payload FROM ideas
                WHERE json_extract(payload, '$.source.name') = ?
                  AND json_extract(payload, '$.source.external_id') = ?
                LIMIT 1
                """,
                (source_name, external_id),
            ).fetchone()
        if row is None:
            return None
        return Idea.model_validate(json.loads(row["payload"]))

    def list_ideas(self, *, limit: int = 50) -> list[Idea]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT payload FROM ideas
                ORDER BY created_at DESC, rowid DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [Idea.model_validate(json.loads(row["payload"])) for row in rows]

    def list_ideas_by_status(
        self, status: IdeaProcessingStatus, *, limit: int = 500
    ) -> list[Idea]:
        """Queue view: oldest first, so pipeline steps drain in capture order."""
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT payload FROM ideas
                WHERE json_extract(payload, '$.processing.status') = ?
                ORDER BY created_at ASC, rowid ASC
                LIMIT ?
                """,
                (status, limit),
            ).fetchall()
        return [Idea.model_validate(json.loads(row["payload"])) for row in rows]

    def list_ideas_unsynced_angled(self) -> list[Idea]:
        """Angled ideas not yet in Notion."""
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT payload FROM ideas
                WHERE json_extract(payload, '$.processing.status') = 'angled'
                  AND notion_page_id IS NULL
                ORDER BY created_at ASC, rowid ASC
                """
            ).fetchall()
        return [Idea.model_validate(json.loads(row["payload"])) for row in rows]

    def list_all_ideas(self) -> list[Idea]:
        """Every idea, oldest first (merge/export use — no limit)."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT payload FROM ideas ORDER BY created_at ASC, rowid ASC"
            ).fetchall()
        return [Idea.model_validate(json.loads(row["payload"])) for row in rows]

    def merge_ideas_from(
        self, source: SqliteStore, *, dry_run: bool = False
    ) -> tuple[int, int, int]:
        """One-way drain of another ideas DB into this one (remote capture inbox → canonical).

        Upserts by UUID: unknown ideas are imported, known ideas are updated only
        when the source copy is newer (updated_at); the COALESCE in upsert_idea
        keeps local notion_page_id/last_synced_at when the source has none.
        Idempotent — re-running against the same source changes nothing.
        Returns (imported, updated, skipped).
        """
        imported = 0
        updated = 0
        skipped = 0
        for idea in source.list_all_ideas():
            local = self.get_idea(idea.id)
            if local is None:
                imported += 1
            elif idea.updated_at > local.updated_at:
                updated += 1
            else:
                skipped += 1
                continue
            if not dry_run:
                self.upsert_idea(idea)
        return imported, updated, skipped
