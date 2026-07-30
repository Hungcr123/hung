"""Verify cold Lesson Task shortcuts preserve task and learning semantics."""

from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from FUTURE import server_app as app


def main() -> int:
    task_only_user = "codexload001"
    task_only_folder = app.user_folder_path(task_only_user)
    folder_existed = task_only_folder.exists()
    original = app.server_database_load_lesson_task_record(task_only_user).get("record") or {}
    original_task_time = app.server_database_load_lesson_time_payload(task_only_user)
    try:
        app.server_database_replace_lesson_time_payload(task_only_user, {})
        if not (original.get("tasks") if isinstance(original, dict) else None):
            raw_path = "common/File 02 - {7}.Space_V"
            app.server_database_write_lesson_task_record(task_only_user, {"tasks": [{
                "id": app.lesson_task_id(task_only_user, raw_path),
                "path": raw_path,
                "effective_path": raw_path,
                "name": Path(raw_path).name,
                "title": Path(raw_path).stem,
                "added_by": task_only_user,
                "creator_role": "user",
                "added_at": app.utc_timestamp(),
                "severity": "normal",
            }]})
            with app.LESSON_TASKS_RAM_CACHE_LOCK:
                getattr(app, "LESSON_TASKS_USER_RECORD_CACHE", {}).pop(task_only_user, None)
        assert app.lesson_tasks_user_has_renderable_state(task_only_user) is True

        row = app.build_lesson_tasks_response_cache_row(task_only_user, task_only_user, False)
        payload = json.loads(row["bytes"].decode("utf-8"))
        assert len(payload.get("tasks") or []) >= 1
        actual_stats = dict(payload.get("learning_stats") or {})
        expected_stats = dict(app.lesson_user_learning_summary_cached_or_empty(task_only_user) or {})
        actual_stats.pop("updatedAt", None)
        expected_stats.pop("updatedAt", None)
        assert actual_stats == expected_stats
        assert task_only_folder.exists() is folder_existed

        task = (app.read_lesson_task_user_locked(task_only_user).get("tasks") or [])[0]
        raw_path = app.clean_path_value(task.get("path", ""))
        info = app.lesson_task_file_info(raw_path, task_only_user)
        effective = info.get("effective_target")
        meta = app.cached_lesson_file_metadata(effective)
        kwargs = {
            "username": task_only_user,
            "progress_index": {},
            "time_index": {},
            "progress_relative_path": app.clean_path_value(info.get("effective_path", "")) or raw_path,
            "path_is_effective": True,
            "progress_relative_paths": [raw_path, app.clean_path_value(info.get("effective_path", ""))],
            "strict_progress_paths": True,
        }
        old_summary = app.summarize_lesson_study(effective, **kwargs)
        reused_summary = app.summarize_lesson_study(effective, file_meta=meta, **kwargs)
        assert old_summary == reused_summary
    finally:
        app.server_database_replace_lesson_time_payload(task_only_user, original_task_time)
        if original:
            app.server_database_write_lesson_task_record(task_only_user, original)
        else:
            app.server_database_delete_lesson_task_record(task_only_user)

    assert app.server_database_user_has_lesson_state("hung") is True
    hung_payload = app.build_lesson_tasks_response_cache_row("hung", "hung", True)["payload"]
    assert hung_payload.get("learning_stats") == app.lesson_user_learning_summary_cached_or_empty("hung")

    # A time-only learner has server state but no lifetime summary; Task GET must remain cache-only.
    time_only_user = "codexload050"
    original_time = app.server_database_load_lesson_time_payload(time_only_user)
    original_tasks = app.server_database_load_lesson_task_record(time_only_user).get("record") or {}
    original_reader = app.read_cached_lesson_user_learning_summary
    original_compute = app.compute_lesson_user_learning_summary
    try:
        app.server_database_delete_lesson_task_record(time_only_user)
        with app.LESSON_TASKS_RAM_CACHE_LOCK:
            getattr(app, "LESSON_TASKS_USER_RECORD_CACHE", {}).pop(time_only_user, None)
        app.server_database_replace_lesson_time_payload(time_only_user, {
            "states": {
                "common/file 02 - {7}.space_v": {
                    "path": "common/File 02 - {7}.Space_V",
                    "title": "File 02 - {7}",
                    "space": "Space_V",
                    "seconds": 1,
                    "ticks": 1,
                    "updatedAt": app.utc_timestamp(),
                }
            }
        })
        assert app.server_database_user_has_lesson_state(time_only_user) is True
        assert app.lesson_tasks_user_has_renderable_state(time_only_user) is False
        app.read_cached_lesson_user_learning_summary = lambda _username="": {}

        def fail_full_scan(_username=""):
            raise AssertionError("Task GET attempted a full lesson summary scan")

        app.compute_lesson_user_learning_summary = fail_full_scan
        with app.LESSON_TASKS_RESPONSE_BYTES_CACHE_LOCK:
            app.LESSON_TASKS_RESPONSE_BYTES_CACHE.clear()
        time_only_payload = app.build_lesson_tasks_response_cache_row(time_only_user, time_only_user, False)["payload"]
        time_only_stats = time_only_payload.get("learning_stats") or {}
        assert time_only_stats.get("username") == time_only_user
        assert time_only_stats == app.empty_lesson_learning_summary(time_only_user)
        assert int(time_only_stats.get("total_files", 0) or 0) == 0
    finally:
        app.read_cached_lesson_user_learning_summary = original_reader
        app.compute_lesson_user_learning_summary = original_compute
        app.server_database_replace_lesson_time_payload(time_only_user, original_time)
        if original_tasks:
            app.server_database_write_lesson_task_record(time_only_user, original_tasks)
        else:
            app.server_database_delete_lesson_task_record(time_only_user)
        with app.LESSON_TASKS_RAM_CACHE_LOCK:
            getattr(app, "LESSON_TASKS_USER_RECORD_CACHE", {}).pop(time_only_user, None)
        with app.LESSON_TASKS_RESPONSE_BYTES_CACHE_LOCK:
            app.LESSON_TASKS_RESPONSE_BYTES_CACHE.clear()

    print("lesson_tasks_cold_response=ok task_only_fast=true time_only_no_scan=true no_folder=true metadata_reuse=true real_state=true")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
