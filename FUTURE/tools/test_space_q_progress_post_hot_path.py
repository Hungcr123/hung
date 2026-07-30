"""Regressions for idempotent SQLite-authoritative Space_Q autosaves."""

import sys
from pathlib import Path


ROOT = Path(__file__).parents[2]
sys.path.insert(0, str(ROOT))

from FUTURE import server_app as app


SOURCE = ROOT / "FUTURE" / "server_parts" / "progress_inventory_vocab" / "02_space_q_progress.py"
ROUTE = ROOT / "FUTURE" / "server_parts" / "http_server" / "post_route_parts" / "05_vocab_progress_leaderboard.pyfrag"
CLIENT = ROOT / "FUTURE" / "web" / "js_parts" / "13_translation_vocab_sync.js"
SNAPSHOT = ROOT / "FUTURE" / "web" / "js_parts" / "21_progress_bootstrap_events.js"


# Added 2026-07-21: lock Space_Q single-entry writes, retry IDs, compact ACKs, and local-state reconstruction.
def main() -> int:
    source = SOURCE.read_text(encoding="utf-8")
    start = source.index("def save_space_q_progress(")
    end = source.index("\ndef clear_space_q_progress", start)
    function = source[start:end]
    assert "clone_space_progress_payload" not in function
    assert "space_w_progress_semantic_identity(existing)" in function
    assert "sqlite_authoritative=True" in function
    assert "syncOperationId" in function
    assert "remember_space_progress_store(" not in function

    base = {
        "path": "common/probe.Space_Q",
        "identity": "probe",
        "savedAt": "2026-07-21T00:00:00Z",
        "updatedAt": "2026-07-21T00:00:01Z",
        "syncOperationId": "space-q-probe",
        "state": {"savedAt": "2026-07-21T00:00:00Z", "questionDone": 1, "questionTotal": 20},
        "_serverRevision": 7,
    }
    retry = {**base, "updatedAt": "2026-07-21T00:00:09Z", "_serverRevision": 99}
    assert app.space_w_progress_semantic_identity(base) == app.space_w_progress_semantic_identity(retry)
    compact = app.space_w_progress_compact_response(base)
    assert compact["syncOperationId"] == "space-q-probe"
    assert compact["_serverRevision"] == 7
    assert "state" not in compact

    route = ROUTE.read_text(encoding="utf-8")
    route_start = route.index('if path == "/space-q/progress":')
    route_end = route.index('if path == "/space-v/progress":', route_start)
    progress_route = route[route_start:route_end]
    assert 'compact_response = clean((query.get("response")' in progress_route
    assert '"space-q-progress-compact-v1"' in progress_route
    assert "request_operation_id == progress_operation_id" in progress_route

    client = CLIENT.read_text(encoding="utf-8")
    assert '"/space-q/progress?client_source=space_q_progress_save&response=compact-v1"' in client
    assert '"/space-q/progress?client_source=offline_outbox&response=compact-v1"' in client
    assert "canonicalRecord = record && record.state" in client
    snapshot = SNAPSHOT.read_text(encoding="utf-8")
    assert "createQuestionProgressOperationId" in snapshot
    assert "snapshot.syncOperationId = createQuestionProgressOperationId()" in snapshot
    print("space_q_progress_post_hot_path=ok single_entry=true idempotent=true compact_ack=true local_state=true")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
