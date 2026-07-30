"""Benchmark 100 isolated preference updates and exact retries."""

from __future__ import annotations

import concurrent.futures
import hashlib
import json
import os
import sqlite3
import time

import requests

from benchmark_server2_100_users import BASE, DATABASE, USERS, measured, response_sizes, server_process, wait_for_writer_quiescence


USER_ROOT = r"C:\QMLearn\users"


def provision_legacy_documents() -> None:
    now = time.time_ns()
    connection = sqlite3.connect(DATABASE)
    try:
        connection.execute("BEGIN IMMEDIATE")
        for index, username in enumerate(USERS):
            path = os.path.normpath(os.path.abspath(os.path.join(USER_ROOT, f"{username}.txt")))
            path_key = os.path.normcase(path)
            raw = f"load-test-{index:03d}\n".encode("utf-8")
            connection.execute(
                "INSERT INTO documents(path_key,path,content,encoding,sha256,file_size,file_mtime_ns,updated_at_utc) "
                "VALUES(?,?,?,?,?,?,?,?) ON CONFLICT(path_key) DO UPDATE SET content=excluded.content,sha256=excluded.sha256,"
                "file_size=excluded.file_size,file_mtime_ns=excluded.file_mtime_ns,updated_at_utc=excluded.updated_at_utc",
                (path_key, path, raw, "utf-8", hashlib.sha256(raw).hexdigest(), len(raw), now + index, "2026-07-20T12:57:00Z"),
            )
        connection.commit()
    finally:
        connection.close()


def preference_state() -> dict:
    connection = sqlite3.connect(DATABASE)
    try:
        table = connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='user_preferences'"
        ).fetchone()
        if table:
            rows = connection.execute(
                "SELECT username,preferences_json,server_revision FROM user_preferences WHERE lower(username) LIKE 'codexload%' ORDER BY username"
            ).fetchall()
            raw = json.dumps(rows, ensure_ascii=True, separators=(",", ":")).encode("utf-8")
            return {
                "authority": "user_preferences",
                "rows": len(rows),
                "bytes": sum(len(str(row[1]).encode("utf-8")) for row in rows),
                "revision_sum": sum(int(row[2] or 0) for row in rows),
                "sha256": hashlib.sha256(raw).hexdigest(),
            }
        rows = connection.execute(
            "SELECT path,content,file_size FROM documents WHERE lower(path) LIKE ? ORDER BY path",
            (r"%\codexload%.txt",),
        ).fetchall()
        raw = json.dumps([(row[0], bytes(row[1]).decode("utf-8")) for row in rows], ensure_ascii=True, separators=(",", ":")).encode("utf-8")
        return {
            "authority": "documents",
            "rows": len(rows),
            "bytes": sum(int(row[2] or 0) for row in rows),
            "revision_sum": 0,
            "sha256": hashlib.sha256(raw).hexdigest(),
        }
    finally:
        connection.close()


def main() -> int:
    password = os.environ.get("FUTURE_TEST_PASSWORD", "")
    if not password:
        raise RuntimeError("Set FUTURE_TEST_PASSWORD for this benchmark only")
    if os.environ.get("PREFERENCES_BENCHMARK_LEGACY_DOCS") == "1":
        provision_legacy_documents()
    process = server_process()

    def login(username: str) -> str:
        response = requests.post(f"{BASE}/auth/login", json={"username": username, "password": password}, timeout=30)
        response.raise_for_status()
        payload = response.json()
        if payload.get("server_data", {}).get("load_test") is not True:
            raise RuntimeError(f"Load-test isolation missing for {username}")
        return str(payload.get("token") or "")

    with concurrent.futures.ThreadPoolExecutor(max_workers=25) as pool:
        tokens = dict(zip(USERS, pool.map(login, USERS)))
    variant = int(os.environ.get("PREFERENCES_BENCHMARK_VARIANT", "0") or 0)
    payloads = {
        username: {
            "chat_voice": {"enabled": bool((index + variant) % 2), "voice": "male-us", "label": f"Male US {index:03d}"},
            "question_animation": {"paused": bool((index + variant) % 3 == 0)},
            "pdf_settings": {"ui": {"voice": f"voice-{(index + variant) % 7}", "penActive": bool((index + variant) % 4 == 0)}},
        }
        for index, username in enumerate(USERS, 1)
    }

    def update(index: int):
        username = USERS[index]
        body = json.dumps(payloads[username], ensure_ascii=False, separators=(",", ":"))
        started = time.perf_counter()
        response = requests.post(
            f"{BASE}/auth/preferences",
            headers={
                "Authorization": f"Bearer {tokens[username]}",
                "Content-Type": "application/json",
                "X-Future-Response-Mode": "preferences-compact-v1",
            },
            data=body.encode("utf-8"),
            timeout=30,
        )
        decoded, wire, request_bytes = response_sizes(response)
        payload = response.json()
        return (
            (time.perf_counter() - started) * 1000,
            response.status_code,
            decoded,
            wire,
            request_bytes,
            clean_updated_at(payload),
        )

    def phase(name: str):
        wait_for_writer_quiescence()

        def run():
            with concurrent.futures.ThreadPoolExecutor(max_workers=40) as pool:
                return list(pool.map(update, range(len(USERS))))

        rows, metrics = measured(process, run)
        result = {**metrics, "updated_at_values": len({row[5] for row in rows if row[5]}), "state": preference_state()}
        print(name, json.dumps(result, ensure_ascii=True), flush=True)
        return result

    unique = phase("UNIQUE_UPDATE")
    retry = phase("EXACT_RETRY")
    print(json.dumps({"unique": unique["state"], "retry": retry["state"]}, ensure_ascii=True))
    return 0


def clean_updated_at(payload: dict) -> str:
    preferences = payload.get("preferences") if isinstance(payload, dict) else {}
    if isinstance(preferences, dict) and preferences.get("updated_at"):
        return str(preferences.get("updated_at", ""))
    return str(payload.get("updated_at", "") if isinstance(payload, dict) else "")


if __name__ == "__main__":
    raise SystemExit(main())
