"""Provision or reset the permanent SQLite-only codexload001..100 benchmark pool."""

from __future__ import annotations

import argparse
import base64
import hashlib
import hmac
import json
import os
import secrets
import shutil
import socket
import sqlite3
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


DATABASE = Path(r"C:\server data\server2.db")
QMLEARN_ROOT = Path(os.environ.get("FUTURE_QMLEARN_ROOT") or r"C:\QMLearn")
LOAD_USERS = tuple(f"codexload{index:03d}" for index in range(1, 101))
LOAD_USER_SET = set(LOAD_USERS)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def password_hash(value: str) -> str:
    rounds = max(1, min(260000, int(os.environ.get("FUTURE_PASSWORD_HASH_ROUNDS", "2") or 2)))
    salt = secrets.token_urlsafe(18)
    digest = hashlib.pbkdf2_hmac("sha256", value.encode("utf-8"), salt.encode("utf-8"), rounds)
    encoded = base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")
    return f"pbkdf2_sha256${rounds}${salt}${encoded}"


def password_hash_matches(value: str, encoded: str) -> bool:
    parts = str(encoded or "").split("$")
    if len(parts) != 4 or parts[0] != "pbkdf2_sha256":
        return False
    try:
        rounds = max(1, int(parts[1]))
        digest = hashlib.pbkdf2_hmac("sha256", value.encode("utf-8"), parts[2].encode("utf-8"), rounds)
    except (TypeError, ValueError):
        return False
    actual = base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")
    return hmac.compare_digest(actual, parts[3])


def server2_is_listening() -> bool:
    try:
        with socket.create_connection(("127.0.0.1", 8877), timeout=0.3):
            return True
    except OSError:
        return False


def reset_sqlite_state(connection: sqlite3.Connection) -> int:
    placeholders = ",".join("?" for _ in LOAD_USERS)
    deleted = 0
    for table_name, in connection.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"):
        if table_name in {"users", "server_load_test_credentials", "sqlite_sequence"}:
            continue
        columns = {str(row[1]).lower() for row in connection.execute(f'PRAGMA table_info("{table_name}")')}
        if "username" not in columns:
            continue
        cursor = connection.execute(f'DELETE FROM "{table_name}" WHERE username IN ({placeholders})', LOAD_USERS)
        deleted += max(0, int(cursor.rowcount or 0))

    session_rows = connection.execute(
        "SELECT path_key,content,encoding FROM documents WHERE lower(path) LIKE ?",
        ("%_future_auth_sessions.json",),
    ).fetchall()
    for path_key, content, encoding in session_rows:
        if str(encoding or "").lower() not in {"utf-8", "utf8"}:
            continue
        payload = json.loads(bytes(content).decode("utf-8"))
        sessions = payload.get("sessions") if isinstance(payload, dict) and isinstance(payload.get("sessions"), dict) else {}
        next_sessions = {
            token: row for token, row in sessions.items()
            if not isinstance(row, dict) or str(row.get("username", "")).lower() not in LOAD_USERS
        }
        if len(next_sessions) == len(sessions):
            continue
        next_payload = {**payload, "sessions": next_sessions}
        raw = json.dumps(next_payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        connection.execute(
            "UPDATE documents SET content=?,sha256=?,file_size=?,updated_at_utc=? WHERE path_key=?",
            (raw, hashlib.sha256(raw).hexdigest(), len(raw), utc_now(), path_key),
        )

    def scrub(value):
        if isinstance(value, dict):
            username = str(value.get("username", "")).lower()
            if username in LOAD_USER_SET:
                return None
            result = {}
            for key, item in value.items():
                if str(key).lower() in LOAD_USER_SET:
                    continue
                cleaned = scrub(item)
                if cleaned is not None:
                    result[key] = cleaned
            return result
        if isinstance(value, list):
            return [cleaned for item in value if (cleaned := scrub(item)) is not None]
        return value

    for path_key, content, encoding in connection.execute(
        "SELECT path_key,content,encoding FROM documents WHERE lower(path) LIKE '%.json'"
    ).fetchall():
        raw_content = bytes(content)
        if b"codexload" not in raw_content.lower() or str(encoding or "").lower() not in {"utf-8", "utf8"}:
            continue
        payload = json.loads(raw_content.decode("utf-8"))
        cleaned_payload = scrub(payload)
        raw = json.dumps(cleaned_payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        connection.execute(
            "UPDATE documents SET content=?,sha256=?,file_size=?,updated_at_utc=? WHERE path_key=?",
            (raw, hashlib.sha256(raw).hexdigest(), len(raw), utc_now(), path_key),
        )
    # Test-user documents have no username column, so remove them by their authoritative path identity.
    for path_key, path in connection.execute("SELECT path_key,path FROM documents").fetchall():
        normalized_path = str(path or "").replace("/", "\\").lower()
        target = Path(str(path or ""))
        direct_user_file = (
            target.parent == QMLEARN_ROOT / "users"
            and target.suffix.lower() == ".txt"
            and target.stem.lower() in LOAD_USER_SET
        )
        if direct_user_file or any(f"\\{username}\\" in normalized_path for username in LOAD_USERS):
            connection.execute("DELETE FROM documents WHERE path_key=?", (path_key,))
    return deleted


def cleanup_test_directories() -> tuple[int, list[str]]:
    removed = 0
    manifest_paths: set[str] = set()
    roots = (QMLEARN_ROOT / "users", QMLEARN_ROOT / "server_users", Path(r"C:\server data"))
    for root in roots:
        root_resolved = root.resolve()
        for username in LOAD_USERS:
            generated_files = tuple(root.glob(f"{username}_*")) if root in {QMLEARN_ROOT / "users", QMLEARN_ROOT / "server_users"} else ()
            targets = (root / username, root / f"{username}.txt", *generated_files)
            for target in targets:
                if not target.exists():
                    continue
                resolved = target.resolve()
                if root_resolved not in resolved.parents:
                    raise RuntimeError(f"Refusing to clean path outside load-test roots: {resolved}")
                if resolved.is_dir():
                    shutil.rmtree(resolved)
                else:
                    resolved.unlink()
                if root == Path(r"C:\server data"):
                    manifest_paths.add(username)
                removed += 1
    return removed, sorted(manifest_paths)


def refresh_server_manifest_paths(paths: list[str]) -> bool:
    if not paths:
        return False
    request = urllib.request.Request(
        "http://127.0.0.1:8877/server-data/manifest-refresh",
        data=json.dumps({"paths": paths}, ensure_ascii=True, separators=(",", ":")).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = json.loads(response.read().decode("utf-8"))
        return bool(isinstance(payload, dict) and payload.get("ok") and payload.get("mode") == "paths")
    except Exception:
        return False


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reset-state", action="store_true")
    parser.add_argument("--rotate-credentials", action="store_true")
    args = parser.parse_args()
    password = os.environ.get("FUTURE_TEST_PASSWORD", "")
    if not password:
        raise RuntimeError("Set FUTURE_TEST_PASSWORD for provisioning; it is never written to source or AGENTS.md")
    connection = sqlite3.connect(DATABASE, timeout=30)
    connection.execute("PRAGMA foreign_keys=ON")
    connection.execute("PRAGMA synchronous=FULL")
    schema = connection.execute("SELECT value FROM database_meta WHERE key='schema_version'").fetchone()
    if not schema or int(schema[0]) < 6:
        raise RuntimeError("Restart Server 2 on schema 6 before provisioning the load-test pool")
    now = utc_now()
    existing_credentials = dict(connection.execute(
        "SELECT username,password_hash FROM server_load_test_credentials WHERE username IN ("
        + ",".join("?" for _ in LOAD_USERS) + ")",
        LOAD_USERS,
    ))
    mismatched = [
        username for username, existing_hash in existing_credentials.items()
        if existing_hash and not password_hash_matches(password, existing_hash)
    ]
    # Added 2026-07-22: never desynchronize the live Server 2 credential cache during a benchmark reset.
    if mismatched and server2_is_listening() and not args.rotate_credentials:
        raise RuntimeError(
            f"Refusing to rotate {len(mismatched)} live load-test credentials; stop/restart Server 2 or pass --rotate-credentials explicitly"
        )
    connection.execute("BEGIN IMMEDIATE")
    deleted = reset_sqlite_state(connection) if args.reset_state else 0
    for index, username in enumerate(LOAD_USERS, 1):
        profile = json.dumps(
            {"full_name": f"Server Load Test {index:03d}", "intro": "SQLite-only Server 2 load-test identity.", "load_test": True},
            ensure_ascii=True,
            separators=(",", ":"),
        )
        connection.execute(
            "INSERT INTO users(username,is_admin,is_test,profile_json,updated_at_utc) VALUES(?,0,1,?,?) "
            "ON CONFLICT(username) DO UPDATE SET is_admin=0,is_test=1,profile_json=excluded.profile_json,updated_at_utc=excluded.updated_at_utc",
            (username, profile, now),
        )
        existing_hash = existing_credentials.get(username, "")
        credential_hash = existing_hash if password_hash_matches(password, existing_hash) else password_hash(password)
        connection.execute(
            "INSERT INTO server_load_test_credentials(username,password_hash,updated_at_utc) VALUES(?,?,?) "
            "ON CONFLICT(username) DO UPDATE SET password_hash=excluded.password_hash,updated_at_utc=excluded.updated_at_utc",
            (username, credential_hash, now),
        )
    connection.commit()
    connection.execute("PRAGMA wal_checkpoint(FULL)")
    counts = {
        "users": connection.execute("SELECT COUNT(*) FROM users WHERE is_test=1").fetchone()[0],
        "credentials": connection.execute("SELECT COUNT(*) FROM server_load_test_credentials").fetchone()[0],
        "state_rows": sum(
            connection.execute(f'SELECT COUNT(*) FROM "{table}" WHERE username IN ({",".join("?" for _ in LOAD_USERS)})', LOAD_USERS).fetchone()[0]
            for table, in connection.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT IN ('users','server_load_test_credentials')")
            if "username" in {str(row[1]).lower() for row in connection.execute(f'PRAGMA table_info("{table}")')}
        ),
        "quick_check": connection.execute("PRAGMA quick_check").fetchone()[0],
    }
    connection.close()
    removed_paths, manifest_paths = cleanup_test_directories() if args.reset_state else (0, [])
    if args.reset_state:
        # Added 2026-07-22: refresh absent roots too, because an earlier interrupted cleanup may leave cache revisions behind.
        manifest_paths = sorted(set(manifest_paths).union(LOAD_USERS))
    if manifest_paths:
        # Let native create/delete notifications settle so this explicit refresh is the final manifest writer.
        time.sleep(3.0)
    manifest_delta = refresh_server_manifest_paths(manifest_paths) if manifest_paths else False
    print({**counts, "reset_rows": deleted, "removed_paths": removed_paths, "manifest_delta": manifest_delta})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
