"""Regression checks for lossless inventory tables and atomic award deltas."""

from __future__ import annotations

import ast
import concurrent.futures
import json
import sqlite3
import tempfile
import threading
from pathlib import Path


DATABASE = Path(r"C:\server data\server2.db")
BASELINE = Path(r"E:\FutureServer2LegacyBackup\2026-07-20_113623_inventory_sqlite_delta\server2.db")
SOURCE = Path(__file__).parents[1] / "server_parts" / "06a_server_database.py"


def load_inventory_award_function(database: Path):
    tree = ast.parse(SOURCE.read_text(encoding="utf-8"), filename=str(SOURCE))
    wanted = {
        "server_database_inventory_item_row",
        "server_database_inventory_cached_retry",
        "server_database_inventory_finish_flight",
        "server_database_award_inventory_items",
    }
    nodes = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in wanted]

    def clean(value) -> str:
        return str(value or "").strip()

    submit_count = [0]

    def submit_write(callback):
        submit_count[0] += 1
        connection = sqlite3.connect(database, timeout=30, isolation_level=None)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA busy_timeout=30000")
        connection.execute("PRAGMA synchronous=FULL")
        try:
            connection.execute("BEGIN IMMEDIATE")
            result = callback(connection)
            connection.execute("COMMIT")
            return result
        except Exception:
            connection.execute("ROLLBACK")
            raise
        finally:
            connection.close()

    namespace = {
        "sqlite3": sqlite3,
        "threading": threading,
        "clean": clean,
        "space_w_int": lambda value, fallback=0: int(value if value is not None else fallback),
        "normalize_username": lambda value: clean(value).lower(),
        "utc_timestamp": lambda: "2026-07-20T02:50:00Z",
        "server_database_ensure_user": lambda connection, username: connection.execute(
            "INSERT OR IGNORE INTO users(username) VALUES(?)", (username,)
        ),
        "server_database_submit_write": submit_write,
        "SERVER_DATABASE_CHANGE_GENERATIONS": {"inventory": 0},
        "server_database_bump_user_generation": lambda *_args: None,
        "SERVER_DATABASE_INVENTORY_RAM_CACHE_LOCK": threading.RLock(),
        "SERVER_DATABASE_INVENTORY_RAM_CACHE": {},
        "SERVER_DATABASE_INVENTORY_EVENT_SHARD_COUNT": 64,
        "SERVER_DATABASE_INVENTORY_EVENT_LOCKS": tuple(threading.RLock() for _index in range(64)),
        "SERVER_DATABASE_INVENTORY_EVENT_RAM": tuple({} for _index in range(64)),
        "SERVER_DATABASE_INVENTORY_EVENT_FLIGHTS": tuple({} for _index in range(64)),
        "SERVER_DATABASE_INVENTORY_EVENT_RAM_MAX": 50_000,
        "_submit_count": submit_count,
    }
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(SOURCE), "exec"), namespace)
    return namespace, namespace["server_database_award_inventory_items"]


def test_atomic_awards() -> None:
    with tempfile.TemporaryDirectory(prefix="future-inventory-") as temp:
        database = Path(temp) / "inventory.db"
        connection = sqlite3.connect(database)
        connection.executescript(
            """
            PRAGMA journal_mode=WAL;
            PRAGMA synchronous=FULL;
            CREATE TABLE users (username TEXT PRIMARY KEY COLLATE NOCASE);
            CREATE TABLE inventory_items (
                username TEXT NOT NULL COLLATE NOCASE,
                item_id TEXT NOT NULL,
                name TEXT NOT NULL DEFAULT '',
                use_text TEXT NOT NULL DEFAULT '',
                quantity INTEGER NOT NULL DEFAULT 0,
                updated_at_utc TEXT NOT NULL,
                PRIMARY KEY (username, item_id),
                FOREIGN KEY (username) REFERENCES users(username) ON DELETE CASCADE
            );
            CREATE TABLE inventory_events (
                username TEXT NOT NULL COLLATE NOCASE,
                event_id TEXT NOT NULL,
                item_id TEXT NOT NULL DEFAULT '',
                quantity INTEGER NOT NULL DEFAULT 0,
                awarded_at_utc TEXT NOT NULL,
                PRIMARY KEY (username, event_id),
                FOREIGN KEY (username) REFERENCES users(username) ON DELETE CASCADE
            );
            INSERT INTO users(username) VALUES('codex_inventory');
            """
        )
        connection.close()
        namespace, award = load_inventory_award_function(database)

        duplicate = {
            "event_id": "same-event",
            "quantity": 1,
            "item": {"id": "gold", "name": "Gold", "use": "Atomic duplicate test"},
        }
        submit_before = namespace["_submit_count"][0]
        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as pool:
            duplicate_results = list(pool.map(lambda _index: award("codex_inventory", [duplicate]), range(100)))
        assert sum(bool(result["results"][0]["awarded"]) for result in duplicate_results) == 1
        assert namespace["_submit_count"][0] - submit_before == 1
        conflict_before = namespace["_submit_count"][0]
        conflict = award(
            "codex_inventory",
            [{"event_id": "same-event", "quantity": 2, "item": {"id": "diamond", "name": "Diamond", "use": "Conflict"}}],
        )
        assert conflict["results"][0]["awarded"] is False
        assert conflict["results"][0]["item"]["id"] == "gold"
        assert namespace["_submit_count"][0] - conflict_before == 1
        exact_retry_before = namespace["_submit_count"][0]
        assert award("codex_inventory", [duplicate])["results"][0]["awarded"] is False
        assert namespace["_submit_count"][0] == exact_retry_before

        workloads = (("gold", 50), ("diamond", 20), ("ticket", 30))
        rows = [
            {
                "event_id": f"{item_id}-{index}",
                "quantity": 1,
                "item": {"id": item_id, "name": item_id.title(), "use": "Parallel item test"},
            }
            for item_id, count in workloads
            for index in range(count)
        ]
        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as pool:
            list(pool.map(lambda payload: award("codex_inventory", [payload]), rows))

        connection = sqlite3.connect(database)
        quantities = dict(
            connection.execute(
                "SELECT item_id,quantity FROM inventory_items WHERE username='codex_inventory'"
            ).fetchall()
        )
        assert quantities == {"diamond": 20, "gold": 51, "ticket": 30}, quantities
        assert connection.execute(
            "SELECT COUNT(*) FROM inventory_events WHERE username='codex_inventory'"
        ).fetchone()[0] == 101
        connection.execute(
            "CREATE TRIGGER fail_inventory_item BEFORE INSERT ON inventory_items "
            "WHEN NEW.item_id='rollback_item' BEGIN SELECT RAISE(ABORT, 'forced rollback'); END"
        )
        connection.commit()
        connection.close()

        try:
            award(
                "codex_inventory",
                [{
                    "event_id": "rollback-event",
                    "quantity": 1,
                    "item": {"id": "rollback_item", "name": "Rollback", "use": "Forced failure"},
                }],
            )
            raise AssertionError("forced inventory failure did not propagate")
        except sqlite3.IntegrityError:
            pass

        connection = sqlite3.connect(database)
        assert connection.execute(
            "SELECT COUNT(*) FROM inventory_events WHERE event_id='rollback-event'"
        ).fetchone()[0] == 0
        assert connection.execute(
            "SELECT COUNT(*) FROM inventory_items WHERE item_id='rollback_item'"
        ).fetchone()[0] == 0
        connection.close()


def main() -> int:
    test_atomic_awards()
    baseline = sqlite3.connect(BASELINE)
    documents = baseline.execute(
        "SELECT path,content FROM documents WHERE lower(path) LIKE ?",
        ("%_future_inventory.json",),
    ).fetchall()
    baseline.close()
    expected_items = {}
    expected_events = set()
    for path, content in documents:
        username = Path(path).parent.name.lower()
        payload = json.loads(bytes(content).decode("utf-8"))
        for item_key, item in (payload.get("items") or {}).items():
            expected_items[(username, str(item.get("id") or item_key))] = int(item.get("quantity", 0) or 0)
        expected_events.update((username, str(event_id)) for event_id in (payload.get("events") or []))

    connection = sqlite3.connect(DATABASE, timeout=30)
    marker = connection.execute("SELECT value FROM database_meta WHERE key='inventory_tables_v1'").fetchone()
    legacy_documents = connection.execute(
        "SELECT COUNT(*) FROM documents WHERE lower(path) LIKE ?",
        ("%_future_inventory.json",),
    ).fetchone()[0]
    actual_items = {(u.lower(), item_id): int(quantity) for u, item_id, quantity in connection.execute("SELECT username,item_id,quantity FROM inventory_items")}
    actual_events = {(u.lower(), event_id) for u, event_id in connection.execute("SELECT username,event_id FROM inventory_events")}
    assert marker and legacy_documents == 0
    # The migration baseline is a lower bound; users may legitimately earn more after conversion.
    assert all(int(actual_items.get(key, -1)) >= quantity for key, quantity in expected_items.items())
    assert expected_events <= actual_events

    existing_user, existing_event = next(iter(actual_events))
    try:
        connection.execute("BEGIN IMMEDIATE")
        cursor = connection.execute(
            "INSERT OR IGNORE INTO inventory_events(username,event_id,item_id,quantity,awarded_at_utc) VALUES(?,?,?,?,?)",
            (existing_user, existing_event, "", 0, "2026-07-20T02:50:00Z"),
        )
        assert int(cursor.rowcount or 0) == 0
    finally:
        connection.execute("ROLLBACK")
        connection.close()
    print(
        f"inventory_sqlite=ok items={len(actual_items)} events={len(actual_events)} "
        "legacy_documents=0 duplicate_100=once parallel_items=exact rollback=atomic"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
