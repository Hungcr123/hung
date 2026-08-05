"""Exercise the QmDict feeder/writer split without network or production data."""

from __future__ import annotations

import sys
import tempfile
import threading
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import FUTURE.server_app as app  # noqa: E402


def main() -> None:
    items = [(f"WORD{i}", f"Word{i}", "sot:en-GB") for i in range(20)]
    lock = threading.Lock()
    synth_active = synth_done = persist_active = persist_done = 0
    max_synth_active = max_persist_active = max_backlog = 0
    first_persist_synth_done = 0

    app.verify_qmdict_word_audio_runtime = lambda: None
    app.ensure_qmdict_runtime_fresh = lambda force=False: None
    app.sync_qmlearn_audio_qmdict_catalog_if_changed = lambda: {}
    app.qmdict_selected_word_audio_refresh_entries = lambda requested: list(items)
    app.qmdict_bulk_audio_concurrency = lambda remaining=0: min(4, max(0, int(remaining or 0)))
    app.qmdict_word_audio_refresh_cancel_requested = lambda job_id="": False
    app.atomic_write_json = lambda *args, **kwargs: None
    app.write_qmdict_word_audio_refresh_progress = lambda *args, **kwargs: None
    app.stt_debug_log = lambda *args, **kwargs: None
    app.QMDICT_WORD_AUDIO_WRITER_WORKERS = 2
    app.QMDICT_WORD_AUDIO_RESULT_BUFFER = 4

    def synthesize(key, word, voice, job_id="", force=True):
        nonlocal synth_active, synth_done, max_synth_active, max_backlog
        with lock:
            synth_active += 1
            max_synth_active = max(max_synth_active, synth_active)
        time.sleep(0.01)
        with lock:
            synth_active -= 1
            synth_done += 1
            max_backlog = max(max_backlog, synth_done - persist_done)
        return {"row": {"key": key, "word": word, "voice": voice}, "audio_bytes": b"ID3", "audio_source": "test"}

    def persist(result, job_id=""):
        nonlocal persist_active, persist_done, max_persist_active, first_persist_synth_done
        with lock:
            persist_active += 1
            max_persist_active = max(max_persist_active, persist_active)
        time.sleep(0.1)
        with lock:
            persist_active -= 1
            persist_done += 1
            if not first_persist_synth_done:
                first_persist_synth_done = synth_done
        row = dict(result["row"])
        row["status"] = "refreshed"
        return row

    app.synthesize_qmdict_word_audio_item = synthesize
    app.persist_qmdict_word_audio_item = persist
    app.QMDICT_WORD_AUDIO_REFRESH_JOB.update({"running": True, "job_id": "pipeline-test", "cancel_requested": False})
    app.run_qmdict_word_audio_refresh_job("pipeline-test", "selected-force", [row[1] for row in items])

    state = app.qmdict_word_audio_refresh_job_snapshot()
    assert state["phase"] == "complete"
    assert state["done"] == 20 and state["refreshed"] == 20 and state["failed"] == 0
    assert max_synth_active == 4
    assert max_persist_active == 2
    assert first_persist_synth_done >= 8, first_persist_synth_done
    assert max_backlog <= 8, max_backlog

    vi_synth_active = vi_persist_active = vi_max_synth = vi_max_persist = 0
    vi_items = [(f"KEY{i}", f"Nghia {i}") for i in range(20)]
    app.qmdict_audio_refresh_entries = lambda keys=None: list(vi_items)
    app.qmdict_meaning_audio_local_path = lambda meaning="": None
    app.qmdict_audio_refresh_cancel_requested = lambda job_id="": False
    app.write_qmdict_audio_refresh_progress = lambda *args, **kwargs: None
    app.refresh_qmlearn_audio_dir_index_entry = lambda *args, **kwargs: None
    app.qmlearn_data_relative_path = lambda path=None: "sot-vi-vn/test.mp3"

    with tempfile.TemporaryDirectory(prefix="qmdict-pipeline-") as tmp:
        vi_path = Path(tmp) / "test.mp3"
        vi_path.write_bytes(b"ID3")

        def vi_synthesize(text, voice, log=None):
            nonlocal vi_synth_active, vi_max_synth
            with lock:
                vi_synth_active += 1
                vi_max_synth = max(vi_max_synth, vi_synth_active)
            time.sleep(0.01)
            with lock:
                vi_synth_active -= 1
            return b"ID3", "test"

        def vi_persist(text, voice, audio_bytes, log=None):
            nonlocal vi_persist_active, vi_max_persist
            with lock:
                vi_persist_active += 1
                vi_max_persist = max(vi_max_persist, vi_persist_active)
            time.sleep(0.1)
            with lock:
                vi_persist_active -= 1
            return vi_path

        app.synthesize_bulk_audio_worker_first = vi_synthesize
        app.force_save_space_v_sound_audio = vi_persist
        app.QMDICT_AUDIO_REFRESH_JOB.update({"running": True, "job_id": "vi-pipeline-test", "cancel_requested": False})
        app.run_qmdict_meaning_audio_refresh_job("vi-pipeline-test", None, "force")
        vi_state = app.qmdict_audio_refresh_job_snapshot()
        assert vi_state["phase"] == "complete"
        assert vi_state["done"] == 20 and vi_state["downloaded"] == 20 and vi_state["failed"] == 0
        assert vi_max_synth == 4
        assert vi_max_persist == 2
    print("qmdict feeder/writer pipeline: ok")


if __name__ == "__main__":
    main()
