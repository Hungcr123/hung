"""Benchmark Space_W progress writes across unique, retry, stale, contention, and real namespaces."""

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
import benchmark_space_w_progress_get_hot_path as space_w_get


BASE = common.BASE
DATABASE = common.DATABASE
USERS = common.USERS
WAL_FILE = Path(str(DATABASE) + "-wal")


def progress_row(username: str, path: str) -> tuple[int, dict]:
    connection = sqlite3.connect(DATABASE)
    try:
        row = connection.execute(
            "SELECT server_revision,record_json FROM lesson_progress WHERE username=? AND space='Space_W' AND path=? ORDER BY updated_at_utc DESC LIMIT 1",
            (username, path),
        ).fetchone()
    finally:
        connection.close()
    return (int(row[0] or 0), json.loads(row[1])) if row else (0, {})


def snapshot_hung() -> tuple[list[str], list[tuple], list[str], list[tuple]]:
    connection = sqlite3.connect(DATABASE)
    try:
        progress_columns = [row[1] for row in connection.execute("PRAGMA table_info(lesson_progress)")]
        namespace_columns = [row[1] for row in connection.execute("PRAGMA table_info(lesson_progress_namespaces)")]
        progress_rows = connection.execute(
            "SELECT * FROM lesson_progress WHERE username='hung' AND space='Space_W'"
        ).fetchall()
        namespace_rows = connection.execute(
            "SELECT * FROM lesson_progress_namespaces WHERE username='hung' AND space='Space_W'"
        ).fetchall()
    finally:
        connection.close()
    return progress_columns, progress_rows, namespace_columns, namespace_rows


def restore_hung(snapshot: tuple[list[str], list[tuple], list[str], list[tuple]]) -> None:
    progress_columns, progress_rows, namespace_columns, namespace_rows = snapshot
    connection = sqlite3.connect(DATABASE, timeout=30)
    try:
        connection.execute("BEGIN IMMEDIATE")
        connection.execute("DELETE FROM lesson_progress WHERE username='hung' AND space='Space_W'")
        connection.execute("DELETE FROM lesson_progress_namespaces WHERE username='hung' AND space='Space_W'")
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


def main() -> int:
    password = os.environ.get("FUTURE_TEST_PASSWORD", "")
    if not password:
        raise RuntimeError("Set FUTURE_TEST_PASSWORD for this benchmark only")
    process = common.server_process()
    paths = space_w_get.lesson_paths()
    template = space_w_get.seed_record()
    hung_snapshot = snapshot_hung()

    def login(username: str) -> str:
        response = requests.post(f"{BASE}/auth/login", json={"username": username, "password": password}, timeout=30)
        response.raise_for_status()
        return common.clean(response.json().get("token"))

    with concurrent.futures.ThreadPoolExecutor(max_workers=25) as pool:
        tokens = dict(zip(USERS, pool.map(login, USERS)))
    hung_token = login("hung")
    base_time = datetime.now(timezone.utc) - timedelta(minutes=15)

    def make_payload(index: int, path: str, identity: str, stamp: datetime, done: int = 0) -> dict:
        record = copy.deepcopy(template)
        saved_at = stamp.isoformat().replace("+00:00", "Z")
        total = max(2, int(record.get("progressTotal") or 10))
        state = record.get("state") if isinstance(record.get("state"), dict) else {}
        state.update({
            "savedAt": saved_at,
            "updatedAt": saved_at,
            "runId": f"codex-space-w-post-run-{index:03d}",
            "activeRun": True,
            "progressDone": done,
            "progressTotal": total,
            "trainEnabled": bool(index % 2),
            "syncOperationId": f"codex-space-w-operation-{identity}-{saved_at}",
        })
        record.update({
            "action": "autosave",
            "path": path,
            "identity": identity,
            "title": Path(path).stem,
            "savedAt": saved_at,
            "updatedAt": saved_at,
            "runId": state["runId"],
            "activeRun": True,
            "progressDone": done,
            "progressTotal": total,
            "syncOperationId": state["syncOperationId"],
            "state": state,
        })
        return record

    def post(token: str, payload: dict) -> tuple:
        started = time.perf_counter()
        response = requests.post(
            f"{BASE}/space-w/progress?client_source=codex_post_benchmark&response=compact-v1",
            headers={"Authorization": f"Bearer {token}"},
            json=payload,
            timeout=45,
        )
        body = response.json() if response.content else {}
        return (
            (time.perf_counter() - started) * 1000,
            response.status_code,
            len(response.content),
            isinstance(body.get("progress"), dict),
            body,
        )

    phases = {}
    def record_schemas(rows: list[tuple], metrics: dict) -> None:
        schemas = [common.clean(row[4].get("response_schema")) for row in rows]
        metrics["response_schemas"] = {schema: schemas.count(schema) for schema in sorted(set(schemas))}

    unique_payloads = [
        make_payload(index, paths[index], f"codex-space-w-post-{index:03d}", base_time + timedelta(seconds=index), index % 5)
        for index in range(100)
    ]
    wal_before = WAL_FILE.stat().st_size if WAL_FILE.exists() else 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=40) as pool:
        unique_rows, phases["unique_100_users"] = common.measured(
            process,
            lambda: list(pool.map(lambda index: post(tokens[USERS[index]], unique_payloads[index]), range(100))),
        )
    record_schemas(unique_rows, phases["unique_100_users"])
    common.wait_for_writer_quiescence()
    time.sleep(1.0)
    phases["unique_100_users"]["sqlite_wal_growth"] = (WAL_FILE.stat().st_size if WAL_FILE.exists() else 0) - wal_before

    duplicate_path = paths[0]
    duplicate_payload = unique_payloads[0]
    duplicate_before = progress_row(USERS[0], duplicate_path)[0]
    wal_before = WAL_FILE.stat().st_size if WAL_FILE.exists() else 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=40) as pool:
        duplicate_rows, phases["duplicate_retry_same_payload"] = common.measured(
            process,
            lambda: list(pool.map(lambda _index: post(tokens[USERS[0]], duplicate_payload), range(100))),
        )
    record_schemas(duplicate_rows, phases["duplicate_retry_same_payload"])
    common.wait_for_writer_quiescence()
    time.sleep(1.0)
    duplicate_after = progress_row(USERS[0], duplicate_path)[0]
    phases["duplicate_retry_same_payload"]["server_revision_delta"] = duplicate_after - duplicate_before
    phases["duplicate_retry_same_payload"]["sqlite_wal_growth"] = (WAL_FILE.stat().st_size if WAL_FILE.exists() else 0) - wal_before

    stale_path = paths[1]
    newer = make_payload(1, stale_path, "codex-space-w-post-001", base_time + timedelta(minutes=10), 4)
    post(tokens[USERS[1]], newer)
    stale = make_payload(1, stale_path, "codex-space-w-post-001", base_time, 1)
    stale_before = progress_row(USERS[1], stale_path)[0]
    with concurrent.futures.ThreadPoolExecutor(max_workers=40) as pool:
        stale_rows, phases["stale_retry_older_checkpoint"] = common.measured(
            process,
            lambda: list(pool.map(lambda _index: post(tokens[USERS[1]], stale), range(100))),
        )
    record_schemas(stale_rows, phases["stale_retry_older_checkpoint"])
    common.wait_for_writer_quiescence()
    stale_after, stale_record = progress_row(USERS[1], stale_path)
    phases["stale_retry_older_checkpoint"]["server_revision_delta"] = stale_after - stale_before
    phases["stale_retry_older_checkpoint"]["newest_progress_done"] = int(stale_record.get("progressDone") or stale_record.get("state", {}).get("progressDone") or -1)

    contention_path = paths[2]
    contention_payloads = [
        make_payload(2, contention_path, "codex-space-w-post-002", base_time + timedelta(seconds=index), index % 10)
        for index in range(100)
    ]
    random.Random(20260721).shuffle(contention_payloads)
    contention_before = progress_row(USERS[2], contention_path)[0]
    with concurrent.futures.ThreadPoolExecutor(max_workers=40) as pool:
        contention_rows, phases["same_row_contention"] = common.measured(
            process,
            lambda: list(pool.map(lambda payload: post(tokens[USERS[2]], payload), contention_payloads)),
        )
    record_schemas(contention_rows, phases["same_row_contention"])
    common.wait_for_writer_quiescence()
    contention_after, contention_record = progress_row(USERS[2], contention_path)
    phases["same_row_contention"]["server_revision_delta"] = contention_after - contention_before
    phases["same_row_contention"]["final_saved_at"] = common.clean(contention_record.get("savedAt"))
    phases["same_row_contention"]["expected_saved_at"] = max(common.clean(row.get("savedAt")) for row in contention_payloads)

    hung_path, hung_identity = space_w_get.hung_rows()[0]
    _, hung_record = progress_row("hung", hung_path)
    hung_payload = copy.deepcopy(hung_record)
    hung_payload.update({"action": "autosave", "path": hung_path, "identity": hung_identity})
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=40) as pool:
            hung_rows, phases["hung_real_namespace_duplicate"] = common.measured(
                process,
                lambda: list(pool.map(lambda _index: post(hung_token, hung_payload), range(100))),
            )
        record_schemas(hung_rows, phases["hung_real_namespace_duplicate"])
        common.wait_for_writer_quiescence()
    finally:
        restore_hung(hung_snapshot)

    if any(row[4].get("response_schema") != "space-w-progress-compact-v1" for row in unique_rows + duplicate_rows):
        raise RuntimeError("Accepted/duplicate Space_W writes did not use compact ACKs")
    if phases["duplicate_retry_same_payload"]["postgres_writer"]["tasks"] != 0:
        raise RuntimeError("Duplicate Space_W retry created SQLite writes")
    if phases["stale_retry_older_checkpoint"]["postgres_writer"]["tasks"] != 0:
        raise RuntimeError("Stale Space_W retry created SQLite writes")
    if phases["same_row_contention"]["final_saved_at"] != phases["same_row_contention"]["expected_saved_at"]:
        raise RuntimeError("Same-row contention lost the newest Space_W checkpoint")
    print(json.dumps({"space_w_progress_post_hot_path": phases}, ensure_ascii=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

