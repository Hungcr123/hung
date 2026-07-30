"""Regressions for idempotent SQLite-authoritative Space_W autosaves."""

import sys
from pathlib import Path


ROOT = Path(__file__).parents[2]
sys.path.insert(0, str(ROOT))

from FUTURE import server_app as app


SOURCE = ROOT / "FUTURE" / "server_parts" / "progress_inventory_vocab" / "01_space_w_progress.py"
ROUTE = ROOT / "FUTURE" / "server_parts" / "http_server" / "post_route_parts" / "05_vocab_progress_leaderboard.pyfrag"
DATABASE = ROOT / "FUTURE" / "server_parts" / "06a_server_database.py"


# Added 2026-07-21: lock the one-record, no-op retry, compact ACK, and atomic legacy-key contracts.
def main() -> int:
    source = SOURCE.read_text(encoding="utf-8")
    start = source.index("def save_space_w_progress(")
    end = source.index("\ndef clear_space_w_progress", start)
    function = source[start:end]
    assert "clone_space_progress_payload" not in function
    assert "space_w_progress_semantic_identity(existing)" in function
    assert "sqlite_authoritative=True" in function
    assert "syncOperationId" in function
    assert "remember_space_progress_store(" not in function
    assert "def space_w_progress_compact_response(" in source

    base = {
        "path": "common/probe.Space_W",
        "identity": "probe",
        "savedAt": "2026-07-21T00:00:00Z",
        "updatedAt": "2026-07-21T00:00:01Z",
        "syncOperationId": "space-w-probe",
        "state": {"savedAt": "2026-07-21T00:00:00Z", "progressDone": 1, "progressTotal": 4},
        "_serverRevision": 7,
    }
    retry = {**base, "updatedAt": "2026-07-21T00:00:09Z", "_serverRevision": 99}
    assert app.space_w_progress_semantic_identity(base) == app.space_w_progress_semantic_identity(retry)
    compact = app.space_w_progress_compact_response(base)
    assert compact["syncOperationId"] == "space-w-probe"
    assert compact["_serverRevision"] == 7
    assert "state" not in compact

    route = ROUTE.read_text(encoding="utf-8")
    route_start = route.index('if path == "/space-w/progress":')
    route_end = route.index('if path == "/space-q/progress":', route_start)
    progress_route = route[route_start:route_end]
    assert 'compact_response = clean((query.get("response")' in progress_route
    assert '"space-w-progress-compact-v1"' in progress_route
    assert "request_operation_id == progress_operation_id" in progress_route

    database = DATABASE.read_text(encoding="utf-8")
    db_start = database.index("def server_database_apply_progress_entry(")
    db_end = database.index("\ndef server_database_replace_progress_payload", db_start)
    db_function = database[db_start:db_end]
    assert "legacy_key" in db_function
    assert db_function.index("DELETE FROM lesson_progress") < db_function.index("_server_database_progress_upsert")
    print("space_w_progress_post_hot_path=ok single_entry=true idempotent=true compact_ack=true sqlite_only=true legacy_key_atomic=true")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
