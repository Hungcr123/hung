"""Regression checks for clean-manifest task path and metadata reuse."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from FUTURE import server_app as app


def main() -> int:
    manifest = app.get_server_data_manifest()
    candidate = None
    for rows in (manifest.get("folders") or {}).values():
        for item in rows if isinstance(rows, list) else []:
            path = app.clean_path_value(item.get("path", "")) if isinstance(item, dict) else ""
            if path.lower().startswith("common/") and path.lower().endswith(".space_p"):
                candidate = path
                break
        if candidate:
            break
    assert candidate

    previous_dirty = bool(app.SERVER_DATA_MANIFEST_STATE.get("dirty"))
    original_file_signature = app.file_cache_signature
    original_dependency_signature = app.lesson_dependency_signature
    original_manifest_file_entry = app.server_data_manifest_file_entry
    try:
        app.SERVER_DATA_MANIFEST_STATE["dirty"] = False
        getattr(app, "LESSON_TASK_FILE_INFO_CACHE", {}).clear()
        app.clear_lesson_metadata_cache()
        info = app.lesson_task_file_info(candidate, "codexload001")
        assert info.get("from_manifest") is True
        assert info.get("file_exists") is True
        assert isinstance(info.get("manifest_entry"), dict)
        meta = app.cached_lesson_file_metadata(info["effective_target"], manifest_entry=info["manifest_entry"])
        assert meta

        def unexpected_signature(*_args, **_kwargs):
            raise AssertionError("clean-manifest cache hit touched filesystem signature")

        app.file_cache_signature = unexpected_signature
        app.lesson_dependency_signature = unexpected_signature
        cached = app.cached_lesson_file_metadata(info["effective_target"], manifest_entry=info["manifest_entry"])
        assert cached == meta

        app.SERVER_DATA_MANIFEST_STATE["dirty"] = True
        getattr(app, "LESSON_TASK_FILE_INFO_CACHE", {}).clear()
        fallback = app.lesson_task_file_info(candidate, "codexload001")
        assert not fallback.get("from_manifest")
        assert fallback.get("file_exists") is True

        app.SERVER_DATA_MANIFEST_STATE["dirty"] = False
        dependency_entry = {
            "type": "file",
            "path": candidate,
            "modified_ns": 100,
            "size": 480,
            "metadata_dependency_mtime_ns": 200,
            "metadata_dependency_size": 1000,
        }
        app.server_data_manifest_file_entry = lambda _path: dict(dependency_entry)
        dependency_before = app.lesson_tasks_file_dependency_signature("hung")
        dependency_entry["modified_ns"] = 101
        dependency_after = app.lesson_tasks_file_dependency_signature("hung")
        assert dependency_before != dependency_after
    finally:
        app.file_cache_signature = original_file_signature
        app.lesson_dependency_signature = original_dependency_signature
        app.server_data_manifest_file_entry = original_manifest_file_entry
        app.SERVER_DATA_MANIFEST_STATE["dirty"] = previous_dirty
        getattr(app, "LESSON_TASK_FILE_INFO_CACHE", {}).clear()
        app.clear_lesson_metadata_cache()

    print("lesson_task_manifest_fast_path=ok clean=no-stat dirty=filesystem-fallback metadata=revision-keyed response=file-revision")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
