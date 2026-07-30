"""Verify private Lesson Vault roots never reuse the common-only tree cache identity."""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from FUTURE import server_app as app


def main() -> int:
    manifest = app.get_server_data_manifest(force=False)
    folders = manifest.get("folders") if isinstance(manifest.get("folders"), dict) else {}
    checked = []
    for username in ("hung", "hungcr", "quynh"):
        if not isinstance(folders.get(username), list):
            continue
        snapshot_username, identity = app.server_data_tree_snapshot_identity(username, False, manifest)
        assert snapshot_username == username
        assert identity != "__shared_common_only__"
        payload = app.build_server_data_tree_snapshot(snapshot_username, admin=False)
        rows = payload.get("rows") if isinstance(payload.get("rows"), list) else []
        paths = {app.clean_path_value(row.get("path", "")).lower() for row in rows if isinstance(row, dict)}
        assert "common" in paths and username.lower() in paths
        root_row = next(row for row in rows if app.clean_path_value(row.get("path", "")).lower() == "")
        columns = payload.get("entry_columns") if isinstance(payload.get("entry_columns"), list) else []
        path_index = columns.index("path")
        root_paths = {
            app.clean_path_value(values[path_index]).lower()
            for values in (root_row.get("entries") or [])
            if isinstance(values, list) and len(values) > path_index
        }
        assert username.lower() in root_paths
        checked.append(username)
    assert checked
    empty_username, empty_identity = app.server_data_tree_snapshot_identity("codexload001", False, manifest)
    assert empty_username == "" and empty_identity == "__shared_common_only__"
    print(f"server_data_tree_private_roots=ok users={','.join(checked)} common_only_shared=true")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
