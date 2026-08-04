"""PostgreSQL runtime repository for inventory award writes.

Added 2026-07-25: route `/inventory/award` transactions through
PostgreSQL in process tests while SQLite remains authoritative by default.
"""

from __future__ import annotations

import hashlib
import json
import os

import FUTURE.server_app as app

def _sha(row: dict) -> str:
    return hashlib.sha256(
        json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    ).hexdigest()

def _item_public(row, fallback: dict | None = None) -> dict:
    if row is None:
        return dict(fallback or {})
    # Added 2026-07-30: keep the PostgreSQL repository independent of the retired
    # local-database document helper that used to format this row.
    return {
        "id": app.clean(row[0]),
        "name": app.clean(row[1])[:160],
        "use": app.clean(row[2])[:320],
        "quantity": max(0, app.space_w_int(row[3], 0)),
        "updated_at": app.clean(row[4]),
    }

def award_inventory_items(username: str, awards: list[dict] | tuple[dict, ...], now: str) -> dict:
    normalized = app.normalize_username(username)
    normalized_awards = [row for row in awards if isinstance(row, dict)]
    if not normalized:
        return {"results": [], "items": {}, "events": [], "updated_at": now, "_event_cache": {}}

    def _write(connection):
        results = []
        changed_items = {}
        accepted_events = []
        event_cache = {}
        with connection.cursor() as cursor:
            for award in normalized_awards:
                item = award.get("item") if isinstance(award.get("item"), dict) else {}
                item_id = app.clean(item.get("id", ""))[:80]
                event_id = app.clean(award.get("event_id", ""))[:240]
                quantity = max(1, min(9999, app.space_w_int(award.get("quantity", 1), 1)))
                if not item_id or not event_id:
                    results.append({"awarded": False, "event_id": event_id, "item": item, "quantity": quantity})
                    continue
                event_payload = {
                    "username": normalized,
                    "event_id": event_id,
                    "item_id": item_id,
                    "quantity": quantity,
                    "awarded_at_utc": now,
                    "awarded_epoch": app.timestamp_to_epoch(now),
                }
                cursor.execute(
                    """
                    INSERT INTO future_server2.inventory_events(username,event_id,item_id,quantity,awarded_at_utc,awarded_epoch,migrated_at_utc,source_sha256)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                    ON CONFLICT(username,event_id) DO NOTHING
                    """,
                    (
                        normalized, event_id, item_id, quantity, now, app.timestamp_to_epoch(now),
                        app.utc_timestamp(), _sha(event_payload),
                    ),
                )
                awarded = bool(cursor.rowcount or 0)
                event_item_id = item_id
                event_quantity = quantity
                if awarded:
                    if os.environ.get("FUTURE_TEST_INVENTORY_FORCE_ROLLBACK") == "1" and item_id == "rollback_item":
                        raise RuntimeError("forced inventory rollback")
                    item_payload = {
                        "username": normalized,
                        "item_id": item_id,
                        "name": app.clean(item.get("name", ""))[:160],
                        "use_text": app.clean(item.get("use", ""))[:320],
                        "quantity": quantity,
                        "updated_at_utc": now,
                        "updated_epoch": app.timestamp_to_epoch(now),
                    }
                    cursor.execute(
                        """
                        INSERT INTO future_server2.inventory_items(username,item_id,name,use_text,quantity,updated_at_utc,updated_epoch,migrated_at_utc,source_sha256)
                        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                        ON CONFLICT(username,item_id) DO UPDATE SET
                            name=CASE WHEN excluded.name<>'' THEN excluded.name ELSE future_server2.inventory_items.name END,
                            use_text=CASE WHEN excluded.use_text<>'' THEN excluded.use_text ELSE future_server2.inventory_items.use_text END,
                            quantity=future_server2.inventory_items.quantity+excluded.quantity,
                            updated_at_utc=excluded.updated_at_utc,
                            updated_epoch=excluded.updated_epoch,
                            migrated_at_utc=excluded.migrated_at_utc,
                            source_sha256=excluded.source_sha256
                        """,
                        (
                            normalized, item_id, item_payload["name"], item_payload["use_text"], quantity,
                            now, app.timestamp_to_epoch(now), app.utc_timestamp(), _sha(item_payload),
                        ),
                    )
                    accepted_events.append(event_id)
                else:
                    cursor.execute(
                        "SELECT item_id,quantity FROM future_server2.inventory_events WHERE username=%s AND event_id=%s",
                        (normalized, event_id),
                    )
                    existing_event = cursor.fetchone()
                    if existing_event is not None:
                        event_item_id = app.clean(existing_event[0])[:80] or item_id
                        event_quantity = max(1, min(9999, app.space_w_int(existing_event[1], quantity)))

                cursor.execute(
                    "SELECT item_id,name,use_text,quantity,updated_at_utc FROM future_server2.inventory_items WHERE username=%s AND item_id=%s",
                    (normalized, event_item_id),
                )
                item_row = cursor.fetchone()
                public_item = _item_public(item_row, item)
                if item_row is not None:
                    changed_items[event_item_id] = public_item
                event_cache[event_id] = {
                    "item_id": event_item_id,
                    "quantity": event_quantity,
                    "item": dict(public_item),
                }
                results.append({"awarded": awarded, "event_id": event_id, "item": public_item, "quantity": quantity})
        return {"results": results, "items": changed_items, "events": accepted_events, "updated_at": now, "_event_cache": event_cache}

    return app.postgres_execute(_write)


# Added 2026-07-30: replace imported inventory state in one PostgreSQL transaction.
def replace_inventory_payload(username: str, payload: dict) -> bool:
    normalized = app.normalize_username(username)
    source = payload if isinstance(payload, dict) else {}
    items = source.get("items") if isinstance(source.get("items"), dict) else {}
    events = source.get("events") if isinstance(source.get("events"), list) else []
    updated_at = app.normalize_timestamp_text(source.get("updated_at"), fallback_now=True)
    if not normalized:
        return False

    item_rows = []
    for item_key, item in items.items():
        if not isinstance(item, dict):
            continue
        item_id = app.clean(item.get("id") or item_key)[:80]
        if not item_id:
            continue
        item_updated_at = app.normalize_timestamp_text(item.get("updated_at") or updated_at, fallback_now=True)
        item_rows.append((
            normalized, item_id, app.clean(item.get("name", ""))[:160], app.clean(item.get("use", ""))[:320],
            max(0, app.space_w_int(item.get("quantity", 0), 0)), item_updated_at,
            app.timestamp_to_epoch(item_updated_at), app.utc_timestamp(), "",
        ))
    event_rows = [
        (normalized, event_key, "", 0, updated_at, app.timestamp_to_epoch(updated_at), app.utc_timestamp(), "")
        for event_key in (app.clean(event_id)[:240] for event_id in events[-5000:])
        if event_key
    ]

    def _write(connection):
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM future_server2.inventory_events WHERE username=%s", (normalized,))
            cursor.execute("DELETE FROM future_server2.inventory_items WHERE username=%s", (normalized,))
            if item_rows:
                cursor.executemany(
                    """
                    INSERT INTO future_server2.inventory_items
                        (username,item_id,name,use_text,quantity,updated_at_utc,updated_epoch,migrated_at_utc,source_sha256)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    """,
                    item_rows,
                )
            if event_rows:
                cursor.executemany(
                    """
                    INSERT INTO future_server2.inventory_events
                        (username,event_id,item_id,quantity,awarded_at_utc,awarded_epoch,migrated_at_utc,source_sha256)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                    """,
                    event_rows,
                )
        return True

    return bool(app.postgres_execute(_write))
