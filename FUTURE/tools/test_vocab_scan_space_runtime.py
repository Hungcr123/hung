"""Regressions for Server 2-native lesson vocabulary scans."""

import sys
from pathlib import Path


ROOT = Path(__file__).parents[2]
sys.path.insert(0, str(ROOT))

from FUTURE import server_app as app


HELPERS = ROOT / "FUTURE" / "server_parts" / "vocab_build_status" / "01_lesson_vocab_helpers.py"
MISSIONS = ROOT / "FUTURE" / "server_parts" / "vocab_build_status" / "02_space_w_vocab_missions.py"
ROUTE = ROOT / "FUTURE" / "server_parts" / "http_server" / "post_route_parts" / "05_vocab_progress_leaderboard.pyfrag"
CLIENT = ROOT / "FUTURE" / "web" / "js_parts" / "16_notices_vocabulary_missions.js"


# Added 2026-07-21: prevent runtime scans from reintroducing builder GUI/openpyxl dependencies.
def main() -> int:
    helpers = HELPERS.read_text(encoding="utf-8")
    start = helpers.index("def resolve_vocab_entries_for_text(")
    end = helpers.index("\ndef is_single_vocab_word", start)
    function = helpers[start:end]
    assert "from scratch_vocab_builder_gui" not in function
    assert "import openpyxl" not in function
    assert "qmdict_lookup_summary" in function
    assert "pdf_vocab_inflight_run" in function
    assert "valid-space-v-runtime-v3" in function

    missions = MISSIONS.read_text(encoding="utf-8")
    scan_start = missions.index("def scan_space_w_vocabulary(")
    scan_end = missions.index("\ndef build_space_w_vocab_mission", scan_start)
    scan_function = missions[scan_start:scan_end]
    assert "with SERVER_DATA_LOCK" not in scan_function
    assert "include_words" in scan_function
    assert "VOCAB_SCAN_RESPONSE_CACHE" in scan_function
    assert "server_database_user_generation" in scan_function
    assert '"lesson-vocab-scan"' in scan_function
    assert "QMDICT_VOCAB_BASE_CACHE" in missions
    assert '"lesson-vocab-source-v1"' in missions

    route = ROUTE.read_text(encoding="utf-8")
    route_start = route.index('if path == "/vocab/scan-space-w":')
    route_end = route.index('if path == "/vocab/build-mission":', route_start)
    scan_route = route[route_start:route_end]
    assert '"vocab-scan-compact-v1"' in scan_route
    assert "include_words=not compact_response" in scan_route
    assert "/vocab/scan-space-w?response=compact-v1" in CLIENT.read_text(encoding="utf-8")

    entries = app.resolve_vocab_entries_for_text("Eyebrow travel parents eyebrow")
    assert isinstance(entries, list)
    assert all(app.is_valid_space_v_vocab_entry(entry) for entry in entries)
    print(f"vocab_scan_space_runtime=ok builder_import=false coalesced=true compact=true entries={len(entries)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
