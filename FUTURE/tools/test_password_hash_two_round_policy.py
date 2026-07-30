"""Verify the intentional two-round password policy and login-time downgrade path."""

from __future__ import annotations

import base64
import hashlib
import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from FUTURE import server_app as app


def encoded(password: str, rounds: int) -> str:
    salt = "two-round-policy-test"
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), rounds)
    return f"pbkdf2_sha256${rounds}${salt}$" + base64.urlsafe_b64encode(digest).decode().rstrip("=")


def main() -> int:
    password = "LocalOnly9"
    username = "codexpbkdf2policy"
    original_env = os.environ.get("FUTURE_PASSWORD_HASH_ROUNDS")
    originals = {
        "read_user_lines": app.read_user_lines,
        "write_user_lines": app.write_user_lines,
        "read_user_profile": app.read_user_profile,
        "server_database_test_user_password_hash": app.server_database_test_user_password_hash,
    }
    fake_lines = [f"{username}:{encoded(password, 120000)}", "Full Name: Policy Test"]
    try:
        os.environ["FUTURE_PASSWORD_HASH_ROUNDS"] = "120000"
        assert app.configured_password_hash_rounds() == 2
        fresh = app.password_hash(password)
        assert app.password_hash_rounds(fresh) == 2
        assert app.password_hash_matches(password, fresh)
        assert app.password_hash_needs_rehash(encoded(password, 120000)) is True
        assert app.password_hash_needs_rehash(fresh) is False

        app.read_user_lines = lambda _username: list(fake_lines)
        app.write_user_lines = lambda _username, lines: fake_lines.__setitem__(slice(None), list(lines))
        app.read_user_profile = lambda _username: {"full_name": "Policy Test"}
        app.server_database_test_user_password_hash = lambda _username: ""
        app.AUTH_SUCCESS_VERIFY_CACHE.clear()

        ok, reason, _profile = app.check_user_login(username, password)
        assert ok is True and reason == "ok"
        _stored_user, stored = app.parse_user_header(fake_lines[0])
        assert app.password_hash_rounds(stored) == 2
        assert app.password_hash_matches(password, stored)

        high = encoded(password, 120000)
        fake_lines[0] = f"{username}:{high}"
        app.AUTH_SUCCESS_VERIFY_CACHE.clear()
        app.remember_auth_success_verify(username, password, high)
        ok, reason, _profile = app.check_user_login(username, password)
        assert ok is True and reason == "ok"
        _stored_user, stored = app.parse_user_header(fake_lines[0])
        assert app.password_hash_rounds(stored) == 2
        print("password_hash_two_round_policy=ok generator=2 cold_downgrade=2 cached_downgrade=2 password_preserved=true")
        return 0
    finally:
        app.AUTH_SUCCESS_VERIFY_CACHE.clear()
        for name, value in originals.items():
            setattr(app, name, value)
        if original_env is None:
            os.environ.pop("FUTURE_PASSWORD_HASH_ROUNDS", None)
        else:
            os.environ["FUTURE_PASSWORD_HASH_ROUNDS"] = original_env


if __name__ == "__main__":
    raise SystemExit(main())
