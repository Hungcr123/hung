"""Focused Space_V progress delta probe.

Added 2026-07-27 for the common/overlay checkpoint. It performs one durable
Space_V write on Quynh, verifies that shared common cache remains isolated for
Hưng and Quynh, then restores Quynh's original Space_V payload through HTTP.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path

import psycopg
from psycopg.types.json import Jsonb
import requests

from benchmark_space_v_progress_get_hot_path import clean

BASE = os.environ.get("FUTURE_PROBE_BASE", "http://127.0.0.1:8877")


def login(username: str, password: str) -> requests.Session:
    session = requests.Session()
    response = session.post(f"{BASE}/auth/login", json={"username": username, "password": password}, timeout=30)
    response.raise_for_status()
    token = str(response.json().get("token") or "").strip()
    if not token:
        raise RuntimeError(f"Login returned no token for {username}")
    session.headers.update({"Authorization": f"Bearer {token}"})
    return session


def pg_connect() -> psycopg.Connection:
    dsn = os.environ.get("FUTURE_PG_DSN", "").strip()
    if not dsn:
        raise RuntimeError("Set FUTURE_PG_DSN for this probe only")
    return psycopg.connect(dsn, autocommit=False)


def pg_snapshot(username: str) -> tuple[list[str], list[tuple], list[str], list[tuple], dict]:
    with pg_connect() as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT current_database(), current_user")
            current_database, current_user = cursor.fetchone()
            cursor.execute(
                """
                SELECT *
                FROM future_server2.lesson_progress
                WHERE lower(username) = %s AND space = 'Space_V'
                ORDER BY updated_epoch DESC, updated_at_utc DESC, file_id DESC
                """,
                (username.lower(),),
            )
            progress_rows = cursor.fetchall()
            progress_columns = [col.name for col in cursor.description]
            cursor.execute(
                """
                SELECT *
                FROM future_server2.lesson_progress_namespaces
                WHERE lower(username) = %s AND space = 'Space_V'
                ORDER BY updated_epoch DESC, updated_at_utc DESC
                """,
                (username.lower(),),
            )
            namespace_rows = cursor.fetchall()
            namespace_columns = [col.name for col in cursor.description]
    if not progress_rows:
        raise RuntimeError(f"No Space_V PG rows exist for {username}")
    return progress_columns, progress_rows, namespace_columns, namespace_rows, {
        "current_database": str(current_database or ""),
        "current_user": str(current_user or ""),
    }


def rows_hash(rows: list[tuple]) -> str:
    encoded = json.dumps(rows, ensure_ascii=False, separators=(",", ":"), default=str)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def jsonish(value: object) -> dict:
    if isinstance(value, dict):
        return value
    if value is None:
        return {}


def restore_pg_snapshot(username: str, snapshot: tuple[list[str], list[tuple], list[str], list[tuple], dict]) -> None:
    progress_columns, progress_rows, namespace_columns, namespace_rows, _pg = snapshot
    progress_json_indexes = {index for index, name in enumerate(progress_columns) if name == "record_json"}
    with pg_connect() as connection:
        with connection.cursor() as cursor:
            cursor.execute("BEGIN")
            cursor.execute(
                "DELETE FROM future_server2.lesson_progress WHERE lower(username) = %s AND space = 'Space_V'",
                (username.lower(),),
            )
            cursor.execute(
                "DELETE FROM future_server2.lesson_progress_namespaces WHERE lower(username) = %s AND space = 'Space_V'",
                (username.lower(),),
            )
            progress_placeholders = ",".join("%s" for _ in progress_columns)
            progress_insert = (
                f"INSERT INTO future_server2.lesson_progress ({','.join(progress_columns)}) "
                f"VALUES ({progress_placeholders})"
            )
            for row in progress_rows:
                adapted = [Jsonb(value) if index in progress_json_indexes and isinstance(value, (dict, list)) else value for index, value in enumerate(row)]
                cursor.execute(progress_insert, adapted)
            namespace_placeholders = ",".join("%s" for _ in namespace_columns)
            namespace_insert = (
                f"INSERT INTO future_server2.lesson_progress_namespaces ({','.join(namespace_columns)}) "
                f"VALUES ({namespace_placeholders})"
            )
            for row in namespace_rows:
                cursor.execute(namespace_insert, row)
        connection.commit()
    try:
        return json.loads(str(value))
    except Exception:
        return {}


def common_tree(session: requests.Session, etag: str = "") -> dict:
    headers = {}
    if etag:
        headers["If-None-Match"] = etag
    response = session.get(f"{BASE}/server-data/common-tree", headers=headers, timeout=45)
    payload = response.json() if response.status_code != 304 else {}
    return {
        "status": response.status_code,
        "etag": str(response.headers.get("ETag") or ""),
        "cache_hit": str(response.headers.get("X-Future-Cache-Hit") or ""),
        "rows": int(payload.get("row_count", 0) or 0),
        "common_signature": str(payload.get("common_manifest_signature") or ""),
    }


def user_overlay(session: requests.Session, etag: str = "") -> dict:
    headers = {}
    if etag:
        headers["If-None-Match"] = etag
    response = session.get(f"{BASE}/server-data/user-overlay", headers=headers, timeout=45)
    payload = response.json() if response.status_code != 304 else {}
    return {
        "status": response.status_code,
        "etag": str(response.headers.get("ETag") or ""),
        "cache_hit": str(response.headers.get("X-Future-Cache-Hit") or ""),
        "rows": int(payload.get("row_count", 0) or 0),
        "overlay_revision": str(payload.get("overlay_revision") or ""),
    }


def space_v_read(session: requests.Session, path: str, identity: str, etag: str = "") -> dict:
    headers = {}
    if etag:
        headers["If-None-Match"] = etag
    response = session.get(
        f"{BASE}/space-v/progress",
        headers=headers,
        params={"path": path, "identity": identity},
        timeout=45,
    )
    payload = response.json() if response.status_code != 304 else {}
    return {
        "status": response.status_code,
        "etag": str(response.headers.get("ETag") or ""),
        "cache_hit": str(response.headers.get("X-Future-Cache-Hit") or ""),
        "body_bytes": len(response.content),
        "response_schema": str(payload.get("response_schema") or ""),
        "progress": payload.get("progress") if isinstance(payload.get("progress"), dict) else {},
        "summary": payload.get("summary") if isinstance(payload.get("summary"), dict) else {},
    }


def pick_quynh_row(snapshot: tuple[list[str], list[tuple], list[str], list[tuple], dict]) -> dict:
    progress_columns, progress_rows, _namespace_columns, _namespace_rows, _pg = snapshot
    column_index = {name: idx for idx, name in enumerate(progress_columns)}
    candidates = [row for row in progress_rows if str(row[column_index.get("username", -1)] or "").lower() == "quynh"]
    if not candidates:
        raise RuntimeError("No Quynh Space_V row exists")
    candidates.sort(
        key=lambda row: (
            str(row[column_index.get("updated_at_utc", -1)] or ""),
            int(row[column_index.get("server_revision", -1)] or 0),
            str(row[column_index.get("path", -1)] or ""),
            str(row[column_index.get("identity", -1)] or ""),
        ),
        reverse=True,
    )
    row = candidates[0]
    return {
        "row": row,
        "path": str(row[column_index.get("path", -1)] or ""),
        "identity": str(row[column_index.get("identity", -1)] or ""),
        "server_revision": int(row[column_index.get("server_revision", -1)] or 0),
        "record_json": jsonish(row[column_index.get("record_json", -1)]),
    }


def main() -> int:
    hung_password = os.environ.get("FUTURE_HUNG_PASSWORD", "")
    quynh_password = os.environ.get("FUTURE_QUYNH_PASSWORD", "")
    if not hung_password or not quynh_password:
        raise RuntimeError("Set FUTURE_HUNG_PASSWORD and FUTURE_QUYNH_PASSWORD for this probe only")

    hung = login("hung", hung_password)
    quynh = login("quynh", quynh_password)

    before_snapshot = pg_snapshot("quynh")
    quynh_target = pick_quynh_row(before_snapshot)
    progress_before = space_v_read(quynh, quynh_target["path"], quynh_target["identity"])
    before_hash = rows_hash(before_snapshot[1])
    hung_common_before = common_tree(hung)
    quynh_common_before = common_tree(quynh)
    hung_overlay_before = user_overlay(hung)
    quynh_overlay_before = user_overlay(quynh)

    write_payload = json.loads(json.dumps(progress_before["progress"]))
    stamp = str(time.time_ns())
    saved_at = write_payload.get("savedAt") or write_payload.get("updatedAt") or ""
    if not clean(saved_at):
        saved_at = "2026-07-27T00:00:00Z"
    write_payload.update({
        "action": "new_run",
        "runId": f"codex-delta-isolation-{stamp}",
        "activeRun": True,
        "savedAt": saved_at,
        "updatedAt": saved_at,
        "syncOperationId": f"codex-delta-op-{stamp}",
    })
    state = write_payload.get("state") if isinstance(write_payload.get("state"), dict) else {}
    state.update({
        "runId": write_payload["runId"],
        "activeRun": True,
        "savedAt": saved_at,
        "updatedAt": saved_at,
        "syncOperationId": write_payload["syncOperationId"],
    })
    write_payload["state"] = state

    write_started = time.perf_counter()
    write_response = quynh.post(
        f"{BASE}/space-v/progress?client_source=codex_delta_isolation&response=compact-v1",
        json=write_payload,
        timeout=45,
    )
    write_ms = (time.perf_counter() - write_started) * 1000
    write_response.raise_for_status()
    write_body = write_response.json()

    after_snapshot = pg_snapshot("quynh")
    after_hash = rows_hash(after_snapshot[1])
    after_target = pick_quynh_row(after_snapshot)
    progress_after_write = space_v_read(quynh, quynh_target["path"], quynh_target["identity"], progress_before["etag"])

    hung_common_after = common_tree(hung, hung_common_before["etag"])
    quynh_common_after = common_tree(quynh, quynh_common_before["etag"])
    hung_overlay_after = user_overlay(hung, hung_overlay_before["etag"])
    quynh_overlay_after = user_overlay(quynh, quynh_overlay_before["etag"])

    restore_pg_snapshot("quynh", before_snapshot)
    restored_snapshot = pg_snapshot("quynh")
    restored_hash = rows_hash(restored_snapshot[1])
    progress_after_restore = space_v_read(quynh, quynh_target["path"], quynh_target["identity"], progress_before["etag"])

    raw = {
        "pg_probe": before_snapshot[4],
        "write_ms": round(write_ms, 3),
        "write_status": write_response.status_code,
        "write_response_schema": clean(write_body.get("response_schema")),
        "write_body_bytes": len(write_response.content),
        "progress_before": progress_before,
        "progress_after_write": progress_after_write,
        "progress_after_restore": progress_after_restore,
        "quynh_before_hash": before_hash,
        "quynh_after_hash": after_hash,
        "quynh_restored_hash": restored_hash,
        "quynh_rows_changed": before_hash != after_hash,
        "quynh_restore_ok": before_hash == restored_hash,
        "progress_restored_304": progress_after_restore["status"] == 304,
        "common_unchanged_for_hung": hung_common_before["etag"] == hung_common_after["etag"] and hung_common_after["status"] == 304,
        "common_unchanged_for_quynh": quynh_common_before["etag"] == quynh_common_after["etag"] and quynh_common_after["status"] == 304,
        "hung_overlay_304": hung_overlay_after["status"] == 304,
        "quynh_overlay_304": quynh_overlay_after["status"] == 304,
        "write_changed_summary": progress_before["etag"] != progress_after_write["etag"],
        "write_changed_row_revision": int(after_target["server_revision"]) != int(quynh_target["server_revision"]),
        "write_before_revision": int(quynh_target["server_revision"]),
        "write_after_revision": int(after_target["server_revision"]),
        "restore_row_count": len(restored_snapshot[1]),
    }

    out = Path(r"C:\Users\Admin\.codex\plans\server2_postgres_full_audit\checkpoint_006_space_v_progress_delta_isolation_raw.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "ok": True,
        "output": str(out),
        "pg_probe": raw["pg_probe"],
        "write_response_schema": raw["write_response_schema"],
        "write_body_bytes": raw["write_body_bytes"],
        "write_before_revision": raw["write_before_revision"],
        "write_after_revision": raw["write_after_revision"],
        "quynh_rows_changed": raw["quynh_rows_changed"],
        "quynh_restore_ok": raw["quynh_restore_ok"],
        "progress_restored_304": raw["progress_restored_304"],
        "common_unchanged_for_hung": raw["common_unchanged_for_hung"],
        "common_unchanged_for_quynh": raw["common_unchanged_for_quynh"],
        "hung_overlay_304": raw["hung_overlay_304"],
        "quynh_overlay_304": raw["quynh_overlay_304"],
        "write_changed_summary": raw["write_changed_summary"],
        "write_changed_row_revision": raw["write_changed_row_revision"],
        "write_ms": raw["write_ms"],
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
