"""Focused lesson_time delta probe.

Added 2026-07-27 for the checkpoint audit. It performs one lease-backed
heartbeat on Quynh, verifies that the shared common tree ETag stays stable
for Hưng and Quynh, then restores Quynh's lesson_time rows exactly.
"""

from __future__ import annotations

import json
import os
import sqlite3
import time
import uuid
from pathlib import Path

import requests

BASE = "http://127.0.0.1:8877"
DATABASE = Path(r"C:\server data\server2.db")


def login(username: str, password: str) -> requests.Session:
    session = requests.Session()
    response = session.post(f"{BASE}/auth/login", json={"username": username, "password": password}, timeout=30)
    response.raise_for_status()
    token = str(response.json().get("token") or "").strip()
    if not token:
        raise RuntimeError(f"Login returned no token for {username}")
    session.headers.update({"Authorization": f"Bearer {token}"})
    return session


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


def lesson_row(username: str) -> tuple[list[str], list[tuple], list[str], list[tuple]]:
    connection = sqlite3.connect(DATABASE)
    try:
        columns = [item[1] for item in connection.execute("PRAGMA table_info(lesson_time)").fetchall()]
        rows = connection.execute("SELECT * FROM lesson_time WHERE lower(username)=?", (username.lower(),)).fetchall()
        credit_columns = [item[1] for item in connection.execute("PRAGMA table_info(lesson_time_credit_state)").fetchall()]
        credit_rows = connection.execute("SELECT * FROM lesson_time_credit_state WHERE lower(username)=?", (username.lower(),)).fetchall() if credit_columns else []
    finally:
        connection.close()
    if not rows:
        raise RuntimeError(f"No lesson_time rows exist for {username}")
    return columns, rows, credit_columns, credit_rows


def restore_lesson_row(username: str, snapshot: tuple[list[str], list[tuple], list[str], list[tuple]]) -> None:
    columns, rows, credit_columns, credit_rows = snapshot
    connection = sqlite3.connect(DATABASE, timeout=30)
    try:
        connection.execute("BEGIN IMMEDIATE")
        connection.execute("DELETE FROM lesson_time WHERE lower(username)=?", (username.lower(),))
        if credit_columns:
            connection.execute("DELETE FROM lesson_time_credit_state WHERE lower(username)=?", (username.lower(),))
        if rows:
            placeholders = ",".join("?" for _ in columns)
            connection.executemany(f"INSERT INTO lesson_time ({','.join(columns)}) VALUES ({placeholders})", rows)
        if credit_columns and credit_rows:
            placeholders = ",".join("?" for _ in credit_columns)
            connection.executemany(f"INSERT INTO lesson_time_credit_state ({','.join(credit_columns)}) VALUES ({placeholders})", credit_rows)
        connection.commit()
    finally:
        connection.close()


def lesson_file() -> dict:
    connection = sqlite3.connect(DATABASE)
    try:
        row = connection.execute(
            """
            SELECT a.normalized_path, a.file_id
            FROM lesson_file_aliases a
            JOIN lesson_files f ON f.file_id=a.file_id
            WHERE a.active=1 AND f.status='active'
              AND lower(a.normalized_path) LIKE 'common/%'
              AND lower(a.normalized_path) LIKE '%.space_v'
            ORDER BY a.normalized_path
            LIMIT 1
            """
        ).fetchone()
    finally:
        connection.close()
    if not row:
        raise RuntimeError("No active common Space_V lesson found")
    return {"path": str(row[0]), "lesson_id": str(row[1])}


def main() -> int:
    hung_password = os.environ.get("FUTURE_HUNG_PASSWORD", "")
    quynh_password = os.environ.get("FUTURE_QUYNH_PASSWORD", "")
    if not hung_password or not quynh_password:
        raise RuntimeError("Set FUTURE_HUNG_PASSWORD and FUTURE_QUYNH_PASSWORD")

    hung = login("hung", hung_password)
    quynh = login("quynh", quynh_password)

    lesson = lesson_file()
    time_snapshot = lesson_row("quynh")
    common_hung_before = common_tree(hung)
    common_quynh_before = common_tree(quynh)

    path = lesson["path"]
    session_id = f"codex-lesson-time-{uuid.uuid4().hex}"
    start = quynh.post(
        f"{BASE}/lesson/time",
        json={
            "path": path,
            "lesson_id": lesson["lesson_id"],
            "space": "Space_V",
            "protocol": "server-time-v1",
            "session_id": session_id,
            "seconds": 0,
            "sequence": 0,
        },
        timeout=30,
    )
    start.raise_for_status()
    start_body = start.json().get("time", {})
    lease = str(start_body.get("offlineLease") or "")
    if not lease:
        raise RuntimeError("Lesson time session start did not return an offline lease")

    time.sleep(1.15)
    write_started = time.perf_counter()
    write = quynh.post(
        f"{BASE}/lesson/time",
        json={
            "path": path,
            "lesson_id": lesson["lesson_id"],
            "space": "Space_V",
            "protocol": "server-time-v1",
            "session_id": session_id,
            "seconds": 1,
            "sequence": 1,
            "offline_lease": lease,
        },
        timeout=30,
    )
    write_ms = (time.perf_counter() - write_started) * 1000
    write.raise_for_status()
    write_body = write.json().get("time", {})

    common_hung_after = common_tree(hung, common_hung_before["etag"])
    common_quynh_after = common_tree(quynh, common_quynh_before["etag"])
    time_after = lesson_row("quynh")
    restore_lesson_row("quynh", time_snapshot)
    time_restored = lesson_row("quynh")

    raw = {
        "lesson": lesson,
        "start_reason": str(start_body.get("heartbeatReason") or ""),
        "write_reason": str(write_body.get("heartbeatReason") or ""),
        "write_accepted_seconds": int(write_body.get("acceptedSeconds", 0) or 0),
        "write_status": write.status_code,
        "write_ms": round(write_ms, 3),
        "common_unchanged_for_hung": common_hung_before["etag"] == common_hung_after["etag"] and common_hung_after["status"] == 304,
        "common_unchanged_for_quynh": common_quynh_before["etag"] == common_quynh_after["etag"] and common_quynh_after["status"] == 304,
        "lesson_time_rows_changed": time_after[1] != time_snapshot[1] or time_after[3] != time_snapshot[3],
        "lesson_time_restored": time_restored[1] == time_snapshot[1] and time_restored[3] == time_snapshot[3],
    }

    out = Path(r"C:\Users\Admin\.codex\plans\server2_postgres_full_audit\checkpoint_005_lesson_time_delta_isolation_raw.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "ok": True,
        "output": str(out),
        "write_reason": raw["write_reason"],
        "write_accepted_seconds": raw["write_accepted_seconds"],
        "common_unchanged_for_hung": raw["common_unchanged_for_hung"],
        "common_unchanged_for_quynh": raw["common_unchanged_for_quynh"],
        "lesson_time_rows_changed": raw["lesson_time_rows_changed"],
        "lesson_time_restored": raw["lesson_time_restored"],
        "write_ms": raw["write_ms"],
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
