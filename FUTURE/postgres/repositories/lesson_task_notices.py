"""PostgreSQL repository for per-user lesson task notices."""

from __future__ import annotations

import hashlib
import json

import FUTURE.server_app as app


def _stamp_epoch(value: str) -> float:
    return app.timestamp_to_epoch(app.clean(value))


def _payload_sha(payload: dict) -> str:
    clean_payload = app._clean_lesson_task_notice_store(payload)
    return hashlib.sha256(
        json.dumps(clean_payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _user_payload_sha(username: str, record: dict) -> str:
    return _payload_sha({"version": 1, "by_user": {app.normalize_username(username): record if isinstance(record, dict) else {}}})


def load_payload(target_user: str = "") -> dict:
    target_user = app.normalize_username(target_user)

    def _run(connection):
        notice_sql = """
            SELECT username, notice_id, position, notice_json, active, created_at_utc, updated_at_utc
            FROM future_server2.lesson_task_notices
        """
        state_sql = """
            SELECT username, notice_id, read_at_utc, seen_at_utc
            FROM future_server2.lesson_task_notice_state
        """
        params: tuple = ()
        if target_user:
            notice_sql += " WHERE username=%s"
            state_sql += " WHERE username=%s"
            params = (target_user,)
        notice_sql += " ORDER BY username ASC, position ASC, notice_id ASC"
        state_sql += " ORDER BY username ASC, notice_id ASC"
        with connection.cursor() as cursor:
            cursor.execute(notice_sql, params)
            notice_rows = cursor.fetchall()
            cursor.execute(state_sql, params)
            state_rows = cursor.fetchall()
        out = {"version": 1, "by_user": {}}
        for username, notice_id, _position, notice_json, active, created_at, updated_at in notice_rows:
            clean_user = app.normalize_username(username)
            if not clean_user:
                continue
            notice = dict(notice_json or {}) if isinstance(notice_json, dict) else {}
            notice["id"] = app.clean(notice.get("id") or notice_id)
            notice["active"] = bool(active)
            if created_at and not app.clean(notice.get("created_at", "")):
                notice["created_at"] = app.clean(created_at)
            if updated_at and not app.clean(notice.get("updated_at", "")):
                notice["updated_at"] = app.clean(updated_at)
            record = out["by_user"].setdefault(clean_user, {"notices": [], "read": {}})
            record.setdefault("notices", []).append(notice)
        for username, notice_id, read_at, seen_at in state_rows:
            clean_user = app.normalize_username(username)
            clean_notice = app.clean(notice_id)
            if not clean_user or not clean_notice:
                continue
            record = out["by_user"].setdefault(clean_user, {"notices": [], "read": {}})
            if app.clean(read_at):
                record.setdefault("read", {})[clean_notice] = app.clean(read_at)
            if app.clean(seen_at):
                record.setdefault("seen", {})[clean_notice] = app.clean(seen_at)
        return app._clean_lesson_task_notice_store(out)

    return app.postgres_execute(_run)


def save_payload(payload: dict, target_user: str = "") -> dict:
    cleaned = app._clean_lesson_task_notice_store(payload)
    users = [app.normalize_username(target_user)] if app.normalize_username(target_user) else list(cleaned.get("by_user", {}).keys())
    users = [user for user in users if user]
    now = app.utc_timestamp()
    migrated_at = now

    saved_payload = {"version": 1, "by_user": {}}
    for username in users:
        saved_payload["by_user"][username] = cleaned.get("by_user", {}).get(username, {})

    def _run(connection):
        with connection.cursor() as cursor:
            for username in users:
                record = cleaned.get("by_user", {}).get(username, {})
                notices = record.get("notices") if isinstance(record.get("notices"), list) else []
                read_map = record.get("read") if isinstance(record.get("read"), dict) else {}
                seen_map = record.get("seen") if isinstance(record.get("seen"), dict) else {}
                keep_notice_ids: list[str] = []
                keep_state_ids: set[str] = set()
                source_sha = _user_payload_sha(username, record)
                for index, raw_notice in enumerate(notices[-200:]):
                    notice = dict(raw_notice) if isinstance(raw_notice, dict) else {}
                    notice_id = app.clean(notice.get("id", ""))
                    if not notice_id:
                        continue
                    keep_notice_ids.append(notice_id)
                    updated_at = app.clean(notice.get("updated_at", "")) or now
                    created_at = app.clean(notice.get("created_at", "")) or updated_at
                    cursor.execute(
                        """
                        INSERT INTO future_server2.lesson_task_notices
                            (username,notice_id,position,notice_json,active,created_at_utc,updated_at_utc,updated_epoch,migrated_at_utc,source_sha256)
                        VALUES (%s,%s,%s,%s::jsonb,%s,%s,%s,%s,%s,%s)
                        ON CONFLICT (username, notice_id) DO UPDATE SET
                            position=excluded.position,
                            notice_json=excluded.notice_json,
                            active=excluded.active,
                            created_at_utc=excluded.created_at_utc,
                            updated_at_utc=excluded.updated_at_utc,
                            updated_epoch=excluded.updated_epoch,
                            migrated_at_utc=excluded.migrated_at_utc,
                            source_sha256=excluded.source_sha256
                        """,
                        (
                            username,
                            notice_id,
                            index,
                            json.dumps(notice, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
                            bool(notice.get("active", True)),
                            created_at,
                            updated_at,
                            _stamp_epoch(updated_at),
                            migrated_at,
                            source_sha,
                        ),
                    )
                for notice_id in sorted(set(read_map.keys()) | set(seen_map.keys())):
                    clean_id = app.clean(notice_id)
                    if not clean_id:
                        continue
                    read_at = app.clean(read_map.get(notice_id, ""))
                    seen_at = app.clean(seen_map.get(notice_id, ""))
                    updated_at = app.timestamp_latest_text(read_at, seen_at) or now
                    keep_state_ids.add(clean_id)
                    cursor.execute(
                        """
                        INSERT INTO future_server2.lesson_task_notice_state
                            (username,notice_id,read_at_utc,seen_at_utc,updated_at_utc,updated_epoch,migrated_at_utc,source_sha256)
                        VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                        ON CONFLICT (username, notice_id) DO UPDATE SET
                            read_at_utc=excluded.read_at_utc,
                            seen_at_utc=excluded.seen_at_utc,
                            updated_at_utc=excluded.updated_at_utc,
                            updated_epoch=excluded.updated_epoch,
                            migrated_at_utc=excluded.migrated_at_utc,
                            source_sha256=excluded.source_sha256
                        """,
                        (username, clean_id, read_at, seen_at, updated_at, _stamp_epoch(updated_at), migrated_at, source_sha),
                    )
                if keep_notice_ids:
                    cursor.execute(
                        "DELETE FROM future_server2.lesson_task_notices WHERE username=%s AND NOT (notice_id = ANY(%s))",
                        (username, keep_notice_ids),
                    )
                else:
                    cursor.execute("DELETE FROM future_server2.lesson_task_notices WHERE username=%s", (username,))
                keep_state_list = list(keep_state_ids)
                if keep_state_list:
                    cursor.execute(
                        "DELETE FROM future_server2.lesson_task_notice_state WHERE username=%s AND NOT (notice_id = ANY(%s))",
                        (username, keep_state_list),
                    )
                else:
                    cursor.execute("DELETE FROM future_server2.lesson_task_notice_state WHERE username=%s", (username,))
        return {"ok": True, "users": len(users), "source_sha256": _payload_sha(saved_payload)}

    return app.postgres_execute(_run)


def delete_user(username: str) -> bool:
    username = app.normalize_username(username)
    if not username:
        return False

    def _run(connection):
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM future_server2.lesson_task_notice_state WHERE username=%s", (username,))
            cursor.execute("DELETE FROM future_server2.lesson_task_notices WHERE username=%s", (username,))
            return True

    return bool(app.postgres_execute(_run))


def signature(target_user: str = "") -> tuple:
    payload = load_payload(target_user)
    return ("postgres-lesson-task-notices", app.normalize_username(target_user).lower(), _payload_sha(payload))
