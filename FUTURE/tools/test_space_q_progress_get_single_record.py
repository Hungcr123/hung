"""Regression for single-record Space_Q progress reads."""

from pathlib import Path


ROOT = Path(__file__).parents[2]
SOURCE = ROOT / "FUTURE" / "server_parts" / "progress_inventory_vocab" / "02_space_q_progress.py"
ROUTE = ROOT / "FUTURE" / "server_parts" / "http_server" / "get_route_parts" / "05_progress_vocab_leaderboard.pyfrag"


# Added 2026-07-21: keep Space_Q GET on one RAM record and serialize only after ETag validation.
def main() -> int:
    source = SOURCE.read_text(encoding="utf-8")
    start = source.index("def read_space_q_progress(")
    end = source.index("\ndef space_q_progress_etag", start)
    function = source[start:end]
    assert "read_cached_space_progress_file" not in function
    assert "clone_space_progress_payload" not in function
    assert function.index("states.get(raw_key)") < function.index("space_progress_lookup_for_request")
    assert function.index('record.get("path", "")') < function.index("space_progress_lookup_for_request")
    assert "legacy_path" in function and "identity_lower" in function
    assert function.count("return dict(record)") >= 3
    assert "def space_q_progress_etag(" in source

    route = ROUTE.read_text(encoding="utf-8")
    route_start = route.index('if path == "/space-q/progress":')
    route_end = route.index('if path == "/space-v/progress":', route_start)
    progress_route = route[route_start:route_end]
    assert progress_route.index("space_q_progress_etag") < progress_route.index("json_bytes({")
    assert 'self.headers.get("If-None-Match"' in progress_route
    assert '"X-Future-Cache-Hit": "space-q-progress-etag"' in progress_route
    print("space_q_progress_get_single_record=ok raw_key_first=true namespace_clone=false fallback=true etag_preflight=true")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
