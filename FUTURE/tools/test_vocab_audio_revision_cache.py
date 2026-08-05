"""Regression for revision-aware shared vocabulary audio and stale preference ordering."""

from __future__ import annotations

import atexit
import os
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from FUTURE import server_app as app


def main() -> int:
    original_root = app.QMLEARN_DATA_ROOT
    original_candidates = app.qmlearn_audio_direct_candidates
    original_meaning_path = app.qmdict_meaning_audio_local_path
    original_meaning_stem = app.qmdict_meaning_has_local_audio_stem
    original_stem_index = app.qmdict_audio_stem_index_shared
    try:
        with tempfile.TemporaryDirectory(prefix="future-vocab-audio-revision-") as temp_dir:
            root = Path(temp_dir)
            voice_dir = root / "sot-en-us"
            voice_dir.mkdir()
            target = voice_dir / "to_en-US.mp3"
            target.write_bytes(b"A" * 512)
            os.utime(target, ns=(1_800_000_000_000_000_000, 1_800_000_000_000_000_000))
            app.QMLEARN_DATA_ROOT = root
            app.qmlearn_audio_direct_candidates = lambda *_args, **_kwargs: [target]
            app.QMLEARN_AUDIO_DIR_INDEX.clear()
            app.QMLEARN_AUDIO_DIR_REVISION_INDEX.clear()
            app.QMLEARN_AUDIO_REVISION_CACHE.clear()

            first = app.qmlearn_word_audio_asset("to", "sot:en-US")
            first_map = app.qmdict_space_v_dynamic_audio_map("to", "den")
            first_clip = first_map.get("sot:en-US") or {}
            assert first.get("revision") and first.get("revision") != "missing"
            assert first_clip.get("aid", "").startswith("v3:w:to:")
            assert "audio_epoch=" in first_clip.get("u", "") and "file_rev=" in first_clip.get("u", "")

            target.write_bytes(b"B" * 640)
            os.utime(target, ns=(1_800_000_001_000_000_000, 1_800_000_001_000_000_000))
            app.invalidate_qmlearn_audio_path_cache("to", "sot:en-US")
            second = app.qmlearn_word_audio_asset("to", "sot:en-US")
            assert second.get("revision") != first.get("revision")
            assert second.get("asset_id") != first.get("asset_id")
            payload, _mime, stable_revision = app.read_qmlearn_data_sound_file_revisioned(target)
            assert payload == b"B" * 640
            assert stable_revision == second.get("revision")

            meaning_target = root / "meaning_ban_be.mp3"
            meaning_target.write_bytes(b"M" * 128)
            app.qmdict_meaning_audio_local_path = lambda _meaning: meaning_target
            app.qmdict_meaning_has_local_audio_stem = lambda *_args: True
            app.qmdict_audio_stem_index_shared = lambda: {"ban_be"}
            meaning_clip = app.qmdict_meaning_audio_dynamic_clip("ban be")
            assert meaning_clip.get("aid", "").startswith("v2:m:")
            assert "audio_epoch=" in meaning_clip.get("u", "") and "file_rev=" in meaning_clip.get("u", "")

            app.QMLEARN_HTTP_AUDIO_CACHE.clear()
            app.qmlearn_http_audio_cache_put("word:to:sot:en-us|revision-a", b"C" * 256, "audio/mpeg", "revision-a", '"etag-a"')
            immutable_row = app.qmlearn_http_audio_cache_get("word:to:sot:en-us|revision-a")
            assert immutable_row and immutable_row.get("data") == b"C" * 256
            assert app.qmlearn_http_audio_cache_get_current(
                "word:to:sot:en-us|revision-a", "revision-a", "revision-b"
            ) is None
            assert app.qmlearn_http_audio_cache_get_current(
                "word:to:sot:en-us|revision-a", "revision-a", "revision-a"
            ) is immutable_row

        base = {"voice": "sot:en-US", "updated_at": "2026-07-30T12:00:00Z", "updated_epoch": 1_800_000_000.0}
        stale = app.normalize_vocab_audio_preference(
            {"voice": "sot:en-GB", "updated_at": "2026-07-30T11:00:00Z", "updated_epoch": 1_799_996_400.0},
            base,
        )
        assert stale.get("voice") == "sot:en-US"
        fresh = app.normalize_vocab_audio_preference(
            {"voice": "sot:en-GB", "updated_at": "2026-07-30T13:00:00Z", "updated_epoch": 1_800_003_600.0},
            base,
        )
        assert fresh.get("voice") == "sot:en-GB"

        frontend = (ROOT / "FUTURE/web/js_parts/01_bootstrap_guard_ai_agent.js").read_text(encoding="utf-8")
        scheduler = (ROOT / "FUTURE/web/js_parts/06_spacew_audio_scheduler.js").read_text(encoding="utf-8")
        vocab = (ROOT / "FUTURE/web/js_parts/12_question_translation_loader.js").read_text(encoding="utf-8")
        postgres = (ROOT / "FUTURE/server_parts/06a_postgres_adapter.py").read_text(encoding="utf-8")
        route = (ROOT / "FUTURE/server_parts/http_server/get_route_parts/06_world_game_assets.pyfrag").read_text(encoding="utf-8")
        assert "media-audio:v3:qm-sound" in frontend and "semanticParams, epoch, revision" in frontend
        assert "resolveQmSoundProtocolUrl" in frontend
        assert 'revision === "0"' in frontend
        assert "window.__futureRevisionSafeAudioUrl = revisionSafeAudioUrl" in frontend
        assert "audio-manager:${hashSpaceWText(url)}" in scheduler
        assert 'parsed.pathname.toLowerCase() === "/server-data/qm-sound"' in scheduler
        assert "vocabVoiceUserStorageKey" in vocab and 'window.addEventListener("storage"' in vocab
        assert "if (localEpoch > serverEpoch)" not in vocab
        assert "A server preference is authoritative on login/reload" in vocab
        assert "clearVocabAudioCache" not in vocab
        assert "invalidateCachedAudioClip(result.clip)" in vocab and "const invalidateCachedAudioClip" in scheduler
        assert "pg_advisory_xact_lock" in postgres and "FOR UPDATE" in postgres
        assert 'max-age=0, must-revalidate' in route and 'X-Future-Audio-Revision' in route
        assert 'etag=etag if revision_matches else ""' in route
        assert "qmlearn_http_audio_cache_get" in route and "qmlearn_http_audio_cache_put" in route
        assert route.index('read_qmlearn_data_sound_file_revisioned(descriptor["path"])') < route.index("qmlearn_http_audio_cache_get_current(")
        assert "qm_sound_protocol_descriptor" in route
        assert "store.clear()" not in scheduler
    finally:
        app.QMLEARN_DATA_ROOT = original_root
        app.qmlearn_audio_direct_candidates = original_candidates
        app.qmdict_meaning_audio_local_path = original_meaning_path
        app.qmdict_meaning_has_local_audio_stem = original_meaning_stem
        app.qmdict_audio_stem_index_shared = original_stem_index
        app.QMLEARN_AUDIO_DIR_INDEX.clear()
        app.QMLEARN_AUDIO_DIR_REVISION_INDEX.clear()
        app.QMLEARN_AUDIO_REVISION_CACHE.clear()
        app.QMLEARN_HTTP_AUDIO_CACHE.clear()
        try:
            atexit.unregister(app.flush_auth_sessions_to_disk)
        except Exception:
            pass

    print("vocab_audio_revision_cache=ok per_word_revision=true stale_tab_rejected=true unrelated_idb_preserved=true")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
