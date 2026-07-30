"""Regression checks that file and folder links share original-file progress."""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from FUTURE import server_app as app


# Added 2026-07-21: lock the canonical progress identity contract for both link types.
def main() -> int:
    manifest = app.get_server_data_manifest()
    entries = [
        item
        for rows in (manifest.get("folders") or {}).values()
        for item in (rows if isinstance(rows, list) else [])
        if isinstance(item, dict)
    ]

    file_link = next((
        item
        for item in entries
        if item.get("type") == "file"
        and app.clean_path_value(item.get("link_target", ""))
        and app.clean_path_value(item.get("path", "")).lower().startswith("hung/")
    ), None)
    if file_link:
        file_alias = app.clean_path_value(file_link["path"])
        file_original = app.clean_path_value(file_link["link_target"])
        file_identity = app.space_progress_identity_for_path(file_alias, "hung")
        assert file_identity["path"].lower() == file_original.lower()
        assert file_identity["legacy_path"].lower() == file_alias.lower()
        assert app.normalize_space_w_progress_path(file_alias, "hung").lower() == file_original.lower()

    folder_link = next(
        item
        for item in entries
        if item.get("type") == "folder"
        and app.clean_path_value(item.get("link_target", ""))
        and app.clean_path_value(item.get("path", "")).lower().startswith("quynh/")
    )
    folder_alias = app.clean_path_value(folder_link["path"])
    folder_original = app.clean_path_value(folder_link["link_target"])
    original_child = next(
        app.clean_path_value(item.get("path", ""))
        for item in entries
        if item.get("type") == "file"
        and app.clean_path_value(item.get("path", "")).lower().startswith(folder_original.lower() + "/")
    )
    child_suffix = original_child[len(folder_original) :].lstrip("/")
    linked_child = f"{folder_alias}/{child_suffix}"
    child_identity = app.space_progress_identity_for_path(linked_child, "quynh")
    assert child_identity["path"].lower() == original_child.lower()
    assert child_identity["legacy_path"].lower() == linked_child.lower()
    assert app.normalize_space_w_progress_path(linked_child, "quynh").lower() == original_child.lower()
    completion_source = app.lesson_completion_source_for_request(
        linked_child,
        "quynh",
        child_identity["lesson_id"],
    )
    assert completion_source["effective_path"].lower() == original_child.lower()
    assert completion_source["lesson_id"] == child_identity["lesson_id"]
    assert completion_source["admin_run"] is False
    assert completion_source["display_path"].lower() == linked_child.lower()
    assert completion_source["effective_path"].lower() == original_child.lower()
    assert completion_source["link_path"].lower() == linked_child.lower()
    assert completion_source["task_owner"].lower() == "quynh"
    restored_last_file = app.normalize_lesson_last_file_row({
        "path": linked_child,
        "lesson_id": child_identity["lesson_id"],
        "task_owner": "quynh",
    }, "quynh", trusted_persisted=True)
    assert restored_last_file["path"].lower() == linked_child.lower()
    assert restored_last_file["lesson_id"] == child_identity["lesson_id"]

    record_path = file_original if file_link else original_child
    record_alias = file_alias if file_link else linked_child
    record_user = "hung" if file_link else "quynh"
    record = {
        "path": record_path,
        "nodeCount": 7,
        "state": {"learned": ["one", "two", "three"]},
        "updatedAt": "2026-07-21T03:00:00Z",
        "runId": "link-progress-test",
        "activeRun": True,
    }
    progress_index = {("Space_V", record_path.lower()): record}
    original_summary = app.lesson_progress_summary_from_index(
        progress_index,
        record_user,
        record_path,
        ".Space_V",
        alias_paths=[record_alias, record_path],
        strict_paths=True,
    )
    link_summary = app.lesson_progress_summary_from_index(
        progress_index,
        record_user,
        record_alias,
        ".Space_V",
        alias_paths=[record_alias, record_path],
        strict_paths=True,
    )
    assert original_summary["text"] == "3/7"
    assert link_summary == original_summary

    print("server_data_link_progress_identity=ok file_link=canonical folder_link_child=canonical completion=canonical last_file=display_path original_link_same_progress=true")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
