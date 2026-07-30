"""Regression for single-record Space_W progress reads."""

from pathlib import Path


ROOT = Path(__file__).parents[2]
SOURCE = ROOT / "FUTURE" / "server_parts" / "progress_inventory_vocab" / "01_space_w_progress.py"
ROUTE = ROOT / "FUTURE" / "server_parts" / "http_server" / "get_route_parts" / "05_progress_vocab_leaderboard.pyfrag"


# Added 2026-07-20: keep Space_W GET on one RAM record and serialize only after ETag validation.
def main() -> int:
    source = SOURCE.read_text(encoding="utf-8")
    start = source.index("def read_space_w_progress(")
    end = source.index("\ndef space_w_int", start)
    function = source[start:end]
    assert "read_cached_space_progress_file" not in function
    assert "clone_space_progress_payload" not in function
    assert function.index("states.get(raw_key)") < function.index("space_progress_lookup_for_request")
    assert function.index('record.get("path", "")') < function.index("space_progress_lookup_for_request")
    assert "legacy_path" in function and "identity_lower" in function
    assert function.count("return dict(record)") >= 3
    assert "def space_w_progress_etag(" in source

    route = ROUTE.read_text(encoding="utf-8")
    route_start = route.index('if path == "/space-w/progress":')
    route_end = route.index('if path == "/space-w/speak-skip/state":', route_start)
    progress_route = route[route_start:route_end]
    assert progress_route.index("space_w_progress_etag") < progress_route.index("json_bytes({")
    assert 'self.headers.get("If-None-Match"' in progress_route
    assert '"X-Future-Cache-Hit": "space-w-progress-etag"' in progress_route
    print("space_w_progress_get_single_record=ok raw_key_first=true namespace_clone=false fallback=true etag_preflight=true")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
