"""Regression: overwritten QmSound audio must bypass stale immutable RAM bytes."""

from __future__ import annotations

import atexit
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from FUTURE import server_app as app


ROUTES = (
    ROOT / "FUTURE/server_parts/http_server/03_handler_get_routes.py",
    ROOT / "FUTURE/server_parts/http_server/get_route_parts/06_world_game_assets.pyfrag",
)


def main() -> int:
    cache_key = "word:book:sot:en-gb|old-revision"
    app.QMLEARN_HTTP_AUDIO_CACHE.clear()
    app.qmlearn_http_audio_cache_put(cache_key, b"old-audio", "audio/mpeg", "old-revision", '"old-etag"')
    assert app.qmlearn_http_audio_cache_get_current(cache_key, "old-revision", "new-revision") is None
    current = app.qmlearn_http_audio_cache_get_current(cache_key, "old-revision", "old-revision")
    assert current and current["data"] == b"old-audio"

    for route_path in ROUTES:
        source = route_path.read_text(encoding="utf-8")
        marker = 'if path == "/server-data/qm-sound":'
        route = source[source.index(marker):]
        assert route.index('descriptor = qm_sound_protocol_descriptor(') < route.index(
            'read_qmlearn_data_sound_file_revisioned(descriptor["path"])'
        ), route_path
        assert route.index('read_qmlearn_data_sound_file_revisioned(descriptor["path"])') < route.index(
            "qmlearn_http_audio_cache_get_current("
        ), route_path
        assert "requested_epoch == current_epoch" in route
        assert "requested_file_revision == current_revision" in route
        assert 'etag=etag if revision_matches else ""' in route
        assert '"no-store, no-cache, max-age=0, must-revalidate"' in route

    app.QMLEARN_HTTP_AUDIO_CACHE.clear()
    try:
        atexit.unregister(app.flush_auth_sessions_to_disk)
    except Exception:
        pass
    print("qm_sound_stale_ram_cache=ok stale_revision_bypasses_server_ram=true")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
