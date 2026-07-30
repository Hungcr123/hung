"""Regression for single-record Space_V progress reads."""

from pathlib import Path


ROOT = Path(__file__).parents[2]
SOURCE = ROOT / "FUTURE" / "server_parts" / "progress_inventory_vocab" / "03_space_v_progress.py"
ROUTE = ROOT / "FUTURE" / "server_parts" / "http_server" / "get_route_parts" / "05_progress_vocab_leaderboard.pyfrag"


# Added 2026-07-20: keep GET reads from cloning an entire user's progress namespace.
def main() -> int:
    source = SOURCE.read_text(encoding="utf-8")
    start = source.index("def read_space_v_progress(")
    end = source.index("\ndef space_v_progress_summary_from_record", start)
    function = source[start:end]
    assert "clone_space_progress_payload" not in function
    assert function.index("states.get(raw_key)") < function.index("space_progress_lookup_for_request")
    assert function.index('record.get("path", "")') < function.index("space_progress_lookup_for_request")
    assert function.count("return dict(record)") >= 3
    assert "legacy_path" in function and "identity_lower" in function
    assert "def space_v_progress_etag(" in source
    route = ROUTE.read_text(encoding="utf-8")
    route_start = route.index('if path == "/space-v/progress":')
    route_end = route.index('if path == "/space-p/progress":', route_start)
    progress_route = route[route_start:route_end]
    assert progress_route.index("space_v_progress_etag") < progress_route.index("space_v_progress_summary_from_record")
    assert 'self.headers.get("If-None-Match"' in progress_route
    assert '"X-Future-Cache-Hit": "space-v-progress-etag"' in progress_route
    print("space_v_progress_get_single_record=ok raw_key_first=true namespace_clone=false fallback=true etag_preflight=true")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
