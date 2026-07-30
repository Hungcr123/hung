"""Verify exact Lesson Task retries are revision- and file-dependent no-ops."""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from FUTURE import server_app as app


def main() -> int:
    username = "codexload001"
    relative_path = "common/File 02 - {7}.Space_V"
    original = app.server_database_load_lesson_task_record(username).get("record") or {}
    cache_key = app.lesson_task_add_retry_cache_key(
        username,
        relative_path,
        username,
        "user",
        "normal",
    )
    try:
        app.server_database_delete_lesson_task_record(username)
        with app.LESSON_TASKS_RAM_CACHE_LOCK:
            getattr(app, "LESSON_TASKS_USER_RECORD_CACHE", {}).pop(username, None)
            getattr(app, "LESSON_TASKS_USER_REVISIONS", {}).pop(username, None)
        getattr(app, "LESSON_TASK_ADD_RETRY_CACHE", {}).clear()

        first = app.add_lesson_task(username, relative_path, username, "normal", "user")
        first_row = app.server_database_load_lesson_task_record(username)
        retry = app.add_lesson_task(username, relative_path, username, "normal", "user")
        retry_row = app.server_database_load_lesson_task_record(username)
        assert first.get("changed") is True
        assert retry.get("changed") is False and retry.get("retry") is True
        assert first.get("task") == retry.get("task")
        assert first_row.get("revision") == retry_row.get("revision") == 1
        cached_retry = app.lesson_task_add_retry_cache_get(cache_key, username)
        assert cached_retry.get("changed") is False and cached_retry.get("task") == first.get("task")
        with app.LESSON_TASK_ADD_RETRY_CACHE_LOCK:
            cached_row = app.LESSON_TASK_ADD_RETRY_CACHE[cache_key]
            original_signature = cached_row["file_signature"]
            cached_row["file_signature"] = (original_signature[0] + 1, original_signature[1])
        assert app.lesson_task_add_retry_cache_get(cache_key, username) is None
        with app.LESSON_TASK_ADD_RETRY_CACHE_LOCK:
            cached_row["file_signature"] = original_signature

        second_path = "common/Future lesson.Space_W"
        app.add_lesson_task(username, second_path, username, "normal", "user")
        before_restart_retry = app.server_database_load_lesson_task_record(username)
        before_order = [row.get("path") for row in before_restart_retry.get("record", {}).get("tasks", [])]
        getattr(app, "LESSON_TASK_ADD_RETRY_CACHE", {}).clear()
        delayed_retry = app.add_lesson_task(username, relative_path, username, "normal", "user")
        after_restart_retry = app.server_database_load_lesson_task_record(username)
        after_order = [row.get("path") for row in after_restart_retry.get("record", {}).get("tasks", [])]
        assert before_restart_retry.get("revision") == after_restart_retry.get("revision") == 2
        assert before_order == after_order
        assert delayed_retry.get("changed") is False

        record = dict(after_restart_retry.get("record") or {})
        record["space_task"] = {"preferred_folders": ["common"]}
        app.write_lesson_task_user_locked(username, record)
        changed = app.server_database_load_lesson_task_record(username)
        assert changed.get("revision") == 3
        assert app.lesson_task_add_retry_cache_get(cache_key, username) is None
        print("lesson_task_add_retry_cache=ok exact=noop delayed_revision=noop revision_invalidation=true file_signature=true")
        return 0
    finally:
        getattr(app, "LESSON_TASK_ADD_RETRY_CACHE", {}).clear()
        if original:
            app.server_database_write_lesson_task_record(username, original)
        else:
            app.server_database_delete_lesson_task_record(username)


if __name__ == "__main__":
    raise SystemExit(main())
