"""Regressions for Server 2-native lesson vocabulary scans."""

import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).parents[2]
sys.path.insert(0, str(ROOT))

from FUTURE import server_app as app


HELPERS = ROOT / "FUTURE" / "server_parts" / "vocab_build_status" / "01_lesson_vocab_helpers.py"
MISSIONS = ROOT / "FUTURE" / "server_parts" / "vocab_build_status" / "02_space_w_vocab_missions.py"
ROUTE = ROOT / "FUTURE" / "server_parts" / "http_server" / "post_route_parts" / "05_vocab_progress_leaderboard.pyfrag"
MANIFEST = ROOT / "FUTURE" / "server_parts" / "server_data_pdf_qmdict" / "server_data_manifest_listing" / "01_manifest_build_scan.py"
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
    assert '"lesson-vocab-source-v2"' in missions
    assert "lesson_file_vocab_meta_for_target(target)" in missions
    assert 'source_identity = lesson_id or str(target).lower()' in missions
    assert '"lesson_id": lesson_id' in missions
    assert 'lookup_status="QmDict shared file index"' in missions

    registry_source = (ROOT / "FUTURE" / "server_parts" / "progress_inventory_vocab" / "06_vocab_registry_core.py").read_text(encoding="utf-8")
    assert '"vocab_valid_word_keys"' in registry_source
    assert '"vocab_validated_signature"' in registry_source
    assert "qmdict_valid_vocab_keys_for_words" in registry_source
    assert "summary_maps = qmdict_registry_summary_maps()" in registry_source
    assert 'word_keys = list(meta.get("vocab_valid_word_keys") or [])' in registry_source
    assert 'qmdict_signature = qmdict_source_signature_key()' in registry_source
    manifest_source = MANIFEST.read_text(encoding="utf-8")
    assert "def server_data_manifest_vocab_metadata(" in manifest_source
    assert "entry.update(server_data_manifest_vocab_metadata(" in manifest_source

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
    all_text_payload = {
        "k": "ftq",
        "rootText": "Lantern harbor",
        "nodes": [{
            "question": "Explain velvet",
            "answers": ["Orbit answer"],
            "wrong": ["Copper choice"],
            "explanation": "Harbor solution",
            "guidance_tree": [{"text": "Signal hint"}],
            "root_notice": {"info_text": "Anchor notice"},
            "root_highlights": [{"text": "Beacon highlight", "info": "Compass note"}],
        }],
    }
    extracted_keys = {app.vocab_key(item.get("word", "")) for item in app.vocabulary_text_words_from_payload(all_text_payload)}
    for expected in ("lantern", "harbor", "explain", "velvet", "orbit", "copper", "solution", "signal", "anchor", "beacon", "compass"):
        assert expected in extracted_keys, f"missing Space_Q text key: {expected}"
    valid_keys, signature = app.qmdict_valid_vocab_keys_for_words([{"word": "Eyebrow"}, {"word": "travel"}, {"word": "parents"}])
    assert valid_keys and signature

    globals_map = app.lesson_file_vocab_meta_for_target.__globals__
    original_values = {
        name: globals_map[name]
        for name in (
            "qmdict_source_signature_key",
            "qmdict_valid_vocab_keys_for_words",
            "load_vocab_file_meta_index_once",
            "server_data_relative",
            "schedule_vocab_file_meta_index_write",
        )
    }
    original_cache = dict(globals_map["VOCAB_FILE_META_RAM_CACHE"])
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            lesson_path = Path(temp_dir) / "cache.Space_Q"
            lesson_path.write_text("fixture", encoding="utf-8")
            stat = lesson_path.stat()
            persistent_rows = {
                "cache.space_q": {
                    "mtime_ns": stat.st_mtime_ns,
                    "size": stat.st_size,
                    "vocab_word_keys": ["eyebrow"],
                    "vocab_valid_word_keys": ["eyebrow"],
                    "vocab_validated_signature": "1:1",
                    "vocab_extractor_version": app.VOCAB_FILE_META_EXTRACTOR_VERSION,
                    "vocab_source_revision": f"{stat.st_mtime_ns}:{stat.st_size}",
                    "vocab_total_words": 1,
                }
            }
            signature_state = {"value": (1, 1)}
            validation_calls = []
            globals_map["VOCAB_FILE_META_RAM_CACHE"].clear()
            globals_map["qmdict_source_signature_key"] = lambda: signature_state["value"]
            globals_map["qmdict_valid_vocab_keys_for_words"] = (
                lambda words: (validation_calls.append(list(words)) or (["travel"], "2:2"))
            )
            globals_map["load_vocab_file_meta_index_once"] = lambda: persistent_rows
            globals_map["server_data_relative"] = lambda _path: "cache.Space_Q"
            globals_map["schedule_vocab_file_meta_index_write"] = lambda: None

            first = app.lesson_file_vocab_meta_for_target(lesson_path)
            assert first["vocab_valid_word_keys"] == ["eyebrow"]
            assert not validation_calls
            signature_state["value"] = (2, 2)
            second = app.lesson_file_vocab_meta_for_target(lesson_path)
            assert second["vocab_valid_word_keys"] == ["travel"]
            assert len(validation_calls) == 1
    finally:
        globals_map["VOCAB_FILE_META_RAM_CACHE"].clear()
        globals_map["VOCAB_FILE_META_RAM_CACHE"].update(original_cache)
        globals_map.update(original_values)

    print(f"vocab_scan_space_runtime=ok builder_import=false coalesced=true compact=true shared_valid={len(valid_keys)} entries={len(entries)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
