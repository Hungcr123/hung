"""Ensure the heartbeat wrapper reuses its already validated effective lesson path."""

from __future__ import annotations

import ast
import json
import sys
from pathlib import Path


ROOT = Path(__file__).parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from FUTURE import server_app as app


def main() -> int:
    source_path = ROOT / "FUTURE" / "server_parts" / "server_data_pdf_qmdict" / "02_lesson_study_progress.py"
    tree = ast.parse(source_path.read_text(encoding="utf-8"), filename=str(source_path))
    function = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "add_lesson_study_time")
    calls = [node.func.id for node in ast.walk(function) if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)]
    assert calls.count("normalize_space_w_progress_path") == 1
    assert "lesson_time_identity" not in calls

    manifest = json.loads(Path(r"C:\server data\_future_server_data_manifest.json").read_text(encoding="utf-8"))
    paths = []
    for entries in (manifest.get("folders") or {}).values():
        for entry in entries if isinstance(entries, list) else []:
            path = str(entry.get("path") or "") if isinstance(entry, dict) else ""
            if path.lower().startswith("common/") and app.is_lesson_file(Path(path)):
                paths.append(path)
            if len(paths) >= 100:
                break
        if len(paths) >= 100:
            break
    assert len(paths) == 100
    for path in paths:
        normalized = app.normalize_space_w_progress_path(path, "codexload001")
        previous = app.lesson_time_identity(normalized, "codexload001")
        file_id = str(previous.get("file_id") or "")
        if file_id:
            assert previous.get("source") == f"file_id:{file_id}"
            assert app.lesson_time_key(normalized) == app.lesson_time_key(previous.get("legacy_source", ""))
        else:
            assert app.lesson_time_key(normalized) == app.lesson_time_key(previous.get("source", ""))
    print("lesson_time_path_identity=ok paths=100 filesystem_resolve_per_wrapper=1 id_first_with_path_fallback=true")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
