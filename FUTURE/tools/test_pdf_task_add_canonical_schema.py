"""Verify POST-add task data already matches the hydrated PDF task schema."""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from FUTURE import server_app as app


def selected(task: dict) -> dict:
    keys = (
        "id", "lesson_id", "file_id", "path", "normalized_path", "effective_path",
        "filename", "extension", "mime_type", "file_type", "source_type", "is_pdf",
        "icon", "open_action", "package_path", "package_backed", "available",
    )
    return {key: task.get(key) for key in keys}


def main() -> int:
    username = "codexload001"
    path = "common/PDF/Destination/Destination B2 Grammar and Vocabulary with Answer key.space_pdf"
    original = app.server_database_load_lesson_task_record(username).get("record") or {}
    try:
        app.server_database_delete_lesson_task_record(username)
        with app.LESSON_TASKS_RAM_CACHE_LOCK:
            getattr(app, "LESSON_TASKS_USER_RECORD_CACHE", {}).pop(username, None)
            getattr(app, "LESSON_TASKS_USER_REVISIONS", {}).pop(username, None)
        getattr(app, "LESSON_TASK_ADD_RETRY_CACHE", {}).clear()

        added = app.add_lesson_task(username, path, username, creator_role="user")
        task = added.get("task") or {}
        assert added.get("changed") is True
        assert str(task.get("lesson_id") or "").startswith("ftg-lesson-")
        assert task.get("file_id") == task.get("lesson_id")
        assert task.get("path") == task.get("normalized_path") == path
        assert task.get("extension") == ".pdf"
        assert str(task.get("filename") or "").lower().endswith(".pdf")
        assert task.get("mime_type") == "application/pdf"
        assert task.get("file_type") == "pdf"
        assert task.get("source_type") == "package"
        assert task.get("is_pdf") is True
        assert task.get("icon") == "pdf"
        assert task.get("open_action") == "space_pdf"
        assert task.get("package_backed") is True
        assert task.get("available") is True

        hydrated = next(row for row in app.lesson_tasks_for_user(username, username) if row.get("path") == path)
        assert selected(task) == selected(hydrated)
        retry = app.add_lesson_task(username, path, username, creator_role="user")
        assert retry.get("changed") is False
        assert selected(retry.get("task") or {}) == selected(task)
        print("pdf_task_add_canonical_schema=ok add=hydrated retry=identical pdf=openable")
        return 0
    finally:
        getattr(app, "LESSON_TASK_ADD_RETRY_CACHE", {}).clear()
        if original:
            app.server_database_write_lesson_task_record(username, original)
        else:
            app.server_database_delete_lesson_task_record(username)


if __name__ == "__main__":
    raise SystemExit(main())
