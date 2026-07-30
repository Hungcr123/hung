#!/usr/bin/env python3
"""Dry-run reconciliation for Server 2 vocabulary Earn/Top PostgreSQL ledgers."""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime
from zoneinfo import ZoneInfo

import psycopg


DEFAULT_USERS = ("hung", "quynh", "vietanh", "ryandepzai", "hungcr")
DEFAULT_DSN = "postgresql://future_server2_app@127.0.0.1:5432/future_server2"
TZ = ZoneInfo("Asia/Ho_Chi_Minh")


def _now_local() -> datetime:
    return datetime.now(TZ)


def _buckets(now: datetime) -> dict[str, str]:
    week_start = now.date()
    week_start = week_start.fromordinal(week_start.toordinal() - week_start.weekday())
    return {
        "day": now.strftime("%Y-%m-%d"),
        "week": week_start.strftime("%Y-%m-%d"),
        "month": now.strftime("%Y-%m"),
    }


def _one(cursor, sql: str, params: tuple = ()) -> int:
    cursor.execute(sql, params)
    row = cursor.fetchone()
    return int(row[0] or 0) if row else 0


def _count_by_space(cursor, username: str) -> dict[str, int]:
    cursor.execute(
        """
        SELECT COALESCE(NULLIF(lower(event_json->>'space_type'), ''), 'unknown') AS space_type, count(*)
        FROM future_server2.append_events
        WHERE stream='learning' AND username=%s
        GROUP BY COALESCE(NULLIF(lower(event_json->>'space_type'), ''), 'unknown')
        ORDER BY 1
        """,
        (username,),
    )
    return {str(row[0]): int(row[1] or 0) for row in cursor.fetchall()}


def reconcile_user(cursor, username: str, buckets: dict[str, str]) -> dict:
    expected_day = _one(
        cursor,
        "SELECT count(DISTINCT word_key) FROM future_server2.vocabulary_events WHERE username=%s AND local_day=%s",
        (username, buckets["day"]),
    )
    expected_week = _one(
        cursor,
        "SELECT count(DISTINCT word_key) FROM future_server2.vocabulary_events WHERE username=%s AND iso_week=%s",
        (username, buckets["week"]),
    )
    expected_month = _one(
        cursor,
        "SELECT count(DISTINCT word_key) FROM future_server2.vocabulary_events WHERE username=%s AND local_month=%s",
        (username, buckets["month"]),
    )
    actual_day = _one(
        cursor,
        "SELECT count(DISTINCT word_key) FROM future_server2.daily_earn WHERE username=%s AND day_key=%s",
        (username, buckets["day"]),
    )
    actual_week = _one(
        cursor,
        "SELECT count(DISTINCT word_key) FROM future_server2.weekly_earn WHERE username=%s AND week_key=%s",
        (username, buckets["week"]),
    )
    actual_month = _one(
        cursor,
        "SELECT count(DISTINCT word_key) FROM future_server2.monthly_earn WHERE username=%s AND month_key=%s",
        (username, buckets["month"]),
    )
    migrated = {}
    sourced = {}
    for scope, table, column in (
        ("day", "daily_earn", "day_key"),
        ("week", "weekly_earn", "week_key"),
        ("month", "monthly_earn", "month_key"),
    ):
        migrated[scope] = _one(
            cursor,
            f"SELECT count(*) FROM future_server2.{table} WHERE username=%s AND {column}=%s AND NULLIF(migrated_at_utc, '') IS NOT NULL",
            (username, buckets[scope]),
        )
        sourced[scope] = _one(
            cursor,
            f"SELECT count(*) FROM future_server2.{table} WHERE username=%s AND {column}=%s AND NULLIF(source_sha256, '') IS NOT NULL",
            (username, buckets[scope]),
        )
    registry_total = _one(
        cursor,
        "SELECT count(DISTINCT word_key) FROM future_server2.vocabulary_registry WHERE username=%s",
        (username,),
    )
    event_total = _one(
        cursor,
        "SELECT count(*) FROM future_server2.vocabulary_events WHERE username=%s",
        (username,),
    )
    completed_progress = _one(
        cursor,
        "SELECT count(*) FROM future_server2.lesson_progress WHERE username=%s AND complete=true",
        (username,),
    )
    lesson_time_seconds = _one(
        cursor,
        "SELECT COALESCE(sum(seconds), 0) FROM future_server2.lesson_time WHERE username=%s",
        (username,),
    )
    actual = {"day": actual_day, "week": actual_week, "month": actual_month, "all_time": registry_total}
    event_expected = {"day": expected_day, "week": expected_week, "month": expected_month, "all_time": registry_total}
    missing_from_period_rows = {key: max(0, event_expected[key] - actual[key]) for key in ("day", "week", "month")}
    historical_not_in_event_ledger = {key: max(0, actual[key] - event_expected[key]) for key in ("day", "week", "month")}
    delta = {key: event_expected[key] - actual[key] for key in ("day", "week", "month")}
    delta["all_time"] = 0
    repair_needed = any(value > 0 for value in missing_from_period_rows.values())
    coverage_note = (
        "period rows are missing source events and can be deterministically upserted"
        if repair_needed
        else (
            "period rows include migrated/source-hash history not represented in vocabulary_events"
            if any(value > 0 for value in historical_not_in_event_ledger.values())
            else "event ledger and period rows match"
        )
    )
    return {
        "user": username,
        "space": "space_v",
        "source_of_truth": "future_server2.vocabulary_events proves new period writes; migrated/source-hash earn rows preserve older period history; vocabulary_registry proves all-time Top",
        "source_event_count": event_total,
        "completion_progress_rows": completed_progress,
        "lesson_time_seconds": lesson_time_seconds,
        "completion_events_by_space": _count_by_space(cursor, username),
        "event_expected": event_expected,
        "actual": actual,
        "delta": delta,
        "missing_from_period_rows": missing_from_period_rows,
        "historical_not_in_event_ledger": historical_not_in_event_ledger,
        "migrated_period_rows": migrated,
        "source_hash_period_rows": sourced,
        "recoverability": "A: deterministic from vocabulary_events" if repair_needed else "none_needed",
        "coverage_note": coverage_note,
        "repair_needed": repair_needed,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dsn", default=os.environ.get("FUTURE_PG_DSN", DEFAULT_DSN))
    parser.add_argument("--users", nargs="*", default=list(DEFAULT_USERS))
    parser.add_argument("--output", default="")
    args = parser.parse_args()

    now = _now_local()
    buckets = _buckets(now)
    users = [user.strip() for user in args.users if user.strip()]
    with psycopg.connect(args.dsn) as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT current_database(), current_user, current_schema()")
            database, db_user, schema = cursor.fetchone()
            rows = [reconcile_user(cursor, user, buckets) for user in users]
    manifest = {
        "generated_at": now.isoformat(timespec="seconds"),
        "timezone": "Asia/Ho_Chi_Minh",
        "period_rules": {
            "day": "local calendar day",
            "week": "Monday local date stored in vocabulary_events.iso_week",
            "month": "local YYYY-MM",
        },
        "database": {"current_database": database, "current_user": db_user, "current_schema": schema},
        "dry_run": True,
        "mutations": 0,
        "buckets": buckets,
        "rows": rows,
        "summary": {
            "users": len(rows),
            "repair_needed_users": sum(1 for row in rows if row["repair_needed"]),
            "total_period_delta": {
                scope: sum(int(row["delta"][scope]) for row in rows)
                for scope in ("day", "week", "month")
            },
            "missing_from_period_rows": {
                scope: sum(int(row["missing_from_period_rows"][scope]) for row in rows)
                for scope in ("day", "week", "month")
            },
            "historical_not_in_event_ledger": {
                scope: sum(int(row["historical_not_in_event_ledger"][scope]) for row in rows)
                for scope in ("day", "week", "month")
            },
        },
    }
    text = json.dumps(manifest, ensure_ascii=False, indent=2)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as handle:
            handle.write(text + "\n")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
