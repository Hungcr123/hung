#!/usr/bin/env python3
"""A/B/C correctness gate for /server-data/user-overlay.

Added 2026-07-28 for the final overlay checkpoint. It creates isolated
benchmark users, seeds empty/medium/heavy private state, restarts the test
runtime externally when requested, and verifies overlay/task correctness.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import secrets
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

import requests

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import FUTURE.server_app as app

BASE = "http://127.0.0.1:18877"
OUT = Path(r"C:\Users\Admin\.codex\plans\server2_user_overlay_opt_20260727\overlay_abc_correctness_20260728.json")
PREFIX = "codexoverlayabc"
TEST_PASSWORD = "CodexOverlayAbc1!"
MANIFEST_FILE = Path(r"C:\server data\_future_server_data_manifest.json")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def cleanup() -> dict:
    prefix = PREFIX + "%"

    def _write(con):
        out = {}
        with con.cursor() as cur:
            for table in (
                "auth_sessions",
                "lesson_time_credit_state",
                "lesson_time",
                "lesson_progress",
                "lesson_progress_namespaces",
                "lesson_task_state",
                "lesson_task_notice_state",
                "lesson_task_notices",
                "append_events",
                "vocabulary_events",
                "vocabulary_registry",
                "daily_earn",
                "weekly_earn",
                "monthly_earn",
                "npc_period_earn",
                "vault_entries",
                "vault_folders",
                "vault_hidden_paths",
                "vault_revisions",
                "server_load_test_credentials",
                "user_auth_credentials",
                "users",
            ):
                if table in {"append_events", "vocabulary_events"}:
                    cur.execute(f"DELETE FROM future_server2.{table} WHERE lower(username) LIKE %s OR lower(event_key) LIKE %s", (prefix, prefix))
                else:
                    cur.execute(f"DELETE FROM future_server2.{table} WHERE lower(username) LIKE %s", (prefix,))
                out[table] = int(cur.rowcount or 0)
        return out

    return app.postgres_execute(_write)


def pick_common_lessons(limit: int = 12) -> list[dict]:
    if MANIFEST_FILE.is_file():
        manifest = json.loads(MANIFEST_FILE.read_text(encoding="utf-8-sig", errors="replace"))
    else:
        manifest = requests.get(BASE + "/server-data/common-tree", timeout=60).json().get("manifest", {})
    folders = manifest.get("folders") if isinstance(manifest.get("folders"), dict) else {}
    rows = []
    for parent, entries in folders.items():
        if not str(parent).lower().startswith("common"):
            continue
        for item in entries if isinstance(entries, list) else []:
            if not isinstance(item, dict) or str(item.get("type", "")).lower() != "file":
                continue
            path = app.clean_path_value(item.get("path", ""))
            ext = Path(path).suffix.lower()
            if path.startswith("common/") and ext in {".space_v", ".space_w", ".space_q", ".space_p"}:
                rows.append({
                    "path": path,
                    "lesson_id": app.clean(item.get("lesson_id", "")) or f"codex-{hashlib.sha1(path.encode()).hexdigest()[:12]}",
                    "space": ext.lstrip(".").upper(),
                    "title": app.clean(item.get("name", "")) or Path(path).stem,
                })
    if len(rows) < limit:
        raise RuntimeError(f"Not enough common lesson files for ABC gate: {len(rows)}")
    return rows[:limit]


def seed_users(password: str, lessons: list[dict]) -> dict:
    now = utc_now()
    hashed = app.password_hash(password)
    groups = {
        "A": [f"{PREFIX}a001", f"{PREFIX}a002"],
        "B": [f"{PREFIX}b001", f"{PREFIX}b002"],
        "C": [f"{PREFIX}c001", f"{PREFIX}c002"],
    }

    def _write(con):
        with con.cursor() as cur:
            for group_users in groups.values():
                for username in group_users:
                    cur.execute(
                        """
                        INSERT INTO future_server2.users(username,is_admin,profile_json,updated_at_utc,updated_epoch,is_test)
                        VALUES(%s,false,%s,%s,extract(epoch from now()),true)
                        ON CONFLICT(username) DO UPDATE SET profile_json=excluded.profile_json, updated_at_utc=excluded.updated_at_utc, is_test=true
                        """,
                        (username, json.dumps({"group": username[len(PREFIX):1+len(PREFIX)], "abc_overlay_checkpoint": True}), now),
                    )
                    cur.execute(
                        """
                        INSERT INTO future_server2.user_auth_credentials(username,password_hash,source_path,updated_at_utc,updated_epoch)
                        VALUES(%s,%s,'codex-overlay-abc',%s,extract(epoch from now()))
                        ON CONFLICT(username) DO UPDATE SET password_hash=excluded.password_hash, updated_at_utc=excluded.updated_at_utc
                        """,
                        (username, hashed, now),
                    )
            for username in groups["B"] + groups["C"]:
                count = 4 if username in groups["B"] else 12
                vocab_count = 8 if username in groups["B"] else 120
                for idx, lesson in enumerate(lessons[:count]):
                    complete = idx % 3 == 0
                    cur.execute(
                        """
                        INSERT INTO future_server2.lesson_progress(username,space,progress_key,path,identity,file_id,node_index,node_count,learned_count,complete,server_revision,updated_at_utc,updated_epoch,record_json)
                        VALUES(%s,%s,%s,%s,%s,%s,%s,10,%s,%s,1,%s,extract(epoch from now()),%s)
                        """,
                        (
                            username,
                            lesson["space"],
                            f"{PREFIX}-{username}-{idx}",
                            lesson["path"],
                            lesson["lesson_id"],
                            lesson["lesson_id"],
                            idx + 1,
                            idx + 1,
                            complete,
                            now,
                            json.dumps({"done": idx + 1, "total": 10, "complete": complete, "group": username[:len(PREFIX)+1]}),
                        ),
                    )
                    cur.execute(
                        """
                        INSERT INTO future_server2.lesson_time(username,lesson_key,file_id,path,title,space,seconds,ticks,updated_at_utc,updated_epoch)
                        VALUES(%s,%s,%s,%s,%s,%s,%s,1,%s,extract(epoch from now()))
                        """,
                        (username, lesson["lesson_id"], lesson["lesson_id"], lesson["path"], lesson["title"], lesson["space"], 60 + idx, now),
                    )
                task_lesson = lessons[0]
                task_record = {
                    "tasks": [{
                        "id": f"task-{username}-manual",
                        "path": task_lesson["path"],
                        "lesson_id": task_lesson["lesson_id"],
                        "file_id": task_lesson["lesson_id"],
                        "title": f"Manual {username}",
                        "name": task_lesson["title"],
                        "creator_role": "user",
                        "added_by": username,
                        "added_at": now,
                        "severity": "normal",
                    }],
                    "space_task": {
                        "preferred_folders": ["/".join(lessons[1]["path"].split("/")[:-1])],
                        "updated_at": now,
                        "updated_by": username,
                        "updated_rev": f"{PREFIX}-{username}-rev1",
                        "assigned": {
                            f"{PREFIX}-{username}-auto": {"path": lessons[1]["path"], "assigned_at": now}
                        },
                    },
                }
                cur.execute(
                    """
                    INSERT INTO future_server2.lesson_task_state(username,record_json,server_revision,updated_at_utc,updated_epoch)
                    VALUES(%s,%s,1,%s,extract(epoch from now()))
                    """,
                    (username, json.dumps(task_record, ensure_ascii=False, sort_keys=True, separators=(",", ":")), now),
                )
                for idx in range(vocab_count):
                    cur.execute(
                        """
                        INSERT INTO future_server2.vocabulary_registry(username,word_key,word,meaning,learn_count,last_at_utc,last_epoch,sources_json)
                        VALUES(%s,%s,%s,'checkpoint',1,%s,extract(epoch from now()),%s)
                        """,
                        (username, f"{PREFIX}_{username}_{idx}", f"{PREFIX} word {idx}", now, json.dumps([{"path": lessons[idx % len(lessons)]["path"]}])),
                    )
        return groups

    return app.postgres_execute(_write)


def restart_test_server() -> dict:
    script = ROOT / "FUTURE" / "tools" / "start_current_checkpoint_server_18877.ps1"
    started = time.perf_counter()
    subprocess.run(["powershell", "-ExecutionPolicy", "Bypass", "-File", str(script)], cwd=str(ROOT), check=True, timeout=120)
    return {"restarted": True, "wall_ms": round((time.perf_counter() - started) * 1000, 3)}


def login(base: str, username: str, password: str) -> requests.Session:
    session = requests.Session()
    response = session.post(base + "/auth/login", json={"username": username, "password": password}, timeout=45)
    response.raise_for_status()
    token = response.json().get("token")
    if not token:
        raise RuntimeError(f"missing token for {username}")
    session.headers.update({"Authorization": f"Bearer {token}"})
    return session


def get_payload(session: requests.Session, base: str, path: str) -> tuple[dict, requests.Response]:
    response = session.get(base + path, headers={"Accept-Encoding": "gzip"}, timeout=60)
    response.raise_for_status()
    return response.json(), response


def validate_user(base: str, username: str, password: str, group: str) -> dict:
    session = login(base, username, password)
    common, common_response = get_payload(session, base, "/server-data/common-tree")
    overlay, overlay_response = get_payload(session, base, "/server-data/user-overlay")
    tree, tree_response = get_payload(session, base, f"/server-data/tree-preload?username={quote(username)}")
    tasks, tasks_response = get_payload(session, base, f"/lesson-tasks?user={quote(username)}")
    task_rows = tasks.get("tasks") if isinstance(tasks.get("tasks"), list) else []
    missing_task_keys = [
        task for task in task_rows
        if isinstance(task, dict) and (not app.clean(task.get("id", "")) or not app.clean_path_value(task.get("path", "")))
    ]
    overlay_fast = bool(overlay.get("empty_overlay_fast_path"))
    expected_empty = group == "A"
    remove_result = {}
    if group in {"B", "C"} and task_rows:
        target = next((task for task in task_rows if isinstance(task, dict) and app.clean(task.get("creator_role", "")) == "user"), task_rows[0])
        remove_response = session.post(base + "/lesson-tasks", json={"action": "remove", "id": target.get("id"), "path": target.get("path")}, timeout=45)
        remove_result = {"status": remove_response.status_code, "body": remove_response.json() if remove_response.content else {}}
        tasks_after, _after_response = get_payload(session, base, f"/lesson-tasks?user={quote(username)}")
        remove_result["remaining_same_id"] = any(isinstance(item, dict) and item.get("id") == target.get("id") for item in (tasks_after.get("tasks") or []))
    return {
        "username": username,
        "group": group,
        "common": {"status": common_response.status_code, "rows": common.get("row_count"), "common_revision": common.get("common_revision"), "cache": common_response.headers.get("X-Future-Cache-Hit", "")},
        "overlay": {"status": overlay_response.status_code, "rows": overlay.get("row_count"), "fast_path": overlay_fast, "revision": overlay.get("overlay_revision"), "cache": overlay_response.headers.get("X-Future-Cache-Hit", ""), "private_state": overlay.get("empty_overlay_private_state", {})},
        "tree": {"status": tree_response.status_code, "rows": tree.get("row_count"), "common_rows": sum(1 for row in (tree.get("rows") or []) if isinstance(row, dict) and str(row.get("path", "")).startswith("common/"))},
        "tasks": {"status": tasks_response.status_code, "count": len(task_rows), "missing_key_count": len(missing_task_keys), "cache": tasks_response.headers.get("X-Future-Cache-Hit", "")},
        "remove": remove_result,
        "pass": common.get("row_count", 0) > 0
        and tree.get("row_count", 0) > 0
        and len(missing_task_keys) == 0
        and (overlay_fast if expected_empty else not overlay_fast)
        and (not remove_result or (remove_result.get("status") == 200 and not remove_result.get("remaining_same_id"))),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default=BASE)
    parser.add_argument("--output", default=str(OUT))
    parser.add_argument("--restart", action="store_true")
    args = parser.parse_args()
    result = {"started_utc": utc_now(), "base": args.base, "cleanup_before": cleanup()}
    try:
        lessons = pick_common_lessons()
        result["lesson_fixtures"] = lessons[:6]
        groups = seed_users(TEST_PASSWORD, lessons)
        result["groups"] = groups
        if args.restart:
            result["restart_after_seed"] = restart_test_server()
        checks = []
        for group, users in groups.items():
            for username in users:
                checks.append(validate_user(args.base, username, TEST_PASSWORD, group))
        result["checks"] = checks
        result["pass"] = all(item.get("pass") for item in checks)
    finally:
        result["cleanup_after"] = cleanup()
        result["finished_utc"] = utc_now()
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"ok": result.get("pass", False), "output": args.output}, ensure_ascii=False))
    return 0 if result.get("pass") else 1


if __name__ == "__main__":
    raise SystemExit(main())
