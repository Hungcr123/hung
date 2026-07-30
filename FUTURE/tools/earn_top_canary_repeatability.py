#!/usr/bin/env python3
"""Controlled Earn/Top canary harness for production Server 2.

Default mode is read-only. Use --execute only after choosing a canary user/file
and accepting that the script will create real completion/progress/earn writes,
then verify and optionally roll them back with generated SQL.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import psycopg


DEFAULT_DSN = "postgresql://future_server2_app@127.0.0.1:5432/future_server2"
DEFAULT_BASE_URL = "http://127.0.0.1:8877"
TZ = ZoneInfo("Asia/Ho_Chi_Minh")


def now_text() -> str:
    return datetime.now(TZ).isoformat(timespec="seconds")


def bucket_keys() -> dict[str, str]:
    now = datetime.now(TZ)
    week_start = now.date().fromordinal(now.date().toordinal() - now.date().weekday())
    return {"day": now.strftime("%Y-%m-%d"), "week": week_start.strftime("%Y-%m-%d"), "month": now.strftime("%Y-%m")}


def sql_count(cursor, sql: str, params: tuple) -> int:
    cursor.execute(sql, params)
    row = cursor.fetchone()
    return int(row[0] or 0) if row else 0


def export_rows(cursor, username: str, path: str) -> dict[str, list[dict]]:
    like_path = f"%{path}%"
    tables = {
        "vocabulary_registry": (
            """
            SELECT * FROM future_server2.vocabulary_registry
            WHERE username=%s AND sources_json::text ILIKE %s
            ORDER BY word_key
            """,
            (username, like_path),
        ),
        "vocabulary_events": (
            """
            SELECT * FROM future_server2.vocabulary_events
            WHERE username=%s AND source_path=%s
            ORDER BY id
            """,
            (username, path),
        ),
        "daily_earn": (
            """
            SELECT de.* FROM future_server2.daily_earn de
            LEFT JOIN future_server2.vocabulary_events ve ON ve.id=de.event_id
            WHERE de.username=%s AND (ve.source_path=%s OR de.word_key IN (
              SELECT word_key FROM future_server2.vocabulary_registry
              WHERE username=%s AND sources_json::text ILIKE %s
            ))
            ORDER BY de.day_key, de.word_key
            """,
            (username, path, username, like_path),
        ),
        "weekly_earn": (
            """
            SELECT we.* FROM future_server2.weekly_earn we
            LEFT JOIN future_server2.vocabulary_events ve ON ve.id=we.event_id
            WHERE we.username=%s AND (ve.source_path=%s OR we.word_key IN (
              SELECT word_key FROM future_server2.vocabulary_registry
              WHERE username=%s AND sources_json::text ILIKE %s
            ))
            ORDER BY we.week_key, we.word_key
            """,
            (username, path, username, like_path),
        ),
        "monthly_earn": (
            """
            SELECT me.* FROM future_server2.monthly_earn me
            LEFT JOIN future_server2.vocabulary_events ve ON ve.id=me.event_id
            WHERE me.username=%s AND (ve.source_path=%s OR me.word_key IN (
              SELECT word_key FROM future_server2.vocabulary_registry
              WHERE username=%s AND sources_json::text ILIKE %s
            ))
            ORDER BY me.month_key, me.word_key
            """,
            (username, path, username, like_path),
        ),
        "lesson_progress": (
            """
            SELECT * FROM future_server2.lesson_progress
            WHERE username=%s AND path=%s
            ORDER BY space, progress_key
            """,
            (username, path),
        ),
        "lesson_time": (
            """
            SELECT * FROM future_server2.lesson_time
            WHERE username=%s AND path=%s
            ORDER BY lesson_key
            """,
            (username, path),
        ),
        "append_events": (
            """
            SELECT * FROM future_server2.append_events
            WHERE username=%s AND event_json::text ILIKE %s
            ORDER BY id
            """,
            (username, like_path),
        ),
    }
    exported: dict[str, list[dict]] = {}
    for name, (sql, params) in tables.items():
        cursor.execute(sql, params)
        columns = [desc.name for desc in cursor.description]
        rows = []
        for row in cursor.fetchall():
            record = {}
            for key, value in zip(columns, row):
                record[key] = value
            rows.append(record)
        exported[name] = rows
    return exported


def stable_json_hash(value: object) -> str:
    data = json.dumps(value, ensure_ascii=False, sort_keys=True, default=str, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def snapshot_user(cursor, username: str, path: str) -> dict:
    buckets = bucket_keys()
    cursor.execute("SELECT current_database(), current_user, current_schema()")
    database, db_user, schema = cursor.fetchone()
    cursor.execute(
        """
        SELECT word_key
        FROM future_server2.vocabulary_registry
        WHERE username=%s AND sources_json::text ILIKE %s
        ORDER BY word_key
        """,
        (username, f"%{path}%"),
    )
    registry_words_for_path = [row[0] for row in cursor.fetchall()]
    exported = export_rows(cursor, username, path)
    return {
        "at": now_text(),
        "database": {"current_database": database, "current_user": db_user, "current_schema": schema},
        "user": username,
        "path": path,
        "buckets": buckets,
        "counts": {
            "vocabulary_registry": sql_count(cursor, "SELECT count(*) FROM future_server2.vocabulary_registry WHERE username=%s", (username,)),
            "vocabulary_events": sql_count(cursor, "SELECT count(*) FROM future_server2.vocabulary_events WHERE username=%s", (username,)),
            "daily_earn": sql_count(cursor, "SELECT count(*) FROM future_server2.daily_earn WHERE username=%s AND day_key=%s", (username, buckets["day"])),
            "weekly_earn": sql_count(cursor, "SELECT count(*) FROM future_server2.weekly_earn WHERE username=%s AND week_key=%s", (username, buckets["week"])),
            "monthly_earn": sql_count(cursor, "SELECT count(*) FROM future_server2.monthly_earn WHERE username=%s AND month_key=%s", (username, buckets["month"])),
            "lesson_progress": sql_count(cursor, "SELECT count(*) FROM future_server2.lesson_progress WHERE username=%s", (username,)),
            "lesson_time": sql_count(cursor, "SELECT count(*) FROM future_server2.lesson_time WHERE username=%s", (username,)),
            "learning_events": sql_count(cursor, "SELECT count(*) FROM future_server2.append_events WHERE stream='learning' AND username=%s", (username,)),
        },
        "registry_words_for_path_sample": registry_words_for_path[:40],
        "registry_words_for_path_count": len(registry_words_for_path),
        "export_row_counts": {key: len(value) for key, value in exported.items()},
        "export_sha256": stable_json_hash(exported),
        "export_rows": exported,
    }


def http_json(url: str, method: str = "GET", payload: dict | None = None, token: str = "") -> tuple[int, dict]:
    data = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"
        headers["X-Future-Auth"] = token
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            raw = response.read()
            return int(response.status), json.loads(raw.decode("utf-8-sig") or "{}")
    except urllib.error.HTTPError as exc:
        raw = exc.read()
        try:
            body = json.loads(raw.decode("utf-8-sig") or "{}")
        except Exception:
            body = {"error": raw.decode("utf-8", errors="replace")[:500]}
        return int(exc.code), body


def login(base_url: str, username: str, password: str) -> str:
    status, body = http_json(f"{base_url}/auth/login", "POST", {"username": username, "password": password})
    if status != 200 or not body.get("ok"):
        raise RuntimeError(f"login failed status={status} error={body.get('error')}")
    token = str(body.get("token") or body.get("auth_token") or body.get("authToken") or "")
    if not token and isinstance(body.get("session"), dict):
        token = str(body["session"].get("token") or "")
    if not token:
        raise RuntimeError("login succeeded but no token field was found")
    return token


def leaderboard_user(base_url: str, token: str, username: str, scope: str) -> dict:
    status, body = http_json(f"{base_url}/vocab/leaderboard?limit=80&double_check=0&scope={scope}&type=space_v", token=token)
    if status != 200:
        raise RuntimeError(f"leaderboard {scope} failed status={status}")
    rows = ((body.get("boards") if isinstance(body.get("boards"), dict) else {}).get(scope) or [])
    for row in rows:
        if str(row.get("username", "")).lower() == username.lower():
            return row
    return {}


def completion_payload(path: str, run_id: str) -> dict:
    title = Path(path).stem
    return {
        "path": path,
        "name": title,
        "title": title,
        "nodes": 0,
        "completed_at": datetime.now(TZ).isoformat(timespec="seconds"),
        "completion_run_id": run_id,
        "source": "server",
        "reason": "canary_repeatability",
    }


def rollback_sql(username: str, before: dict) -> str:
    # Conservative rollback skeleton: generated for operator review, not run by this harness.
    return "\n".join(
        [
            "-- Review before running. Prefer restoring from a full SQL dump when available.",
            "BEGIN;",
            f"-- DELETE canary learning append_events for user {username!r} by event_key/run_id captured in execute manifest.",
            f"-- Restore aggregate tables to counts captured at {before.get('at')}:",
            f"-- daily={before['counts']['daily_earn']} weekly={before['counts']['weekly_earn']} monthly={before['counts']['monthly_earn']}",
            "ROLLBACK;",
        ]
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dsn", default=os.environ.get("FUTURE_PG_DSN", DEFAULT_DSN))
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--user", required=True)
    parser.add_argument("--path", required=True)
    parser.add_argument("--cycles", type=int, default=5)
    parser.add_argument("--password-env", default="FUTURE_TEST_PASSWORD")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--output", default="")
    args = parser.parse_args()

    with psycopg.connect(args.dsn) as connection:
        with connection.cursor() as cursor:
            before = snapshot_user(cursor, args.user, args.path)

    manifest = {
        "generated_at": now_text(),
        "mode": "execute" if args.execute else "dry-run",
        "mutations": 0,
        "base_url": args.base_url,
        "user": args.user,
        "path": args.path,
        "cycles": max(1, int(args.cycles or 1)),
        "before": before,
        "rollback_sql_review_only": rollback_sql(args.user, before),
        "cycle_results": [],
    }

    if not args.execute:
        manifest["status"] = "DRY_RUN_ONLY"
        manifest["next_step"] = "Set password env and rerun with --execute only for an approved canary user/file."
    else:
        password = os.environ.get(args.password_env, "")
        if not password:
            raise RuntimeError(f"Missing password env {args.password_env}; refusing to execute.")
        token = login(args.base_url, args.user, password)
        before_day = leaderboard_user(args.base_url, token, args.user, "day")
        manifest["leaderboard_before_day"] = before_day
        seen_event_ids: set[str] = set()
        for index in range(max(1, int(args.cycles or 1))):
            run_id = f"earn-top-canary-{int(time.time())}-{index}-{hashlib.sha1(os.urandom(8)).hexdigest()[:10]}"
            payload = completion_payload(args.path, run_id)
            status, body = http_json(f"{args.base_url}/lesson/complete", "POST", payload, token=token)
            event_key = str(body.get("event_key") or body.get("eventKey") or "")
            if event_key:
                seen_event_ids.add(event_key)
            day_row = leaderboard_user(args.base_url, token, args.user, "day")
            manifest["cycle_results"].append(
                {
                    "cycle": index + 1,
                    "status": status,
                    "ok": bool(body.get("ok", status == 200)),
                    "event_key": event_key,
                    "recorded": body.get("recorded"),
                    "duplicate": body.get("duplicate"),
                    "leaderboard_day": {
                        "score": day_row.get("score"),
                        "today_words": day_row.get("today_words"),
                        "rank": day_row.get("rank"),
                    },
                }
            )
            time.sleep(0.8)
        manifest["mutations"] = len(manifest["cycle_results"])
        manifest["unique_event_keys"] = len(seen_event_ids)
        with psycopg.connect(args.dsn) as connection:
            with connection.cursor() as cursor:
                manifest["after"] = snapshot_user(cursor, args.user, args.path)
        manifest["status"] = "EXECUTED_REVIEW_REQUIRED"

    text = json.dumps(manifest, ensure_ascii=False, indent=2)
    if args.output:
        Path(args.output).write_text(text + "\n", encoding="utf-8")
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
