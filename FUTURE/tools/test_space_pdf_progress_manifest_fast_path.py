"""Verify Space_PDF progress trusts a clean manifest and falls back safely when dirty."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from FUTURE import server_app as app


def main() -> int:
    manifest = app.get_server_data_manifest()
    candidate = next(
        app.clean_path_value(item.get("path", ""))
        for rows in (manifest.get("folders") or {}).values()
        for item in (rows if isinstance(rows, list) else [])
        if isinstance(item, dict)
        and app.clean_path_value(item.get("path", "")).lower().startswith("common/")
        and app.clean_path_value(item.get("path", "")).lower().endswith(".pdf")
    )
    previous_dirty = bool(app.SERVER_DATA_MANIFEST_STATE.get("dirty"))
    original_safe_path = app.safe_server_data_path
    original_manifest_lookup = app.server_data_manifest_file_entry
    original_identity_for_path = app.space_progress_identity_for_path
    original_load_store = app.load_space_progress_store
    try:
        app.SERVER_DATA_MANIFEST_STATE["dirty"] = False

        def unexpected_filesystem(*_args, **_kwargs):
            raise AssertionError("clean Space_PDF manifest identity touched filesystem")

        app.safe_server_data_path = unexpected_filesystem
        direct = app.space_pdf_progress_identity_for_source(
            "codexload001", {"path": candidate, "identity": "manifest-direct"}
        )
        assert direct["path"] == candidate, direct

        alias = "common/codex-space-pdf-link.pdf"
        target_entry = original_manifest_lookup(candidate)
        assert isinstance(target_entry, dict)

        def linked_lookup(path: str):
            normalized = app.clean_path_value(path)
            if normalized == alias:
                return {"type": "file", "path": alias, "link_target": candidate}
            if normalized == candidate:
                return dict(target_entry)
            return None

        app.server_data_manifest_file_entry = linked_lookup
        linked = app.space_pdf_progress_identity_for_source(
            "codexload001", {"path": alias, "identity": "manifest-link"}
        )
        assert linked["path"] == candidate and linked["legacy_path"] == alias, linked

        read_identity = "manifest-read"
        read_key = app.space_pdf_progress_key("codexload001", candidate, read_identity)
        expected_record = {"path": candidate, "identity": read_identity, "page": 7, "pages": 20}
        app.server_data_manifest_file_entry = original_manifest_lookup
        app.space_progress_identity_for_path = unexpected_filesystem
        app.load_space_progress_store = lambda _space, _user: {
            "payload": {"version": 1, "states": {read_key: expected_record}}
        }
        read_record = app.read_space_pdf_progress("codexload001", candidate, read_identity)
        assert read_record == expected_record, read_record

        fallback_calls = 0

        def counted_safe_path(*args, **kwargs):
            nonlocal fallback_calls
            fallback_calls += 1
            return original_safe_path(*args, **kwargs)

        app.server_data_manifest_file_entry = original_manifest_lookup
        app.safe_server_data_path = counted_safe_path
        app.SERVER_DATA_MANIFEST_STATE["dirty"] = True
        fallback = app.space_pdf_progress_identity_for_source(
            "codexload001", {"path": candidate, "identity": "manifest-dirty"}
        )
        assert fallback["path"] == candidate and fallback_calls == 1, (fallback, fallback_calls)

        read_fallback_calls = 0

        def counted_identity_for_path(*_args, **_kwargs):
            nonlocal read_fallback_calls
            read_fallback_calls += 1
            return {"path": candidate}

        app.space_progress_identity_for_path = counted_identity_for_path
        dirty_read = app.read_space_pdf_progress("codexload001", candidate, read_identity)
        assert dirty_read == expected_record and fallback_calls == 2 and read_fallback_calls == 0, (
            dirty_read,
            fallback_calls,
            read_fallback_calls,
        )
    finally:
        app.safe_server_data_path = original_safe_path
        app.server_data_manifest_file_entry = original_manifest_lookup
        app.space_progress_identity_for_path = original_identity_for_path
        app.load_space_progress_store = original_load_store
        app.SERVER_DATA_MANIFEST_STATE["dirty"] = previous_dirty

    print("space_pdf_progress_manifest_fast_path=ok post=no-stat get=no-stat link=canonical dirty=safe-path-fallback")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
