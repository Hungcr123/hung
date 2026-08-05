#!/usr/bin/env python3
"""Fast in-process matrix for PDF/Picture AI notice audio and exact sound-index repair."""

from __future__ import annotations

import copy
import json
import os
import shutil
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
RUN_ROOT = ROOT / "programe_cache" / "pdf_ai_notice_sound_index_matrix"
if RUN_ROOT.exists():
    shutil.rmtree(RUN_ROOT)
(RUN_ROOT / "Sound").mkdir(parents=True)
os.environ["FUTURE_SERVER_DATA_ROOT"] = str(RUN_ROOT)

from FUTURE import server_app as app


def main() -> int:
    app.SERVER_DATA_ROOT = RUN_ROOT
    builder = app.chat_builder_tools()
    asset_globals = builder.indexed_write_server_sound_asset.__globals__
    configure_root = asset_globals["configure_sound_asset_root"]
    configure_root(RUN_ROOT)
    rebuild_calls = {"count": 0}
    original_rebuild = asset_globals["rebuild_sound_asset_index"]

    def forbidden_rebuild(*args, **kwargs):
        rebuild_calls["count"] += 1
        raise AssertionError("full sound index rebuild is forbidden on notice paths")

    asset_globals["rebuild_sound_asset_index"] = forbidden_rebuild
    stores = {"documents": {}}
    store_lock = threading.RLock()
    tts_calls = {"count": 0}

    def document_key(path: str, mode: str) -> str:
        return app.space_pdf_child_document_key(path, mode, "")

    def fake_identity(_viewer: str, source: dict | None = None) -> dict:
        payload = source or {}
        path = app.clean_path_value(payload.get("path", ""))
        return {"path": path, "identity": "", "key": document_key(path, app.normalize_space_pdf_shared_audio_mode(payload.get("mode", "pdf")))}

    def fake_read(_viewer: str, relative_path: str = "", page: object = 1, mode: object = "pdf", *_args) -> dict:
        normalized_mode = app.normalize_space_pdf_shared_audio_mode(mode)
        normalized_page = app.normalize_space_pdf_drawing_page(page)
        path = app.clean_path_value(relative_path)
        key = document_key(path, normalized_mode)
        with store_lock:
            document = stores["documents"].get(key) or {}
            rows = copy.deepcopy(((document.get("pages") or {}).get(str(normalized_page)) or []))
        notices = [app.normalize_space_pdf_ai_notice_item(row, page=normalized_page, mode=normalized_mode) for row in rows]
        return {"key": key, "path": path, "page": normalized_page, "mode": normalized_mode, "notices": notices}

    def fake_store_read() -> dict:
        with store_lock:
            return copy.deepcopy(stores)

    def fake_store_write(payload: dict) -> None:
        with store_lock:
            stores.clear()
            stores.update(copy.deepcopy(payload))

    raw_calls = {"count": 0}

    def fake_raw(text: str, voice: str, **_kwargs) -> dict:
        raw_calls["count"] += 1
        return {
            "audio_bytes": f"RIFF|{voice}|{text}".encode("utf-8"),
            "audio_mime": "audio/wav",
            "voice": voice,
            "voice_label": voice,
        }

    original_values = {
        "is_admin_user": app.is_admin_user,
        "space_pdf_progress_identity_for_source": app.space_pdf_progress_identity_for_source,
        "read_space_pdf_ai_region_notices": app.read_space_pdf_ai_region_notices,
        "_read_space_pdf_ai_region_notice_store_locked": app._read_space_pdf_ai_region_notice_store_locked,
        "_write_space_pdf_ai_region_notice_store_locked": app._write_space_pdf_ai_region_notice_store_locked,
        "flush_space_pdf_ai_runtime_store": app.flush_space_pdf_ai_runtime_store,
        "durable_tts_submit_raw": app.durable_tts_submit_raw,
        "chat_synthesize_message_audio_queued": app.chat_synthesize_message_audio_queued,
    }
    app.is_admin_user = lambda _viewer: True
    app.space_pdf_progress_identity_for_source = fake_identity
    app.read_space_pdf_ai_region_notices = fake_read
    app._read_space_pdf_ai_region_notice_store_locked = fake_store_read
    app._write_space_pdf_ai_region_notice_store_locked = fake_store_write
    app.flush_space_pdf_ai_runtime_store = lambda *_args, **_kwargs: True
    app.durable_tts_submit_raw = fake_raw
    app.SPACE_PDF_AI_REGION_NOTICES_PUBLIC_CACHE.clear()
    app.SPACE_PDF_AI_NOTICE_AUDIO_REPAIR_FAILURES.clear()

    try:
        admin_results = []
        for mode, path in (("pdf", "common/proof.pdf"), ("picture", "common/proof.png")):
            saved = app.save_space_pdf_ai_region_notice("admin", {
                "path": path,
                "mode": mode,
                "page": 1,
                "rect": {"x": 0.1, "y": 0.1, "w": 0.3, "h": 0.2},
                "text": f"Admin notice {mode}",
                "audioText": f"Admin audio {mode}",
                "voice": "kokoro:af_jessica",
                "action": "build_audio",
            })
            notice = saved["notice"]
            audio_path = notice.get("audio_path") or notice.get("audioPath")
            index_probe = asset_globals["ensure_sound_asset_index_entry"](audio_path)
            if not audio_path or not (RUN_ROOT / audio_path).is_file() or not index_probe.get("ok"):
                raise AssertionError(f"admin build did not finish file+index: {saved}")
            admin_results.append({"mode": mode, "id": notice["id"], "audio_path": audio_path, "index_key": index_probe["key"]})

        rebuilt = app.save_space_pdf_ai_region_notice("admin", {
            "path": "common/proof.pdf",
            "mode": "pdf",
            "page": 1,
            "id": admin_results[0]["id"],
            "rect": {"x": 0.1, "y": 0.1, "w": 0.3, "h": 0.2},
            "text": "Admin notice pdf",
            "audioText": "Admin audio pdf rebuilt",
            "voice": "kokoro:af_jessica",
            "action": "build_audio",
        })
        rebuilt_path = rebuilt["notice"].get("audio_path") or rebuilt["notice"].get("audioPath")
        if rebuilt_path == admin_results[0]["audio_path"] or not (RUN_ROOT / rebuilt_path).is_file():
            raise AssertionError("admin region rebuild did not replace the audio path")

        picture_notice = fake_read("learner", "common/proof.png", 1, "picture")["notices"][0]
        picture_path = picture_notice["audio_path"]
        picture_index_key = asset_globals["ensure_sound_asset_index_entry"](picture_path)["key"]
        index = asset_globals["load_sound_asset_index"]()
        index["assets"].pop(picture_index_key, None)
        asset_globals["SOUND_ASSET_INDEX_DIRTY"] = True
        asset_globals["write_sound_asset_index_now"]("matrix-remove-one-entry")
        before_missing_index_tts = raw_calls["count"]
        index_repair = app.ensure_space_pdf_ai_region_notice_audio("learner", {
            "path": "common/proof.png", "mode": "picture", "page": 1, "id": picture_notice["id"], "action": "ensure_audio",
        })
        if raw_calls["count"] != before_missing_index_tts or not index_repair.get("sound_index_repaired"):
            raise AssertionError(f"missing index should repair without TTS: {index_repair}")

        pdf_notice = fake_read("learner", "common/proof.pdf", 1, "pdf")["notices"][0]
        pdf_path = pdf_notice["audio_path"]
        (RUN_ROOT / pdf_path).unlink()
        before_missing_file_tts = raw_calls["count"]
        concurrent = []
        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = [executor.submit(app.ensure_space_pdf_ai_region_notice_audio, "learner", {
                "path": "common/proof.pdf", "mode": "pdf", "page": 1, "id": pdf_notice["id"], "action": "ensure_audio",
            }) for _index in range(8)]
            concurrent = [future.result() for future in futures]
        concurrent_tts_calls = raw_calls["count"] - before_missing_file_tts
        repaired_path = concurrent[0]["notice"].get("audio_path") or concurrent[0]["notice"].get("audioPath")
        if concurrent_tts_calls != 1 or not (RUN_ROOT / repaired_path).is_file():
            raise AssertionError(f"single-flight failed: calls={concurrent_tts_calls} results={concurrent}")

        second_click_before = raw_calls["count"]
        second_click = app.ensure_space_pdf_ai_region_notice_audio("learner", {
            "path": "common/proof.pdf", "mode": "pdf", "page": 1, "id": pdf_notice["id"], "action": "ensure_audio",
        })
        if raw_calls["count"] != second_click_before or second_click.get("audio_repaired"):
            raise AssertionError(f"second click rebuilt ready audio: {second_click}")

        asset_globals["write_sound_asset_index_now"]("matrix-restart")
        asset_globals["SOUND_ASSET_INDEX_RAM"] = None
        restarted_index = asset_globals["load_sound_asset_index"](force=True, build_if_missing=False)
        restart_probe = asset_globals["ensure_sound_asset_index_entry"](repaired_path)
        if not restart_probe.get("ok") or restart_probe.get("index_repaired"):
            raise AssertionError("restart did not preserve the exact sound index entry")
        for row in admin_results[1:]:
            probe = asset_globals["ensure_sound_asset_index_entry"](row["audio_path"])
            if not probe.get("ok") or probe.get("index_repaired"):
                raise AssertionError(f"restart lost {row['mode']} sound index entry: {probe}")

        picture_after_restart = fake_read("learner", "common/proof.png", 1, "picture")["notices"][0]
        picture_after_restart_path = picture_after_restart["audio_path"]
        (RUN_ROOT / picture_after_restart_path).unlink()
        failure_calls = {"count": 0}

        def failing_synth(*_args, **_kwargs):
            failure_calls["count"] += 1
            raise RuntimeError("worker unavailable")

        app.chat_synthesize_message_audio_queued = failing_synth
        app.SPACE_PDF_AI_NOTICE_AUDIO_REPAIR_USER_LAST.clear()
        first_failure = ""
        second_failure = ""
        try:
            app.ensure_space_pdf_ai_region_notice_audio("learner", {
                "path": "common/proof.png", "mode": "picture", "page": 1, "id": picture_after_restart["id"], "action": "ensure_audio",
            })
        except RuntimeError as exc:
            first_failure = str(exc)
        try:
            app.ensure_space_pdf_ai_region_notice_audio("learner", {
                "path": "common/proof.png", "mode": "picture", "page": 1, "id": picture_after_restart["id"], "action": "ensure_audio",
            })
        except RuntimeError as exc:
            second_failure = str(exc)
        if failure_calls["count"] != 1 or "sau vai giay" not in second_failure:
            raise AssertionError({"failure_calls": failure_calls["count"], "first": first_failure, "second": second_failure})

        result = {
            "ok": True,
            "root": str(RUN_ROOT),
            "production_root_used": str(builder.SERVER_DATA_ROOT).lower() == str(Path(r"C:\server data")).lower(),
            "admin_builds": admin_results,
            "admin_rebuild_path": rebuilt_path,
            "tts_calls_total": raw_calls["count"],
            "missing_index_tts_calls": raw_calls["count"] - before_missing_index_tts - concurrent_tts_calls,
            "missing_index_repaired": bool(index_repair.get("sound_index_repaired")),
            "missing_file_concurrent_clicks": 8,
            "missing_file_tts_calls": concurrent_tts_calls,
            "second_click_reused": raw_calls["count"] == second_click_before,
            "restart_index_entries": len(restarted_index.get("assets") or {}),
            "restart_pdf_picture_index_ready": True,
            "tts_failure_calls_across_two_clicks": failure_calls["count"],
            "cooldown_blocked_second_click": "sau vai giay" in second_failure,
            "full_rebuild_calls": rebuild_calls["count"],
            "polling_threads_added": 0,
        }
        if result["production_root_used"] or result["full_rebuild_calls"]:
            raise AssertionError(result)
        print(json.dumps(result, ensure_ascii=False))
        return 0
    finally:
        for name, value in original_values.items():
            setattr(app, name, value)
        asset_globals["rebuild_sound_asset_index"] = original_rebuild
        timer = asset_globals.get("SOUND_ASSET_INDEX_FLUSH_TIMER")
        if timer is not None:
            timer.cancel()
        if RUN_ROOT.exists():
            shutil.rmtree(RUN_ROOT)


if __name__ == "__main__":
    raise SystemExit(main())
