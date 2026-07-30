#!/usr/bin/env python3
"""Migrate legacy user auth/admin/pending/reset state to scoped PostgreSQL tables."""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import FUTURE.server_app as app  # noqa: E402

DATABASE = Path(r"C:\server data\server2.db")
USER_ROOT = Path(r"C:\QMLearn\users")
CODEX_USER = "codexpguserdoc"


def _json_loads(raw: object) -> object:
    try:
        text = raw.decode("utf-8", "ignore") if isinstance(raw, (bytes, bytearray, memoryview)) else str(raw or "")
        return json.loads(text or "{}")
    except Exception:
        return {}


def _document(con: sqlite3.Connection, name: str) -> tuple[dict, str]:
    key = str((USER_ROOT / name).resolve()).lower()
    row = con.execute("SELECT content,sha256,updated_at_utc FROM documents WHERE path_key=?", (key,)).fetchone()
    if row is None:
        return {}, ""
    payload = _json_loads(row["content"])
    return (payload if isinstance(payload, dict) else {}), app.clean(row["sha256"])


def _user_lines_from_document(con: sqlite3.Connection, username: str) -> tuple[list[str], str, str]:
    path = USER_ROOT / f"{app.normalize_username(username)}.txt"
    key = str(path.resolve()).lower()
    row = con.execute("SELECT content,sha256,updated_at_utc FROM documents WHERE path_key=?", (key,)).fetchone()
    if row is None:
        return [], "", ""
    raw = row["content"]
    text = raw.decode("utf-8", "ignore") if isinstance(raw, (bytes, bytearray, memoryview)) else str(raw or "")
    return text.lstrip("\ufeff").splitlines(), app.clean(row["sha256"]), app.clean(row["updated_at_utc"])


def sqlite_payload() -> dict:
    con = sqlite3.connect(f"file:{DATABASE.as_posix()}?mode=ro", uri=True, timeout=30)
    con.row_factory = sqlite3.Row
    try:
        credentials = []
        for row in con.execute("SELECT username,updated_at_utc FROM users WHERE is_test=0 ORDER BY lower(username)"):
            username = app.normalize_username(row["username"])
            lines, sha, doc_updated = _user_lines_from_document(con, username)
            if not lines or ":" not in lines[0]:
                continue
            stored_user, password_hash = lines[0].split(":", 1)
            if app.normalize_username(stored_user) != username:
                continue
            credentials.append({
                "username": username,
                "password_hash": app.clean(password_hash),
                "source_path": str(USER_ROOT / f"{username}.txt"),
                "updated_at_utc": doc_updated or app.clean(row["updated_at_utc"]),
                "source_sha256": sha,
            })
        admins_doc, admins_sha = _document(con, "_future_admins.json")
        admins = admins_doc.get("admins", admins_doc) if isinstance(admins_doc, dict) else []
        admin_rows = [
            {
                "username": app.normalize_username(item),
                "enabled": True,
                "updated_at_utc": app.clean(admins_doc.get("updated_at", "")) or app.utc_timestamp(),
                "source_sha256": admins_sha,
            }
            for item in (admins if isinstance(admins, list) else [])
            if app.normalize_username(item)
        ]
        pending_doc, pending_sha = _document(con, "_web_pending_users.json")
        pending = []
        for key, item in sorted((pending_doc or {}).items(), key=lambda pair: app.normalize_username(pair[0])):
            if not isinstance(item, dict):
                continue
            username = app.normalize_username(item.get("username", key))
            if not username:
                continue
            profile = item.get("profile") if isinstance(item.get("profile"), dict) else {}
            updated = app.clean(item.get("reviewed_at") or item.get("requested_at")) or app.utc_timestamp()
            pending.append({
                "username": username,
                "password_hash": app.clean(item.get("password_hash", "")),
                "profile": profile,
                "status": app.clean(item.get("status", "pending")) or "pending",
                "requested_at_utc": app.clean(item.get("requested_at", "")),
                "reviewed_at_utc": app.clean(item.get("reviewed_at", "")),
                "updated_at_utc": updated,
                "source_sha256": pending_sha,
            })
        reset_doc, reset_sha = _document(con, "_future_password_resets.json")
        resets = []
        for key, item in sorted((reset_doc or {}).items(), key=lambda pair: app.normalize_username(pair[0])):
            if not isinstance(item, dict):
                continue
            username = app.normalize_username(item.get("username", key))
            if not username:
                continue
            updated = app.clean(item.get("reviewed_at") or item.get("requested_at")) or app.utc_timestamp()
            resets.append({
                "username": username,
                "status": app.clean(item.get("status", "pending")) or "pending",
                "full_name": app.clean(item.get("full_name", "")),
                "email": app.clean(item.get("email", "")),
                "email_alias": app.clean(item.get("email_alias", "")),
                "client": app.clean(item.get("client", "")),
                "requested_at_utc": app.clean(item.get("requested_at", "")),
                "reviewed_at_utc": app.clean(item.get("reviewed_at", "")),
                "expires_epoch": float(item.get("expires_at", 0) or 0),
                "attempts": int(item.get("attempts", 0) or 0),
                "has_code_hash": bool(app.clean(item.get("code_hash", ""))),
                "updated_at_utc": updated,
                "source_sha256": reset_sha,
            })
        return {"credentials": credentials, "admins": admin_rows, "pending": pending, "resets": resets}
    finally:
        con.close()


def fingerprint(rows: list[dict]) -> str:
    digest = hashlib.sha256()
    for row in rows:
        digest.update(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8"))
        digest.update(b"\n")
    return digest.hexdigest()


def stable_rows(kind: str, rows: list[dict]) -> list[dict]:
    stable = []
    for row in rows:
        item = dict(row)
        item.pop("source_sha256", None)
        if kind == "admins":
            item.pop("updated_at_utc", None)
        stable.append(item)
    return stable


def postgres_payload() -> dict:
    def _read(connection):
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT username,password_hash,source_path,updated_at_utc,source_sha256 FROM future_server2.user_auth_credentials ORDER BY lower(username)"
            )
            credentials = [
                {"username": app.normalize_username(r[0]), "password_hash": app.clean(r[1]), "source_path": app.clean(r[2]), "updated_at_utc": app.clean(r[3]), "source_sha256": app.clean(r[4])}
                for r in cursor.fetchall()
            ]
            cursor.execute("SELECT username,enabled,updated_at_utc,source_sha256 FROM future_server2.admin_users ORDER BY lower(username)")
            admins = [
                {"username": app.normalize_username(r[0]), "enabled": bool(r[1]), "updated_at_utc": app.clean(r[2]), "source_sha256": app.clean(r[3])}
                for r in cursor.fetchall()
            ]
            cursor.execute(
                "SELECT username,password_hash,profile_json,status,requested_at_utc,reviewed_at_utc,updated_at_utc,source_sha256 FROM future_server2.pending_registrations ORDER BY lower(username)"
            )
            pending = [
                {
                    "username": app.normalize_username(r[0]),
                    "password_hash": app.clean(r[1]),
                    "profile": dict(r[2]) if isinstance(r[2], dict) else {},
                    "status": app.clean(r[3]),
                    "requested_at_utc": app.clean(r[4]),
                    "reviewed_at_utc": app.clean(r[5]),
                    "updated_at_utc": app.clean(r[6]),
                    "source_sha256": app.clean(r[7]),
                }
                for r in cursor.fetchall()
            ]
            cursor.execute(
                "SELECT username,status,full_name,email,email_alias,client,requested_at_utc,reviewed_at_utc,expires_epoch,attempts,has_code_hash,updated_at_utc,source_sha256 FROM future_server2.password_reset_requests ORDER BY lower(username)"
            )
            resets = [
                {
                    "username": app.normalize_username(r[0]),
                    "status": app.clean(r[1]),
                    "full_name": app.clean(r[2]),
                    "email": app.clean(r[3]),
                    "email_alias": app.clean(r[4]),
                    "client": app.clean(r[5]),
                    "requested_at_utc": app.clean(r[6]),
                    "reviewed_at_utc": app.clean(r[7]),
                    "expires_epoch": float(r[8] or 0),
                    "attempts": int(r[9] or 0),
                    "has_code_hash": bool(r[10]),
                    "updated_at_utc": app.clean(r[11]),
                    "source_sha256": app.clean(r[12]),
                }
                for r in cursor.fetchall()
            ]
        return {"credentials": credentials, "admins": admins, "pending": pending, "resets": resets}

    return app.postgres_execute(_read)


def copy_to_postgres(payload: dict) -> dict:
    now = app.utc_timestamp()

    def _write(connection):
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM future_server2.user_auth_credentials")
            cursor.execute("DELETE FROM future_server2.admin_users")
            cursor.execute("DELETE FROM future_server2.pending_registrations")
            cursor.execute("DELETE FROM future_server2.password_reset_requests")
            for row in payload["credentials"]:
                updated = app.clean(row["updated_at_utc"]) or now
                cursor.execute(
                    "INSERT INTO future_server2.user_auth_credentials(username,password_hash,source_path,updated_at_utc,updated_epoch,migrated_at_utc,source_sha256) VALUES (%s,%s,%s,%s,%s,%s,%s)",
                    (row["username"], row["password_hash"], row["source_path"], updated, app.timestamp_to_epoch(updated), now, row["source_sha256"]),
                )
            for row in payload["admins"]:
                updated = app.clean(row["updated_at_utc"]) or now
                cursor.execute(
                    "INSERT INTO future_server2.admin_users(username,enabled,updated_at_utc,updated_epoch,migrated_at_utc,source_sha256) VALUES (%s,%s,%s,%s,%s,%s)",
                    (row["username"], row["enabled"], updated, app.timestamp_to_epoch(updated), now, row["source_sha256"]),
                )
            for row in payload["pending"]:
                updated = app.clean(row["updated_at_utc"]) or now
                cursor.execute(
                    "INSERT INTO future_server2.pending_registrations(username,password_hash,profile_json,status,requested_at_utc,reviewed_at_utc,updated_at_utc,updated_epoch,migrated_at_utc,source_sha256) VALUES (%s,%s,%s::jsonb,%s,%s,%s,%s,%s,%s,%s)",
                    (row["username"], row["password_hash"], json.dumps(row["profile"], ensure_ascii=False, separators=(",", ":")), row["status"], row["requested_at_utc"], row["reviewed_at_utc"], updated, app.timestamp_to_epoch(updated), now, row["source_sha256"]),
                )
            for row in payload["resets"]:
                updated = app.clean(row["updated_at_utc"]) or now
                cursor.execute(
                    "INSERT INTO future_server2.password_reset_requests(username,status,full_name,email,email_alias,client,requested_at_utc,reviewed_at_utc,expires_epoch,attempts,has_code_hash,updated_at_utc,updated_epoch,migrated_at_utc,source_sha256) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                    (row["username"], row["status"], row["full_name"], row["email"], row["email_alias"], row["client"], row["requested_at_utc"], row["reviewed_at_utc"], row["expires_epoch"], row["attempts"], row["has_code_hash"], updated, app.timestamp_to_epoch(updated), now, row["source_sha256"]),
                )
        return {key: len(payload[key]) for key in payload}

    return app.postgres_execute(_write)


def cleanup_test_rows() -> dict:
    def _cleanup(connection):
        out = {}
        with connection.cursor() as cursor:
            for table in ("user_auth_credentials", "admin_users", "pending_registrations", "password_reset_requests"):
                cursor.execute(f"DELETE FROM future_server2.{table} WHERE lower(username)=%s", (CODEX_USER,))
                out[table] = int(cursor.rowcount or 0)
        return out

    return app.postgres_execute(_cleanup)


def round_trip() -> dict:
    stamp = app.utc_timestamp()

    def _write(connection):
        with connection.cursor() as cursor:
            cursor.execute(
                "INSERT INTO future_server2.user_auth_credentials(username,password_hash,source_path,updated_at_utc,updated_epoch,migrated_at_utc,source_sha256) VALUES (%s,%s,%s,%s,%s,%s,%s) ON CONFLICT(username) DO UPDATE SET password_hash=excluded.password_hash,updated_at_utc=excluded.updated_at_utc",
                (CODEX_USER, "pbkdf2_sha256$2$codex$redacted", "", stamp, app.timestamp_to_epoch(stamp), stamp, "codex"),
            )
            cursor.execute(
                "INSERT INTO future_server2.admin_users(username,enabled,updated_at_utc,updated_epoch,migrated_at_utc,source_sha256) VALUES (%s,true,%s,%s,%s,%s) ON CONFLICT(username) DO UPDATE SET enabled=excluded.enabled,updated_at_utc=excluded.updated_at_utc",
                (CODEX_USER, stamp, app.timestamp_to_epoch(stamp), stamp, "codex"),
            )
            cursor.execute(
                "INSERT INTO future_server2.pending_registrations(username,password_hash,profile_json,status,requested_at_utc,reviewed_at_utc,updated_at_utc,updated_epoch,migrated_at_utc,source_sha256) VALUES (%s,%s,%s::jsonb,'pending',%s,'',%s,%s,%s,'codex') ON CONFLICT(username) DO UPDATE SET status=excluded.status,updated_at_utc=excluded.updated_at_utc",
                (CODEX_USER, "pbkdf2_sha256$2$codex$redacted", '{"full_name":"Codex"}', stamp, stamp, app.timestamp_to_epoch(stamp), stamp),
            )
            cursor.execute(
                "INSERT INTO future_server2.password_reset_requests(username,status,requested_at_utc,updated_at_utc,updated_epoch,migrated_at_utc,source_sha256) VALUES (%s,'pending',%s,%s,%s,%s,'codex') ON CONFLICT(username) DO UPDATE SET status=excluded.status,updated_at_utc=excluded.updated_at_utc",
                (CODEX_USER, stamp, stamp, app.timestamp_to_epoch(stamp), stamp),
            )
        return True

    return {"ok": bool(app.postgres_execute(_write))}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--verify-only", action="store_true")
    parser.add_argument("--cleanup-test-rows", action="store_true")
    args = parser.parse_args()
    app.postgres_initialize_schema()
    cleanup = cleanup_test_rows() if args.cleanup_test_rows else None
    sqlite = sqlite_payload()
    result = {"parity": False}
    try:
        copied = None if args.verify_only else copy_to_postgres(sqlite)
        rt = None if args.verify_only else round_trip()
        if rt is not None:
            post_rt_cleanup = cleanup_test_rows()
        else:
            post_rt_cleanup = None
        pg = postgres_payload()
        fps = {key: fingerprint(stable_rows(key, sqlite[key])) for key in sqlite}
        pg_fps = {key: fingerprint(stable_rows(key, pg[key])) for key in pg}
        counts = {key: len(sqlite[key]) for key in sqlite}
        pg_counts = {key: len(pg[key]) for key in pg}
        parity = counts == pg_counts and fps == pg_fps and all(v == 0 for v in cleanup_test_rows().values())
        result = {
            "counts": counts,
            "postgres_counts": pg_counts,
            "fingerprints": fps,
            "postgres_fingerprints": pg_fps,
            "parity": parity,
            "copied": copied,
            "round_trip": rt,
            "cleanup": cleanup,
            "post_round_trip_cleanup": post_rt_cleanup,
            "verify_only": args.verify_only,
        }
    finally:
        if not args.verify_only:
            cleanup_test_rows()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("parity") else 1


if __name__ == "__main__":
    raise SystemExit(main())
