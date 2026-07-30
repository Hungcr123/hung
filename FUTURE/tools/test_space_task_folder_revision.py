"""Verify Space Task folder retries and concurrent stale devices cannot overwrite newer settings."""

from __future__ import annotations

import concurrent.futures
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from FUTURE import server_app as app


def main() -> int:
    username = "codexload001"
    original = app.server_database_load_lesson_task_record(username).get("record") or {}
    folders = ("common/PDF", "common/Study", "common/Ngữ pháp")
    try:
        app.server_database_delete_lesson_task_record(username)
        with app.LESSON_TASKS_RAM_CACHE_LOCK:
            getattr(app, "LESSON_TASKS_USER_RECORD_CACHE", {}).pop(username, None)
            getattr(app, "LESSON_TASKS_USER_REVISIONS", {}).pop(username, None)

        first = app.save_space_task_settings(username, [folders[0]], username, allow_any_top=False, base_revision="")
        first_row = app.server_database_load_lesson_task_record(username)
        retry = app.save_space_task_settings(username, [folders[0]], username, allow_any_top=False, base_revision="")
        retry_row = app.server_database_load_lesson_task_record(username)
        assert first.get("changed") is True and retry.get("changed") is False
        assert first_row.get("revision") == retry_row.get("revision") == 1

        second = app.save_space_task_settings(
            username,
            [folders[1]],
            username,
            allow_any_top=False,
            base_revision=first.get("updated_rev", ""),
        )
        assert second.get("changed") is True
        try:
            app.save_space_task_settings(username, [folders[0]], username, allow_any_top=False, base_revision="")
            raise AssertionError("stale initial-device packet was accepted")
        except RuntimeError as exc:
            assert "another device" in str(exc)

        base = second.get("updated_rev", "")

        def update(folder: str):
            try:
                return app.save_space_task_settings(username, [folder], username, allow_any_top=False, base_revision=base)
            except RuntimeError:
                return {"conflict": True}

        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(update, (folders[0], folders[2])))
        assert sum(bool(row.get("changed")) for row in results) == 1
        assert sum(bool(row.get("conflict")) for row in results) == 1
        final = app.space_task_settings_for_user(username)
        assert final.get("preferred_folders") in ([folders[0]], [folders[2]])
        assert app.server_database_load_lesson_task_record(username).get("revision") == 3
        print("space_task_folder_revision=ok exact_retry=noop stale_device=reject concurrent=one-winner")
        return 0
    finally:
        if original:
            app.server_database_write_lesson_task_record(username, original)
        else:
            app.server_database_delete_lesson_task_record(username)


if __name__ == "__main__":
    raise SystemExit(main())
