"""Regressions for idempotent SQLite-authoritative Space_V autosaves."""

import sys
from pathlib import Path


ROOT = Path(__file__).parents[2]
sys.path.insert(0, str(ROOT))

from FUTURE import server_app as app


SOURCE = ROOT / "FUTURE" / "server_parts" / "progress_inventory_vocab" / "03_space_v_progress.py"
ROUTE = ROOT / "FUTURE" / "server_parts" / "http_server" / "post_route_parts" / "05_vocab_progress_leaderboard.pyfrag"
CLIENT = ROOT / "FUTURE" / "web" / "js_parts" / "14_vocab_sync_tasks.js"


# Added 2026-07-21: lock Space_V one-row writes, retry IDs, compact ACKs, and callback dedupe.
def main() -> int:
    source = SOURCE.read_text(encoding="utf-8")
    start = source.index("def save_space_v_progress(")
    end = source.index("\ndef clear_space_v_progress", start)
    function = source[start:end]
    assert "clone_space_progress_payload" not in function
    assert "space_v_progress_semantic_identity(existing)" in function
    assert "preserve_space_v_progress_context(existing" in function
    assert "sqlite_authoritative=True" in function
    assert "syncOperationId" in function
    assert "server_database_apply_progress_entry" not in function

    base = {
        "path": "common/probe.Space_V",
        "identity": "probe",
        "savedAt": "2026-07-21T00:00:00Z",
        "updatedAt": "2026-07-21T00:00:01Z",
        "syncOperationId": "space-v-probe",
        "state": {"savedAt": "2026-07-21T00:00:00Z", "learned": ["one"], "learnedCount": 1},
        "_serverRevision": 7,
    }
    retry = {
        **base,
        "savedAt": "2026-07-21T00:00:09Z",
        "updatedAt": "2026-07-21T00:00:09Z",
        "syncOperationId": "space-v-fresh-open",
        "_serverRevision": 99,
        "state": {
            **base["state"],
            "savedAt": "2026-07-21T00:00:09Z",
            "syncOperationId": "space-v-fresh-open",
        },
    }
    assert app.space_v_progress_semantic_identity(base) == app.space_v_progress_semantic_identity(retry)
    changed = {**retry, "state": {**retry["state"], "learned": ["one", "two"], "learnedCount": 2}}
    assert app.space_v_progress_semantic_identity(base) != app.space_v_progress_semantic_identity(changed)
    enriched = {
        **base,
        "state": {
            **base["state"],
            "effective_path": "common/probe.Space_V",
            "lessonSource": {"study": {"progress": {"done": 1, "total": 10}, "time": {"seconds": 42}}},
        },
    }
    stripped = {**retry, "state": {**retry["state"], "effective_path": "", "lessonSource": {"study": {"users": 2}}}}
    preserved = app.preserve_space_v_progress_context(enriched, stripped)
    assert preserved["state"]["effective_path"] == "common/probe.Space_V"
    assert preserved["state"]["lessonSource"] == enriched["state"]["lessonSource"]
    compact = app.space_v_progress_compact_response(base)
    assert compact["syncOperationId"] == "space-v-probe"
    assert compact["_serverRevision"] == 7
    assert compact["state"]["learnedCount"] == 1

    route = ROUTE.read_text(encoding="utf-8")
    route_start = route.index('if path == "/space-v/progress":')
    route_end = route.index('if path == "/space-p/progress":', route_start)
    progress_route = route[route_start:route_end]
    assert progress_route.count('query = parse_qs(urlparse(self.path).query)') == 1
    assert '"space-v-progress-compact-v1"' in progress_route

    client = CLIENT.read_text(encoding="utf-8")
    assert "createVocabProgressOperationId" in client
    assert "vocabProgressSemanticSignature" in client
    assert "state.syncOperationId = createVocabProgressOperationId()" in client
    assert "vocabProgressLastSemanticSignature = semanticSignature" in client
    print("space_v_progress_post_hot_path=ok single_entry=true idempotent=true compact_ack=true callback_dedupe=true sqlite_only=true")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
