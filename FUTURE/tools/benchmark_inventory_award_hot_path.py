"""Benchmark unique inventory awards for hung and restore the exact SQLite document afterward."""

from __future__ import annotations

import argparse
import concurrent.futures
import os
import sqlite3
import statistics
import time
import uuid

import psutil
import requests


DATABASE = r"C:\server data\server2.db"


def server_process() -> psutil.Process:
    for connection in psutil.net_connections(kind="tcp"):
        if connection.laddr and connection.laddr.port == 8877 and connection.status == psutil.CONN_LISTEN and connection.pid:
            return psutil.Process(connection.pid)
    raise RuntimeError("Server 2 listener not found")


def snapshot_inventory() -> tuple[list[str], list[tuple], list[str], list[tuple]]:
    connection = sqlite3.connect(DATABASE)
    item_columns = [row[1] for row in connection.execute("PRAGMA table_info(inventory_items)")]
    event_columns = [row[1] for row in connection.execute("PRAGMA table_info(inventory_events)")]
    item_rows = connection.execute("SELECT * FROM inventory_items WHERE username=?", ("hung",)).fetchall()
    event_rows = connection.execute("SELECT * FROM inventory_events WHERE username=?", ("hung",)).fetchall()
    connection.close()
    if not item_rows:
        raise RuntimeError("hung inventory rows not found")
    return item_columns, item_rows, event_columns, event_rows


def restore_inventory(item_columns, item_rows, event_columns, event_rows) -> None:
    connection = sqlite3.connect(DATABASE, timeout=30)
    connection.execute("BEGIN IMMEDIATE")
    connection.execute("DELETE FROM inventory_events WHERE username=?", ("hung",))
    connection.execute("DELETE FROM inventory_items WHERE username=?", ("hung",))
    connection.executemany(
        f"INSERT INTO inventory_items ({','.join(item_columns)}) VALUES ({','.join('?' for _ in item_columns)})",
        item_rows,
    )
    connection.executemany(
        f"INSERT INTO inventory_events ({','.join(event_columns)}) VALUES ({','.join('?' for _ in event_columns)})",
        event_rows,
    )
    connection.commit()
    connection.close()


def inventory_totals() -> tuple[int, int]:
    connection = sqlite3.connect(DATABASE)
    quantity = connection.execute("SELECT COALESCE(SUM(quantity),0) FROM inventory_items WHERE username=?", ("hung",)).fetchone()[0]
    events = connection.execute("SELECT COUNT(*) FROM inventory_events WHERE username=?", ("hung",)).fetchone()[0]
    connection.close()
    return int(quantity or 0), int(events or 0)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="http://127.0.0.1:8877")
    parser.add_argument("--requests", type=int, default=100)
    parser.add_argument("--workers", type=int, default=20)
    args = parser.parse_args()
    password = os.environ.get("FUTURE_TEST_PASSWORD", "")
    if not password:
        raise RuntimeError("Set FUTURE_TEST_PASSWORD for the active benchmark only")
    item_columns, item_rows, event_columns, event_rows = snapshot_inventory()
    original_quantity, original_events = inventory_totals()
    login = requests.post(f"{args.base}/auth/login", json={"username": "hung", "password": password}, timeout=15)
    login.raise_for_status()
    headers = {"Authorization": f"Bearer {login.json()['token']}", "Content-Type": "application/json"}
    prefix = f"codex-inventory-{uuid.uuid4().hex}"
    process = server_process()
    rows = []
    try:
        before = sum(process.cpu_times()[:2])
        started = time.perf_counter()

        def request_once(index: int):
            request_started = time.perf_counter()
            response = requests.post(
                f"{args.base}/inventory/award?response=delta-v1",
                headers=headers,
                json={
                    "event_id": f"{prefix}-{index}",
                    "quantity": 1,
                    "item": {"id": "prism_crystal", "name": "Prism Crystal", "use": "Benchmark rollback item"},
                },
                timeout=60,
            )
            response.raise_for_status()
            return response.status_code, len(response.content), (time.perf_counter() - request_started) * 1000

        with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
            rows = list(pool.map(request_once, range(max(1, args.requests))))
        wall_ms = (time.perf_counter() - started) * 1000
        cpu_ms = max(0.0, (sum(process.cpu_times()[:2]) - before) * 1000)
        final_quantity, final_events = inventory_totals()
        assert final_quantity - original_quantity == len(rows), (original_quantity, final_quantity, len(rows))
        assert final_events - original_events == len(rows), (original_events, final_events, len(rows))
    finally:
        restore_inventory(item_columns, item_rows, event_columns, event_rows)

    latencies = sorted(row[2] for row in rows)
    print({
        "requests": len(rows),
        "workers": args.workers,
        "server_cpu_ms": round(cpu_ms, 3),
        "cpu_ms_per_request": round(cpu_ms / len(rows), 3),
        "wall_ms": round(wall_ms, 3),
        "p50_ms": round(statistics.median(latencies), 3),
        "p95_ms": round(latencies[max(0, int(len(latencies) * 0.95) - 1)], 3),
        "response_bytes": sum(row[1] for row in rows),
        "quantity_delta": final_quantity - original_quantity,
        "event_delta": final_events - original_events,
        "statuses": {status: sum(1 for row in rows if row[0] == status) for status in sorted({row[0] for row in rows})},
        "sqlite_rows_restored": True,
    })
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
