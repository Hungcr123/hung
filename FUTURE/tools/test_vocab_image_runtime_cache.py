"""Regression for local-only Space_V picture lookup and the shared RAM index."""

from __future__ import annotations

import atexit
import concurrent.futures
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from FUTURE import server_app as app


def main() -> int:
    runtime_source = (ROOT / "FUTURE/server_parts/server_data_pdf_qmdict/07_qmlearn_audio_spacev_repair.py").read_text(encoding="utf-8")
    builder_source = (ROOT / "future_vocab_builder_gui.py").read_text(encoding="utf-8")
    frontend = (ROOT / "FUTURE/web/js_parts/12_question_translation_loader.js").read_text(encoding="utf-8")
    constants = (ROOT / "FUTURE/web/js_parts/05_screen_motion_layout.js").read_text(encoding="utf-8")
    dashboard = (ROOT / "FUTURE/server_parts/vocab_build_status/status_page_parts/03_dashboard_markup.pyfrag").read_text(encoding="utf-8")
    combined = runtime_source + "\n" + builder_source
    if "api." + "openverse.org" in combined or "Open" + "verse/" in combined or "urllib.request" in builder_source:
        raise RuntimeError("An Internet/Openverse vocabulary image path is still present")
    if 'store.clear();' not in frontend or "VOCAB_IMAGE_DB_VERSION = 3" not in constants:
        raise RuntimeError("The old browser-downloaded vocabulary image cache is not cleared")
    if dashboard.index('id="space-v-picture-folder-input"') > dashboard.index('id="model"'):
        raise RuntimeError("The picture-folder input is not at the top of the Server tab")

    original_load_settings = app.load_server_settings
    original_scandir = app.os.scandir
    scan_calls = 0

    try:
        with tempfile.TemporaryDirectory(prefix="future-space-v-picture-") as temp_dir:
            picture_dir = Path(temp_dir)
            (picture_dir / "Unit Apple Image.PNG").write_bytes(b"png")
            (picture_dir / "unit apple image.jpg").write_bytes(b"jpg")
            (picture_dir / "Second Word.webp").write_bytes(b"webp")
            (picture_dir / "ignored.txt").write_text("ignored", encoding="utf-8")

            app.load_server_settings = lambda: {"space_v_picture_folder": str(picture_dir)}

            def counted_scandir(path):
                nonlocal scan_calls
                scan_calls += 1
                return original_scandir(path)

            app.os.scandir = counted_scandir
            app.invalidate_space_v_local_picture_index()
            with concurrent.futures.ThreadPoolExecutor(max_workers=32) as pool:
                rows = list(pool.map(lambda _index: app.qmdict_space_v_image_lookup("Unit Apple Image"), range(100)))
            if scan_calls != 1:
                raise RuntimeError(f"Concurrent local lookups rescanned the folder: scans={scan_calls}")
            if any(row.get("pending") or not row.get("image", {}).get("u", "").startswith("/vocab/image-file?") for row in rows):
                raise RuntimeError("Local image lookup did not return an immediate local asset URL")
            record = app.space_v_local_picture_asset("unit apple image")
            if Path(record.get("path", "")).suffix.lower() != ".png":
                raise RuntimeError("Deterministic image-extension priority did not prefer PNG")
            missing = app.qmdict_space_v_image_lookup("No Local Image")
            if missing.get("pending") or missing.get("image") or scan_calls != 1:
                raise RuntimeError("Missing local images should be an immediate cached miss")
            status = app.space_v_local_picture_settings_payload()
            if status.get("matched_words") != 2 or status.get("duplicate_words") != 1 or status.get("ignored_files") != 1:
                raise RuntimeError(f"Unexpected local index statistics: {status}")
    finally:
        app.os.scandir = original_scandir
        app.load_server_settings = original_load_settings
        app.invalidate_space_v_local_picture_index()
        try:
            atexit.unregister(app.flush_auth_sessions_to_disk)
        except Exception:
            pass

    print("vocab_image_runtime_cache=ok source=local-only scans=1 browser_old_cache=cleared dashboard_top=true")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
