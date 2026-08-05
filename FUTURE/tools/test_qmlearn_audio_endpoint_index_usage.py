"""Static contract checks for deterministic lookup plus repair-only scanning."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
REPAIR = (ROOT / "FUTURE/server_parts/server_data_pdf_qmdict/07_qmlearn_audio_spacev_repair.py").read_text(encoding="utf-8")
ROUTE = (ROOT / "FUTURE/server_parts/http_server/03_handler_get_routes.py").read_text(encoding="utf-8")


def main() -> None:
    dir_index_body = REPAIR.split("def qmlearn_audio_dir_index", 1)[1].split("def ", 1)[0]
    word_body = REPAIR.split("def qmlearn_word_audio_asset", 1)[1].split("def ", 1)[0]
    warm_body = REPAIR.split("def warm_qmlearn_voice_audio_index_async", 1)[1].split("def qmlearn_cached_word_audio_payload", 1)[0]
    assert "os.scandir" in dir_index_body
    path_body = REPAIR.split("def fast_qmlearn_audio_path", 1)[1].split("def qmlearn_audio_file_revision", 1)[0]
    assert "lookup_qmlearn_audio_asset" not in REPAIR
    assert "qmlearn_audio_assets_snapshot" not in REPAIR
    assert 'SERVER_STATE["qmlearn_audio_index_mode"] = "deterministic-exact-path"' in warm_body
    assert "fast_qmlearn_audio_path(target_word, target_voice, allow_scan=False, use_index=True)" in word_body
    assert "qmlearn_audio_dir_index(" not in warm_body
    assert "qmdict_source_signature_key()" in warm_body
    assert "if found is None and use_index and allow_scan:" in path_body
    assert "qmlearn_meaning_audio_asset" in ROUTE and "qmlearn_word_audio_asset" in ROUTE
    assert "qmdict_meaning_audio_local_path(text)" in REPAIR
    print("qmlearn deterministic lookup and repair-only scan usage: ok")


if __name__ == "__main__":
    main()
