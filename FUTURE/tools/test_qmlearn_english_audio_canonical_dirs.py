from __future__ import annotations

import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from FUTURE import server_app as app


def main() -> int:
    original_root = app.QMLEARN_DATA_ROOT
    original_resolved = app.QMLEARN_DATA_ROOT_RESOLVED_CACHE
    try:
        with tempfile.TemporaryDirectory(prefix="future-qmlearn-canonical-audio-") as temp_dir:
            data_root = Path(temp_dir)
            gb_dir = data_root / "sot-en-gb"
            us_dir = data_root / "sot-en-us"
            gb_dir.mkdir()
            us_dir.mkdir()
            (data_root / "Book_en-GB.mp3").write_bytes(b"broken-root")
            (data_root / "Book_en-US.mp3").write_bytes(b"broken-root")
            gb_audio = gb_dir / "Book_en-GB.mp3"
            us_audio = us_dir / "Book_en-US.mp3"
            gb_audio.write_bytes(b"canonical-gb")
            us_audio.write_bytes(b"canonical-us")

            app.QMLEARN_DATA_ROOT = data_root
            app.QMLEARN_DATA_ROOT_RESOLVED_CACHE = None
            app.QMLEARN_AUDIO_PATH_CACHE.clear()

            gb_candidates = app.qmlearn_audio_direct_candidates("Book", "sot:en-GB")
            us_candidates = app.qmlearn_audio_direct_candidates("Book", "sot:en-US")
            assert gb_candidates and all(path.parent == gb_dir for path in gb_candidates)
            assert us_candidates and all(path.parent == us_dir for path in us_candidates)
            assert app.fast_qmlearn_audio_path("Book", "sot:en-GB") == gb_audio.resolve()
            assert app.fast_qmlearn_audio_path("Book", "sot:en-US") == us_audio.resolve()
            assert app.safe_qmlearn_data_sound_path("Book_en-GB.mp3") == gb_audio.resolve()
            assert app.safe_qmlearn_data_sound_path("Book_en-US.mp3") == us_audio.resolve()
    finally:
        app.QMLEARN_DATA_ROOT = original_root
        app.QMLEARN_DATA_ROOT_RESOLVED_CACHE = original_resolved
        app.QMLEARN_AUDIO_PATH_CACHE.clear()
    print("QmLearn English audio uses canonical UK/US directories only")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
