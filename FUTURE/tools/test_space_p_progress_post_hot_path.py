"""Regressions for the shared Space_P/L/S idempotent progress route."""

import sys
from pathlib import Path


ROOT = Path(__file__).parents[2]
sys.path.insert(0, str(ROOT))

from FUTURE import server_app as app


SOURCE = ROOT / "FUTURE" / "server_parts" / "progress_inventory_vocab" / "04_space_p_pdf_progress.py"
ROUTE = ROOT / "FUTURE" / "server_parts" / "http_server" / "post_route_parts" / "05_vocab_progress_leaderboard.pyfrag"
CLIENT = ROOT / "FUTURE" / "web" / "js_parts" / "13_translation_vocab_sync.js"


# Added 2026-07-21: lock single-entry writes, P/L/S identity, retry IDs, compact ACKs, and callback dedupe.
def main() -> int:
    source = SOURCE.read_text(encoding="utf-8")
    start = source.index("def save_space_p_progress(")
    end = source.index("\ndef space_p_progress_compact_response", start)
    function = source[start:end]
    assert "clone_space_progress_payload" not in function
    assert "space_w_progress_semantic_identity(existing)" in function
    assert "sqlite_authoritative=True" in function
    assert "syncOperationId" in function
    assert "remember_space_progress_store(" not in function
    assert app.normalize_paragraph_progress_space("space_l") == "Space_L"
    assert app.normalize_paragraph_progress_space("Space_S") == "Space_S"
    assert app.normalize_paragraph_progress_space("unknown") == "Space_P"

    base = {
        "path": "common/probe.Space_L",
        "identity": "probe",
        "space": "Space_L",
        "savedAt": "2026-07-21T00:00:00Z",
        "updatedAt": "2026-07-21T00:00:01Z",
        "syncOperationId": "space-p-probe",
        "state": {"savedAt": "2026-07-21T00:00:00Z", "completedSegments": 1, "totalSegments": 12},
        "_serverRevision": 7,
    }
    retry = {**base, "updatedAt": "2026-07-21T00:00:09Z", "_serverRevision": 99}
    assert app.space_w_progress_semantic_identity(base) == app.space_w_progress_semantic_identity(retry)
    compact = app.space_p_progress_compact_response(base)
    assert compact["syncOperationId"] == "space-p-probe"
    assert compact["space"] == "Space_L"
    assert compact["_serverRevision"] == 7
    assert "state" not in compact

    route = ROUTE.read_text(encoding="utf-8")
    route_start = route.index('if path == "/space-p/progress":')
    route_end = route.index('if path == "/space-pdf/progress":', route_start)
    progress_route = route[route_start:route_end]
    assert 'compact_response = clean((query.get("response")' in progress_route
    assert '"space-p-progress-compact-v1"' in progress_route
    assert "normalize_paragraph_progress_space" in progress_route

    client = CLIENT.read_text(encoding="utf-8")
    assert '"/space-p/progress?client_source=space_p_progress_save&response=compact-v1"' in client
    assert "createParagraphProgressOperationId" in client
    assert "paragraphProgressSemanticSignature" in client
    assert "canonicalRecord = record && record.state" in client
    assert 'space: isSpaceLPayload() ? "Space_L"' in client
    print("space_p_progress_post_hot_path=ok spaces=pls single_entry=true idempotent=true compact_ack=true callback_dedupe=true")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
