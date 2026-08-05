"""Verify Space_V emits exact epoch/file-revision audio references."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from FUTURE import server_app as app


def main() -> int:
    audio = app.qmdict_space_v_dynamic_audio_map("Communicate", "ban be")

    uk = audio.get("sot:en-GB") or {}
    us = audio.get("sot:en-US") or {}
    vi = audio.get("sot:vi-VN") or {}
    assert "word=Communicate" in uk.get("u", "") and "voice=sot%3Aen-GB" in uk.get("u", "")
    assert "word=Communicate" in us.get("u", "") and "voice=sot%3Aen-US" in us.get("u", "")
    assert "audio_epoch=" in uk.get("u", "") and "file_rev=" in uk.get("u", "")
    assert "audio_epoch=" in us.get("u", "") and "file_rev=" in us.get("u", "")
    assert uk.get("aid", "").startswith("v3:w:communicate:g:")
    assert us.get("aid", "").startswith("v3:w:communicate:u:")
    assert "meaning=ban%20be" in vi.get("u", "")
    assert str(vi.get("aid", "")).startswith("v3:m:")
    assert "audio_epoch=" in vi.get("u", "") and "file_rev=" in vi.get("u", "")
    print("space_v_audio_payload=ok exact_epoch_revision=true")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
