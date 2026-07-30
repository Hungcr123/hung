#!/usr/bin/env python3
"""Phase audit for /server-data/common-tree with semantic comparison.

Added 2026-07-28 to prove whether common-tree bottleneck is rebuild, serialize,
compress, cache lookup, or response send before any further optimization.
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
from typing import Any

import requests

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = Path(r"C:\Users\Admin\.codex\plans\server2_common_tree_phase_audit_20260728")
BASE = "http://127.0.0.1:18877"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def timing(header: str) -> dict[str, float]:
    out: dict[str, float] = {}
    for name, value in re.findall(r"([a-zA-Z0-9_\-]+);dur=([0-9.]+)", header or ""):
        out[name] = float(value)
    return out


def login_local(base: str, username: str) -> tuple[requests.Session, str]:
    session = requests.Session()
    response = session.get(
        f"{base}/auth/codex-local-login",
        params={"marker": "1", "username": username, "next": "/status"},
        allow_redirects=False,
        timeout=30,
    )
    if response.status_code != 302:
        raise RuntimeError(f"local login failed for {username}: {response.status_code}")
    token = ""
    for cookie in session.cookies:
        if cookie.name == "future_lesson_auth_token":
            token = cookie.value
            break
    if not token:
        set_cookie = response.headers.get("Set-Cookie", "")
        if "future_lesson_auth_token=" in set_cookie:
            token = set_cookie.split("future_lesson_auth_token=", 1)[1].split(";", 1)[0]
    if not token:
        raise RuntimeError(f"missing token for {username}")
    return session, token


def clone_session(token: str) -> requests.Session:
    session = requests.Session()
    session.cookies.set("future_lesson_auth_token", token)
    return session


def request_json(session: requests.Session, base: str, path: str, *, etag: str = "") -> dict[str, Any]:
    headers = {"Accept-Encoding": "gzip"}
    if etag:
        headers["If-None-Match"] = etag
    started = time.perf_counter()
    response = session.get(base + path, headers=headers, timeout=60)
    elapsed = (time.perf_counter() - started) * 1000
    payload = response.json() if response.status_code != 304 and response.content else {}
    rows = payload.get("rows") if isinstance(payload, dict) else []
    if not isinstance(rows, list):
        rows = []
    row_paths = [str(row.get("path") or "") for row in rows if isinstance(row, dict)]
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
        "payload": payload if isinstance(payload, dict) else {},
    }


def canonical(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {key: canonical(value) for key, value in sorted(obj.items()) if key not in {"generated_at"}}
    if isinstance(obj, list):
        return [canonical(value) for value in obj]
    return obj


def hash_semantic(payload: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(canonical(payload), ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def common_semantic_check(common: dict[str, Any], label: str) -> dict[str, Any]:
    payload = common.get("payload") or {}
    return {
        "label": label,
        "status": common.get("status"),
        "sha256": common.get("sha256"),
        "semantic_sha256": hash_semantic(payload) if payload else "",
        "row_count": common.get("row_count"),
        "common_rows": common.get("common_rows"),
        "private_rows": common.get("private_rows"),
        "cache_hit": common.get("cache_hit"),
        "server_timing": common.get("server_timing"),
    }


def concurrent_common_tree(base: str, token: str, level: int) -> dict[str, Any]:
    sessions = [clone_session(token) for _ in range(level)]
    rows: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=level) as pool:
        futures = [pool.submit(request_json, sessions[index], base, "/server-data/common-tree") for index in range(level)]
        for future in as_completed(futures):
            rows.append(future.result())
    elapsed = sorted(float(row.get("elapsed_ms") or 0) for row in rows)
    timings = [row.get("server_timing") or {} for row in rows]
    return {
        "level": level,
        "count": len(rows),
        "statuses": {str(code): sum(1 for row in rows if int(row.get("status") or 0) == code) for code in sorted({int(row.get("status") or 0) for row in rows})},
        "cache_hits": {hit: sum(1 for row in rows if row.get("cache_hit") == hit) for hit in sorted({row.get("cache_hit") for row in rows})},
        "p50_ms": elapsed[len(elapsed) // 2] if elapsed else 0.0,
        "p95_ms": elapsed[min(len(elapsed) - 1, max(0, int(len(elapsed) * 0.95) - 1))] if elapsed else 0.0,
        "p99_ms": elapsed[min(len(elapsed) - 1, max(0, int(len(elapsed) * 0.99) - 1))] if elapsed else 0.0,
        "common_build_max_ms": max(float(t.get("common_build") or 0) for t in timings) if timings else 0.0,
        "common_serialize_max_ms": max(float(t.get("common_serialize") or 0) for t in timings) if timings else 0.0,
        "common_compress_max_ms": max(float(t.get("common_compress") or 0) for t in timings) if timings else 0.0,
        "common_prepare_max_ms": max(float(t.get("common_prepare") or 0) for t in timings) if timings else 0.0,
        "errors": sum(1 for row in rows if int(row.get("status") or 0) >= 400),
    }


def fetch_user_payloads(base: str, username: str, token: str) -> dict[str, Any]:
    session = clone_session(token)
    common = request_json(session, base, "/server-data/common-tree")
    overlay = request_json(session, base, "/server-data/user-overlay")
    tree = request_json(session, base, f"/server-data/tree-preload?username={username}")
    login_preload = request_json(session, base, f"/server-data/login-preload?username={username}&response=compact-v2")
    listing = request_json(session, base, f"/server-data/list?path=common&task_owner={username}&defer_task_board=1&include_space_task=1")
    return {
        "username": username,
        "common_tree": common_semantic_check(common, f"{username}.common_tree"),
        "user_overlay": {
            "status": overlay.get("status"),
            "cache_hit": overlay.get("cache_hit"),
            "server_timing": overlay.get("server_timing"),
            "row_count": overlay.get("row_count"),
            "common_rows": overlay.get("common_rows"),
            "private_rows": overlay.get("private_rows"),
            "sha256": overlay.get("sha256"),
        },
        "tree_preload": {
            "status": tree.get("status"),
            "cache_hit": tree.get("cache_hit"),
            "row_count": tree.get("row_count"),
            "common_rows": tree.get("common_rows"),
            "private_rows": tree.get("private_rows"),
            "sha256": tree.get("sha256"),
        },
        "login_preload": {
            "status": login_preload.get("status"),
            "cache_hit": login_preload.get("cache_hit"),
            "row_count": login_preload.get("row_count"),
            "common_rows": login_preload.get("common_rows"),
            "private_rows": login_preload.get("private_rows"),
            "sha256": login_preload.get("sha256"),
        },
        "folder_common": {
            "status": listing.get("status"),
            "cache_hit": listing.get("cache_hit"),
            "row_count": listing.get("row_count"),
            "common_rows": listing.get("common_rows"),
            "private_rows": listing.get("private_rows"),
            "sha256": listing.get("sha256"),
        },
        "pass": all(item.get("status") in (200, 304) for item in (common, overlay, tree, login_preload, listing))
        and common.get("common_rows", 0) > 0
        and common.get("private_rows", 0) == 0,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default=BASE)
    parser.add_argument("--output", default=str(OUT_DIR / "common_tree_phase_audit_20260728.json"))
    parser.add_argument("--rounds", type=int, default=3)
    args = parser.parse_args()

    users = ["hung", "quynh", "hungcr"]

    result: dict[str, Any] = {
        "timestamp_utc": utc_now(),
        "base": args.base,
        "source_hashes": {},
        "users": {},
        "concurrency": {},
        "notes": [],
    }

    by_user: dict[str, dict[str, Any]] = {}
    for username in users:
        session, token = login_local(args.base, username)
        session.close()
        by_user[username] = fetch_user_payloads(args.base, username, token)
    result["users"] = by_user
    result["semantic_cross_user"] = {
        "common_tree_sha256_unique": sorted({data["common_tree"]["semantic_sha256"] for data in by_user.values()}),
        "common_tree_equal": len({data["common_tree"]["semantic_sha256"] for data in by_user.values()}) == 1,
        "tree_preload_common_rows": {username: data["tree_preload"]["common_rows"] for username, data in by_user.items()},
        "login_preload_common_rows": {username: data["login_preload"]["common_rows"] for username, data in by_user.items()},
    }

    session, token = login_local(args.base, "hung")
    try:
        result["concurrency"] = {str(level): concurrent_common_tree(args.base, token, level) for level in (1, 5, 10, 25, 50, 100)}
    finally:
        session.close()

    result["pass"] = bool(result["semantic_cross_user"]["common_tree_equal"]) and all(data["pass"] for data in by_user.values())

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    path = Path(args.output)
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"ok": result["pass"], "output": str(path)}, ensure_ascii=False))
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
