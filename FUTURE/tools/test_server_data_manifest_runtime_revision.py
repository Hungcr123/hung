"""Regression checks for cheap delta revisions versus full-tree integrity signatures."""

from __future__ import annotations

import copy
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from FUTURE import server_app as app


def main() -> int:
    folders = {
        "": [
            {"type": "folder", "path": "common", "name": "common"},
            {"type": "folder", "path": "hung", "name": "hung"},
            {"type": "folder", "path": "quynh", "name": "quynh"},
        ],
        "common": [{"type": "file", "path": "common/demo.Space_P", "size": 100, "modified_ns": 10}],
        "hung": [],
        "quynh": [],
    }
    manifest = {
        "signature": "integrity-v1",
        "runtime_revision": "runtime-v1",
        "runtime_root_revision_version": 1,
        "runtime_root_revisions": {"common": "common-v1", "hung": "hung-v1", "quynh": "quynh-v1"},
        "folders": copy.deepcopy(folders),
    }
    assert app.server_data_manifest_runtime_revision(manifest) == "runtime-v1"

    stale_root_manifest = copy.deepcopy(manifest)
    stale_root_manifest["runtime_root_revisions"]["codexload001"] = "stale-v1"
    stale_revision = stale_root_manifest["runtime_revision"]
    app.ensure_server_data_manifest_runtime_revisions(stale_root_manifest)
    assert "codexload001" not in stale_root_manifest["runtime_root_revisions"]
    assert stale_root_manifest["runtime_revision"] != stale_revision

    deleted_root_manifest = copy.deepcopy(manifest)
    deleted_root_manifest["runtime_root_revisions"]["codexload001"] = "stale-v1"
    app.update_server_data_manifest_runtime_revision(deleted_root_manifest, "before", "after", ["codexload001"])
    assert "codexload001" not in deleted_root_manifest["runtime_root_revisions"]

    legacy_scoped = {"signature": "integrity-v1", "runtime_revision": "runtime-old", "folders": copy.deepcopy(folders)}
    common_before = app.server_data_manifest_runtime_revision(legacy_scoped, {"common"})
    legacy_scoped["runtime_revision"] = "runtime-new"
    assert app.server_data_manifest_runtime_revision(legacy_scoped, {"common"}) == common_before

    before = app.server_data_manifest_paths_fingerprint(manifest["folders"], ["common"])
    changed_folders = copy.deepcopy(manifest["folders"])
    changed_folders["common"][0]["size"] = 101
    after = app.server_data_manifest_paths_fingerprint(changed_folders, ["common"])
    assert before != after
    manifest["folders"] = changed_folders
    hung_before = app.server_data_manifest_runtime_revision(manifest, {"common", "hung"})
    quynh_before = app.server_data_manifest_runtime_revision(manifest, {"common", "quynh"})
    revision = app.update_server_data_manifest_runtime_revision(manifest, before, after, ["common"])
    assert revision and revision != "runtime-v1"
    assert manifest["signature"] == "integrity-v1"
    assert app.server_data_manifest_runtime_revision(manifest, {"common", "hung"}) != hung_before
    assert app.server_data_manifest_runtime_revision(manifest, {"common", "quynh"}) != quynh_before

    unchanged = app.update_server_data_manifest_runtime_revision(manifest, after, after, ["common"])
    assert unchanged == revision
    assert manifest["runtime_revision"] == revision

    private_before = app.server_data_manifest_runtime_revision(manifest, {"common", "hung"})
    other_before = app.server_data_manifest_runtime_revision(manifest, {"common", "quynh"})
    private_folders = copy.deepcopy(manifest["folders"])
    private_before_fp = app.server_data_manifest_paths_fingerprint(private_folders, ["hung"])
    private_folders["hung"] = [{"type": "file", "path": "hung/private.Space_V", "size": 50, "modified_ns": 30}]
    private_after_fp = app.server_data_manifest_paths_fingerprint(private_folders, ["hung"])
    manifest["folders"] = private_folders
    app.update_server_data_manifest_runtime_revision(manifest, private_before_fp, private_after_fp, ["hung"])
    assert app.server_data_manifest_runtime_revision(manifest, {"common", "hung"}) != private_before
    assert app.server_data_manifest_runtime_revision(manifest, {"common", "quynh"}) == other_before

    original_manifest_path = app.server_data_manifest_path
    original_should_skip = app.server_data_manifest_should_skip
    try:
        app.server_data_manifest_path = lambda _path: Path(r"C:\definitely-missing-codex-root")
        app.server_data_manifest_should_skip = lambda _path: False
        deletion_folders = {
            "": [{"type": "folder", "path": "common"}, {"type": "folder", "path": "codexload001"}],
            "codexload001": [{"type": "file", "path": "codexload001/demo.Space_P"}],
        }
        assert app.update_server_data_manifest_top_root_entry(deletion_folders, "codexload001") is True
        assert all(str(entry.get("path", "")).lower() != "codexload001" for entry in deletion_folders[""])
        assert app.remove_server_data_manifest_subtree(deletion_folders, "codexload001") == 1
        assert "codexload001" not in deletion_folders
    finally:
        app.server_data_manifest_path = original_manifest_path
        app.server_data_manifest_should_skip = original_should_skip

    route_source = (ROOT / "FUTURE/server_parts/http_server/get_route_parts/03_auth_dashboard_server_data.pyfrag").read_text(encoding="utf-8")
    assert "manifest_signature = server_data_tree_runtime_revision(username, admin_view, manifest)" in route_source
    assert '"integrity_signature": clean(manifest.get("signature", ""))' in route_source

    print("server_data_manifest_runtime_revision=ok delta=changes duplicate=stable roots=isolated top_delete=delta integrity=preserved tree_etag=runtime")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
