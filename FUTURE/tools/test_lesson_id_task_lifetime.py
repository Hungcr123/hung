"""Verify canonical lesson_id lifetime and time are identical on task cards."""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from FUTURE import server_app as app


def main() -> int:
    username = "hung"
    file_id = "ftg-lesson-000002312"
    progress_index = app.lesson_progress_record_index(username)
    canonical = progress_index.get(("Space_V", f"id:{file_id}")) or {}
    expected_runs = app.lesson_progress_completed_runs(canonical, "Space_V")
    expected_seconds = 6966
    payload = app.build_lesson_tasks_response_cache_row(username, username, False)["payload"]
    matches = [row for row in payload.get("tasks", []) if row.get("file_id") == file_id]
    assert matches, "canonical lesson task is missing"
    for row in matches:
        study = row.get("study") if isinstance(row.get("study"), dict) else {}
        assert int(study.get("mine", 0) or 0) == expected_runs == 12
        assert int(study.get("completedRuns", 0) or 0) == expected_runs
        assert int(study.get("time_seconds", 0) or 0) == expected_seconds == 6966
    snapshot = app.lesson_progress_snapshot_for_client(username)
    snapshot_matches = [
        item for item in (snapshot.get("items") or {}).values()
        if isinstance(item, dict)
        and int(((item.get("study") or {}).get("completedRuns", 0) or 0)) == expected_runs
        and "File 02" in str(item.get("path", ""))
    ]
    assert snapshot_matches, "login progress snapshot is missing the canonical lesson"
    assert any(int(((item.get("study") or {}).get("time_seconds", 0) or 0)) == expected_seconds for item in snapshot_matches)
    print(f"lesson_id_task_lifetime=ok tasks={len(matches)} snapshots={len(snapshot_matches)} runs={expected_runs} seconds={expected_seconds}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
