from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
REFRESH = ROOT / "FUTURE" / "server_parts" / "server_data_pdf_qmdict" / "07_qmlearn_audio_spacev_repair.py"
ROUTES = ROOT / "FUTURE" / "server_parts" / "http_server" / "post_route_parts" / "01_entry_dashboard_admin.pyfrag"
SERVER_APP = ROOT / "FUTURE" / "server_app.py"
MARKUP = ROOT / "FUTURE" / "server_parts" / "vocab_build_status" / "status_page_parts" / "03_dashboard_markup.pyfrag"
SCRIPT = ROOT / "FUTURE" / "server_parts" / "vocab_build_status" / "status_page_parts" / "04_dashboard_script_01.pyfrag"
DURABLE_TTS = ROOT / "FUTURE" / "server_parts" / "process_frontend_runtime" / "04_durable_tts_queue.py"
WORKER_POOL = ROOT / "FUTURE" / "server_parts" / "process_frontend_runtime" / "04_distributed_worker_pool.py"


def main() -> None:
    refresh = REFRESH.read_text(encoding="utf-8")
    routes = ROUTES.read_text(encoding="utf-8")
    server_app = SERVER_APP.read_text(encoding="utf-8")
    dashboard = MARKUP.read_text(encoding="utf-8") + SCRIPT.read_text(encoding="utf-8")
    durable_tts = DURABLE_TTS.read_text(encoding="utf-8")
    worker_pool = WORKER_POOL.read_text(encoding="utf-8")

    synthesis_body = refresh.split("def synthesize_qmdict_word_audio_item", 1)[1].split("def persist_qmdict_word_audio_item", 1)[0]
    persist_body = refresh.split("def persist_qmdict_word_audio_item", 1)[1].split("def refresh_qmdict_word_audio_item", 1)[0]
    assert "future_vocab_builder_gui" not in synthesis_body + persist_body
    assert "synthesize_bulk_audio_worker_first" in synthesis_body
    assert "force_save_space_v_sound_audio" not in synthesis_body
    assert "force_save_space_v_sound_audio" in persist_body
    bulk_body = refresh.split("def synthesize_bulk_audio_worker_first", 1)[1].split("def force_save_space_v_sound_audio", 1)[0]
    assert "distributed_worker_try_tts_raw" in bulk_body
    assert "synthesize_space_v_sound_of_text_bytes" in bulk_body
    assert bulk_body.index("distributed_worker_try_tts_raw") < bulk_body.index("synthesize_space_v_sound_of_text_bytes")
    assert 'preferred_user=""' in bulk_body
    assert "priority=2" in bulk_body
    assert 'worker_voice = f"sot:{normalized_voice}"' in bulk_body
    assert '"server_fallback"' in bulk_body
    assert "audio_bytes, audio_source = synthesize_bulk_audio_worker_first" in refresh
    assert 'preferred_user="admin"' not in refresh
    assert 'row["source"] = audio_source' in refresh
    assert "distributed_worker_effective_job_limit(\"tts\")" in refresh
    assert "live_capacity * 2" in refresh
    assert "SOT slots" in dashboard
    assert "fill_word_audio_capacity" in refresh
    assert "fill_meaning_audio_capacity" in refresh
    assert "def refresh_qmlearn_audio_dir_index_entry" in refresh
    assert "Directory indexes are repair-only" in refresh
    invalidate_body = refresh.split("def invalidate_qmlearn_audio_path_cache", 1)[1].split("def ", 1)[0]
    assert "QMLEARN_AUDIO_DIR_INDEX.pop" not in invalidate_body
    assert "refresh_qmlearn_audio_dir_index_entry(target_word, target_voice)" in refresh
    assert 'refresh_qmlearn_audio_dir_index_entry(meaning, "vi-VN")' in refresh
    assert "never block a learner on a full folder scan" in refresh
    assert 'index_ready = bool(SERVER_STATE.get("qmlearn_voice_index_ready"))' not in refresh
    assert "if found is None and use_index and allow_scan:" in refresh
    assert "qmdict-word-synthesis" in refresh and "qmdict-word-writer" in refresh
    assert "qmdict-vi-synthesis" in refresh and "qmdict-vi-writer" in refresh
    assert "result_buffer_limit" in refresh
    assert "writer_futures[writer_executor.submit(persist_qmdict_word_audio_item" in refresh
    assert "writer_futures[writer_executor.submit(persist_meaning" in refresh
    assert "done % 50 == 0" in refresh
    assert "timeout=1.0" in refresh
    assert '"session_total": session_total' in refresh
    assert '"session_done": resume_done_offset + done' in refresh
    assert "resume_seed" in refresh
    assert "durable_tts_ensure_dispatcher_capacity" in durable_tts
    assert "distributed_worker_effective_job_limit(\"tts\")" in durable_tts
    assert 'globals().get("durable_tts_ensure_dispatcher_capacity")' in worker_pool
    assert "verify_qmdict_word_audio_runtime()" in refresh
    assert "cancel_futures=True" in refresh
    assert "os.replace(temp_target, target)" in refresh
    assert "def normalize_qmdict_tts_word" in refresh
    assert 'SERVER_STATE.get("qmdict_runtime_ready")' in refresh
    assert "direct = qmdict_lookup_summary(text, surface)" in refresh
    assert "target_word = normalize_qmdict_tts_word(word)" in refresh
    assert "return lowered[:index] + char.upper() + lowered[index + 1:]" in refresh
    assert '"status": "already_present"' in refresh
    assert "selected_items = selected_items[:1000]" in refresh
    assert "qmdict/word-audio-refresh/cancel" in routes
    assert "qmdict/meaning-audio-refresh/cancel" in routes
    assert 'clean_mode not in {"missing", "force", "resume"}' in refresh
    assert 'if mode in {"missing", "selected-missing"}' in refresh
    assert '"selected-missing"' in refresh
    assert '"session_mode": session_mode' in refresh
    assert "ocr_cache_text_snapshot()" in refresh
    assert "is_valid_word(token, qmdict, valid_lines" in refresh
    assert "pdf_vocab_word_key" in refresh
    assert '"phase": "prioritizing"' in refresh
    assert '"priority_total": 0' in refresh
    assert "cancelled=lambda: qmdict_word_audio_refresh_cancel_requested(job_id)" in refresh
    assert "qmdict_word_audio_refresh_entries(session_mode, priority_words=priority_words)" in refresh
    assert "QMDICT_OCR_AUDIO_PRIORITY_FILE.read_text" in refresh
    assert '"source": "postgresql_ocr_cache"' in refresh
    assert "The persisted list is intentionally opt-in" in refresh
    assert refresh.count("verify_qmdict_word_audio_runtime()") >= 2
    for control_id in (
        "qmdict-word-audio-force",
        "qmdict-word-audio-missing",
        "qmdict-word-audio-resume",
        "qmdict-meaning-audio-force",
        "qmdict-meaning-audio-missing",
        "qmdict-meaning-audio-resume",
    ):
        assert control_id in dashboard
    assert "QMDICT_WORD_AUDIO_REFRESH_MAX_WORKERS = 4" in server_app
    print("qmdict word audio refresh safety: ok")


if __name__ == "__main__":
    main()
