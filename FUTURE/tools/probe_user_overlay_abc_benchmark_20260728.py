#!/usr/bin/env python3
"""A/B/C benchmark matrix for /server-data/user-overlay and login flow.

Added 2026-07-28 for the final overlay checkpoint. It seeds three isolated
benchmark groups, runs the existing login CPU harness against each group at
1/5/10/25/50/100 concurrency, and cleans up in finally.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import FUTURE.server_app as app
from FUTURE.tools import probe_user_overlay_abc_correctness_20260728 as abc_gate

BENCH_PATH = ROOT / "FUTURE" / "tools" / "benchmark_login_cpu_baseline_20260727.py"
spec = importlib.util.spec_from_file_location("future_login_benchmark", BENCH_PATH)
benchmark = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(benchmark)

BASE = "http://127.0.0.1:18877"
OUT = Path(r"C:\Users\Admin\.codex\plans\server2_user_overlay_opt_20260727\overlay_abc_benchmark_20260728.json")
PREFIX = "codexoverlaybm"
PASSWORD = abc_gate.TEST_PASSWORD


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


def group_users(group: str, count: int = 100) -> list[str]:
    return [f"{PREFIX}{group.lower()}{index:03d}" for index in range(1, count + 1)]


def seed_group(group: str, lessons: list[dict]) -> list[str]:
    users = group_users(group)
    now = utc_now()
    hashed = app.password_hash(PASSWORD)

    def _write(con):
        with con.cursor() as cur:
            for username in users:
                cur.execute(
                    """
                    INSERT INTO future_server2.users(username,is_admin,profile_json,updated_at_utc,updated_epoch,is_test)
                    VALUES(%s,false,%s,%s,extract(epoch from now()),true)
                    ON CONFLICT(username) DO UPDATE SET profile_json=excluded.profile_json, updated_at_utc=excluded.updated_at_utc, is_test=true
                    """,
                    (username, json.dumps({"group": group, "abc_benchmark": True}), now),
                )
                cur.execute(
                    """
                    INSERT INTO future_server2.user_auth_credentials(username,password_hash,source_path,updated_at_utc,updated_epoch)
                    VALUES(%s,%s,'codex-overlay-benchmark',%s,extract(epoch from now()))
                    ON CONFLICT(username) DO UPDATE SET password_hash=excluded.password_hash, updated_at_utc=excluded.updated_at_utc
                    """,
                    (username, hashed, now),
                )
                if group in {"B", "C"}:
                    prog_count = 5 if group == "B" else 12
                    vocab_count = 10 if group == "B" else 120
                    task_count = 1 if group == "B" else 2
                    for idx, lesson in enumerate(lessons[:prog_count]):
                        complete = idx % 3 == 0
                        cur.execute(
                            """
                            INSERT INTO future_server2.lesson_progress(username,space,progress_key,path,identity,file_id,node_index,node_count,learned_count,complete,server_revision,updated_at_utc,updated_epoch,record_json)
                            VALUES(%s,%s,%s,%s,%s,%s,%s,10,%s,%s,1,%s,extract(epoch from now()),%s)
                            """,
                            (
                                username,
                                lesson["space"],
                                f"{PREFIX}-{group.lower()}-{username}-{idx}",
                                lesson["path"],
                                lesson["lesson_id"],
                                lesson["lesson_id"],
                                idx + 1,
                                idx + 1,
                                complete,
                                now,
                                json.dumps({"done": idx + 1, "total": 10, "complete": complete, "group": group}),
                            ),
                        )
                        cur.execute(
                            """
                            INSERT INTO future_server2.lesson_time(username,lesson_key,file_id,path,title,space,seconds,ticks,updated_at_utc,updated_epoch)
                            VALUES(%s,%s,%s,%s,%s,%s,%s,1,%s,extract(epoch from now()))
                            """,
                            (username, lesson["lesson_id"], lesson["lesson_id"], lesson["path"], lesson["title"], lesson["space"], 60 + idx, now),
                        )
                    tasks = []
                    for idx in range(task_count):
                        lesson = lessons[(idx + 1) % len(lessons)]
                        tasks.append({
                            "id": f"{username}-task-{idx}",
                            "path": lesson["path"],
                            "lesson_id": lesson["lesson_id"],
                            "file_id": lesson["lesson_id"],
                            "title": f"{group} Task {idx}",
                            "name": lesson["title"],
                            "creator_role": "user" if idx == 0 else "space_task",
                            "added_by": username,
                            "added_at": now,
                            "severity": "normal",
                        })
                    record = {
                        "tasks": tasks,
                        "space_task": {
                            "preferred_folders": ["/".join(lessons[0]["path"].split("/")[:-1])],
                            "updated_at": now,
                            "updated_by": username,
                            "updated_rev": f"{PREFIX}-{username}-rev1",
                            "assigned": {
                                f"{username}-auto": {"path": lessons[0]["path"], "assigned_at": now}
                            },
                        },
                    }
                    cur.execute(
                        """
                        INSERT INTO future_server2.lesson_task_state(username,record_json,server_revision,updated_at_utc,updated_epoch)
                        VALUES(%s,%s,1,%s,extract(epoch from now()))
                        """,
                        (username, json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":")), now),
                    )
                    for idx in range(vocab_count):
                        cur.execute(
                            """
                            INSERT INTO future_server2.vocabulary_registry(username,word_key,word,meaning,learn_count,last_at_utc,last_epoch,sources_json)
                            VALUES(%s,%s,%s,'benchmark',1,%s,extract(epoch from now()),%s)
                            """,
                            (username, f"{PREFIX}_{group}_{username}_{idx}", f"{group} word {idx}", now, json.dumps([{"path": lessons[idx % len(lessons)]["path"]}])),
                        )
        return users

    return app.postgres_execute(_write)


def run_group(name: str, users: list[str], password: str) -> dict:
    loads = [1, 5, 10, 25, 50, 100]
    result = {"group": name, "users": len(users), "levels": {}}
    server_pid = int(benchmark.wait_health(BASE).get("pid") or benchmark.listener_pid(18877))
    for level in loads:
        accounts = [(username, password) for username in users[:level]]
        phase = benchmark.measure_login_phase(f"{name}_load_{level}", accounts, server_pid, rounds=3, concurrent=True)
        result["levels"][str(level)] = phase
        if phase["errors"] > max(1, int(phase["flows"] * 0.01)):
            result["stop_reason"] = f"errors exceeded threshold at {level}"
            break
        if phase["flow_wall_ms"].get("p95") and phase["flow_wall_ms"]["p95"] > 10000:
            result["stop_reason"] = f"P95 exceeded 10s at {level}"
            break
        if phase["whole_cpu_percent_peak"] > 85:
            result["stop_reason"] = f"whole CPU exceeded 85% at {level}"
            break
    return result


def main() -> int:
    result = {"started_utc": utc_now(), "cleanup_before": cleanup()}
    lessons = abc_gate.pick_common_lessons(12)
    try:
        result["lesson_fixtures"] = lessons[:6]
        groups = {group: seed_group(group, lessons) for group in ("A", "B", "C")}
        result["groups"] = {group: len(users) for group, users in groups.items()}
        result["benchmark"] = {group: run_group(group, users, PASSWORD) for group, users in groups.items()}
        result["pass"] = all(
            result["benchmark"][group]["levels"].get("1", {}).get("errors", 1) == 0
            and result["benchmark"][group]["levels"].get("5", {}).get("errors", 1) == 0
            for group in ("A", "B", "C")
            if "1" in result["benchmark"][group]["levels"] and "5" in result["benchmark"][group]["levels"]
        )
    finally:
        result["cleanup_after"] = cleanup()
        result["finished_utc"] = utc_now()
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"ok": result.get("pass", False), "output": str(OUT)}, ensure_ascii=False))
    return 0 if result.get("pass") else 1


if __name__ == "__main__":
    raise SystemExit(main())
