"""Keep cold Space_V hydration off the heavyweight QmDict worker queue."""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import FUTURE.server_app as app  # noqa: E402


def main() -> None:
    original_ready = app.SERVER_STATE.get("qmdict_runtime_ready")
    original_direct = app.qmdict_lookup_summary
    original_queued = app.qmdict_lookup_summary_queued
    original_maps = dict(app.QMDICT_SUMMARY_MAP_CACHE)
    calls = {"direct": 0, "queued": 0}
    try:
        app.SERVER_STATE["qmdict_runtime_ready"] = True
        app.QMDICT_SUMMARY_MAP_CACHE.update({
            "signature": app.qmdict_source_signature_key(),
            "maps": {"known": {"word": "Known", "meaning": "da biet"}},
        })

        def direct(word="", surface=""):
            calls["direct"] += 1
            return {"word": "Mark", "meaning": "danh dau"} if str(word).lower() == "marks" else {}

        def queued(word="", surface=""):
            calls["queued"] += 1
            return {}

        app.qmdict_lookup_summary = direct
        app.qmdict_lookup_summary_queued = queued
        result = app.qmdict_lookup_summary_space_v_fast("marks")
        assert result.get("word") == "Mark"
        assert calls == {"direct": 1, "queued": 0}, calls
        assert app.qmdict_bulk_audio_concurrency(1000) >= min(128, app.distributed_worker_effective_job_limit("tts") * 2)
    finally:
        if original_ready is None:
            app.SERVER_STATE.pop("qmdict_runtime_ready", None)
        else:
            app.SERVER_STATE["qmdict_runtime_ready"] = original_ready
        app.qmdict_lookup_summary = original_direct
        app.qmdict_lookup_summary_queued = original_queued
        app.QMDICT_SUMMARY_MAP_CACHE.clear()
        app.QMDICT_SUMMARY_MAP_CACHE.update(original_maps)
    print("Space_V cold QmDict lookup: ok")


if __name__ == "__main__":
    main()
