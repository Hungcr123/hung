"""Regression checks for settings, announcements, and last-file final-byte caches."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from FUTURE import server_app as app


def assert_cached(first: dict, second: dict, prefix: str) -> None:
    assert isinstance(first.get("bytes"), bytes) and first["bytes"]
    assert json.loads(first["bytes"].decode("utf-8"))["ok"] is True
    assert first["etag"].startswith(prefix)
    assert second["cache_hit"] is True and second["bytes"] == first["bytes"]


def main() -> int:
    settings_first = app.public_server_settings_response_cache_row()
    assert_cached(settings_first, app.public_server_settings_response_cache_row(), '"settings-')

    announcements_first = app.announcements_response_cache_row()
    assert_cached(announcements_first, app.announcements_response_cache_row(), '"announcements-')

    last_file_first = app.lesson_last_file_response_cache_row("hung")
    assert_cached(last_file_first, app.lesson_last_file_response_cache_row("hung"), '"last-file-')
    assert json.loads(last_file_first["bytes"].decode("utf-8"))["username"] == "hung"

    print("public_last_file_response_cache=ok settings=true announcements=true last_file=true")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
