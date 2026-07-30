#!/usr/bin/env python3
"""Measure Space_Q/W/P/L/S completion and Top on a fresh isolated PostgreSQL copy."""

from __future__ import annotations

import json
import os
import secrets
import shutil
import statistics
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

import psutil
import requests

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import FUTURE.tools.test_lesson_complete_isolated_harness as isolated

RUN_ROOT = ROOT / "programe_cache" / "node_space_completion_isolated_18877"
HARNESS_MODE = str(os.environ.get("FUTURE_NODE_HARNESS_MODE") or "manifest").strip().lower()
OUTPUT = Path(rf"C:\Users\Admin\.codex\plans\node_space_completion_ab_{HARNESS_MODE}_20260729.json")
TEST_USER = "codexnodespace"
COLD_USER = "codexcold"
MULTI_USERS = {
    "space_q": "codexnodeq",
    "space_w": "codexnodew",
    "space_p": "codexnodep",
    "space_l": "codexnodel",
    "space_s": "codexnodes",
}
STAGGER_USERS = [f"codexstagger{index:02d}" for index in range(10)]
RANK_USERS = ("codexranka", "codexrankb", "codexrankc")
BATCH_COUNT = 20

LESSONS = {
    "space_q": {
        "path": "common/IELTS Reading/How tennis rackets have changed.Space_Q",
        "lesson_id": "ftg-lesson-000000182",
        "nodes": 544,
    },
    "space_w": {
        "path": "common/Daily Skills 115-125/Writing - Lan's Good Habits.Space_W",
        "lesson_id": "ftg-lesson-000010705",
        "nodes": 10,
    },
    "space_p": {
        "path": "common/Daily Skills 115-125/Reading Paragraph - A Small Bookshop.Space_P",
        "lesson_id": "ftg-lesson-000010706",
        "nodes": 9,
    },
    "space_l": {
        "path": "common/Daily Skills 115-125/Listening Space_L - Nam's Daily Routine.Space_L",
        "lesson_id": "ftg-lesson-000010709",
        "nodes": 9,
    },
    "space_s": {
        "path": "common/Daily Skills 115-125/Speaking Space_S - Successful Student.Space_S",
        "lesson_id": "ftg-lesson-000010710",
        "nodes": 8,
    },
}

RANK_LESSONS = {
    "w1": {
        "path": "common/Study/Empower A1/Space_W/Unit 06/Empower A1 Unit 06 Work_and_routines Space W 21.Space_W",
        "lesson_id": "ftg-lesson-000010407",
        "nodes": 1,
    },
    "w3": {
        "path": "common/Study/Global Success/High school/Grade 10/Space_W/Unit 08/Global Success Grade 10 Unit 08 New_ways_to_learn Space W 19.Space_W",
        "lesson_id": "ftg-lesson-000008369",
        "nodes": 3,
    },
    "w5a": {
        "path": "common/Study/Empower A1/Space_W/Unit 06/Empower A1 Unit 06 Work_and_routines Space W 20.Space_W",
        "lesson_id": "ftg-lesson-000010406",
        "nodes": 5,
    },
    "w5b": {
        "path": "common/Study/Empower A1/Space_W/Unit 06/Empower A1 Unit 06 Work_and_routines Space W 19.Space_W",
        "lesson_id": "ftg-lesson-000010405",
        "nodes": 5,
    },
    "w5c": {
        "path": "common/Study/Empower A1/Space_W/Unit 06/Empower A1 Unit 06 Work_and_routines Space W 11.Space_W",
        "lesson_id": "ftg-lesson-000010397",
        "nodes": 5,
    },
}


def configure() -> None:
    isolated.RUN_ROOT = RUN_ROOT
    isolated.PG_ROOT = RUN_ROOT / "postgres"
    isolated.SERVER_DATA_ROOT = RUN_ROOT / "server-data"
    isolated.RUNTIME_ROOT = RUN_ROOT / "runtime"
    isolated.QMLEARN_ROOT = RUN_ROOT / "qml"
    isolated.SERVER_LOG = RUN_ROOT / "server.log"
    isolated.PG_LOG = RUN_ROOT / "postgres.log"


def wait_ready_only(process) -> dict:
    deadline = time.monotonic() + 120
    while time.monotonic() < deadline:
        try:
            health = requests.get(f"{isolated.BASE}/health", timeout=5).json()
            if int(health.get("pid", 0) or 0) == process.pid and health.get("ready"):
                return health
        except Exception:
            pass
        time.sleep(0.2)
    raise RuntimeError(f"isolated Server 2 not ready: {isolated.SERVER_LOG}")


# Added 2026-07-29: copy only the five real lessons needed by this isolated completion gate.
def copy_lessons() -> None:
    for row in (*LESSONS.values(), *RANK_LESSONS.values()):
        source = Path(r"C:\server data") / row["path"].replace("/", "\\")
        if not source.is_file():
            raise RuntimeError(f"lesson missing: {source}")
        target = isolated.SERVER_DATA_ROOT / row["path"].replace("/", "\\")
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    for name in ("Sound", "Picture", "NPC_TOP"):
        (isolated.SERVER_DATA_ROOT / name).mkdir(parents=True, exist_ok=True)


# Added 2026-07-29: provision one disposable learner only after the production snapshot restore.
def provision_user() -> None:
    import psycopg

    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    with psycopg.connect(isolated.PG_DSN) as connection, connection.cursor() as cursor:
        for username in (TEST_USER, COLD_USER, *MULTI_USERS.values(), *STAGGER_USERS, *RANK_USERS):
            cursor.execute(
                """
                INSERT INTO future_server2.users
                    (username,is_admin,profile_json,updated_at_utc,updated_epoch,is_test,migrated_at_utc,source_sha256)
                VALUES (%s,false,%s,%s,0,true,'','')
                ON CONFLICT(username) DO UPDATE SET is_admin=false,is_test=true,profile_json=excluded.profile_json
                """,
                (username, json.dumps({"load_test": True, "source": "node-space-isolated"}), now),
            )
            cursor.execute(
                """
                INSERT INTO future_server2.user_auth_credentials
                    (username,password_hash,source_path,updated_at_utc,updated_epoch,migrated_at_utc,source_sha256)
                VALUES (%s,%s,'node-space-isolated',%s,0,'','')
                ON CONFLICT(username) DO UPDATE SET password_hash=excluded.password_hash,updated_at_utc=excluded.updated_at_utc
                """,
                (username, isolated.password_hash(isolated.PASSWORD), now),
            )


def login(username: str = TEST_USER) -> str:
    response = requests.post(
        f"{isolated.BASE}/auth/login",
        json={"username": username, "password": isolated.PASSWORD},
        timeout=30,
    )
    response.raise_for_status()
    token = str(response.json().get("token") or "")
    if not token:
        raise RuntimeError("isolated login returned no token")
    return token


def process_cpu_ms(process: psutil.Process) -> float:
    row = process.cpu_times()
    return (row.user + row.system) * 1000.0


def measured_request(process: psutil.Process, method: str, url: str, **kwargs) -> dict:
    server_before = process_cpu_ms(process)
    postgres_before = isolated.postgres_cpu()
    started = time.perf_counter()
    response = requests.request(method, url, timeout=90, **kwargs)
    wall_ms = (time.perf_counter() - started) * 1000.0
    server_after = process_cpu_ms(process)
    postgres_after = isolated.postgres_cpu()
    try:
        payload = response.json()
    except ValueError:
        payload = {"raw": response.text[:500]}
    return {
        "status": response.status_code,
        "wall_ms": round(wall_ms, 3),
        "server_cpu_ms": round(server_after - server_before, 3),
        "postgres_cpu_ms": round(postgres_after - postgres_before, 3),
        "response_bytes": len(response.content),
        "payload": payload,
    }


def completion_body(space_type: str, row: dict, run_id: str) -> dict:
    stamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    return {
        "path": row["path"],
        "lesson_id": row["lesson_id"],
        "file_id": row["lesson_id"],
        "title": Path(row["path"]).stem,
        "name": Path(row["path"]).name,
        "nodes": row["nodes"],
        "completed_at": stamp,
        "completion_run_id": run_id,
        "source": space_type.replace("space_", "Space_").upper(),
        "completion_trace_id": f"node-space-{space_type}-{secrets.token_hex(5)}",
    }


def top_request(process: psutil.Process, token: str, space_type: str) -> dict:
    return measured_request(
        process,
        "GET",
        f"{isolated.BASE}/vocab/leaderboard",
        headers={"Authorization": f"Bearer {token}"},
        params={"limit": 100, "double_check": 0, "scope": "day", "type": space_type},
    )


def postgres_state() -> dict:
    import psycopg

    with psycopg.connect(isolated.PG_DSN) as connection, connection.cursor() as cursor:
        cursor.execute(
            "SELECT count(*) FROM future_server2.lesson_progress WHERE lower(username)=lower(%s)",
            (TEST_USER,),
        )
        progress = int(cursor.fetchone()[0] or 0)
        cursor.execute(
            "SELECT count(*) FROM future_server2.append_events WHERE stream='learning' AND lower(username)=lower(%s)",
            (TEST_USER,),
        )
        events = int(cursor.fetchone()[0] or 0)
        cursor.execute(
            """
            SELECT convert_from(content,'UTF8')::jsonb
            FROM future_server2.documents
            WHERE lower(path) LIKE %s AND lower(path) LIKE %s
            ORDER BY updated_epoch DESC
            LIMIT 1
            """,
            (f"%{TEST_USER.lower()}%", "%_future_learning_summary.json"),
        )
        summary_row = cursor.fetchone()
        summary = dict(summary_row[0]) if summary_row and isinstance(summary_row[0], dict) else {}
        return {"progress_rows": progress, "learning_events": events, "learning_summary": summary}


def top_user_row(payload: dict, username: str = TEST_USER) -> dict | None:
    boards = payload.get("boards") if isinstance(payload.get("boards"), dict) else {}
    rows = boards.get("day") if isinstance(boards.get("day"), list) else []
    return next(
        (row for row in rows if isinstance(row, dict) and str(row.get("username", "")).lower() == username.lower()),
        None,
    )


def main() -> int:
    configure()
    if any(
        connection.laddr and connection.laddr.port == isolated.HTTP_PORT and connection.status == psutil.CONN_LISTEN
        for connection in psutil.net_connections(kind="tcp")
    ):
        raise RuntimeError("port 18877 is already in use")
    shutil.rmtree(RUN_ROOT, ignore_errors=True)
    RUN_ROOT.mkdir(parents=True, exist_ok=True)
    server = None
    try:
        copy_lessons()
        isolated.start_postgres()
        dump_path = isolated.sync_production_database_snapshot()
        provision_user()
        server = isolated.start_server(
            fail_prefix="node-fail-",
            no_preload=False,
            extra_env={"FUTURE_TEST_NODE_COMPLETION_FORCE_FILE_DECODE": "1" if HARNESS_MODE == "decode" else "0"},
        )
        cold_health = wait_ready_only(server)
        cold_process = psutil.Process(int(cold_health["pid"]))
        cold_token = login(COLD_USER)
        cold_body = completion_body("space_q", LESSONS["space_q"], f"node-cold-{secrets.token_hex(8)}")
        cold_completion = measured_request(
            cold_process,
            "POST",
            f"{isolated.BASE}/lesson/complete",
            headers={"Authorization": f"Bearer {cold_token}"},
            json=cold_body,
        )
        cold_top = top_request(cold_process, cold_token, "space_q")
        cold_top_row = top_user_row(cold_top.get("payload") or {}, COLD_USER)
        health = isolated.wait_health(server)
        time.sleep(5.0)
        token = login()
        multi_tokens = {space_type: login(username) for space_type, username in MULTI_USERS.items()}
        stagger_tokens = {username: login(username) for username in STAGGER_USERS}
        rank_tokens = {username: login(username) for username in RANK_USERS}
        process = psutil.Process(int(health["pid"]))
        spaces = {}
        for space_type, row in LESSONS.items():
            run_id = f"node-space-{space_type}-{secrets.token_hex(6)}"
            body = completion_body(space_type, row, run_id)
            first = measured_request(
                process,
                "POST",
                f"{isolated.BASE}/lesson/complete",
                headers={"Authorization": f"Bearer {token}"},
                json=body,
            )
            top = top_request(process, token, space_type)
            retry = measured_request(
                process,
                "POST",
                f"{isolated.BASE}/lesson/complete",
                headers={"Authorization": f"Bearer {token}"},
                json=body,
            )
            warm_top = [top_request(process, token, space_type) for _ in range(10)]
            row_payload = top_user_row(top.get("payload") or {})
            spaces[space_type] = {
                "lesson": row,
                "completion": first,
                "top": {**top, "user_row": row_payload},
                "retry": retry,
                "warm_top": {
                    "wall_mean_ms": round(statistics.mean(item["wall_ms"] for item in warm_top), 3),
                    "wall_p95_ms": round(sorted(item["wall_ms"] for item in warm_top)[-1], 3),
                    "server_cpu_total_ms": round(sum(item["server_cpu_ms"] for item in warm_top), 3),
                    "postgres_cpu_total_ms": round(sum(item["postgres_cpu_ms"] for item in warm_top), 3),
                    "response_bytes": warm_top[-1]["response_bytes"],
                },
            }
        multi_bodies = {
            space_type: completion_body(space_type, LESSONS[space_type], f"node-multi-{space_type}-{secrets.token_hex(6)}")
            for space_type in LESSONS
        }
        multi_server_cpu_before = process_cpu_ms(process)
        multi_postgres_cpu_before = isolated.postgres_cpu()
        multi_started = time.perf_counter()
        multi_results = {}
        with ThreadPoolExecutor(max_workers=len(LESSONS)) as executor:
            futures = {
                executor.submit(
                    measured_request,
                    process,
                    "POST",
                    f"{isolated.BASE}/lesson/complete",
                    headers={"Authorization": f"Bearer {multi_tokens[space_type]}"},
                    json=body,
                ): space_type
                for space_type, body in multi_bodies.items()
            }
            for future in as_completed(futures):
                multi_results[futures[future]] = future.result()
        multi_wall_ms = round((time.perf_counter() - multi_started) * 1000.0, 3)
        multi_top = {space_type: top_request(process, token, space_type) for space_type in LESSONS}
        multi_top_rows = {
            space_type: top_user_row((multi_top[space_type].get("payload") or {}), MULTI_USERS[space_type])
            for space_type in LESSONS
        }
        multi_concurrent = {
            "wall_ms": multi_wall_ms,
            "server_cpu_ms": round(process_cpu_ms(process) - multi_server_cpu_before, 3),
            "postgres_cpu_ms": round(isolated.postgres_cpu() - multi_postgres_cpu_before, 3),
            "sum_individual_wall_ms": round(sum(row["wall_ms"] for row in multi_results.values()), 3),
            "max_individual_wall_ms": round(max(row["wall_ms"] for row in multi_results.values()), 3),
            "results": multi_results,
            "top_rows": multi_top_rows,
        }

        # Added 2026-07-29: model a classroom where completions arrive in uneven
        # bursts instead of one perfectly simultaneous synthetic batch.
        stagger_delays_ms = [0, 100, 180, 270, 390, 520, 680, 850, 1050, 1300]

        def stagger_completion(username: str, delay_ms: int) -> dict:
            time.sleep(delay_ms / 1000.0)
            return measured_request(
                process,
                "POST",
                f"{isolated.BASE}/lesson/complete",
                headers={"Authorization": f"Bearer {stagger_tokens[username]}"},
                json=completion_body("space_w", LESSONS["space_w"], f"node-stagger-{username}-{secrets.token_hex(5)}"),
            )

        stagger_server_cpu_before = process_cpu_ms(process)
        stagger_postgres_cpu_before = isolated.postgres_cpu()
        stagger_started = time.perf_counter()
        stagger_results = {}
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = {
                executor.submit(stagger_completion, username, delay_ms): username
                for username, delay_ms in zip(STAGGER_USERS, stagger_delays_ms)
            }
            for future in as_completed(futures):
                stagger_results[futures[future]] = future.result()
        stagger_walls = sorted(float(row["wall_ms"]) for row in stagger_results.values())

        def stagger_percentile(fraction: float) -> float:
            index = max(0, min(len(stagger_walls) - 1, int((len(stagger_walls) * fraction) + 0.999999) - 1))
            return stagger_walls[index]

        stagger_top = top_request(process, token, "space_w")
        stagger_top_rows = {username: top_user_row(stagger_top.get("payload") or {}, username) for username in STAGGER_USERS}
        staggered = {
            "users": len(STAGGER_USERS),
            "delays_ms": stagger_delays_ms,
            "wall_ms": round((time.perf_counter() - stagger_started) * 1000.0, 3),
            "request_wall_ms": {
                "p50": round(stagger_percentile(0.50), 3),
                "p95": round(stagger_percentile(0.95), 3),
                "p99": round(stagger_percentile(0.99), 3),
                "max": round(max(stagger_walls), 3),
            },
            "server_cpu_ms": round(process_cpu_ms(process) - stagger_server_cpu_before, 3),
            "postgres_cpu_ms": round(isolated.postgres_cpu() - stagger_postgres_cpu_before, 3),
            "errors": sum(row["status"] != 200 for row in stagger_results.values()),
            "sql_round_trips": sorted(set((row.get("payload") or {}).get("postgres_delta", {}).get("sql_round_trips") for row in stagger_results.values())),
            "transactions": sorted(set((row.get("payload") or {}).get("postgres_delta", {}).get("transactions") for row in stagger_results.values())),
            "top_scores": {username: int((row or {}).get("score", 0) or 0) for username, row in stagger_top_rows.items()},
        }

        # Added 2026-07-29: verify real rank overtakes, not only stable scores.
        rank_a, rank_b, rank_c = RANK_USERS
        rank_steps = []

        def rank_complete(username: str, lesson_key: str) -> None:
            completion = measured_request(
                process,
                "POST",
                f"{isolated.BASE}/lesson/complete",
                headers={"Authorization": f"Bearer {rank_tokens[username]}"},
                json=completion_body("space_w", RANK_LESSONS[lesson_key], f"node-rank-{username}-{lesson_key}-{secrets.token_hex(5)}"),
            )
            top = top_request(process, rank_tokens[username], "space_w")
            rank_steps.append({
                "user": username,
                "lesson": lesson_key,
                "completion_status": completion["status"],
                "completion_wall_ms": completion["wall_ms"],
                "rows": {
                    target: top_user_row(top.get("payload") or {}, target)
                    for target in RANK_USERS
                },
            })

        rank_complete(rank_a, "w1")
        rank_complete(rank_b, "w3")
        rank_complete(rank_a, "w5a")
        rank_complete(rank_c, "w5b")
        rank_complete(rank_c, "w5c")
        rank_complete(rank_b, "w5a")
        rank_complete(rank_b, "w5b")
        rank_final_rows = rank_steps[-1]["rows"]
        rank_volatility = {
            "steps": rank_steps,
            "final_scores": {username: int((rank_final_rows.get(username) or {}).get("score", 0) or 0) for username in RANK_USERS},
            "final_ranks": {username: int((rank_final_rows.get(username) or {}).get("rank", 0) or 0) for username in RANK_USERS},
        }
        new_run_body = completion_body("space_q", LESSONS["space_q"], f"node-new-run-{secrets.token_hex(6)}")
        new_run = measured_request(
            process,
            "POST",
            f"{isolated.BASE}/lesson/complete",
            headers={"Authorization": f"Bearer {token}"},
            json=new_run_body,
        )
        new_run_top = top_request(process, token, "space_q")
        concurrent_bodies = {
            space_type: completion_body(space_type, row, f"node-concurrent-{space_type}-{secrets.token_hex(6)}")
            for space_type, row in LESSONS.items()
        }
        concurrent_server_cpu_before = process_cpu_ms(process)
        concurrent_postgres_cpu_before = isolated.postgres_cpu()
        concurrent_started = time.perf_counter()
        concurrent_results = {}
        with ThreadPoolExecutor(max_workers=len(LESSONS)) as executor:
            futures = {
                executor.submit(
                    measured_request,
                    process,
                    "POST",
                    f"{isolated.BASE}/lesson/complete",
                    headers={"Authorization": f"Bearer {token}"},
                    json=body,
                ): space_type
                for space_type, body in concurrent_bodies.items()
            }
            for future in as_completed(futures):
                concurrent_results[futures[future]] = future.result()
        concurrent_wall_ms = round((time.perf_counter() - concurrent_started) * 1000.0, 3)
        concurrent_server_cpu_ms = round(process_cpu_ms(process) - concurrent_server_cpu_before, 3)
        concurrent_postgres_cpu_ms = round(isolated.postgres_cpu() - concurrent_postgres_cpu_before, 3)
        batch_results = {}
        batch_started_all = time.perf_counter()
        batch_server_cpu_before = process_cpu_ms(process)
        batch_postgres_cpu_before = isolated.postgres_cpu()
        for space_type, row in LESSONS.items():
            samples = []
            for _index in range(BATCH_COUNT):
                sample = measured_request(
                    process,
                    "POST",
                    f"{isolated.BASE}/lesson/complete",
                    headers={"Authorization": f"Bearer {token}"},
                    json=completion_body(space_type, row, f"node-batch-{space_type}-{secrets.token_hex(8)}"),
                )
                payload = sample.get("payload") or {}
                pg = payload.get("postgres_delta") or {}
                samples.append({
                    "status": sample["status"],
                    "wall_ms": sample["wall_ms"],
                    "server_cpu_ms": sample["server_cpu_ms"],
                    "postgres_cpu_ms": sample["postgres_cpu_ms"],
                    "response_bytes": sample["response_bytes"],
                    "sql_round_trips": pg.get("sql_round_trips"),
                    "transactions": pg.get("transactions"),
                    "structural_source": payload.get("structural_source", ""),
                })
            walls = sorted(float(item["wall_ms"]) for item in samples)

            def percentile(fraction: float) -> float:
                index = max(0, min(len(walls) - 1, int((len(walls) * fraction) + 0.999999) - 1))
                return walls[index]

            batch_results[space_type] = {
                "count": len(samples),
                "errors": sum(item["status"] != 200 for item in samples),
                "wall_ms": {
                    "min": round(min(walls), 3),
                    "mean": round(statistics.mean(walls), 3),
                    "p50": round(percentile(0.50), 3),
                    "p95": round(percentile(0.95), 3),
                    "p99": round(percentile(0.99), 3),
                    "max": round(max(walls), 3),
                },
                "server_cpu_total_ms": round(sum(float(item["server_cpu_ms"]) for item in samples), 3),
                "postgres_cpu_total_ms": round(sum(float(item["postgres_cpu_ms"]) for item in samples), 3),
                "sql_round_trips": sorted(set(item["sql_round_trips"] for item in samples)),
                "transactions": sorted(set(item["transactions"] for item in samples)),
                "response_bytes": sorted(set(item["response_bytes"] for item in samples)),
                "structural_sources": sorted(set(item["structural_source"] for item in samples)),
            }
        batch_measurements = {
            "count_per_space": BATCH_COUNT,
            "total_requests": len(LESSONS) * BATCH_COUNT,
            "total_wall_ms": round((time.perf_counter() - batch_started_all) * 1000.0, 3),
            "server_cpu_total_ms": round(process_cpu_ms(process) - batch_server_cpu_before, 3),
            "postgres_cpu_total_ms": round(isolated.postgres_cpu() - batch_postgres_cpu_before, 3),
            "spaces": batch_results,
        }
        failed_body = completion_body("space_w", LESSONS["space_w"], f"node-fail-{secrets.token_hex(6)}")
        failed_completion = measured_request(
            process,
            "POST",
            f"{isolated.BASE}/lesson/complete",
            headers={"Authorization": f"Bearer {token}"},
            json=failed_body,
        )
        state_before_restart = postgres_state()
        server_cpu_before_idle = process_cpu_ms(process)
        postgres_cpu_before_idle = isolated.postgres_cpu()
        time.sleep(5)
        idle = {
            "server_cpu_ms": round(process_cpu_ms(process) - server_cpu_before_idle, 3),
            "postgres_cpu_ms": round(isolated.postgres_cpu() - postgres_cpu_before_idle, 3),
        }
        isolated.stop_server(server)
        server = isolated.start_server(
            no_preload=False,
            extra_env={"FUTURE_TEST_NODE_COMPLETION_FORCE_FILE_DECODE": "1" if HARNESS_MODE == "decode" else "0"},
        )
        restart_health = isolated.wait_health(server)
        time.sleep(3.0)
        restart_token = login()
        restart_process = psutil.Process(int(restart_health["pid"]))
        restart_top = {
            space_type: top_request(restart_process, restart_token, space_type)
            for space_type in LESSONS
        }
        state_after_failure_restart = postgres_state()
        failed_retry = measured_request(
            restart_process,
            "POST",
            f"{isolated.BASE}/lesson/complete",
            headers={"Authorization": f"Bearer {restart_token}"},
            json=failed_body,
        )
        failed_retry_top = top_request(restart_process, restart_token, "space_w")
        state_after_restart = postgres_state()
        gates = {}
        for space_type, row in spaces.items():
            completion_payload = row["completion"].get("payload") or {}
            retry_payload = row["retry"].get("payload") or {}
            restart_row = top_user_row((restart_top[space_type].get("payload") or {}))
            gates[space_type] = {
                "completion_200": row["completion"]["status"] == 200,
                "completion_confirmed": bool(completion_payload.get("completion_confirmed")),
                "top_contains_user": isinstance(row["top"].get("user_row"), dict),
                "top_score_matches": int((row["top"].get("user_row") or {}).get("score", 0) or 0) == int(row["lesson"]["nodes"]),
                "retry_deduplicated": row["retry"]["status"] == 200 and bool(retry_payload.get("deduplicated")),
                "restart_top_contains_user": isinstance(restart_row, dict),
                "restart_top_score_matches": int((restart_row or {}).get("score", 0) or 0) == int(row["lesson"]["nodes"]),
            }
        new_run_learning = (new_run.get("payload") or {}).get("learning_stats") or {}
        new_run_row = top_user_row(new_run_top.get("payload") or {})
        concurrent_learning_runs = sorted(
            int(((row.get("payload") or {}).get("learning_stats") or {}).get("completed_runs", 0) or 0)
            for row in concurrent_results.values()
        )
        expected_before_failed_retry_events = len(LESSONS) + 1 + len(LESSONS) + (len(LESSONS) * BATCH_COUNT)
        expected_after_failed_retry_events = expected_before_failed_retry_events + 1
        expected_batch_sources = {
            space_type: (["manifest"] if HARNESS_MODE == "manifest" else (["legacy-synthetic"] if space_type == "space_w" else ["lesson-file"]))
            for space_type in LESSONS
        }
        accuracy_gates = {
            "cold_completion_200": cold_completion["status"] == 200,
            "cold_top_contains_user": isinstance(cold_top_row, dict),
            "cold_top_score_exact": int((cold_top_row or {}).get("score", 0) or 0) == LESSONS["space_q"]["nodes"],
            "new_run_200": new_run["status"] == 200,
            "new_run_total_files_stable": int(new_run_learning.get("total_files", 0) or 0) == len(LESSONS),
            "new_run_completed_runs_incremented": int(new_run_learning.get("completed_runs", 0) or 0) == len(LESSONS) + 1,
            "new_run_top_not_double_counted": int((new_run_row or {}).get("score", 0) or 0) == LESSONS["space_q"]["nodes"],
            "concurrent_all_200": all(row["status"] == 200 for row in concurrent_results.values()),
            "concurrent_all_confirmed": all(bool((row.get("payload") or {}).get("completion_confirmed")) for row in concurrent_results.values()),
            "concurrent_summary_reached_all_runs": bool(concurrent_learning_runs) and concurrent_learning_runs[-1] == (len(LESSONS) * 2) + 1,
            "multi_user_all_200": all(row["status"] == 200 for row in multi_results.values()),
            "multi_user_all_summaries_exact": all(
                int(((row.get("payload") or {}).get("learning_stats") or {}).get("total_files", 0) or 0) == 1
                and int(((row.get("payload") or {}).get("learning_stats") or {}).get("completed_runs", 0) or 0) == 1
                for row in multi_results.values()
            ),
            "multi_user_all_top_scores_exact": all(
                int((multi_top_rows.get(space_type) or {}).get("score", 0) or 0) == LESSONS[space_type]["nodes"]
                for space_type in LESSONS
            ),
            "staggered_all_200": staggered["errors"] == 0,
            "staggered_top_scores_exact": all(score == LESSONS["space_w"]["nodes"] for score in staggered["top_scores"].values()),
            "rank_all_200": all(step["completion_status"] == 200 for step in rank_steps),
            "rank_b_overtook_a": int((rank_steps[1]["rows"].get(rank_b) or {}).get("rank", 0) or 0) < int((rank_steps[1]["rows"].get(rank_a) or {}).get("rank", 0) or 0),
            "rank_a_overtook_b": int((rank_steps[2]["rows"].get(rank_a) or {}).get("rank", 0) or 0) < int((rank_steps[2]["rows"].get(rank_b) or {}).get("rank", 0) or 0),
            "rank_c_overtook_a": int((rank_steps[4]["rows"].get(rank_c) or {}).get("rank", 0) or 0) < int((rank_steps[4]["rows"].get(rank_a) or {}).get("rank", 0) or 0),
            "rank_b_final_overtake": int((rank_final_rows.get(rank_b) or {}).get("rank", 0) or 0) < int((rank_final_rows.get(rank_c) or {}).get("rank", 0) or 0),
            "rank_final_scores_exact": rank_volatility["final_scores"] == {rank_a: 6, rank_b: 13, rank_c: 10},
            "batch_all_200": all(item["errors"] == 0 for item in batch_results.values()),
            "batch_structural_source_exact": all(batch_results[space_type]["structural_sources"] == expected_batch_sources[space_type] for space_type in LESSONS),
            "failure_injected": failed_completion["status"] == 400 and "Injected completion failure" in str((failed_completion.get("payload") or {}).get("error", "")),
            "failed_core_transaction_rolled_back": int(state_after_failure_restart.get("learning_events", 0) or 0) == expected_before_failed_retry_events,
            "failure_kept_single_progress_row_per_lesson": int(state_after_restart.get("progress_rows", 0) or 0) == len(LESSONS),
            "retry_after_failure_succeeded": failed_retry["status"] == 200 and bool((failed_retry.get("payload") or {}).get("completion_confirmed")),
            "retry_after_failure_persisted_once": int(state_after_restart.get("learning_events", 0) or 0) == expected_after_failed_retry_events,
            "retry_after_failure_top_not_double_counted": int((top_user_row(failed_retry_top.get("payload") or {}) or {}).get("score", 0) or 0) == LESSONS["space_w"]["nodes"],
            "durable_summary_total_files_exact": int((state_after_restart.get("learning_summary") or {}).get("total_files", 0) or 0) == len(LESSONS),
            "durable_summary_completed_runs_exact": int((state_after_restart.get("learning_summary") or {}).get("completed_runs", 0) or 0) == expected_after_failed_retry_events,
        }
        output = {
            "database_sync": {
                "enabled": True,
                "source": "127.0.0.1:5432/future_server2",
                "method": "fresh pg_dump + pg_restore before run",
                "dump_bytes": dump_path.stat().st_size,
            },
            "resources": {
                "http_port": isolated.HTTP_PORT,
                "postgres_port": isolated.PG_PORT,
                "database": isolated.TEST_DATABASE,
                "server_data_root": str(isolated.SERVER_DATA_ROOT),
            },
            "health": health,
            "cold": {"health_at_ready": cold_health, "completion": cold_completion, "top": {**cold_top, "user_row": cold_top_row}},
            "mode": HARNESS_MODE,
            "spaces": spaces,
            "new_run": {"completion": new_run, "top": new_run_top},
            "multi_user_concurrent": multi_concurrent,
            "staggered": staggered,
            "rank_volatility": rank_volatility,
            "batch": batch_measurements,
            "concurrent": {
                "wall_ms": concurrent_wall_ms,
                "server_cpu_ms": concurrent_server_cpu_ms,
                "postgres_cpu_ms": concurrent_postgres_cpu_ms,
                "sum_individual_wall_ms": round(sum(row["wall_ms"] for row in concurrent_results.values()), 3),
                "max_individual_wall_ms": round(max(row["wall_ms"] for row in concurrent_results.values()), 3),
                "results": concurrent_results,
                "learning_runs_seen": concurrent_learning_runs,
            },
            "failed_completion": failed_completion,
            "state_after_failure_restart": state_after_failure_restart,
            "failed_retry": {"completion": failed_retry, "top": failed_retry_top},
            "postgres_before_restart": state_before_restart,
            "idle_5s": idle,
            "restart_health": restart_health,
            "restart_top": restart_top,
            "postgres_after_restart": state_after_restart,
            "gates": gates,
            "accuracy_gates": accuracy_gates,
        }
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps({
            "database_sync": output["database_sync"],
            "mode": HARNESS_MODE,
            "measurements": {
                key: {
                    "completion_wall_ms": value["completion"]["wall_ms"],
                    "completion_server_cpu_ms": value["completion"]["server_cpu_ms"],
                    "completion_postgres_cpu_ms": value["completion"]["postgres_cpu_ms"],
                    "sql_count": ((value["completion"].get("payload") or {}).get("postgres_delta") or {}).get("sql_round_trips"),
                    "top_wall_ms": value["top"]["wall_ms"],
                    "warm_top_mean_ms": value["warm_top"]["wall_mean_ms"],
                }
                for key, value in spaces.items()
            },
            "postgres": state_after_restart,
            "concurrent": output["concurrent"],
            "multi_user_concurrent": output["multi_user_concurrent"],
            "staggered": output["staggered"],
            "rank_volatility": output["rank_volatility"],
            "batch": output["batch"],
            "idle_5s": idle,
            "gates": gates,
            "accuracy_gates": accuracy_gates,
        }, indent=2))
        if not all(all(values.values()) for values in gates.values()) or not all(accuracy_gates.values()):
            raise RuntimeError(f"node-space completion gate failed: {gates} accuracy={accuracy_gates}")
        return 0
    finally:
        isolated.stop_server(server)
        isolated.stop_postgres()
        shutil.rmtree(RUN_ROOT, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
