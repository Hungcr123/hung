"""Regression checks for authenticated login-preload bytes and user-local invalidation."""

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
    row = app.build_login_preload_response_cache_row(username, "common")
    payload = json.loads(row["bytes"].decode("utf-8"))
    assert payload["username"] == username
    assert payload["preload"]["progress_snapshot"]["username"] == username
    assert row["etag"].startswith('"login-preload-')
    assert app.login_preload_response_cache_row(username, "common")["cache_hit"] is True
    app.bump_login_preload_cache_generation(username)
    assert app.login_preload_response_cache_row(username, "common") is None
    empty = app.build_login_preload_response_cache_row(username, "", "compact-v2")
    assert empty["payload"]["path"] == ""
    assert app.login_preload_response_cache_row(username, "", "compact-v2")["cache_hit"] is True
    print("login_preload_response_cache=ok bytes=true etag=true user_revision=true empty_path=true")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
