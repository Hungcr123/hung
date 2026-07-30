"""Focused Space_V delta probe.

Added 2026-07-27 for the common/overlay checkpoint. It performs one durable
Space_V write on Quynh, verifies that the shared common tree ETag stays stable
for Hưng and Quynh, then restores Quynh's row to the prior semantic state.
"""

from __future__ import annotations

import json
import os
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

from benchmark_space_v_progress_get_hot_path import BASE, DATABASE, clean, lesson_paths


def login(username: str, password: str) -> requests.Session:
    session = requests.Session()
    response = session.post(f"{BASE}/auth/login", json={"username": username, "password": password}, timeout=30)
    response.raise_for_status()
    token = str(response.json().get("token") or "").strip()
    if not token:
        raise RuntimeError(f"Login returned no token for {username}")
    session.headers.update({"Authorization": f"Bearer {token}"})
    return session


def read_space_v_row(username: str) -> tuple[int, dict]:
    connection = sqlite3.connect(DATABASE)
    try:
        row = connection.execute(
            "SELECT server_revision,record_json FROM lesson_progress "
            "WHERE username=? AND space='Space_V' ORDER BY updated_at_utc DESC LIMIT 1",
            (username,),
        ).fetchone()
    finally:
        connection.close()
    if not row:
        raise RuntimeError(f"No {username} Space_V row exists")
    return int(row[0] or 0), json.loads(row[1])


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


def progress_read(session: requests.Session, path: str, identity: str, etag: str = "") -> dict:
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
        "progress": payload.get("progress") if isinstance(payload.get("progress"), dict) else {},
        "summary": payload.get("summary") if isinstance(payload.get("summary"), dict) else {},
    }


def make_payload(base_record: dict, path: str, identity: str, learned_count: int, action: str, suffix: str) -> dict:
    stamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    record = json.loads(json.dumps(base_record))
    total = max(1, int(record.get("nodeCount") or record.get("state", {}).get("nodeCount") or 1))
    record.update({
        "action": action,
        "path": path,
        "identity": identity,
        "title": Path(path).stem,
        "runId": f"codex-delta-isolation-{time.time_ns()}",
        "activeRun": True,
        "savedAt": stamp,
        "updatedAt": stamp,
        "nodeIndex": min(learned_count, total),
        "nodeCount": total,
        "learnedCount": learned_count,
        "syncOperationId": f"codex-delta-op-{suffix}-{time.time_ns()}",
        "complete": False,
    })
    state = record.get("state") if isinstance(record.get("state"), dict) else {}
    state.update({
        "savedAt": stamp,
        "updatedAt": stamp,
        "runId": record["runId"],
        "activeRun": True,
        "learnedCount": learned_count,
        "syncOperationId": record["syncOperationId"],
        "complete": False,
        "vocabComplete": False,
        "lessonComplete": False,
        "lessonCompletionSent": False,
    })
    record["state"] = state
    return record


def main() -> int:
    hung_password = os.environ.get("FUTURE_HUNG_PASSWORD", "")
    quynh_password = os.environ.get("FUTURE_QUYNH_PASSWORD", "")
    if not hung_password or not quynh_password:
        raise RuntimeError("Set FUTURE_HUNG_PASSWORD and FUTURE_QUYNH_PASSWORD for this probe only")

    hung = login("hung", hung_password)
    quynh = login("quynh", quynh_password)

    hung_common_before = common_tree(hung)
    quynh_common_before = common_tree(quynh)
    hung_overlay_before = user_overlay(hung)
    quynh_overlay_before = user_overlay(quynh)
    quynh_rev_before, quynh_record_before = read_space_v_row("quynh")

    path = clean(quynh_record_before.get("path") or lesson_paths()[0])
    quynh_path = path
    quynh_identity = clean(quynh_record_before.get("identity") or quynh_record_before.get("lesson_id") or "quynh-restore")
    progress_before = progress_read(quynh, quynh_path, quynh_identity)
    current_progress = progress_before.get("progress") if isinstance(progress_before.get("progress"), dict) else quynh_record_before
    base_learned = int(current_progress.get("learnedCount") or current_progress.get("state", {}).get("learnedCount") or 0)
    write_payload = make_payload(current_progress, path, "quynh-delta-isolation-001", base_learned, "new_run", "write")
    write_payload["state"]["forceNewRun"] = True
    write_started = time.perf_counter()
    write_response = quynh.post(
        f"{BASE}/space-v/progress?client_source=codex_delta_isolation&response=compact-v1",
        json=write_payload,
        timeout=45,
    )
    write_ms = (time.perf_counter() - write_started) * 1000
    write_response.raise_for_status()
    write_body = write_response.json()
    progress_after_write = progress_read(quynh, quynh_path, quynh_identity, progress_before["etag"])
    quynh_rev_after, quynh_record_after = read_space_v_row("quynh")

    hung_common_after = common_tree(hung, hung_common_before["etag"])
    quynh_common_after = common_tree(quynh, quynh_common_before["etag"])
    hung_overlay_after = user_overlay(hung, hung_overlay_before["etag"])
    quynh_overlay_after = user_overlay(quynh, quynh_overlay_before["etag"])

    restore_payload = make_payload(
        current_progress,
        str(quynh_record_before.get("path") or path),
        clean(quynh_record_before.get("identity") or quynh_record_before.get("lesson_id") or "quynh-restore"),
        base_learned,
        "autosave",
        "restore",
    )
    restore_payload["savedAt"] = clean(quynh_record_before.get("savedAt") or quynh_record_before.get("state", {}).get("savedAt") or restore_payload["savedAt"])
    restore_payload["updatedAt"] = restore_payload["savedAt"]
    restore_payload["state"]["savedAt"] = restore_payload["savedAt"]
    restore_payload["state"]["updatedAt"] = restore_payload["updatedAt"]
    restore_response = quynh.post(
        f"{BASE}/space-v/progress?client_source=codex_delta_restore&response=compact-v1",
        json=restore_payload,
        timeout=45,
    )
    restore_response.raise_for_status()
    restore_body = restore_response.json()
    progress_after_restore = progress_read(quynh, quynh_path, quynh_identity, progress_after_write["etag"])
    quynh_rev_restore, quynh_record_restore = read_space_v_row("quynh")

    raw = {
        "write_ms": round(write_ms, 3),
        "write_status": write_response.status_code,
        "write_response_schema": clean(write_body.get("response_schema")),
        "restore_status": restore_response.status_code,
        "restore_response_schema": clean(restore_body.get("response_schema")),
        "progress_before": progress_before,
        "progress_after_write": progress_after_write,
        "progress_after_restore": progress_after_restore,
        "quynh_revision_delta": quynh_rev_after - quynh_rev_before,
        "quynh_restore_delta": quynh_rev_restore - quynh_rev_after,
        "restored_semantics": clean(quynh_record_restore.get("path")) == clean(quynh_record_before.get("path"))
        and clean(quynh_record_restore.get("identity")) == clean(quynh_record_before.get("identity")),
        "common_unchanged_for_hung": hung_common_before["etag"] == hung_common_after["etag"] and hung_common_after["status"] == 304,
        "common_unchanged_for_quynh": quynh_common_before["etag"] == quynh_common_after["etag"] and quynh_common_after["status"] == 304,
        "hung_overlay_304": hung_overlay_after["status"] == 304,
        "quynh_overlay_304": quynh_overlay_after["status"] == 304,
        "progress_changed_on_write": progress_before["etag"] != progress_after_write["etag"] and progress_after_write["status"] == 200,
        "progress_restored": progress_after_restore["etag"] != progress_after_write["etag"],
    }

    out = Path(r"C:\Users\Admin\.codex\plans\server2_postgres_full_audit\checkpoint_004_space_v_delta_isolation_raw.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "ok": True,
        "output": str(out),
        "write_response_schema": raw["write_response_schema"],
        "restore_response_schema": raw["restore_response_schema"],
        "quynh_revision_delta": raw["quynh_revision_delta"],
        "quynh_restore_delta": raw["quynh_restore_delta"],
        "progress_changed_on_write": raw["progress_changed_on_write"],
        "progress_restored": raw["progress_restored"],
        "common_unchanged_for_hung": raw["common_unchanged_for_hung"],
        "common_unchanged_for_quynh": raw["common_unchanged_for_quynh"],
        "hung_overlay_304": raw["hung_overlay_304"],
        "quynh_overlay_304": raw["quynh_overlay_304"],
        "restored_semantics": raw["restored_semantics"],
        "write_ms": raw["write_ms"],
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
