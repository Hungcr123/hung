#!/usr/bin/env python3
"""Verify /server-data/user-overlay empty fast path is semantically safe.

Added 2026-07-28 for the final user-overlay checkpoint. This creates isolated
PostgreSQL-only users, seeds private state for one of them, and fails if the
empty overlay fast path is selected for a user with private state.
"""

from __future__ import annotations

import argparse
import json
import os
import secrets
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import FUTURE.server_app as app

BASE = "http://127.0.0.1:18877"
OUT = Path(r"C:\Users\Admin\.codex\plans\server2_user_overlay_opt_20260727\overlay_empty_fast_path_safety_20260728.json")
PREFIX = "codexoverlaychk"


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
                if table == "vocabulary_events":
                    cur.execute(f"DELETE FROM future_server2.{table} WHERE lower(username) LIKE %s OR lower(event_key) LIKE %s", (prefix, prefix))
                else:
                    cur.execute(f"DELETE FROM future_server2.{table} WHERE lower(username) LIKE %s", (prefix,))
                out[table] = int(cur.rowcount or 0)
        return out

    return app.postgres_execute(_write)


def seed(password: str) -> dict:
    now = utc_now()
    hashed = app.password_hash(password)
    empty_user = f"{PREFIX}empty"
    data_user = f"{PREFIX}data"

    def _write(con):
        with con.cursor() as cur:
            for username in (empty_user, data_user):
                cur.execute(
                    """
                    INSERT INTO future_server2.users(username,is_admin,profile_json,updated_at_utc,updated_epoch,is_test)
                    VALUES(%s,false,%s,%s,extract(epoch from now()),true)
                    ON CONFLICT(username) DO UPDATE SET profile_json=excluded.profile_json, updated_at_utc=excluded.updated_at_utc, is_test=true
                    """,
                    (username, json.dumps({"codex_overlay_checkpoint": True}), now),
                )
                cur.execute(
                    """
                    INSERT INTO future_server2.user_auth_credentials(username,password_hash,source_path,updated_at_utc,updated_epoch)
                    VALUES(%s,%s,'codex-overlay-checkpoint',%s,extract(epoch from now()))
                    ON CONFLICT(username) DO UPDATE SET password_hash=excluded.password_hash, updated_at_utc=excluded.updated_at_utc
                    """,
                    (username, hashed, now),
                )
            cur.execute(
                """
                INSERT INTO future_server2.lesson_progress(username,space,progress_key,path,identity,file_id,node_index,node_count,learned_count,complete,server_revision,updated_at_utc,updated_epoch,record_json)
                VALUES(%s,'Space_V','codex-overlay-progress','common/Codex Overlay Check.Space_V','ftg-codex-overlay-check','ftg-codex-overlay-check',3,10,3,false,1,%s,extract(epoch from now()),%s)
                """,
                (data_user, now, json.dumps({"progress": 3, "total": 10, "codex_overlay_checkpoint": True})),
            )
            cur.execute(
                """
                INSERT INTO future_server2.lesson_time(username,lesson_key,file_id,path,title,space,seconds,ticks,updated_at_utc,updated_epoch)
                VALUES(%s,'ftg-codex-overlay-check','ftg-codex-overlay-check','common/Codex Overlay Check.Space_V','Codex Overlay Check','Space_V',42,1,%s,extract(epoch from now()))
                """,
                (data_user, now),
            )
            cur.execute(
                """
                INSERT INTO future_server2.lesson_task_state(username,record_json,server_revision,updated_at_utc,updated_epoch)
                VALUES(%s,%s,1,%s,extract(epoch from now()))
                """,
                (data_user, json.dumps({"manual": [{"id": "codex-overlay-task", "path": "common/Codex Overlay Check.Space_V"}]}), now),
            )
            cur.execute(
                """
                INSERT INTO future_server2.vocabulary_registry(username,word_key,word,meaning,learn_count,last_at_utc,last_epoch,sources_json)
                VALUES(%s,'codex_overlay_word','codex overlay word','checkpoint',1,%s,extract(epoch from now()),%s)
                """,
                (data_user, now, json.dumps([{"path": "common/Codex Overlay Check.Space_V"}])),
            )
        return {"empty_user": empty_user, "data_user": data_user}

    return app.postgres_execute(_write)


def private_counts(username: str) -> dict:
    tables = {
        "lesson_progress": "username",
        "lesson_time": "username",
        "lesson_task_state": "username",
        "lesson_task_notices": "username",
        "vocabulary_registry": "username",
        "vocabulary_events": "username",
        "vault_folders": "username",
        "vault_entries": "username",
        "vault_revisions": "username",
    }

    def _read(con):
        out = {}
        with con.cursor() as cur:
            for table, column in tables.items():
                cur.execute(f"SELECT count(*) FROM future_server2.{table} WHERE lower({column})=%s", (username.lower(),))
                out[table] = int(cur.fetchone()[0] or 0)
        return out

    return app.postgres_execute(_read)


def login(base: str, username: str, password: str) -> requests.Session:
    session = requests.Session()
    response = session.post(base + "/auth/login", json={"username": username, "password": password}, timeout=30)
    response.raise_for_status()
    token = response.json().get("token")
    if not token:
        raise RuntimeError(f"missing token for {username}")
    session.headers.update({"Authorization": f"Bearer {token}"})
    return session


def overlay(base: str, username: str, password: str) -> dict:
    session = login(base, username, password)
    response = session.get(base + "/server-data/user-overlay", headers={"Accept-Encoding": "gzip"}, timeout=45)
    response.raise_for_status()
    payload = response.json()
    return {
        "status": response.status_code,
        "cache_hit": response.headers.get("X-Future-Cache-Hit", ""),
        "etag": response.headers.get("ETag", ""),
        "row_count": int(payload.get("row_count", 0) or 0),
        "empty_overlay_fast_path": bool(payload.get("empty_overlay_fast_path")),
        "overlay_revision": payload.get("overlay_revision", ""),
        "payload_semantically_empty": bool(payload.get("empty_overlay_fast_path")) and int(payload.get("row_count", 0) or 0) == 1,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default=BASE)
    parser.add_argument("--output", default=str(OUT))
    args = parser.parse_args()
    password = "codex-" + secrets.token_urlsafe(12)
    result = {"started_utc": utc_now(), "base": args.base, "cleanup_before": cleanup()}
    try:
        users = seed(password)
        result["users"] = users
        result["checks"] = {}
        for role, username in users.items():
            counts = private_counts(username)
            payload = overlay(args.base, username, password)
            has_private_state = any(int(value or 0) > 0 for value in counts.values())
            result["checks"][role] = {
                "username": username,
                "private_counts": counts,
                "has_private_state": has_private_state,
                "overlay": payload,
                "pass": not (has_private_state and payload["empty_overlay_fast_path"]),
            }
        result["pass"] = all(item["pass"] for item in result["checks"].values())
    finally:
        result["cleanup_after"] = cleanup()
        result["finished_utc"] = utc_now()
        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"ok": result.get("pass", False), "output": args.output}, ensure_ascii=False))
    return 0 if result.get("pass") else 1


if __name__ == "__main__":
    raise SystemExit(main())
