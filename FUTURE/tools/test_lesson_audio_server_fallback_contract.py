from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
ROUTE = (ROOT / "FUTURE/server_parts/http_server/post_route_parts/02_pdf_ocr_scan.pyfrag").read_text(encoding="utf-8")
SCHEDULER = (ROOT / "FUTURE/web/js_parts/06_spacew_audio_scheduler.js").read_text(encoding="utf-8")
PLAYER = (ROOT / "FUTURE/web/js_parts/07_audio_speak_runtime.js").read_text(encoding="utf-8")
VOCAB = (ROOT / "FUTURE/web/js_parts/12_question_translation_loader.js").read_text(encoding="utf-8")


assert 'client_source: "lesson_audio"' in SCHEDULER
assert 'requestServerSpaceWTtsAudio(text, voiceValue).catch(() => null)' not in SCHEDULER
assert 'voiceValue.startsWith("sot:") || voiceValue.startsWith("microsoft:")' in SCHEDULER
assert 'return requestSoundOfTextBlob(text' not in SCHEDULER
assert 'return requestEdgeTtsBlob(text' not in SCHEDULER

assert 'interactive_lesson_audio = client_source in' in ROUTE
assert 'len(text) <= 240' in ROUTE
assert 'source="interactive_lesson_audio" if interactive_lesson_audio else "runtime_voice"' in ROUTE
assert '"reason": "tts_all_generation_failed"' in ROUTE
assert '"server_fallback_attempted": True' in ROUTE

assert PLAYER.count('=== "tts_all_generation_failed"') >= 2
assert 'if (serverExhausted)' in PLAYER
assert 'không dùng giọng trình duyệt thay thế' in PLAYER
assert 'return playBrowserVoiceOnce(item.word, options);' not in VOCAB
assert 'browser speech is allowed only from the explicit final' in VOCAB

print("lesson_audio_server_fallback=ok interactive_priority=true browser_voice=explicit_final_only")
