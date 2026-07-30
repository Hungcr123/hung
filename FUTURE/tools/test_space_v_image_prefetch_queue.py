"""Regression for the bounded/coalesced Space_V image prefetch worker."""

from __future__ import annotations

import threading
import time
import sys
from pathlib import Path

ROOT = Path(__file__).parents[2]
sys.path.insert(0, str(ROOT))
from FUTURE import server_app as app

SOURCE = ROOT / "FUTURE" / "server_parts" / "server_data_pdf_qmdict" / "server_data_manifest_listing" / "03_manifest_query_cache.py"


# Added 2026-07-21: opening many Space_V files must not create a thread pool per file.
def main() -> int:
    source = SOURCE.read_text(encoding="utf-8")
    start = source.index("def cached_space_v_qmdict_file_bytes(")
    end = source.index("\ndef cached_server_data_file_bytes", start)
    if "prefetch_space_v_images_for_entries" in source[start:end]:
        raise RuntimeError("Space_V file GET still starts image prefetch work")
    original = app.qmdict_space_v_dynamic_image
    calls = []

    def fake_lookup(word: str) -> dict:
        calls.append(str(word))
        time.sleep(0.02)
        return {}

    try:
        app.qmdict_space_v_dynamic_image = fake_lookup
        with app.SPACE_V_IMAGE_PREFETCH_LOCK:
            app.SPACE_V_IMAGE_PREFETCH_PENDING.clear()
            app.SPACE_V_IMAGE_PREFETCH_ACTIVE_KEYS.clear()
            app.SPACE_V_IMAGE_PREFETCH_SCHEDULED = False
        entries = [{"word": f"prefetch-word-{index:03d}"} for index in range(80)]
        for _ in range(20):
            app.prefetch_space_v_images_for_entries(entries, limit=80)
        active_workers = [thread for thread in threading.enumerate() if thread.name == "space-v-image-prefetch"]
        if len(active_workers) > 1:
            raise RuntimeError(f"Expected one prefetch worker, found {len(active_workers)}")
        deadline = time.monotonic() + 8.0
        while time.monotonic() < deadline:
            with app.SPACE_V_IMAGE_PREFETCH_LOCK:
                pending = len(app.SPACE_V_IMAGE_PREFETCH_PENDING)
                scheduled = bool(app.SPACE_V_IMAGE_PREFETCH_SCHEDULED)
            if not pending and not scheduled:
                break
            time.sleep(0.05)
        if pending or scheduled:
            raise RuntimeError("Space_V prefetch queue did not drain")
        if len(calls) > 24 or len(calls) != len(set(calls)):
            raise RuntimeError(f"Prefetch was not capped/deduped: calls={len(calls)} unique={len(set(calls))}")
        print(f"space_v_image_prefetch_queue=ok calls={len(calls)} workers<=1 pending=0")
        return 0
    finally:
        app.qmdict_space_v_dynamic_image = original


if __name__ == "__main__":
    raise SystemExit(main())
