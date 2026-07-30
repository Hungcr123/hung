"""Verify authenticated load-test users never create QMLearn/Server Data folders."""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from FUTURE import server_app as app


def main() -> int:
    original_is_test = app.server_database_is_test_user
    original_ensure = app.ensure_server_data_folders
    original_common = app.ensure_server_data_common_folder
    original_user_path = app.server_data_user_folder_path
    original_signature = app.auth_me_cache_signature
    original_profile = app.read_user_profile
    original_preferences = app.read_user_preferences
    original_missing = app.profile_missing
    original_admin = app.is_admin_user
    calls: list[str] = []
    try:
        app.server_database_is_test_user = lambda username="": str(username).lower().startswith("codexload")
        app.ensure_server_data_common_folder = lambda: {"common_folder": r"C:\server data\common"}
        app.server_data_user_folder_path = lambda username="": (_ for _ in ()).throw(
            AssertionError("load-test user attempted to resolve/create a private Server Data folder")
        )
        with app.ENSURE_SERVER_DATA_FOLDERS_CACHE_LOCK:
            app.ENSURE_SERVER_DATA_FOLDERS_CACHE.clear()
        direct_payload = original_ensure("codexload001")
        assert direct_payload["load_test"] is True
        assert direct_payload["user_folder"] == ""
        assert direct_payload["created_user_folder"] is False
        app.ensure_server_data_folders = lambda username="": calls.append(str(username))
        with app.AUTH_ENSURED_FOLDERS_LOCK:
            app.AUTH_ENSURED_FOLDERS.clear()
        app._ensure_session_server_data_folder("codexload001", 1000.0)
        assert calls == []
        app._ensure_session_server_data_folder("hung", 1000.0)
        app._ensure_session_server_data_folder("hung", 1001.0)
        assert calls == ["hung"]
        app.auth_me_cache_signature = lambda username="": (username, 1)
        app.read_user_profile = lambda username="": {"full_name": "Load Test"}
        app.read_user_preferences = lambda username="": {"chat_voice": {"enabled": True}}
        app.profile_missing = lambda profile=None: []
        app.is_admin_user = lambda username="": False
        with app.AUTH_ME_CACHE_LOCK:
            app.AUTH_ME_CACHE.clear()
        payload = app.auth_me_payload("codexload001", include_rewards=True)
        assert payload["server_data"] == {"load_test": True}
        assert payload["preferences"]["chat_voice"]["enabled"] is True
        assert payload["leaderboard_rewards_claimed"]["skipped"] == "load_test"
        assert calls == ["hung"]
    finally:
        app.server_database_is_test_user = original_is_test
        app.ensure_server_data_folders = original_ensure
        app.ensure_server_data_common_folder = original_common
        app.server_data_user_folder_path = original_user_path
        app.auth_me_cache_signature = original_signature
        app.read_user_profile = original_profile
        app.read_user_preferences = original_preferences
        app.profile_missing = original_missing
        app.is_admin_user = original_admin
        with app.AUTH_ENSURED_FOLDERS_LOCK:
            app.AUTH_ENSURED_FOLDERS.clear()
        with app.ENSURE_SERVER_DATA_FOLDERS_CACHE_LOCK:
            app.ENSURE_SERVER_DATA_FOLDERS_CACHE.clear()
    print("auth_session_test_user_folder=ok test_user_skipped=true real_user_throttled=true")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
