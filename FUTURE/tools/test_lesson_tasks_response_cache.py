"""Regression checks for revision-keyed Lesson Task bytes and ETag caching."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from FUTURE import server_app as app


def main() -> int:
    username = "hung"
    # Startup watcher debounce intentionally disables task-byte caching while the
    # manifest is dirty; freeze that external state for this cache-only contract.
    manifest_state = getattr(app, "SERVER_DATA_MANIFEST_STATE", {})
    manifest_lock = getattr(app, "SERVER_DATA_MANIFEST_LOCK", None)
    previous_dirty = bool(manifest_state.get("dirty")) if isinstance(manifest_state, dict) else False
    if manifest_lock is not None:
        with manifest_lock:
            manifest_state["dirty"] = False
    try:
        row = app.build_lesson_tasks_response_cache_row(username, username, True)
        payload = json.loads(row["bytes"].decode("utf-8"))
        assert payload["task_owner"] == username
        assert row["etag"].startswith('"lesson-tasks-')
        cached = app.lesson_tasks_response_cache_row(username, username, True)
        assert cached and cached["cache_hit"] is True and cached["bytes"] == row["bytes"]
        assert isinstance(payload.get("space_task", {}).get("tasks"), list)
        row["at"] = 0.0
        aged = app.lesson_tasks_response_cache_row(username, username, True)
        assert aged and aged["cache_hit"] is True and aged["bytes"] == row["bytes"]
    finally:
        if manifest_lock is not None:
            with manifest_lock:
                manifest_state["dirty"] = previous_dirty

    with app.LESSON_TASKS_RAM_CACHE_LOCK:
        revision_map = getattr(app, "LESSON_TASKS_USER_REVISIONS", None)
        if not isinstance(revision_map, dict):
            revision_map = {}
            setattr(app, "LESSON_TASKS_USER_REVISIONS", revision_map)
        previous_version = int(revision_map.get(username.lower(), 0) or 0)
    app.lesson_tasks_user_revision(username, bump=True)
    try:
        assert app.lesson_tasks_response_cache_row(username, username, True) is None
    finally:
        with app.LESSON_TASKS_RAM_CACHE_LOCK:
            revision_map[username.lower()] = previous_version
    print("lesson_tasks_response_cache=ok bytes=true etag=true revision_invalidation=true age_rebuild=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
