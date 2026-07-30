"""Regression for stream-scoped Task Board cache invalidation."""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from FUTURE import server_app as app


def generation(name: str, username: str) -> int:
    return app.server_database_user_generation(name, username)


def restore_generation(name: str, username: str, value: int) -> None:
    bucket = app.SERVER_DATABASE_USER_CHANGE_GENERATIONS.setdefault(name, {})
    key = app.normalize_username(username).lower()
    if value:
        bucket[key] = value
    else:
        bucket.pop(key, None)


def main() -> int:
    username = "codexeventcache"
    broad_before = generation("events", username)
    learning_before = generation("learning_events", username)
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    connection.executescript(
        """
        CREATE TABLE append_events(
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          stream TEXT NOT NULL,
          username TEXT NOT NULL,
          event_at_utc TEXT NOT NULL,
          event_json TEXT NOT NULL,
          event_key TEXT NOT NULL DEFAULT ''
        );
        CREATE UNIQUE INDEX append_events_stream_key_idx
          ON append_events(stream,event_key) WHERE event_key<>'';
        """
    )
    try:
        app._server_database_append_event_in_transaction(
            connection,
            "login",
            {"event": "login", "user": username, "at": "2026-07-22T10:00:00Z"},
        )
        assert generation("events", username) == broad_before + 1
        assert generation("learning_events", username) == learning_before

        app._server_database_append_event_in_transaction(
            connection,
            "learning",
            {
                "event": "lesson_complete",
                "event_key": "codex-learning-event-cache",
                "user": username,
                "at": "2026-07-22T10:01:00Z",
            },
        )
        assert generation("events", username) == broad_before + 2
        assert generation("learning_events", username) == learning_before + 1
    finally:
        connection.close()
        restore_generation("events", username, broad_before)
        restore_generation("learning_events", username, learning_before)

    cache_user = "codexload001"
    broad_cache_before = generation("events", cache_user)
    learning_cache_before = generation("learning_events", cache_user)
    try:
        row = app.build_lesson_tasks_response_cache_row(cache_user, cache_user, False)
        app.server_database_bump_user_generation("events", cache_user)
        cached = app.lesson_tasks_response_cache_row(cache_user, cache_user, False)
        assert cached and cached["cache_hit"] is True and cached["bytes"] == row["bytes"]
        app.server_database_bump_user_generation("learning_events", cache_user)
        assert app.lesson_tasks_response_cache_row(cache_user, cache_user, False) is None
    finally:
        restore_generation("events", cache_user, broad_cache_before)
        restore_generation("learning_events", cache_user, learning_cache_before)
        app.invalidate_lesson_tasks_response_cache(cache_user)

    print("lesson_tasks_learning_event_cache=ok login=hit learning=miss broad=preserved")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
