"""Telegram capture channel — entry point, composes via pipelines/ (see ARCHITECTURE.md).

Long-polling prototype: runs while the PC is on. Phase 2c will move this to a
webhook deployment.
"""

from __future__ import annotations

import json
import logging
import os
import time
import urllib.parse
import urllib.request

from dotenv import load_dotenv

from core.models.idea import Idea
from core.models.news_item import Source
from core.paths import ENV_PATH
from core.storage.sqlite_store import SqliteStore
from pipelines.idea_pipeline import capture_and_process

logger = logging.getLogger(__name__)

SOURCE_NAME = "telegram"
MAX_ERROR_BACKOFF = 60.0


def _telegram_api(token: str, method: str, **params) -> dict:
    data = urllib.parse.urlencode(params).encode("utf-8")
    url = f"https://api.telegram.org/bot{token}/{method}"
    request = urllib.request.Request(url, data=data, method="POST")
    with urllib.request.urlopen(request, timeout=60) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if not payload.get("ok"):
        raise RuntimeError(payload.get("description", "Telegram API error"))
    return payload["result"]


def _send_message(token: str, chat_id: int, text: str) -> None:
    """Best-effort reply — a failed send must never kill the bot."""
    try:
        _telegram_api(token, "sendMessage", chat_id=chat_id, text=text[:4000])
    except Exception:
        logger.exception("Failed to send Telegram reply to chat %s", chat_id)


def _format_reply(idea: Idea, *, synced: bool) -> str:
    lines: list[str] = []
    if idea.content.title:
        lines.append(f"Title: {idea.content.title}")
    for index, angle in enumerate(idea.script_angles[:2], start=1):
        lines.append(f"{index}. [{angle.framework}] {angle.hook}")
    if synced:
        lines.append("Synced to Notion Idea Bank (Inbox).")
    return "\n".join(lines) or "Processed — check Notion Idea Bank."


def _handle_message(token: str, message: dict, store: SqliteStore) -> None:
    chat_id = message["chat"]["id"]
    text = (message.get("text") or "").strip()
    if not text:
        return
    if text.startswith("/start"):
        _send_message(
            token,
            chat_id,
            "Send me a one-line idea. I'll suggest on-brand angles and add it to your Idea Bank.",
        )
        return

    # Idempotent capture: a re-delivered or reprocessed update must not create
    # a second idea. chat_id:message_id uniquely identifies the message.
    external_id = f"{chat_id}:{message.get('message_id')}"
    existing = store.find_idea_by_external_id(SOURCE_NAME, external_id)
    if existing is not None:
        logger.info("Skipping already-captured Telegram message %s", external_id)
        _send_message(
            token,
            chat_id,
            _format_reply(existing, synced=existing.sync.notion_page_id is not None),
        )
        return

    _send_message(token, chat_id, "Processing…")
    try:
        result = capture_and_process(
            text,
            source=Source(type="telegram", name=SOURCE_NAME, external_id=external_id),
            sync_notion=True,
        )
        _send_message(token, chat_id, _format_reply(result.idea, synced=result.synced_to_notion))
    except Exception as exc:
        logger.exception("Pipeline failed for Telegram message %s", external_id)
        _send_message(token, chat_id, f"Error: {exc}")


def run_bot(*, poll_interval: float = 1.0) -> None:
    load_dotenv(ENV_PATH)
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    allowed_raw = os.getenv("TELEGRAM_ALLOWED_USER_ID", "").strip()
    if not token:
        raise ValueError("TELEGRAM_BOT_TOKEN is not set in .env")
    if not allowed_raw:
        raise ValueError("TELEGRAM_ALLOWED_USER_ID is not set in .env")
    allowed_user_id = int(allowed_raw)

    store = SqliteStore()
    offset = 0
    consecutive_errors = 0
    logger.info("Telegram capture bot started")
    while True:
        try:
            updates = _telegram_api(
                token,
                "getUpdates",
                offset=offset,
                timeout=30,
            )
            consecutive_errors = 0
        except Exception as exc:
            consecutive_errors += 1
            backoff = min(poll_interval * (2**consecutive_errors), MAX_ERROR_BACKOFF)
            logger.warning("Telegram poll failed (%s) — retrying in %.0fs", exc, backoff)
            time.sleep(backoff)
            continue

        for update in updates:
            offset = update["update_id"] + 1
            try:
                message = update.get("message") or update.get("edited_message")
                if not message:
                    continue
                if message.get("from", {}).get("id") != allowed_user_id:
                    continue
                _handle_message(token, message, store)
            except Exception:
                logger.exception("Failed to handle update %s", update.get("update_id"))

        time.sleep(poll_interval)


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    run_bot()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
