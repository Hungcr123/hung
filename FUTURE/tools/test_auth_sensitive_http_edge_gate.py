#!/usr/bin/env python3
"""Focused HTTP edge gate for scoped PostgreSQL auth/admin/pending/reset state."""

from __future__ import annotations

import concurrent.futures
import hashlib
import json
import os
import secrets
import subprocess
import sys
import time
from pathlib import Path

import psutil
import requests

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

os.environ["FUTURE_DB_USER_AUTH_DOCS_BACKEND"] = "postgres"
os.environ["FUTURE_DB_AUTH_BACKEND"] = "postgres"

import FUTURE.server_app as app  # noqa: E402

BASE = "http://127.0.0.1:18877"
PREFIX = "codexpgedge"
USER = f"{PREFIX}user"
OTHER = f"{PREFIX}other"
PENDING_ACCEPT = f"{PREFIX}accept"
PENDING_REJECT = f"{PREFIX}reject"
RESET_DIRECT = f"{PREFIX}resetdirect"
RESET_CODE = f"{PREFIX}resetcode"
PASSWORD = "CodexEdge42"
PASSWORD_NEXT = "CodexEdge43"
PASSWORD_RESET = "CodexEdge44"
CODE = "731429"


def server_pid_on_port(port: int) -> int:
    for connection in psutil.net_connections(kind="tcp"):
        if connection.laddr and connection.laddr.port == port and connection.status == psutil.CONN_LISTEN and connection.pid:
            return int(connection.pid)
    return 0


def stop_pid(pid: int) -> None:
    if not pid:
        return
    try:
        process = psutil.Process(pid)
        process.kill()
        process.wait(timeout=20)
    except psutil.NoSuchProcess:
        pass


def start_server() -> subprocess.Popen:
    env = dict(os.environ)
    env["FUTURE_DB_AUTH_BACKEND"] = "postgres"
    env["FUTURE_DB_USER_AUTH_DOCS_BACKEND"] = "postgres"
    return subprocess.Popen(
        [sys.executable, str(ROOT / "FUTURE_SERVER_2.py"), "--host", "127.0.0.1", "--port", "18877", "--no-browser", "--no-tunnel", "--no-preload"],
        cwd=ROOT,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )


def wait_health(pid: int, timeout: float = 90.0) -> dict:
    deadline = time.monotonic() + timeout
    last = ""
    while time.monotonic() < deadline:
        try:
            response = requests.get(f"{BASE}/health", timeout=3)
            last = f"{response.status_code} {response.text[:120]}"
            payload = response.json()
            if response.status_code == 200 and payload.get("ok") and int(payload.get("pid", 0) or 0) == pid:
                return payload
        except Exception as exc:
            last = f"{type(exc).__name__}: {exc}"
        time.sleep(0.4)
    raise RuntimeError(f"Server 18877 did not become healthy: {last}")


def post(session: requests.Session, path: str, payload: dict, timeout: float = 20.0) -> tuple[int, dict]:
    response = session.post(f"{BASE}{path}", json=payload, timeout=timeout)
    try:
        body = response.json()
    except Exception:
        body = {"raw": response.text[:200]}
    return response.status_code, body


def get(session: requests.Session, path: str, **params) -> tuple[int, dict]:
    response = session.get(f"{BASE}{path}", params=params, timeout=20)
    try:
        body = response.json()
    except Exception:
        body = {"raw": response.text[:200]}
    return response.status_code, body


def brief(body: dict) -> dict:
    return {key: body.get(key) for key in ("ok", "reason", "error", "username", "status") if key in body}


def login(username: str, password: str) -> tuple[requests.Session, int, dict]:
    session = requests.Session()
    status, body = post(session, "/auth/login", {"username": username, "password": password})
    if status == 200 and body.get("token"):
        session.headers.update({"Authorization": f"Bearer {body['token']}"})
    return session, status, body


def cleanup() -> dict:
    names = [USER, OTHER, PENDING_ACCEPT, PENDING_REJECT, RESET_DIRECT, RESET_CODE]

    def _run(connection):
        out = {}
        with connection.cursor() as cursor:
            for table in ("auth_sessions", "user_auth_credentials", "admin_users", "pending_registrations", "password_reset_requests", "user_preferences"):
                cursor.execute(f"DELETE FROM future_server2.{table} WHERE lower(username) = ANY(%s)", ([name.lower() for name in names],))
                out[table] = int(cursor.rowcount or 0)
            cursor.execute("DELETE FROM future_server2.users WHERE lower(username) = ANY(%s)", ([name.lower() for name in names],))
            out["users"] = int(cursor.rowcount or 0)
        return out

    out = app.postgres_execute(_run)
    for name in names:
        try:
            app.user_file_path(name).unlink(missing_ok=True)
        except Exception:
            pass
        try:
            folder = app.user_folder_path(name)
            if folder.exists() and not any(folder.iterdir()):
                folder.rmdir()
        except Exception:
            pass
    return out


def seed_user(username: str, password: str) -> None:
    now = app.utc_timestamp()
    profile = {"full_name": username, "gender": "other", "birth_date": "2000-01-01", "email_alias": f"{username}@example.invalid"}
    app.write_user_lines(username, [
        f"{username}:{app.password_hash(password)}",
        app.PROFILE_PREFIX + json.dumps(profile, ensure_ascii=False, separators=(",", ":")),
    ])
    app.postgres_upsert_user_row({
        "username": username,
        "is_admin": False,
        "is_test": False,
        "profile": profile,
        "updated_at_utc": now,
    })
    app.postgres_upsert_user_auth_credential(username, app.password_hash(password), str(app.user_file_path(username)))


def snapshot_counts() -> dict:
    names = [USER, OTHER, PENDING_ACCEPT, PENDING_REJECT, RESET_DIRECT, RESET_CODE]

    def _run(connection):
        out = {}
        with connection.cursor() as cursor:
            for table in ("auth_sessions", "user_auth_credentials", "admin_users", "pending_registrations", "password_reset_requests", "user_preferences", "users"):
                cursor.execute(f"SELECT count(*) FROM future_server2.{table} WHERE lower(username) = ANY(%s)", ([name.lower() for name in names],))
                out[table] = int(cursor.fetchone()[0] or 0)
        return out

    return app.postgres_execute(_run)


def main() -> int:
    if not os.environ.get("FUTURE_PG_DSN"):
        raise RuntimeError("FUTURE_PG_DSN is required")
    app.postgres_initialize_schema()
    old_pid = server_pid_on_port(18877)
    if old_pid:
        stop_pid(old_pid)
    process: subprocess.Popen | None = None
    result: dict = {"ok": False}
    try:
        cleanup()
        seed_user(USER, PASSWORD)
        seed_user(OTHER, PASSWORD)
        seed_user(RESET_DIRECT, PASSWORD)
        seed_user(RESET_CODE, PASSWORD)

        process = start_server()
        first_health = wait_health(process.pid)

        user_session, login_status, login_body = login(USER, PASSWORD)
        _other_session, other_login_status, _other_login_body = login(OTHER, PASSWORD)
        wrong_status, wrong_body = post(requests.Session(), "/auth/login", {"username": USER, "password": PASSWORD_NEXT})
        admin_users_status, _admin_users_body = get(user_session, "/auth/admin-users")

        profile_status, profile_body = post(user_session, "/auth/profile", {
            "username": OTHER,
            "full_name": "Should stay scoped to requester",
            "email_alias": "owner-scope@example.invalid",
        })

        change_status, _change_body = post(user_session, "/auth/password/change", {
            "current_password": PASSWORD,
            "new_password": PASSWORD_NEXT,
        })
        me_after_change_status, _me_after_change_body = get(user_session, "/auth/me")
        old_login_status, _old_login_body = login(USER, PASSWORD)[1:]
        new_login_session, new_login_status, _new_login_body = login(USER, PASSWORD_NEXT)

        register_accept_status, _register_accept_body = post(requests.Session(), "/auth/register", {
            "username": PENDING_ACCEPT,
            "password": PASSWORD,
            "full_name": "Pending Accept",
            "gender": "other",
            "birth_date": "2000-01-01",
        })
        register_accept_retry_status, _register_accept_retry_body = post(requests.Session(), "/auth/register", {
            "username": PENDING_ACCEPT,
            "password": PASSWORD,
            "full_name": "Pending Accept",
            "gender": "other",
            "birth_date": "2000-01-01",
        })
        register_conflict_status, _register_conflict_body = post(requests.Session(), "/auth/register", {
            "username": PENDING_ACCEPT,
            "password": PASSWORD_NEXT,
            "full_name": "Pending Conflict",
            "gender": "other",
            "birth_date": "2000-01-01",
        })
        approve_accept_status, approve_accept_body = post(requests.Session(), "/auth/approve", {"username": PENDING_ACCEPT, "action": "accept"})
        accepted_login_status = login(PENDING_ACCEPT, PASSWORD)[1]

        register_reject_status, _register_reject_body = post(requests.Session(), "/auth/register", {
            "username": PENDING_REJECT,
            "password": PASSWORD,
            "full_name": "Pending Reject",
            "gender": "other",
            "birth_date": "2000-01-01",
        })
        approve_reject_status, approve_reject_body = post(requests.Session(), "/auth/approve", {"username": PENDING_REJECT, "action": "reject"})
        rejected_login_status = login(PENDING_REJECT, PASSWORD)[1]

        reset_request_status, _reset_request_body = post(requests.Session(), "/auth/password-reset/request", {"username": PENDING_ACCEPT})
        reset_admin_status, reset_admin_body = post(requests.Session(), "/auth/password-reset/admin", {"username": PENDING_ACCEPT, "action": "accept"})
        reset_confirm_status, _reset_confirm_body = post(requests.Session(), "/auth/password-reset/confirm", {
            "username": PENDING_ACCEPT,
            "password": PASSWORD_RESET,
        })
        reset_direct_login_status = login(PENDING_ACCEPT, PASSWORD_RESET)[1]
        reset_direct_second_status, _reset_direct_second_body = post(requests.Session(), "/auth/password-reset/confirm", {
            "username": PENDING_ACCEPT,
            "password": PASSWORD_NEXT,
        })

        reset_state = app.load_password_reset_state()
        reset_state[RESET_CODE] = {
            "username": RESET_CODE,
            "status": "code",
            "code_hash": hashlib.sha256(CODE.encode("utf-8")).hexdigest(),
            "expires_at": time.time() + 600,
            "attempts": 0,
            "requested_at": app.utc_timestamp(),
        }
        app.save_password_reset_state(reset_state)
        stored_code_item = app.load_password_reset_state().get(RESET_CODE, {})
        plaintext_absent = CODE not in json.dumps(stored_code_item, ensure_ascii=False)
        wrong_code_status, _wrong_code_body = post(requests.Session(), "/auth/password-reset/confirm", {
            "username": RESET_CODE,
            "code": "000000",
            "password": PASSWORD_RESET,
        })

        def redeem(_index: int) -> int:
            return post(requests.Session(), "/auth/password-reset/confirm", {
                "username": RESET_CODE,
                "code": CODE,
                "password": PASSWORD_RESET,
            }, timeout=30)[0]

        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            concurrent_statuses = list(executor.map(redeem, range(2)))
        reset_code_login_status = login(RESET_CODE, PASSWORD_RESET)[1]
        used_code_status, _used_code_body = post(requests.Session(), "/auth/password-reset/confirm", {
            "username": RESET_CODE,
            "code": CODE,
            "password": PASSWORD_NEXT,
        })

        reset_state = app.load_password_reset_state()
        reset_state[RESET_CODE] = {
            "username": RESET_CODE,
            "status": "code",
            "code_hash": hashlib.sha256(CODE.encode("utf-8")).hexdigest(),
            "expires_at": time.time() - 1,
            "attempts": 0,
            "requested_at": app.utc_timestamp(),
        }
        app.save_password_reset_state(reset_state)
        expired_status, _expired_body = post(requests.Session(), "/auth/password-reset/confirm", {
            "username": RESET_CODE,
            "code": CODE,
            "password": PASSWORD_NEXT,
        })

        stop_pid(process.pid)
        process = start_server()
        second_health = wait_health(process.pid)
        readback_status = login(USER, PASSWORD_NEXT)[1]
        accepted_old_after_reset_readback_status = login(PENDING_ACCEPT, PASSWORD)[1]
        reset_readback_status = login(PENDING_ACCEPT, PASSWORD_RESET)[1]

        before_cleanup = snapshot_counts()
        cleanup_result = cleanup()
        after_cleanup = snapshot_counts()
        pg_metrics = second_health.get("postgres", {}) if isinstance(second_health.get("postgres"), dict) else {}
        result = {
            "ok": (
                login_status == 200
                and other_login_status == 200
                and wrong_status == 401
                and admin_users_status == 403
                and profile_status == 200
                and profile_body.get("username") == USER
                and change_status == 200
                and me_after_change_status == 200
                and old_login_status == 401
                and new_login_status == 200
                and register_accept_status == 202
                and register_accept_retry_status == 202
                and register_conflict_status == 202
                and approve_accept_status == 200
                and approve_accept_body.get("status") == "approved"
                and accepted_login_status == 200
                and register_reject_status == 202
                and approve_reject_status == 200
                and approve_reject_body.get("status") == "rejected"
                and rejected_login_status != 200
                and reset_request_status == 200
                and reset_admin_status == 200
                and reset_admin_body.get("status") == "approved"
                and reset_confirm_status == 200
                and reset_direct_login_status == 200
                and reset_direct_second_status == 400
                and plaintext_absent
                and wrong_code_status == 400
                and concurrent_statuses.count(200) == 1
                and sum(1 for status in concurrent_statuses if status == 400) == 1
                and reset_code_login_status == 200
                and used_code_status == 400
                and expired_status == 400
                and readback_status == 200
                and accepted_old_after_reset_readback_status == 401
                and reset_readback_status == 200
                and all(value == 0 for value in after_cleanup.values())
                and int(pg_metrics.get("rollbacks", 0) or 0) == 0
            ),
            "health": {"first_pid": first_health.get("pid"), "second_pid": second_health.get("pid")},
            "auth": {
                "login": login_status,
                "login_body": brief(login_body),
                "wrong_password": wrong_status,
                "wrong_body": brief(wrong_body),
                "non_admin_admin_users": admin_users_status,
                "profile_status": profile_status,
                "profile_body": brief(profile_body),
                "profile_scoped_username": profile_body.get("username"),
                "password_change": change_status,
                "old_after_change": old_login_status,
                "new_after_change": new_login_status,
                "existing_session_after_change": me_after_change_status,
            },
            "pending": {
                "register_accept": register_accept_status,
                "retry": register_accept_retry_status,
                "conflicting_retry": register_conflict_status,
                "approve_accept": approve_accept_status,
                "approve_accept_body": brief(approve_accept_body),
                "accepted_login": accepted_login_status,
                "register_reject": register_reject_status,
                "approve_reject": approve_reject_status,
                "approve_reject_body": brief(approve_reject_body),
                "rejected_login": rejected_login_status,
            },
            "reset": {
                "request": reset_request_status,
                "admin_approve": reset_admin_status,
                "admin_approve_body": brief(reset_admin_body),
                "confirm_direct": reset_confirm_status,
                "direct_login": reset_direct_login_status,
                "direct_second": reset_direct_second_status,
                "plaintext_absent": plaintext_absent,
                "wrong_code": wrong_code_status,
                "wrong_code_body": brief(_wrong_code_body),
                "concurrent": concurrent_statuses,
                "code_login": reset_code_login_status,
                "used_code": used_code_status,
                "expired": expired_status,
            },
            "restart_readback": {
                "user": readback_status,
                "accepted_old_after_reset": accepted_old_after_reset_readback_status,
                "reset_direct": reset_readback_status,
            },
            "postgres_metrics": pg_metrics,
            "before_cleanup": before_cleanup,
            "cleanup": cleanup_result,
            "after_cleanup": after_cleanup,
        }
    finally:
        try:
            cleanup()
        finally:
            if process and process.poll() is None:
                stop_pid(process.pid)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
