"""Benchmark Space_V writes across unique users, retries, stale packets, contention, and real state."""

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
USERS = common.USERS


def progress_row(username: str, path: str) -> tuple[int, dict]:
    connection = sqlite3.connect(DATABASE)
    try:
        row = connection.execute(
            "SELECT server_revision,record_json FROM lesson_progress "
            "WHERE username=? AND space='Space_V' AND path=? ORDER BY updated_at_utc DESC LIMIT 1",
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
        progress_rows = connection.execute("SELECT * FROM lesson_progress WHERE username='hung' AND space='Space_V'").fetchall()
        namespace_rows = connection.execute("SELECT * FROM lesson_progress_namespaces WHERE username='hung' AND space='Space_V'").fetchall()
    finally:
        connection.close()
    return progress_columns, progress_rows, namespace_columns, namespace_rows


def restore_hung(snapshot: tuple[list[str], list[tuple], list[str], list[tuple]]) -> None:
    progress_columns, progress_rows, namespace_columns, namespace_rows = snapshot
    connection = sqlite3.connect(DATABASE, timeout=30)
    try:
        connection.execute("BEGIN IMMEDIATE")
        connection.execute("DELETE FROM lesson_progress WHERE username='hung' AND space='Space_V'")
        connection.execute("DELETE FROM lesson_progress_namespaces WHERE username='hung' AND space='Space_V'")
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
            "SELECT record_json FROM lesson_progress WHERE username LIKE 'codexload%' AND space='Space_V'"
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
    paths = common.lesson_paths()
    template = common.seed_record()
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

    def make_payload(index: int, path: str, identity: str, stamp: datetime, learned: int = 0, action: str = "autosave") -> dict:
        record = copy.deepcopy(template)
        saved_at = stamp.isoformat().replace("+00:00", "Z")
        total = max(10, int(record.get("nodeCount") or record.get("state", {}).get("nodeCount") or 25))
        learned_keys = [f"codex-word-{item:03d}" for item in range(max(0, learned))]
        state = record.get("state") if isinstance(record.get("state"), dict) else {}
        state.update({
            "savedAt": saved_at,
            "updatedAt": saved_at,
            "runId": f"codex-space-v-post-run-{run_tag}-{index:03d}",
            "activeRun": True,
            "learned": learned_keys,
            "learnedCount": len(learned_keys),
            "nodeCount": total,
            "syncOperationId": f"codex-space-v-operation-{identity}-{saved_at}-{action}",
            "complete": False,
            "registryReady": False,
            "vocabComplete": False,
            "lessonComplete": False,
            "lessonCompletionSent": False,
        })
        record.update({
            "action": action,
            "path": path,
            "identity": identity,
            "title": Path(path).stem,
            "nodeIndex": min(len(learned_keys), total),
            "nodeCount": total,
            "learnedCount": len(learned_keys),
            "savedAt": saved_at,
            "updatedAt": saved_at,
            "runId": state["runId"],
            "activeRun": True,
            "syncOperationId": state["syncOperationId"],
            "complete": False,
            "state": state,
        })
        for key in ("completedAt", "completed_at", "completionRunId", "completion_run_id"):
            record.pop(key, None)
            state.pop(key, None)
        return record

    def post(token: str, payload: dict) -> tuple:
        started = time.perf_counter()
        response = requests.post(
            f"{BASE}/space-v/progress?client_source=codex_post_benchmark&response=compact-v1",
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
        make_payload(index, paths[index], f"codex-space-v-post-{run_tag}-{index:03d}", base_time + timedelta(seconds=index), index % 5)
        for index in range(100)
    ]
    with concurrent.futures.ThreadPoolExecutor(max_workers=40) as pool:
        unique_rows, phases["unique_100_users"] = common.measured(
            process, lambda: list(pool.map(lambda index: post(tokens[USERS[index]], unique_payloads[index]), range(100)))
        )
    add_details(unique_rows, phases["unique_100_users"])
    common.wait_for_writer_quiescence()

    duplicate_path = paths[0]
    duplicate_payload = unique_payloads[0]
    duplicate_before = progress_row(USERS[0], duplicate_path)[0]
    with concurrent.futures.ThreadPoolExecutor(max_workers=40) as pool:
        duplicate_rows, phases["duplicate_retry_same_payload"] = common.measured(
            process, lambda: list(pool.map(lambda _index: post(tokens[USERS[0]], duplicate_payload), range(100)))
        )
    add_details(duplicate_rows, phases["duplicate_retry_same_payload"])
    common.wait_for_writer_quiescence()
    phases["duplicate_retry_same_payload"]["server_revision_delta"] = progress_row(USERS[0], duplicate_path)[0] - duplicate_before

    stale_path = paths[1]
    identity = f"codex-space-v-post-{run_tag}-001"
    newer = make_payload(1, stale_path, identity, base_time + timedelta(minutes=10), 4)
    post(tokens[USERS[1]], newer)
    common.wait_for_writer_quiescence()
    time.sleep(0.25)
    stale = make_payload(1, stale_path, identity, base_time, 1)
    stale_before = progress_row(USERS[1], stale_path)[0]
    with concurrent.futures.ThreadPoolExecutor(max_workers=40) as pool:
        stale_rows, phases["stale_retry_older_checkpoint"] = common.measured(
            process, lambda: list(pool.map(lambda _index: post(tokens[USERS[1]], stale), range(100)))
        )
    add_details(stale_rows, phases["stale_retry_older_checkpoint"])
    common.wait_for_writer_quiescence()
    stale_after, stale_record = progress_row(USERS[1], stale_path)
    phases["stale_retry_older_checkpoint"]["server_revision_delta"] = stale_after - stale_before
    phases["stale_retry_older_checkpoint"]["newest_learned_count"] = int(stale_record.get("learnedCount") or stale_record.get("state", {}).get("learnedCount") or -1)

    contention_path = paths[2]
    contention_identity = f"codex-space-v-post-{run_tag}-002"
    contention_payloads = [
        make_payload(2, contention_path, contention_identity, base_time + timedelta(seconds=index), index % 10)
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

    hung_path, hung_identity = common.hung_rows()[0]
    _, hung_record = progress_row("hung", hung_path)
    hung_payload = copy.deepcopy(hung_record)
    hung_payload.update({"action": "autosave", "path": hung_path, "identity": hung_identity})
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=40) as pool:
            hung_rows, phases["hung_real_namespace_duplicate"] = common.measured(
                process, lambda: list(pool.map(lambda _index: post(hung_token, hung_payload), range(100)))
            )
        add_details(hung_rows, phases["hung_real_namespace_duplicate"])
        common.wait_for_writer_quiescence()
    finally:
        restore_hung(hung_snapshot)

    all_rows = unique_rows + duplicate_rows + stale_rows + contention_rows + hung_rows
    if any(row[1] != 200 for row in all_rows):
        raise RuntimeError("One or more Space_V writes failed")
    if any(row[4].get("response_schema") != "space-v-progress-compact-v1" for row in unique_rows + duplicate_rows):
        raise RuntimeError("Accepted/duplicate Space_V writes did not use compact ACKs")
    if phases["duplicate_retry_same_payload"]["postgres_writer"]["tasks"] != 0 or phases["duplicate_retry_same_payload"]["server_revision_delta"] != 0:
        raise RuntimeError("Duplicate Space_V retry created durable writes")
    if phases["stale_retry_older_checkpoint"]["postgres_writer"]["tasks"] != 0 or phases["stale_retry_older_checkpoint"]["server_revision_delta"] != 0:
        raise RuntimeError(
            "Stale Space_V retry created durable writes: "
            f"writer={phases['stale_retry_older_checkpoint']['postgres_writer']} "
            f"revision_delta={phases['stale_retry_older_checkpoint']['server_revision_delta']}"
        )
    if phases["same_row_contention"]["final_saved_at"] != phases["same_row_contention"]["expected_saved_at"]:
        raise RuntimeError("Same-row Space_V contention lost the newest checkpoint")
    print(json.dumps({"space_v_progress_post_hot_path": phases}, ensure_ascii=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

