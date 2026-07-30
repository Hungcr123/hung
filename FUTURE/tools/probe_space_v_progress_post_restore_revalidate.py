"""Focused Space_V post-restore revalidation proof.

Added 2026-07-27 for the common cache checkpoint. This script uses the
localhost-only Codex login route only to obtain sessions without placing test
passwords in command lines. It verifies PostgreSQL-backed Space_V writes,
restores the original PostgreSQL rows, restarts the isolated 18877 server, and
then proves the restored progress ETag revalidates.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import psycopg
from psycopg.types.json import Jsonb
import requests

ROOT = Path(__file__).resolve().parents[2]
BASE = os.environ.get("FUTURE_PROBE_BASE", "http://127.0.0.1:18877")
OUT = Path(r"C:\Users\Admin\.codex\plans\server2_postgres_full_audit\checkpoint_006_space_v_progress_post_restore_revalidate_2026-07-27.json")


def clean(value: object) -> str:
    return str(value or "").strip()


def pg_connect() -> psycopg.Connection:
    dsn = os.environ.get("FUTURE_PG_DSN", "").strip()
    if not dsn:
        raise RuntimeError("FUTURE_PG_DSN is required")
    return psycopg.connect(dsn, autocommit=False)


def login_local(username: str) -> requests.Session:
    session = requests.Session()
    response = session.get(
        f"{BASE}/auth/codex-local-login",
        params={"marker": "1", "username": username, "next": "/status"},
        allow_redirects=False,
        timeout=30,
    )
    if response.status_code != 302:
        raise RuntimeError(f"Local session bootstrap failed for {username}: {response.status_code} {response.text[:200]}")
    token = ""
    for cookie in session.cookies:
        if cookie.name == "future_lesson_auth_token":
            token = cookie.value
            break
    if not token:
        set_cookie = response.headers.get("Set-Cookie", "")
        prefix = "future_lesson_auth_token="
        if prefix in set_cookie:
            token = set_cookie.split(prefix, 1)[1].split(";", 1)[0].strip()
    if not token:
        # Cookie name is intentionally not imported from server internals.
        for cookie in session.cookies:
            if "session" in cookie.name.lower():
                token = cookie.value
                break
    if not token:
        raise RuntimeError(f"Local session bootstrap returned no auth cookie for {username}")
    session.headers.update({"Authorization": f"Bearer {token}"})
    return session


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
        raise RuntimeError(f"No Space_V PostgreSQL rows exist for {username}")
    return progress_columns, progress_rows, namespace_columns, namespace_rows, {
        "current_database": str(current_database or ""),
        "current_user": str(current_user or ""),
    }


def restore_pg_snapshot(username: str, snapshot: tuple[list[str], list[tuple], list[str], list[tuple], dict]) -> None:
    progress_columns, progress_rows, namespace_columns, namespace_rows, _pg = snapshot
    progress_json_indexes = {index for index, name in enumerate(progress_columns) if name == "record_json"}
    with pg_connect() as connection:
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM future_server2.lesson_progress WHERE lower(username) = %s AND space = 'Space_V'", (username.lower(),))
            cursor.execute("DELETE FROM future_server2.lesson_progress_namespaces WHERE lower(username) = %s AND space = 'Space_V'", (username.lower(),))
            progress_insert = f"INSERT INTO future_server2.lesson_progress ({','.join(progress_columns)}) VALUES ({','.join('%s' for _ in progress_columns)})"
            for row in progress_rows:
                adapted = [Jsonb(value) if index in progress_json_indexes and isinstance(value, (dict, list)) else value for index, value in enumerate(row)]
                cursor.execute(progress_insert, adapted)
            namespace_insert = f"INSERT INTO future_server2.lesson_progress_namespaces ({','.join(namespace_columns)}) VALUES ({','.join('%s' for _ in namespace_columns)})"
            for row in namespace_rows:
                cursor.execute(namespace_insert, row)
        connection.commit()


def rows_hash(rows: list[tuple]) -> str:
    encoded = json.dumps(rows, ensure_ascii=False, separators=(",", ":"), default=str)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def pick_quynh_row(snapshot: tuple[list[str], list[tuple], list[str], list[tuple], dict]) -> dict:
    columns, rows, _namespace_columns, _namespace_rows, _pg = snapshot
    index = {name: idx for idx, name in enumerate(columns)}
    row = rows[0]
    record = row[index["record_json"]]
    record = dict(record) if isinstance(record, dict) else {}
    return {
        "path": clean(row[index["path"]] or record.get("path")),
        "identity": clean(row[index["identity"]] or record.get("identity")),
        "server_revision": int(row[index["server_revision"]] or 0),
    }


def get_progress(session: requests.Session, path: str, identity: str, etag: str = "") -> dict:
    headers = {"If-None-Match": etag} if etag else {}
    response = session.get(f"{BASE}/space-v/progress", params={"path": path, "identity": identity}, headers=headers, timeout=45)
    payload = response.json() if response.status_code != 304 and response.content else {}
    return {
        "status": response.status_code,
        "etag": response.headers.get("ETag", ""),
        "cache_hit": response.headers.get("X-Future-Cache-Hit", ""),
        "body_bytes": len(response.content),
        "progress": payload.get("progress") if isinstance(payload.get("progress"), dict) else {},
    }


def common_tree(session: requests.Session, etag: str = "") -> dict:
    headers = {"If-None-Match": etag} if etag else {}
    response = session.get(f"{BASE}/server-data/common-tree", headers=headers, timeout=45)
    return {"status": response.status_code, "etag": response.headers.get("ETag", ""), "body_bytes": len(response.content)}


def user_overlay(session: requests.Session, etag: str = "") -> dict:
    headers = {"If-None-Match": etag} if etag else {}
    response = session.get(f"{BASE}/server-data/user-overlay", headers=headers, timeout=45)
    return {"status": response.status_code, "etag": response.headers.get("ETag", ""), "body_bytes": len(response.content)}


def run_server(tag: str, env: dict[str, str]) -> subprocess.Popen:
    stdout = OUT.with_name(f"checkpoint_006_{tag}_18877.out.log")
    stderr = OUT.with_name(f"checkpoint_006_{tag}_18877.err.log")
    process = subprocess.Popen(
        [sys.executable, str(ROOT / "FUTURE_SERVER_2.py"), "--host", "127.0.0.1", "--port", "18877", "--no-browser", "--no-tunnel", "--no-preload"],
        cwd=str(ROOT),
        stdout=stdout.open("wb"),
        stderr=stderr.open("wb"),
        env=env,
    )
    deadline = time.time() + 90
    last = ""
    while time.time() < deadline:
        if process.poll() is not None:
            break
        try:
            health = requests.get(f"{BASE}/health", timeout=4)
            if health.status_code == 200 and health.json().get("ok"):
                return process
        except Exception as exc:
            last = str(exc)
        time.sleep(1)
    raise RuntimeError(f"Server 18877 did not become healthy for {tag}: exit={process.poll()} last={last} stdout={stdout} stderr={stderr}")


def stop_server(process: subprocess.Popen | None) -> None:
    if process is None or process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=10)


def scoped_env() -> dict[str, str]:
    env = dict(os.environ)
    domains = (
        "AI_HISTORY_DOCUMENTS", "ANNOUNCEMENTS", "APPEND_EVENTS", "AUTH", "CHAT", "INVENTORY",
        "LEADERBOARD_DOCUMENTS", "LEARNING_SUMMARY_DOCUMENTS", "LESSON_FOLDER_LINKS", "LESSON_IDENTITY",
        "LESSON_LAST_FILE", "LESSON_PROGRESS", "LESSON_TASK", "LESSON_TASK_NOTICES", "LESSON_TIME",
        "PDF_DRAWINGS", "QMDICT_DOCUMENTS", "QM_CITY_DOCUMENTS", "SPACE_PDF_AI_DOCUMENTS",
        "SPACE_W_SPEAK_SKIP", "USER_AUTH_DOCS", "USER_PREFERENCES", "VAULT_METADATA",
        "VIEWER_TOOL_DOCUMENTS", "VOCABULARY", "VOCAB_IMAGE_CACHE",
    )
    for domain in domains:
        env[f"FUTURE_DB_{domain}_BACKEND"] = "postgres"
    env["FUTURE_POSTGRES_ONLY"] = "1"
    env.pop("FUTURE_DB_BACKEND", None)
    env.pop("FUTURE_POSTGRES_BACKEND", None)
    return env


def main() -> int:
    env = scoped_env()
    first = second = None
    evidence: dict[str, object] = {"started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    before_snapshot = pg_snapshot("quynh")
    before_hash = rows_hash(before_snapshot[1])
    target = pick_quynh_row(before_snapshot)
    try:
        first = run_server("post_restore_first", env)
        evidence["first_pid"] = first.pid
        hung = login_local("hung")
        quynh = login_local("quynh")
        progress_before = get_progress(quynh, target["path"], target["identity"])
        hung_common_before = common_tree(hung)
        quynh_common_before = common_tree(quynh)
        hung_overlay_before = user_overlay(hung)
        quynh_overlay_before = user_overlay(quynh)
        write_payload = json.loads(json.dumps(progress_before["progress"], ensure_ascii=False))
        stamp = str(time.time_ns())
        state = write_payload.get("state") if isinstance(write_payload.get("state"), dict) else {}
        write_payload.update({"action": "new_run", "runId": f"codex-restore-revalidate-{stamp}", "activeRun": True, "syncOperationId": f"codex-restore-revalidate-op-{stamp}"})
        state.update({"runId": write_payload["runId"], "activeRun": True, "syncOperationId": write_payload["syncOperationId"]})
        write_payload["state"] = state
        response = quynh.post(f"{BASE}/space-v/progress?client_source=codex_restore_revalidate&response=compact-v1", json=write_payload, timeout=45)
        response.raise_for_status()
        after_snapshot = pg_snapshot("quynh")
        progress_after_write = get_progress(quynh, target["path"], target["identity"], progress_before["etag"])
        restore_pg_snapshot("quynh", before_snapshot)
        restored_snapshot = pg_snapshot("quynh")
        hung_common_after = common_tree(hung, hung_common_before["etag"])
        quynh_common_after = common_tree(quynh, quynh_common_before["etag"])
        hung_overlay_after = user_overlay(hung, hung_overlay_before["etag"])
        quynh_overlay_after = user_overlay(quynh, quynh_overlay_before["etag"])
        stop_server(first)
        first = None
        second = run_server("post_restore_second", env)
        evidence["second_pid"] = second.pid
        quynh_reloaded = login_local("quynh")
        progress_after_restart = get_progress(quynh_reloaded, target["path"], target["identity"], progress_before["etag"])
        evidence.update({
            "pg_probe": before_snapshot[4],
            "auth_session_method": "localhost_codex_local_login",
            "password_auth_evidence": "not part of this cache probe",
            "write_status": response.status_code,
            "write_response_schema": response.json().get("response_schema"),
            "write_body_bytes": len(response.content),
            "write_before_revision": target["server_revision"],
            "quynh_rows_changed": before_hash != rows_hash(after_snapshot[1]),
            "quynh_restore_ok": before_hash == rows_hash(restored_snapshot[1]),
            "progress_before": {k: progress_before[k] for k in ("status", "etag", "body_bytes")},
            "progress_after_write": {k: progress_after_write[k] for k in ("status", "etag", "cache_hit", "body_bytes")},
            "progress_after_restart_restore": {k: progress_after_restart[k] for k in ("status", "etag", "cache_hit", "body_bytes")},
            "progress_restored_revalidated": progress_after_restart["status"] == 304 and progress_after_restart["etag"] == progress_before["etag"],
            "common_unchanged_for_hung": hung_common_after["status"] == 304 and hung_common_after["etag"] == hung_common_before["etag"],
            "common_unchanged_for_quynh": quynh_common_after["status"] == 304 and quynh_common_after["etag"] == quynh_common_before["etag"],
            "hung_overlay_304": hung_overlay_after["status"] == 304,
            "quynh_overlay_304": quynh_overlay_after["status"] == 304,
        })
        evidence["ok"] = bool(evidence["progress_restored_revalidated"] and evidence["quynh_restore_ok"] and evidence["common_unchanged_for_hung"] and evidence["common_unchanged_for_quynh"])
    finally:
        stop_server(first)
        stop_server(second)
        evidence["ended_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"ok": evidence.get("ok"), "output": str(OUT), "summary": {
        "progress_restored_revalidated": evidence.get("progress_restored_revalidated"),
        "quynh_restore_ok": evidence.get("quynh_restore_ok"),
        "common_unchanged_for_hung": evidence.get("common_unchanged_for_hung"),
        "common_unchanged_for_quynh": evidence.get("common_unchanged_for_quynh"),
        "auth_session_method": evidence.get("auth_session_method"),
    }}, ensure_ascii=False))
    return 0 if evidence.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
