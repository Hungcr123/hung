"""Regression checks for bounded, newest-first startup user warm selection."""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from FUTURE import server_app as app


def main() -> int:
    scope = app.select_startup_warmup_usernames.__globals__
    original_records = scope["future_warmup_user_records"]
    original_reader = scope.get("read_lesson_last_file_state")
    original_mode = os.environ.get("FUTURE_WARMUP_MODE")
    original_max = os.environ.get("FUTURE_WARMUP_MAX_USERS")
    try:
        scope["future_warmup_user_records"] = lambda: [
            {"username": "older", "is_test": False, "is_admin": False},
            {"username": "newer", "is_test": False, "is_admin": False},
            {"username": "legacy", "is_test": False, "is_admin": False},
            {"username": "inactive", "is_test": False, "is_admin": False},
        ]
        states = {
            "older": {"updated_at": "2026-07-30T00:00:00Z", "file": {"path": "older/a.Space_Q"}},
            "newer": {"updated_at": "2026-07-30T08:00:00+07:00", "file": {"path": "newer/a.Space_Q"}},
            "legacy": {"updated_at": "", "file": {"path": "legacy/a.Space_Q"}},
            "inactive": {"updated_at": "2026-07-30T09:00:00Z", "file": {}},
        }
        scope["read_lesson_last_file_state"] = lambda username: states.get(username, {})
        os.environ["FUTURE_WARMUP_MODE"] = "production"
        os.environ["FUTURE_WARMUP_MAX_USERS"] = "2"
        selected = app.select_startup_warmup_usernames()
        assert selected == ["newer", "older"], selected
        print("startup_warmup_user_selection=ok bounded=true numeric_time=true newest_first=true")
        return 0
    finally:
        scope["future_warmup_user_records"] = original_records
        if original_reader is None:
            scope.pop("read_lesson_last_file_state", None)
        else:
            scope["read_lesson_last_file_state"] = original_reader
        if original_mode is None:
            os.environ.pop("FUTURE_WARMUP_MODE", None)
        else:
            os.environ["FUTURE_WARMUP_MODE"] = original_mode
        if original_max is None:
            os.environ.pop("FUTURE_WARMUP_MAX_USERS", None)
        else:
            os.environ["FUTURE_WARMUP_MAX_USERS"] = original_max


if __name__ == "__main__":
    raise SystemExit(main())
