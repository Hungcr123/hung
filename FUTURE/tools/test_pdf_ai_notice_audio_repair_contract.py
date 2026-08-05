from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SERVER = (ROOT / "FUTURE/server_parts/progress_inventory_vocab/04_space_p_pdf_progress.py").read_text(encoding="utf-8")
ROUTE = (ROOT / "FUTURE/server_parts/http_server/post_route_parts/05_vocab_progress_leaderboard.pyfrag").read_text(encoding="utf-8")
CLIENT = (ROOT / "FUTURE/web/js_parts/19_pdf_speak_chrome.js").read_text(encoding="utf-8")
INDEX = (ROOT / "future_sound_asset_index.py").read_text(encoding="utf-8")
VOICE = (ROOT / "FUTURE/server_parts/ai_language_agents/01_chat_translation_voice.py").read_text(encoding="utf-8")

assert "def ensure_space_pdf_ai_region_notice_audio" in SERVER
assert "SPACE_PDF_AI_NOTICE_AUDIO_REPAIR_LOCKS" in SERVER
assert 'source="pdf_ai_notice_repair"' in SERVER
assert "SPACE_PDF_AI_NOTICE_AUDIO_REPAIR_RETRY_SECONDS" in SERVER
assert 'if action == "ensure_audio":' in ROUTE
assert "ensure_space_pdf_ai_region_notice_audio(viewer, payload)" in ROUTE
NOTICE_ROUTE = ROUTE.split('if path == "/space-pdf/ai-region-notices":', 1)[1].split('if path == "/space-pdf/ai-region-questions":', 1)[0]
assert NOTICE_ROUTE.index('if action == "ensure_audio":') < NOTICE_ROUTE.index('if not is_admin_user(viewer):')
assert "pdfAiNoticeAudioRepairRequests = new Map()" in CLIENT
assert 'action: "ensure_audio"' in CLIENT
assert 'path: normalizeServerPathValue(scope.path || notice && notice.path || "")' in CLIENT
assert "JSON.stringify({ ...repairScope, id: noticeId" in CLIENT
assert "if (!audioPath)" in CLIENT
assert 'audio.addEventListener("error"' in CLIENT
assert 'options.source === "hover"' in CLIENT
assert "def configure_sound_asset_root" in INDEX
assert "def ensure_sound_asset_index_entry" in INDEX
assert "atomic_write_bytes(target, data)" in INDEX
assert INDEX.index("atomic_write_bytes(target, data)") < INDEX.index("sound_asset_note_existing(digest, ext, rel)", INDEX.index("def write_server_sound_file_asset"))
assert "rebuild_sound_asset_index" not in SERVER[SERVER.index("def ensure_space_pdf_ai_region_notice_audio"):SERVER.index("def normalize_space_pdf_ai_question_answer")]
assert "def chat_finalize_sound_audio_payload" in VOICE
assert "ensure_sound_asset_index_entry" in VOICE

print("pdf_ai_notice_audio_repair_contract=ok click_only=true singleflight=true cooldown=true exact_index=true atomic_file_first=true")
