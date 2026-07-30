"""Regression for RAM-manifest linked-folder navigation and dirty fallback."""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from FUTURE import server_app as app


# Added 2026-07-21: clean folder links must avoid target enumeration; dirty manifests retain the safe fallback.
def main() -> int:
    manifest = app.get_server_data_manifest(force=False)
    link = next(
        dict(entry)
        for rows in (manifest.get("folders") or {}).values()
        for entry in (rows if isinstance(rows, list) else [])
        if isinstance(entry, dict)
        and entry.get("type") == "folder"
        and app.clean_path_value(entry.get("link_target", ""))
        and app.clean_path_value(entry.get("path", "")).lower() == "quynh/empower a1 - link 2"
    )
    path = app.clean_path_value(link["path"])
    original_virtual_entry = app.server_data_virtual_link_entry
    original_read_folder_link = app.read_server_data_folder_link_payload
    original_space_task_settings = app.space_task_settings_for_user
    original_dirty = bool(app.SERVER_DATA_MANIFEST_STATE.get("dirty"))
    disk_calls = 0

    def unexpected_disk(*_args, **_kwargs):
        raise AssertionError("clean folder-link navigation enumerated the target directory")

    try:
        app.SERVER_DATA_MANIFEST_STATE["dirty"] = False
        app.server_data_virtual_link_entry = unexpected_disk
        app.space_task_settings_for_user = lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("lightweight linked navigation loaded deferred Space Task settings")
        )
        payload = app.list_server_data(
            path,
            username="quynh",
            fresh=True,
            lightweight=True,
            include_task_board=False,
            include_space_task=False,
        )
        assert payload.get("entries")
        assert all(entry.get("managed_mirror") for entry in payload["entries"])
        assert all(app.clean_path_value(entry.get("path", "")).lower().startswith(path.lower() + "/") for entry in payload["entries"])
        assert all(app.clean_path_value(entry.get("effective_path", "")) for entry in payload["entries"])

        root_only = Path(r"C:\server data\Sonanh\Empower B1").resolve()

        def root_marker_only(folder: Path):
            try:
                if Path(folder).resolve() != root_only:
                    return {}
            except Exception:
                return {}
            return original_read_folder_link(root_only)

        app.read_server_data_folder_link_payload = root_marker_only
        nested_path = "Sonanh/Empower B1/Từ vựng - [142 Files] - {3375 words}/Unit 01 - [36 Files] - {889 words}"
        nested = app.list_server_data(
            nested_path,
            username="Sonanh",
            fresh=True,
            lightweight=True,
            include_task_board=False,
            include_space_task=False,
        )
        assert nested.get("entries")
        assert all(entry.get("managed_mirror") for entry in nested["entries"])
        app.read_server_data_folder_link_payload = original_read_folder_link

        def counted_disk(*args, **kwargs):
            nonlocal disk_calls
            disk_calls += 1
            return original_virtual_entry(*args, **kwargs)

        app.SERVER_DATA_MANIFEST_STATE["dirty"] = True
        app.server_data_virtual_link_entry = counted_disk
        fallback = app.list_server_data(
            path,
            username="quynh",
            fresh=True,
            lightweight=True,
            include_task_board=False,
            include_space_task=False,
        )
        assert fallback.get("entries")
        assert disk_calls > 0
    finally:
        app.server_data_virtual_link_entry = original_virtual_entry
        app.read_server_data_folder_link_payload = original_read_folder_link
        app.space_task_settings_for_user = original_space_task_settings
        app.SERVER_DATA_MANIFEST_STATE["dirty"] = original_dirty

    print("folder_link_manifest_fast_path=ok clean=ram_manifest dirty=disk_fallback semantics=live")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
