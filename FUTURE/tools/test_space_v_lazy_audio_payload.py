"""Verify opening Space_V builds lazy stable audio references without filesystem resolution."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from FUTURE import server_app as app


def main() -> int:
    original_fast = app.fast_qmlearn_audio_path
    original_stems = app.qmdict_audio_stem_index_shared
    original_has_meaning = app.qmdict_meaning_has_local_audio_stem
    try:
        app.fast_qmlearn_audio_path = lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("lesson open resolved audio path"))
        app.qmdict_audio_stem_index_shared = lambda *_args, **_kwargs: {"ready"}
        app.qmdict_meaning_has_local_audio_stem = lambda _meaning, _stems: True
        audio = app.qmdict_space_v_dynamic_audio_map("Friend", "ban be")
    finally:
        app.fast_qmlearn_audio_path = original_fast
        app.qmdict_audio_stem_index_shared = original_stems
        app.qmdict_meaning_has_local_audio_stem = original_has_meaning

    uk = audio.get("sot:en-GB") or {}
    us = audio.get("sot:en-US") or {}
    vi = audio.get("sot:vi-VN") or {}
    assert "word=Friend" in uk.get("u", "") and "voice=sot%3Aen-GB" in uk.get("u", "")
    assert "word=Friend" in us.get("u", "") and "voice=sot%3Aen-US" in us.get("u", "")
    assert uk.get("aid") == "v1:w:friend:g"
    assert us.get("aid") == "v1:w:friend:u"
    assert "meaning=ban%20be" in vi.get("u", "")
    assert str(vi.get("aid", "")).startswith("v1:m:")
    print("space_v_lazy_audio_payload=ok lesson_open_fs_reads=0 word_and_meaning=lazy stable_asset_id=true")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
