"""Regression for the structured-lesson ID fast path used by /lesson/time."""

from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from FUTURE import server_app as app


def main() -> int:
    manifest = json.loads(Path(r"C:\server data\_future_server_data_manifest.json").read_text(encoding="utf-8"))
    path = ""
    lesson_id = ""
    private_path = ""
    private_lesson_id = ""
    for entries in (manifest.get("folders") or {}).values():
        for entry in entries if isinstance(entries, list) else []:
            candidate = str(entry.get("path") or "") if isinstance(entry, dict) else ""
            candidate_id = str(entry.get("lesson_id") or "") if isinstance(entry, dict) else ""
            if candidate.lower().startswith("common/") and candidate.lower().endswith(".space_v") and candidate_id:
                path, lesson_id = candidate, candidate_id
            if candidate.lower().startswith("hung/") and candidate.lower().endswith(".space_v") and candidate_id:
                private_path, private_lesson_id = candidate, candidate_id
        if path and private_path:
            break
    assert path and lesson_id and private_path and private_lesson_id
    assert app.server_database_lesson_file_id_for_path(path) == lesson_id

    original_normalize = app.normalize_space_w_progress_path
    original_add = app.server_database_add_lesson_time
    calls = {"normalize": 0, "db": None}

    def tracked_normalize(value, username, admin=False):
        calls["normalize"] += 1
        return original_normalize(value, username, admin=admin)

    def fake_add(*args, **kwargs):
        calls["db"] = (args, kwargs)
        return {"acceptedSeconds": 0, "heartbeatReason": "replay"}

    app.normalize_space_w_progress_path = tracked_normalize
    app.server_database_add_lesson_time = fake_add
    try:
        app.add_lesson_study_time("codexload001", {"path": path, "lesson_id": lesson_id, "seconds": 1})
        assert calls["normalize"] == 0
        fast_args = calls["db"][0]
        assert fast_args[1] == app.lesson_time_key(f"file_id:{lesson_id}")

        app.add_lesson_study_time("codexload001", {"path": path, "seconds": 1})
        fallback_args = calls["db"][0]
        assert calls["normalize"] == 1
        assert fast_args[:7] == fallback_args[:7]

        app.add_lesson_study_time("codexload001", {"path": path, "lesson_id": "ftg-lesson-invalid", "seconds": 1})
        assert calls["normalize"] == 2

        try:
            app.add_lesson_study_time("codexload001", {"path": private_path, "lesson_id": private_lesson_id, "seconds": 1})
            raise AssertionError("Cross-user lesson path was accepted")
        except RuntimeError:
            pass
        assert calls["normalize"] == 3

        original_alias_reader = app.server_database_lesson_file_id_for_path
        app.server_database_lesson_file_id_for_path = lambda _value="": ""
        try:
            app.add_lesson_study_time("codexload001", {"path": path, "lesson_id": lesson_id, "seconds": 1})
        finally:
            app.server_database_lesson_file_id_for_path = original_alias_reader
        assert calls["normalize"] == 4

        pdf_path = path.rsplit(".", 1)[0] + ".pdf"
        try:
            app.add_lesson_study_time("codexload001", {"path": pdf_path, "lesson_id": lesson_id, "seconds": 1})
        except RuntimeError:
            pass
        assert calls["normalize"] == 5
    finally:
        app.normalize_space_w_progress_path = original_normalize
        app.server_database_add_lesson_time = original_add

    print("lesson_time_id_fast_path=ok active_alias=true resolver_equal=true mismatch_fallback=true cross_user_denied=true stale_alias_fallback=true pdf_path_fallback=true")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
