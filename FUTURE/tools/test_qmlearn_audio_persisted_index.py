"""Static contract separating QmDict signatures from audio availability."""

from __future__ import annotations

from pathlib import Path


def main() -> None:
    root = Path(__file__).resolve().parents[2]
    server_app = (root / "FUTURE/server_app.py").read_text(encoding="utf-8")
    repair = (root / "FUTURE/server_parts/server_data_pdf_qmdict/07_qmlearn_audio_spacev_repair.py").read_text(encoding="utf-8")
    registry = (root / "FUTURE/server_parts/progress_inventory_vocab/06_vocab_registry_core.py").read_text(encoding="utf-8")
    warm_body = repair.split("def warm_qmlearn_voice_audio_index_async", 1)[1].split("def qmlearn_cached_word_audio_payload", 1)[0]
    path_body = repair.split("def fast_qmlearn_audio_path", 1)[1].split("def qmlearn_audio_file_revision", 1)[0]
    assert "from future_qmlearn_audio_index import" not in server_app
    assert "qmlearn_audio_assets_snapshot" not in server_app
    assert "qmlearn_audio_assets_snapshot" not in repair
    assert "load_qmlearn_audio_index" not in warm_body
    assert "qmdict_source_signature_key()" in warm_body
    assert "qmdict_runtime_and_dict()" not in warm_body
    assert "lookup_qmlearn_audio_asset" not in repair
    assert "register_qmlearn_audio_asset" not in repair
    assert "if found is None and use_index and allow_scan:" in path_body
    assert "os.scandir(root_path)" in repair
    summary_body = registry.split("def qmdict_registry_summary_maps", 1)[1].split("def reconcile_vocab_registry_with_qmdict", 1)[0]
    assert '"_future_qmdict_summary_index.json"' in summary_body
    assert 'cached_file_signature == signature_key' in summary_body
    assert summary_body.index('cached_file_signature == signature_key') < summary_body.index("qmdict_runtime_and_dict()")
    assert '"signature": list(signature_key)' in summary_body
    print("QmDict signature and audio availability separation: ok")


if __name__ == "__main__":
    main()
