#!/usr/bin/env python3
"""Focused HTTP gate for startup warmup mode selection.

Added 2026-07-28 for the test-user warmup checkpoint. The script assumes a
PostgreSQL-only Server 2 is already listening on 18877 and never stores secrets.
"""

from __future__ import annotations

import json
import os
import time
import sys
from pathlib import Path
from typing import Any

import requests

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import FUTURE.server_app as app  # noqa: E402

BASE = os.environ.get("FUTURE_TEST_BASE", "http://127.0.0.1:18877").rstrip("/")
OUT = Path(os.environ.get("FUTURE_WARMUP_GATE_OUT", r"C:\Users\Admin\.codex\plans\server2_postgres_full_audit\startup_warmup_modes_gate_20260728.json"))
REAL_USER = os.environ.get("FUTURE_REAL_TEST_USER", "hung")
TEST_USER = os.environ.get("FUTURE_BENCH_TEST_USER", "codexload001")


def call(session: requests.Session, method: str, path: str, **kwargs: Any) -> tuple[int, dict[str, Any], float, dict[str, str]]:
    started = time.perf_counter()
    response = session.request(method, BASE + path, timeout=30, **kwargs)
    elapsed_ms = round((time.perf_counter() - started) * 1000, 3)
    try:
        payload = response.json()
    except Exception:
        payload = {"text_prefix": response.text[:240]}
    return response.status_code, payload, elapsed_ms, dict(response.headers)


def login_flow(username: str, password: str) -> dict[str, Any]:
    session = requests.Session()
    rows = []
    status, payload, elapsed, headers = call(session, "POST", "/auth/login", json={"username": username, "password": password})
    token = str(payload.get("token") or "")
    rows.append({"name": "auth_login", "status": status, "elapsed_ms": elapsed, "ok": status == 200 and bool(token)})
    auth_headers = {"Authorization": f"Bearer {token}"} if token else {}
    for name, path in (
        ("login_preload", "/server-data/login-preload?response=compact-v2"),
        ("common_tree", "/server-data/common-tree"),
        ("user_overlay", "/server-data/user-overlay"),
        ("lesson_tasks", f"/lesson-tasks?user={username}"),
    ):
        status, payload, elapsed, headers = call(session, "GET", path, headers=auth_headers)
        rows.append({
            "name": name,
            "status": status,
            "elapsed_ms": elapsed,
            "ok": 200 <= status < 400,
            "cache_hit": headers.get("X-Future-Cache-Hit", ""),
            "etag": bool(headers.get("ETag", "")),
            "row_count": payload.get("row_count") if isinstance(payload, dict) else None,
            "task_count": len(payload.get("tasks") or []) if isinstance(payload, dict) else None,
        })
    return {"username": username, "ok": all(row["ok"] for row in rows), "steps": rows}


def provision_test_user(username: str, password: str) -> None:
    now = time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime()) + "Z"
    hashed = app.password_hash(password)
    app.postgres_upsert_user_row({
        "username": username,
        "is_admin": False,
        "is_test": True,
        "profile_json": {"full_name": f"Codex Bench {username}", "warmup": True},
        "updated_at_utc": now,
    })
    app.postgres_upsert_user_auth_credential(username, hashed, "benchmark:startup-warmup-modes")


def main() -> int:
    real_password = os.environ.get("FUTURE_REAL_TEST_PASSWORD", "")
    test_password = os.environ.get("FUTURE_TEST_PASSWORD", "")
    if not real_password:
        raise SystemExit("Set FUTURE_REAL_TEST_PASSWORD in environment.")
    summary: dict[str, Any] = {
        "base": BASE,
        "real_user": REAL_USER,
        "test_user": TEST_USER,
        "passwords_present": {"real": bool(real_password), "test": bool(test_password)},
    }
    health_status, health, health_elapsed, _headers = call(requests.Session(), "GET", "/health?view=startup-warmup-gate")
    summary["health"] = {
        "status": health_status,
        "elapsed_ms": health_elapsed,
        "ok": health_status == 200 and bool(health.get("ok")),
        "postgres_only": bool(health.get("postgres_only") or (health.get("postgres_writer") or {}).get("postgres_only")),
        "postgres_writer": health.get("postgres_writer"),
    }
    if test_password:
        provision_test_user(TEST_USER, test_password)
    summary["real_cold"] = login_flow(REAL_USER, real_password)
    summary["real_warm"] = login_flow(REAL_USER, real_password)
    if test_password:
        summary["test_cold"] = login_flow(TEST_USER, test_password)
        summary["test_warm"] = login_flow(TEST_USER, test_password)
    else:
        summary["test_cold"] = {"ok": False, "skipped": "FUTURE_TEST_PASSWORD missing"}
        summary["test_warm"] = {"ok": False, "skipped": "FUTURE_TEST_PASSWORD missing"}
    summary["ok"] = bool(summary["health"]["ok"] and summary["real_cold"]["ok"] and summary["real_warm"]["ok"] and summary["test_cold"].get("ok") and summary["test_warm"].get("ok"))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"ok": summary["ok"], "output": str(OUT)}, ensure_ascii=False))
    return 0 if summary["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

