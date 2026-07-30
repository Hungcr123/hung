#!/usr/bin/env python3
"""Runtime gate for scoped PostgreSQL user/admin/pending/reset document state."""

from __future__ import annotations

import json
import os
import secrets
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ["FUTURE_DB_USER_AUTH_DOCS_BACKEND"] = "postgres"

import FUTURE.server_app as app  # noqa: E402

USERNAME = "codexpguserdoc"
PASSWORD = "CodexRuntime42"
PASSWORD_NEXT = "CodexRuntime43"


def cleanup() -> dict:
    def _cleanup(connection):
        out = {}
        with connection.cursor() as cursor:
            for table in ("user_auth_credentials", "admin_users", "pending_registrations", "password_reset_requests"):
                cursor.execute(f"DELETE FROM future_server2.{table} WHERE lower(username)=%s", (USERNAME,))
                out[table] = int(cursor.rowcount or 0)
            cursor.execute("DELETE FROM future_server2.users WHERE lower(username)=%s", (USERNAME,))
            out["users"] = int(cursor.rowcount or 0)
        return out

    return app.postgres_execute(_cleanup)


def snapshot() -> dict:
    def _read(connection):
        out = {}
        with connection.cursor() as cursor:
            for table in ("user_auth_credentials", "admin_users", "pending_registrations", "password_reset_requests"):
                cursor.execute(f"SELECT count(*) FROM future_server2.{table} WHERE lower(username)=%s", (USERNAME,))
                out[table] = int(cursor.fetchone()[0] or 0)
        return out

    return app.postgres_execute(_read)


def main() -> int:
    if not os.environ.get("FUTURE_PG_DSN"):
        raise RuntimeError("Set FUTURE_PG_DSN before running this gate.")
    app.postgres_initialize_schema()
    result = {"ok": False}
    try:
        cleanup()
        stamp = app.utc_timestamp()
        pending_before = app.load_pending_users()
        reset_before = app.load_password_reset_state()
        app.postgres_upsert_user_row({
            "username": USERNAME,
            "is_admin": False,
            "is_test": False,
            "profile": {"full_name": "Codex PG User Doc", "gender": "other", "birth_date": "2000-01-01"},
            "updated_at_utc": stamp,
        })
        app.postgres_upsert_user_auth_credential(USERNAME, app.password_hash(PASSWORD), str(app.user_file_path(USERNAME)))

        login_ok, login_status, _profile = app.check_user_login(USERNAME, PASSWORD)
        wrong_ok, wrong_status, _wrong_profile = app.check_user_login(USERNAME, PASSWORD_NEXT)
        profile_saved = app.server_database_upsert_user(USERNAME, {"full_name": "Codex PG User Doc Updated", "gender": "other", "birth_date": "2000-01-01", "intro": "runtime gate"})
        profile_loaded = app.read_user_profile(USERNAME)

        admins_before = app.read_admins_locked()
        admins = set(admins_before)
        admins.add(USERNAME)
        app.write_admins_locked(admins)
        admin_after_add = USERNAME in app.read_admins_locked()
        admins.discard(USERNAME)
        app.write_admins_locked(admins)
        admin_after_remove = USERNAME in app.read_admins_locked()

        pending_payload = dict(pending_before)
        pending_payload[USERNAME] = {
            "username": USERNAME,
            "password_hash": app.password_hash(PASSWORD),
            "profile": {"full_name": "Codex Pending", "gender": "other", "birth_date": "2001-01-01"},
            "status": "pending",
            "requested_at": stamp,
        }
        app.save_pending_users(pending_payload)
        pending_loaded = app.load_pending_users()
        pending_retry = app.load_pending_users()

        reset_payload = dict(reset_before)
        reset_payload[USERNAME] = {
            "username": USERNAME,
            "status": "pending",
            "full_name": "Codex Reset",
            "email": "",
            "email_alias": "codex@example.invalid",
            "client": "runtime-gate",
            "requested_at": stamp,
        }
        app.save_password_reset_state(reset_payload)
        reset_loaded = app.load_password_reset_state()

        app.set_user_password_hash(USERNAME, PASSWORD_NEXT)
        changed_ok, changed_status, _changed_profile = app.check_user_login(USERNAME, PASSWORD_NEXT)
        old_ok, old_status, _old_profile = app.check_user_login(USERNAME, PASSWORD)

        for _index in range(10):
            users = app.read_admins_locked()
            users.add(USERNAME)
            app.write_admins_locked(users)
            users = app.read_admins_locked()
            users.discard(USERNAME)
            app.write_admins_locked(users)

        concurrency = {}
        for count in (10, 50, 100):
            started = time.perf_counter()
            with ThreadPoolExecutor(max_workers=min(32, count)) as executor:
                results = list(executor.map(lambda _i: app.check_user_login(USERNAME, PASSWORD_NEXT)[:2], range(count)))
            elapsed_ms = round((time.perf_counter() - started) * 1000, 3)
            concurrency[str(count)] = {
                "ok": all(ok and status == "ok" for ok, status in results),
                "elapsed_ms": elapsed_ms,
            }

        before_cleanup = snapshot()
        app.save_pending_users(pending_before)
        app.save_password_reset_state(reset_before)
        cleanup_result = cleanup()
        after_cleanup = snapshot()
        result = {
            "ok": all([
                login_ok and login_status == "ok",
                (not wrong_ok) and wrong_status == "wrongpass",
                profile_saved,
                profile_loaded.get("full_name") == "Codex PG User Doc Updated",
                admin_after_add,
                not admin_after_remove,
                USERNAME in pending_loaded and USERNAME in pending_retry,
                USERNAME in reset_loaded,
                changed_ok and changed_status == "ok",
                (not old_ok) and old_status == "wrongpass",
                all(item.get("ok") for item in concurrency.values()),
                all(value == 0 for value in after_cleanup.values()),
            ]),
            "login": {"success": login_status, "wrong": wrong_status, "changed": changed_status, "old_after_change": old_status},
            "profile": {"saved": bool(profile_saved), "full_name": profile_loaded.get("full_name", "")},
            "admin": {"add": admin_after_add, "remove": admin_after_remove},
            "pending": {"loaded": USERNAME in pending_loaded, "retry": USERNAME in pending_retry},
            "reset": {"loaded": USERNAME in reset_loaded},
            "concurrency": concurrency,
            "before_cleanup": before_cleanup,
            "cleanup": cleanup_result,
            "after_cleanup": after_cleanup,
            "production_flag": os.environ.get("FUTURE_DB_USER_AUTH_DOCS_BACKEND", ""),
        }
    finally:
        try:
            if "pending_before" in locals():
                app.save_pending_users(pending_before)
            if "reset_before" in locals():
                app.save_password_reset_state(reset_before)
        finally:
            cleanup()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
