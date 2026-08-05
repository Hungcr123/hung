"""Ensure warm auth/me preference signatures stay in RAM."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import FUTURE.server_app as app


def main() -> int:
    username = "codex-auth-signature-cache"
    key = username.lower()
    original = app.server_database_load_user_preferences
    calls = 0

    def fail_if_called(_username: str) -> dict:
        nonlocal calls
        calls += 1
        raise AssertionError("warm signature unexpectedly read PostgreSQL")

    app.USER_PREFERENCES_RAM_CACHE[key] = {
        "authority": "postgresql",
        "revision": 7,
        "preferences": {"_serverRevision": 7, "updated_at": "2026-07-30T12:00:00Z"},
    }
    app.server_database_load_user_preferences = fail_if_called
    try:
        signature = app.user_preferences_runtime_signature(username)
    finally:
        app.server_database_load_user_preferences = original
        app.USER_PREFERENCES_RAM_CACHE.pop(key, None)
    if signature != (7, "2026-07-30T12:00:00Z") or calls:
        raise AssertionError(f"unexpected signature={signature!r} calls={calls}")
    print("auth_me_preference_signature_cache=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
