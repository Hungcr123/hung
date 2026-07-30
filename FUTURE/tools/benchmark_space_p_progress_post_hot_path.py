"""Benchmark shared Space_P/L/S writes across unique, retry, stale, contention, and real state."""

from __future__ import annotations

import concurrent.futures
import copy
import json
import os
import random
import sqlite3
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

import benchmark_space_v_progress_get_hot_path as common


BASE = common.BASE
DATABASE = common.DATABASE
SERVER_DATA = common.SERVER_DATA
USERS = common.USERS
WAL_FILE = Path(str(DATABASE) + "-wal")


def lesson_rows() -> list[tuple[str, str]]:
    rows = []
    patterns = (("*.Space_P", "Space_P"), ("*.Space_L", "Space_L"), ("*.Space_S", "Space_S"))
    for pattern, space in patterns:
        for path in (SERVER_DATA / "common").rglob(pattern):
            try:
                if int(path.stat().st_size) < 128:
                    continue
            except OSError:
                continue
            rows.append((path.relative_to(SERVER_DATA).as_posix(), space))
    if not rows:
        raise RuntimeError("No Space_P/L/S files were found")
    return [rows[index % len(rows)] for index in range(len(USERS))]


def progress_row(username: str, path: str) -> tuple[int, dict]:
    connection = sqlite3.connect(DATABASE)
    try:
        row = connection.execute(
            "SELECT server_revision,record_json FROM lesson_progress "
            "WHERE username=? AND space='Space_P' AND path=? ORDER BY updated_at_utc DESC LIMIT 1",
            (username, path),
        ).fetchone()
    finally:
        connection.close()
    return (int(row[0] or 0), json.loads(row[1])) if row else (0, {})


def hung_rows() -> list[tuple[str, str]]:
    connection = sqlite3.connect(DATABASE)
    try:
        rows = connection.execute(
            "SELECT path,identity FROM lesson_progress WHERE username='hung' AND space='Space_P' ORDER BY updated_at_utc DESC"
        ).fetchall()
    finally:
        connection.close()
    if not rows:
        raise RuntimeError("Real user hung has no paragraph progress rows")
    return [(common.clean(path), common.clean(identity)) for path, identity in rows if common.clean(path)]


def seed_record() -> dict:
    connection = sqlite3.connect(DATABASE)
    try:
        row = connection.execute(
            "SELECT record_json FROM lesson_progress WHERE username='hung' AND space='Space_P' ORDER BY length(record_json) DESC LIMIT 1"
        ).fetchone()
    finally:
        connection.close()
    if not row:
        raise RuntimeError("No paragraph seed record exists")
    return json.loads(row[0])


def snapshot_hung() -> tuple[list[str], list[tuple], list[str], list[tuple]]:
    connection = sqlite3.connect(DATABASE)
    try:
        progress_columns = [row[1] for row in connection.execute("PRAGMA table_info(lesson_progress)")]
        namespace_columns = [row[1] for row in connection.execute("PRAGMA table_info(lesson_progress_namespaces)")]
        progress_rows = connection.execute("SELECT * FROM lesson_progress WHERE username='hung' AND space='Space_P'").fetchall()
        namespace_rows = connection.execute("SELECT * FROM lesson_progress_namespaces WHERE username='hung' AND space='Space_P'").fetchall()
    finally:
        connection.close()
    return progress_columns, progress_rows, namespace_columns, namespace_rows


def restore_hung(snapshot: tuple[list[str], list[tuple], list[str], list[tuple]]) -> None:
    progress_columns, progress_rows, namespace_columns, namespace_rows = snapshot
    connection = sqlite3.connect(DATABASE, timeout=30)
    try:
        connection.execute("BEGIN IMMEDIATE")
        connection.execute("DELETE FROM lesson_progress WHERE username='hung' AND space='Space_P'")
        connection.execute("DELETE FROM lesson_progress_namespaces WHERE username='hung' AND space='Space_P'")
        if namespace_rows:
            connection.executemany(
                f"INSERT INTO lesson_progress_namespaces ({','.join(namespace_columns)}) VALUES ({','.join('?' for _ in namespace_columns)})",
                namespace_rows,
            )
        if progress_rows:
            connection.executemany(
                f"INSERT INTO lesson_progress ({','.join(progress_columns)}) VALUES ({','.join('?' for _ in progress_columns)})",
                progress_rows,
            )
        connection.commit()
    finally:
        connection.close()


def next_test_base_time() -> datetime:
    base = datetime.now(timezone.utc) - timedelta(minutes=15)
    connection = sqlite3.connect(DATABASE)
    try:
        rows = connection.execute(
            "SELECT record_json FROM lesson_progress WHERE username LIKE 'codexload%' AND space='Space_P'"
        ).fetchall()
    finally:
        connection.close()
    for (encoded,) in rows:
        try:
            record = json.loads(encoded)
            raw = str(record.get("savedAt") or record.get("state", {}).get("savedAt") or "").strip()
            parsed = datetime.fromisoformat(raw[:-1] + "+00:00" if raw.upper().endswith("Z") else raw)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            base = max(base, parsed.astimezone(timezone.utc) + timedelta(seconds=1))
        except (TypeError, ValueError, json.JSONDecodeError):
            continue
    return base


def main() -> int:
    password = os.environ.get("FUTURE_TEST_PASSWORD", "")
    if not password:
        raise RuntimeError("Set FUTURE_TEST_PASSWORD for this benchmark only")
    process = common.server_process()
    lessons = lesson_rows()
    template = seed_record()
    hung_snapshot = snapshot_hung()

    def login(username: str) -> str:
        response = requests.post(f"{BASE}/auth/login", json={"username": username, "password": password}, timeout=30)
        response.raise_for_status()
        return common.clean(response.json().get("token"))

    with concurrent.futures.ThreadPoolExecutor(max_workers=25) as pool:
        tokens = dict(zip(USERS, pool.map(login, USERS)))
    hung_token = login("hung")
    base_time = next_test_base_time()
    run_tag = str(time.time_ns())

    def make_payload(index: int, path: str, space: str, identity: str, stamp: datetime, done: int = 0) -> dict:
        record = copy.deepcopy(template)
        saved_at = stamp.isoformat().replace("+00:00", "Z")
        state = record.get("state") if isinstance(record.get("state"), dict) else {}
        total = max(2, int(state.get("totalSegments") or record.get("nodeCount") or 12))
        state.update({
            "savedAt": saved_at,
            "updatedAt": saved_at,
            "runId": f"codex-space-p-post-run-{run_tag}-{index:03d}",
            "activeRun": True,
            "space": space,
            "spaceMode": space.lower(),
            "completedSegments": done,
            "totalSegments": total,
            "syncOperationId": f"codex-space-p-operation-{identity}-{saved_at}",
            "complete": False,
            "lessonComplete": False,
            "completedRuns": 0,
        })
        for key in ("completedAt", "completed_at", "completionRunId", "completion_run_id"):
            state.pop(key, None)
        record.update({
            "action": "autosave",
            "path": path,
            "identity": identity,
            "space": space,
            "title": Path(path).stem,
            "nodeIndex": done,
            "nodeCount": total,
            "savedAt": saved_at,
            "updatedAt": saved_at,
            "runId": state["runId"],
            "activeRun": True,
            "syncOperationId": state["syncOperationId"],
            "complete": False,
            "lessonComplete": False,
            "completedRuns": 0,
            "state": state,
        })
        for key in ("completedAt", "completed_at", "completionRunId", "completion_run_id"):
            record.pop(key, None)
        return record

    def post(token: str, payload: dict) -> tuple:
        started = time.perf_counter()
        response = requests.post(
            f"{BASE}/space-p/progress?client_source=codex_post_benchmark&response=compact-v1",
            headers={"Authorization": f"Bearer {token}"},
            json=payload,
            timeout=45,
        )
        body = response.json() if response.content else {}
        return ((time.perf_counter() - started) * 1000, response.status_code, len(response.content), isinstance(body.get("progress"), dict), body)

    phases = {}
    def add_details(rows: list[tuple], metrics: dict) -> None:
        schemas = [common.clean(row[4].get("response_schema")) for row in rows]
        metrics["response_schemas"] = {schema: schemas.count(schema) for schema in sorted(set(schemas))}

    unique_payloads = [
        make_payload(index, lessons[index][0], lessons[index][1], f"codex-space-p-post-{run_tag}-{index:03d}", base_time + timedelta(seconds=index), index % 5)
        for index in range(100)
    ]
    with concurrent.futures.ThreadPoolExecutor(max_workers=40) as pool:
        unique_rows, phases["unique_100_users_mixed_pls"] = common.measured(
            process, lambda: list(pool.map(lambda index: post(tokens[USERS[index]], unique_payloads[index]), range(100)))
        )
    add_details(unique_rows, phases["unique_100_users_mixed_pls"])
    common.wait_for_writer_quiescence()

    duplicate_path = lessons[0][0]
    duplicate_payload = unique_payloads[0]
    duplicate_before = progress_row(USERS[0], duplicate_path)[0]
    with concurrent.futures.ThreadPoolExecutor(max_workers=40) as pool:
        duplicate_rows, phases["duplicate_retry_same_payload"] = common.measured(
            process, lambda: list(pool.map(lambda _index: post(tokens[USERS[0]], duplicate_payload), range(100)))
        )
    add_details(duplicate_rows, phases["duplicate_retry_same_payload"])
    common.wait_for_writer_quiescence()
    phases["duplicate_retry_same_payload"]["server_revision_delta"] = progress_row(USERS[0], duplicate_path)[0] - duplicate_before

    stale_path, stale_space = lessons[1]
    identity = f"codex-space-p-post-{run_tag}-001"
    newer = make_payload(1, stale_path, stale_space, identity, base_time + timedelta(minutes=10), 4)
    post(tokens[USERS[1]], newer)
    common.wait_for_writer_quiescence()
    time.sleep(0.25)
    stale = make_payload(1, stale_path, stale_space, identity, base_time, 1)
    stale_before = progress_row(USERS[1], stale_path)[0]
    with concurrent.futures.ThreadPoolExecutor(max_workers=40) as pool:
        stale_rows, phases["stale_retry_older_checkpoint"] = common.measured(
            process, lambda: list(pool.map(lambda _index: post(tokens[USERS[1]], stale), range(100)))
        )
    add_details(stale_rows, phases["stale_retry_older_checkpoint"])
    common.wait_for_writer_quiescence()
    stale_after, stale_record = progress_row(USERS[1], stale_path)
    phases["stale_retry_older_checkpoint"]["server_revision_delta"] = stale_after - stale_before
    phases["stale_retry_older_checkpoint"]["newest_completed_segments"] = int(stale_record.get("state", {}).get("completedSegments") or -1)

    contention_path, contention_space = lessons[2]
    contention_identity = f"codex-space-p-post-{run_tag}-002"
    contention_payloads = [
        make_payload(2, contention_path, contention_space, contention_identity, base_time + timedelta(seconds=index), index % 10)
        for index in range(100)
    ]
    random.Random(20260721).shuffle(contention_payloads)
    contention_before = progress_row(USERS[2], contention_path)[0]
    with concurrent.futures.ThreadPoolExecutor(max_workers=40) as pool:
        contention_rows, phases["same_row_contention"] = common.measured(
            process, lambda: list(pool.map(lambda payload: post(tokens[USERS[2]], payload), contention_payloads))
        )
    add_details(contention_rows, phases["same_row_contention"])
    common.wait_for_writer_quiescence()
    contention_after, contention_record = progress_row(USERS[2], contention_path)
    phases["same_row_contention"]["server_revision_delta"] = contention_after - contention_before
    phases["same_row_contention"]["final_saved_at"] = common.clean(contention_record.get("savedAt"))
    phases["same_row_contention"]["expected_saved_at"] = max(common.clean(row.get("savedAt")) for row in contention_payloads)

    hung_path, hung_identity = hung_rows()[0]
    _, hung_record = progress_row("hung", hung_path)
    hung_payload = copy.deepcopy(hung_record)
    hung_payload.update({"action": "autosave", "path": hung_path, "identity": hung_identity})
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=40) as pool:
            hung_result, phases["hung_real_namespace_duplicate"] = common.measured(
                process, lambda: list(pool.map(lambda _index: post(hung_token, hung_payload), range(100)))
            )
        add_details(hung_result, phases["hung_real_namespace_duplicate"])
        common.wait_for_writer_quiescence()
    finally:
        restore_hung(hung_snapshot)

    all_rows = unique_rows + duplicate_rows + stale_rows + contention_rows + hung_result
    if any(row[1] != 200 for row in all_rows):
        raise RuntimeError("One or more paragraph writes failed")
    if any(row[4].get("response_schema") != "space-p-progress-compact-v1" for row in unique_rows + duplicate_rows):
        raise RuntimeError(
            "Accepted/duplicate paragraph writes did not use compact ACKs: "
            f"unique={phases['unique_100_users_mixed_pls'].get('response_schemas')} "
            f"duplicate={phases['duplicate_retry_same_payload'].get('response_schemas')}"
        )
    if phases["duplicate_retry_same_payload"]["postgres_writer"]["tasks"] != 0:
        raise RuntimeError("Duplicate paragraph retry created SQLite writes")
    if phases["stale_retry_older_checkpoint"]["postgres_writer"]["tasks"] != 0:
        raise RuntimeError(f"Stale paragraph retry created SQLite writes: {phases['stale_retry_older_checkpoint']['postgres_writer']}")
    if phases["same_row_contention"]["final_saved_at"] != phases["same_row_contention"]["expected_saved_at"]:
        raise RuntimeError("Same-row paragraph contention lost the newest checkpoint")
    print(json.dumps({"space_p_progress_post_hot_path": phases}, ensure_ascii=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

