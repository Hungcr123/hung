"""Regression for the opt-in compact-v2 login-preload response."""

from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from FUTURE import server_app as app


def main() -> int:
    username = "hung"
    relative_path = "common"
    legacy = app.build_login_preload_response_cache_row(username, relative_path, "legacy")
    compact = app.build_login_preload_response_cache_row(username, relative_path, "compact-v2")
    legacy_payload = json.loads(legacy["bytes"].decode("utf-8"))
    compact_payload = json.loads(compact["bytes"].decode("utf-8"))

    assert legacy_payload["progress_snapshots"][username] == legacy_payload["preload"]["progress_snapshot"]
    assert "progress_snapshots" not in compact_payload
    legacy_snapshot = legacy_payload["preload"]["progress_snapshot"]
    compact_snapshot = compact_payload["preload"]["progress_snapshot"]
    assert compact_snapshot["username"] == legacy_snapshot["username"] == username
    assert compact_snapshot["count"] == legacy_snapshot["count"]
    assert compact_snapshot["items"] == legacy_snapshot["items"]
    assert len(compact["bytes"]) < len(legacy["bytes"]) * 0.75
    assert legacy["etag"] != compact["etag"]
    assert app.login_preload_response_cache_row(username, relative_path, "legacy")["cache_hit"] is True
    assert app.login_preload_response_cache_row(username, relative_path, "compact-v2")["cache_hit"] is True

    app.bump_login_preload_cache_generation(username)
    assert app.login_preload_response_cache_row(username, relative_path, "legacy") is None
    assert app.login_preload_response_cache_row(username, relative_path, "compact-v2") is None
    print(
        "login_preload_compact_v2=ok "
        f"legacy_bytes={len(legacy['bytes'])} compact_bytes={len(compact['bytes'])} "
        "legacy=compatible variants=isolated"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
