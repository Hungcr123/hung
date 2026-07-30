"""PostgreSQL repository for global Server 2 announcements."""

from __future__ import annotations

import hashlib
import json

import FUTURE.server_app as app


def _row_id(position: int) -> str:
    return f"announcement-{max(0, int(position or 0)):03d}"


def _snapshot_sha(items: list[str], updated_at: str = "") -> str:
    raw = json.dumps({"items": items, "updated_at": updated_at}, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def load() -> dict:
    def _run(connection):
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT text, updated_at_utc, source_sha256, revision
                FROM future_server2.announcements
                WHERE active=TRUE
                ORDER BY position ASC, announcement_id ASC
                """
            )
            rows = cursor.fetchall()
        items = [app.clean(row[0])[:240] for row in rows if app.clean(row[0])]
        updated_at = ""
        revision = 0
        source_sha = ""
        for row in rows:
            if app.timestamp_order_key(row[1]) >= app.timestamp_order_key(updated_at):
                updated_at = app.clean(row[1])
            revision = max(revision, app.space_w_int(row[3], 0))
            source_sha = app.clean(row[2]) or source_sha
        return {
            "items": app.split_announcement_text("\n".join(items)),
            "updated_at": updated_at,
            "revision": revision,
            "source_sha256": source_sha or _snapshot_sha(items, updated_at),
        }

    return app.postgres_execute(_run)


def save_items(items: list[str], updated_at: str = "") -> dict:
    clean_items = app.split_announcement_text("\n".join(str(item or "") for item in items))
    now = app.clean(updated_at) or app.utc_timestamp()
    updated_epoch = app.timestamp_to_epoch(now)
    source_sha = _snapshot_sha(clean_items, now)

    def _run(connection):
        with connection.cursor() as cursor:
            cursor.execute("SELECT COALESCE(max(revision),0) FROM future_server2.announcements")
            revision = int(cursor.fetchone()[0] or 0) + 1
            cursor.execute("UPDATE future_server2.announcements SET active=FALSE, updated_at_utc=%s, updated_epoch=%s WHERE active=TRUE", (now, updated_epoch))
            for index, text in enumerate(clean_items):
                cursor.execute(
                    """
                    INSERT INTO future_server2.announcements
                        (announcement_id,position,text,active,revision,created_at_utc,updated_at_utc,updated_epoch,migrated_at_utc,source_sha256)
                    VALUES (%s,%s,%s,TRUE,%s,%s,%s,%s,%s,%s)
                    ON CONFLICT (announcement_id) DO UPDATE SET
                        position=excluded.position,
                        text=excluded.text,
                        active=TRUE,
                        revision=excluded.revision,
                        updated_at_utc=excluded.updated_at_utc,
                        updated_epoch=excluded.updated_epoch,
                        migrated_at_utc=excluded.migrated_at_utc,
                        source_sha256=excluded.source_sha256
                    """,
                    (_row_id(index), index, text, revision, now, now, updated_epoch, app.utc_timestamp(), source_sha),
                )
        return {"ok": True, "items": clean_items, "updated_at": now, "revision": revision, "source_sha256": source_sha}

    return app.postgres_execute(_run)


def signature() -> tuple:
    payload = load()
    return ("postgres-announcements", int(payload.get("revision", 0) or 0), app.clean(payload.get("updated_at", "")), app.clean(payload.get("source_sha256", "")))
