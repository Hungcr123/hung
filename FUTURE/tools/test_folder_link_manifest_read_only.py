"""Ensure manifest scans never materialize child folder-link markers."""

from __future__ import annotations

import ast
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from FUTURE import server_app as app


def function_calls(path: Path, name: str) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    function = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == name)
    return {
        node.func.id
        for node in ast.walk(function)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }


# Added 2026-07-21: folder-link scans are derived reads; only explicit copy-link may create the root marker.
def main() -> int:
    source = ROOT / "FUTURE" / "server_parts" / "server_data_pdf_qmdict" / "server_data_manifest_listing" / "01_manifest_build_scan.py"
    for name in ("scan_server_data_manifest_folder", "scan_server_data_manifest_folder_delta"):
        assert "write_server_data_folder_link_marker" not in function_calls(source, name)

    linked_root = Path(r"C:\server data\Sonanh\Empower B1")
    assert app.read_server_data_folder_link_payload(linked_root)
    original_write = app.write_server_data_folder_link_marker
    try:
        app.write_server_data_folder_link_marker = lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("manifest scan attempted to write a child link marker")
        )
        full = {}
        app.scan_server_data_manifest_folder(linked_root, full)
        assert full.get("Sonanh/Empower B1") == []
        delta = {"Sonanh/Empower B1": [{"type": "folder", "path": "stale"}]}
        app.scan_server_data_manifest_folder_delta(linked_root, delta, {"Sonanh/Empower B1"})
        assert delta.get("Sonanh/Empower B1") == []
    finally:
        app.write_server_data_folder_link_marker = original_write

    print("folder_link_manifest_read_only=ok propagated_marker_writes=0 root_only=true")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
