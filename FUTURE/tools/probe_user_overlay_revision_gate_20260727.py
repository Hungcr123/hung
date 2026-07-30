#!/usr/bin/env python3
"""Focused /server-data/user-overlay timing and semantic gate.

Added 2026-07-27 for the user-overlay revision hotspot checkpoint.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

import requests

BASE = "http://127.0.0.1:18877"
OUT_DIR = Path(r"C:\Users\Admin\.codex\plans\server2_user_overlay_opt_20260727")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def timing(header: str) -> dict[str, float]:
    out: dict[str, float] = {}
    for name, value in re.findall(r"([a-zA-Z0-9_\-]+);dur=([0-9.]+)", header or ""):
        out[name] = float(value)
    return out


def login(base: str, username: str, password: str) -> requests.Session:
    session = requests.Session()
    response = session.post(base + "/auth/login", json={"username": username, "password": password}, timeout=45)
    response.raise_for_status()
    token = str((response.json() or {}).get("token") or "")
    if not token:
        raise RuntimeError(f"login token missing for {username}")
    session.headers.update({"Authorization": f"Bearer {token}"})
    return session


def get_json(session: requests.Session, base: str, path: str, etag: str = "") -> dict:
    headers = {"Accept-Encoding": "gzip"}
    if etag:
        headers["If-None-Match"] = etag
    started = time.perf_counter()
    response = session.get(base + path, headers=headers, timeout=60)
    elapsed = (time.perf_counter() - started) * 1000
    payload = response.json() if response.status_code != 304 and response.content else {}
    rows = payload.get("rows") if isinstance(payload, dict) else []
    task_rows = payload.get("tasks") if isinstance(payload, dict) else []
    if not isinstance(rows, list):
        rows = []
    if not isinstance(task_rows, list):
        task_rows = []
    row_paths = [str(row.get("path") or "") for row in rows if isinstance(row, dict)]
    tasks_missing_key = [
        task for task in task_rows
        if isinstance(task, dict) and (not str(task.get("task_id") or task.get("id") or "") or not str(task.get("path") or task.get("file_path") or ""))
    ]
    return {
        "path": path,
        "status": response.status_code,
        "elapsed_ms": round(elapsed, 3),
        "etag": response.headers.get("ETag", ""),
        "cache_hit": response.headers.get("X-Future-Cache-Hit", ""),
        "server_timing": timing(response.headers.get("Server-Timing", "")),
        "wire_bytes": int(response.headers.get("Content-Length") or 0),
        "decoded_bytes": len(response.content),
        "sha256": hashlib.sha256(response.content).hexdigest() if response.content else "",
        "row_count": int(payload.get("row_count", 0) or 0) if isinstance(payload, dict) else 0,
        "common_rows": sum(1 for path_value in row_paths if path_value == "common" or path_value.startswith("common/")),
        "private_rows": sum(1 for path_value in row_paths if "/" in path_value and not path_value.startswith("common/")),
        "tasks_count": len(task_rows),
        "tasks_missing_key_count": len(tasks_missing_key),
        "ok": 200 <= response.status_code < 300 or response.status_code == 304,
    }


def user_gate(base: str, username: str, password: str) -> dict:
    session = login(base, username, password)
    common = get_json(session, base, "/server-data/common-tree")
    overlay = get_json(session, base, "/server-data/user-overlay")
    overlay_304 = get_json(session, base, "/server-data/user-overlay", overlay.get("etag", ""))
    tree = get_json(session, base, f"/server-data/tree-preload?username={quote(username)}")
    folder = get_json(session, base, f"/server-data/list?path=common&task_owner={quote(username)}&defer_task_board=1&include_space_task=1")
    tasks = get_json(session, base, f"/lesson-tasks?user={quote(username)}")
    return {
        "username": username,
        "common_tree": common,
        "user_overlay": overlay,
        "user_overlay_revalidate": overlay_304,
        "tree_preload": tree,
        "folder_common": folder,
        "lesson_tasks": tasks,
        "pass": all(item.get("ok") for item in (common, overlay, overlay_304, tree, folder, tasks))
        and common.get("common_rows", 0) > 0
        and tree.get("common_rows", 0) > 0
        and tasks.get("tasks_missing_key_count", 0) == 0,
    }


def concurrent_overlay(base: str, credentials: dict[str, str], level: int) -> dict:
    names = list(credentials.keys())
    sessions = {name: login(base, name, credentials[name]) for name in names}
    users = [names[index % len(names)] for index in range(level)]
    rows = []
    with ThreadPoolExecutor(max_workers=level) as pool:
        futures = [
            pool.submit(lambda name=user: get_json(sessions[name], base, "/server-data/user-overlay"))
            for user in users
        ]
        for future in as_completed(futures):
            rows.append(future.result())
    durations = sorted(float(row.get("elapsed_ms") or 0) for row in rows)
    overlay_manifest = [float((row.get("server_timing") or {}).get("overlay_manifest_revision") or 0) for row in rows]
    return {
        "level": level,
        "count": len(rows),
        "statuses": {str(code): sum(1 for row in rows if int(row.get("status") or 0) == code) for code in sorted({int(row.get("status") or 0) for row in rows})},
        "p50_ms": durations[len(durations) // 2] if durations else None,
        "p95_ms": durations[min(len(durations) - 1, int(len(durations) * 0.95))] if durations else None,
        "p99_ms": durations[min(len(durations) - 1, int(len(durations) * 0.99))] if durations else None,
        "overlay_manifest_revision_max_ms": round(max(overlay_manifest), 3) if overlay_manifest else 0,
        "errors": sum(1 for row in rows if not row.get("ok")),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default=BASE)
    parser.add_argument("--output", default=str(OUT_DIR / "overlay_revision_gate_current_20260727.json"))
    args = parser.parse_args()
    credentials = {
        "hung": os.environ.get("FUTURE_HUNG_PASSWORD", ""),
        "quynh": os.environ.get("FUTURE_QUYNH_PASSWORD", ""),
        "hungcr": os.environ.get("FUTURE_HUNGCR_PASSWORD", ""),
    }
    missing = [name for name, value in credentials.items() if not value]
    if missing:
        raise RuntimeError(f"Missing password env for: {', '.join(missing)}")
    result = {
        "timestamp_utc": utc_now(),
        "base": args.base,
        "users": {name: user_gate(args.base, name, password) for name, password in credentials.items()},
        "concurrent_overlay": {
            "5": concurrent_overlay(args.base, credentials, 5),
            "10": concurrent_overlay(args.base, credentials, 10),
        },
    }
    result["pass"] = all(row.get("pass") for row in result["users"].values()) and all(
        row.get("errors") == 0 and float(row.get("p95_ms") or 0) < 10000
        for row in result["concurrent_overlay"].values()
    )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"ok": result["pass"], "output": str(output)}, ensure_ascii=False))
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
