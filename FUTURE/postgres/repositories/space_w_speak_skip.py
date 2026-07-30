"""PostgreSQL repository for Space_W speak-skip requests."""

from __future__ import annotations

import hashlib
import json

import FUTURE.server_app as app


def clean_payload(payload: dict) -> dict:
    source = payload if isinstance(payload, dict) else {}
    rows = source.get("requests") if isinstance(source.get("requests"), dict) else {}
    out = {"version": int(source.get("version", 1) or 1), "updated_at": app.clean(source.get("updated_at", "")), "requests": {}}
    for key, value in rows.items():
        request_id = app.clean(key)
        if request_id and isinstance(value, dict):
            row = dict(value)
            row["id"] = app.clean(row.get("id") or request_id)
            out["requests"][request_id] = row
    if len(out["requests"]) > 600:
        ordered = sorted(
            out["requests"].items(),
            key=lambda item: app.timestamp_order_key(item[1].get("updatedAt") or item[1].get("createdAt")),
        )
        out["requests"] = dict(ordered[-600:])
    return out


def fingerprint(payload: dict) -> str:
    return hashlib.sha256(
        json.dumps(clean_payload(payload), ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def load_payload() -> dict:
    def _run(connection):
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT request_id, request_json
                FROM future_server2.space_w_speak_skip_requests
                ORDER BY updated_epoch ASC, request_id ASC
                """
            )
            rows = cursor.fetchall()
        payload = {"version": 1, "updated_at": "", "requests": {}}
        for request_id, request_json in rows:
            row = dict(request_json or {}) if isinstance(request_json, dict) else {}
            clean_id = app.clean(row.get("id") or request_id)
            if not clean_id:
                continue
            row["id"] = clean_id
            payload["requests"][clean_id] = row
            updated = app.clean(row.get("updatedAt") or row.get("respondedAt") or row.get("createdAt"))
            if app.timestamp_order_key(updated) >= app.timestamp_order_key(payload.get("updated_at", "")):
                payload["updated_at"] = updated
        return clean_payload(payload)

    return app.postgres_execute(_run)

def _row_from_record(row: dict) -> tuple:
    request_id = app.clean(row.get("id", ""))
    username = app.normalize_username(row.get("username", ""))
    status = app.clean(row.get("status", "pending")).lower() or "pending"
    progress_key = app.clean(row.get("progressKey", row.get("progress_key", "")))
    session_id = app.clean(row.get("sessionId", row.get("session_id", "")))[:96]
    path = app.clean_path_value(row.get("path", ""))
    identity = app.clean(row.get("identity", ""))[:240]
    node_index = max(0, app.space_w_int(row.get("nodeIndex", row.get("node_index", 0)), 0))
    created_at = app.clean(row.get("createdAt", ""))
    updated_at = app.clean(row.get("updatedAt") or row.get("respondedAt") or created_at)
    responded_at = app.clean(row.get("respondedAt", ""))
    return (
        request_id,
        username,
        status,
        progress_key,
        session_id,
        path,
        identity,
        node_index,
        json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
        created_at,
        updated_at,
        responded_at,
        app.timestamp_to_epoch(updated_at),
        app.utc_timestamp(),
        fingerprint({"version": 1, "requests": {request_id: row}}),
    )


def save_request(row: dict) -> dict:
    record = dict(row) if isinstance(row, dict) else {}
    request_id = app.clean(record.get("id", ""))
    if not request_id:
        raise RuntimeError("Missing speak-skip request id.")

    def _run(connection):
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO future_server2.space_w_speak_skip_requests
                    (request_id,username,status,progress_key,session_id,path,identity,node_index,request_json,created_at_utc,updated_at_utc,responded_at_utc,updated_epoch,migrated_at_utc,source_sha256)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (request_id) DO UPDATE SET
                    username=excluded.username,
                    status=excluded.status,
                    progress_key=excluded.progress_key,
                    session_id=excluded.session_id,
                    path=excluded.path,
                    identity=excluded.identity,
                    node_index=excluded.node_index,
                    request_json=excluded.request_json,
                    created_at_utc=excluded.created_at_utc,
                    updated_at_utc=excluded.updated_at_utc,
                    responded_at_utc=excluded.responded_at_utc,
                    updated_epoch=excluded.updated_epoch,
                    migrated_at_utc=excluded.migrated_at_utc,
                    source_sha256=excluded.source_sha256
                """,
                _row_from_record(record),
            )
        return {"ok": True, "request": record}

    return app.postgres_execute(_run)


def load_request(request_id: str) -> dict | None:
    request_id = app.clean(request_id)
    if not request_id:
        return None

    def _run(connection):
        with connection.cursor() as cursor:
            cursor.execute("SELECT request_json FROM future_server2.space_w_speak_skip_requests WHERE request_id=%s", (request_id,))
            row = cursor.fetchone()
        if not row:
            return None
        data = dict(row[0] or {}) if isinstance(row[0], dict) else {}
        data["id"] = app.clean(data.get("id") or request_id)
        return data

    return app.postgres_execute(_run)


def list_requests(status: str = "pending", username: str = "") -> list[dict]:
    status_filter = app.clean(status).lower()
    username_filter = app.normalize_username(username) if app.clean(username) else ""

    def _run(connection):
        clauses = []
        params = []
        if username_filter:
            clauses.append("username=%s")
            params.append(username_filter)
        if status_filter and status_filter not in {"all", "*"}:
            clauses.append("status=%s")
            params.append(status_filter)
        where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
        with connection.cursor() as cursor:
            cursor.execute(
                f"SELECT request_id,request_json FROM future_server2.space_w_speak_skip_requests{where} ORDER BY updated_epoch DESC, request_id ASC",
                tuple(params),
            )
            rows = cursor.fetchall()
        out = []
        for request_id, request_json in rows:
            data = dict(request_json or {}) if isinstance(request_json, dict) else {}
            data["id"] = app.clean(data.get("id") or request_id)
            out.append(data)
        return out

    return app.postgres_execute(_run)


def latest_accepted(username: str, progress_key: str, session_id: str = "") -> dict | None:
    username = app.normalize_username(username)
    progress_key = app.clean(progress_key)
    session_id = app.clean(session_id)[:96]
    if not username or not progress_key:
        return None

    def _run(connection):
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT request_id,request_json
                FROM future_server2.space_w_speak_skip_requests
                WHERE username=%s AND progress_key=%s AND session_id=%s AND status='accepted'
                ORDER BY updated_epoch DESC, request_id ASC
                LIMIT 1
                """,
                (username, progress_key, session_id),
            )
            row = cursor.fetchone()
        if not row:
            return None
        data = dict(row[1] or {}) if isinstance(row[1], dict) else {}
        data["id"] = app.clean(data.get("id") or row[0])
        return data

    return app.postgres_execute(_run)

def latest_by_user() -> dict[str, dict]:
    def _run(connection):
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT DISTINCT ON (username) username, request_id, request_json
                FROM future_server2.space_w_speak_skip_requests
                ORDER BY username,
                    CASE WHEN status='pending' THEN 0 ELSE 1 END,
                    updated_epoch DESC,
                    request_id ASC
                """
            )
            rows = cursor.fetchall()
        out: dict[str, dict] = {}
        for username, request_id, request_json in rows:
            clean_user = app.normalize_username(username)
            if not clean_user:
                continue
            data = dict(request_json or {}) if isinstance(request_json, dict) else {}
            data["id"] = app.clean(data.get("id") or request_id)
            out[clean_user] = data
        return out

    return app.postgres_execute(_run)


def respond_request(username: str, request_id: str = "", action: str = "accept") -> dict:
    username = app.normalize_username(username)
    request_id = app.clean(request_id)
    action = app.clean(action).lower() or "accept"
    next_status = "accepted" if action in {"accept", "approve", "accepted", "approved"} else "rejected"
    rows = list_requests("pending", username)
    row = load_request(request_id) if request_id else (rows[0] if rows else None)
    if not isinstance(row, dict) or app.normalize_username(row.get("username", "")) != username:
        raise RuntimeError("No matching Speak skip request.")
    now = app.utc_timestamp()
    row_progress_key = app.clean(row.get("progressKey", row.get("progress_key", "")))
    row_session_id = app.clean(row.get("sessionId", row.get("session_id", "")))
    changed = []
    if next_status == "accepted" and row_progress_key:
        for item in list_requests("all", username):
            if app.clean(item.get("progressKey", item.get("progress_key", ""))) != row_progress_key:
                continue
            if app.clean(item.get("sessionId", item.get("session_id", ""))) != row_session_id:
                continue
            if app.clean(item.get("status", "pending")).lower() not in {"pending", "accepted"}:
                continue
            item["status"] = next_status
            item["updatedAt"] = now
            item["respondedAt"] = now
            save_request(item)
            changed.append(item)
    else:
        row["status"] = next_status
        row["updatedAt"] = now
        row["respondedAt"] = now
        save_request(row)
        changed.append(row)
    return changed[0] if changed else row


def respond_many(username: str = "", action: str = "accept") -> list[dict]:
    username = app.normalize_username(username) if app.clean(username) else ""
    action = app.clean(action).lower() or "accept"
    next_status = "accepted" if action in {"accept", "approve", "accepted", "approved"} else "rejected"
    now = app.utc_timestamp()
    changed = []
    for row in list_requests("pending", username):
        row["status"] = next_status
        row["updatedAt"] = now
        row["respondedAt"] = now
        save_request(row)
        changed.append(row)
    return changed


def save_payload(payload: dict) -> dict:
    cleaned = clean_payload(payload)
    rows = cleaned.get("requests", {})
    source_sha = fingerprint(cleaned)
    keep_ids = list(rows.keys())
    migrated_at = app.utc_timestamp()

    def _run(connection):
        with connection.cursor() as cursor:
            for request_id, raw_row in rows.items():
                row = dict(raw_row) if isinstance(raw_row, dict) else {}
                username = app.normalize_username(row.get("username", ""))
                status = app.clean(row.get("status", "pending")).lower() or "pending"
                progress_key = app.clean(row.get("progressKey", row.get("progress_key", "")))
                session_id = app.clean(row.get("sessionId", row.get("session_id", "")))[:96]
                path = app.clean_path_value(row.get("path", ""))
                identity = app.clean(row.get("identity", ""))[:240]
                node_index = max(0, app.space_w_int(row.get("nodeIndex", row.get("node_index", 0)), 0))
                created_at = app.clean(row.get("createdAt", ""))
                updated_at = app.clean(row.get("updatedAt") or row.get("respondedAt") or created_at)
                responded_at = app.clean(row.get("respondedAt", ""))
                cursor.execute(
                    """
                    INSERT INTO future_server2.space_w_speak_skip_requests
                        (request_id,username,status,progress_key,session_id,path,identity,node_index,request_json,created_at_utc,updated_at_utc,responded_at_utc,updated_epoch,migrated_at_utc,source_sha256)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s,%s,%s,%s,%s,%s)
                    ON CONFLICT (request_id) DO UPDATE SET
                        username=excluded.username,
                        status=excluded.status,
                        progress_key=excluded.progress_key,
                        session_id=excluded.session_id,
                        path=excluded.path,
                        identity=excluded.identity,
                        node_index=excluded.node_index,
                        request_json=excluded.request_json,
                        created_at_utc=excluded.created_at_utc,
                        updated_at_utc=excluded.updated_at_utc,
                        responded_at_utc=excluded.responded_at_utc,
                        updated_epoch=excluded.updated_epoch,
                        migrated_at_utc=excluded.migrated_at_utc,
                        source_sha256=excluded.source_sha256
                    """,
                    (
                        request_id,
                        username,
                        status,
                        progress_key,
                        session_id,
                        path,
                        identity,
                        node_index,
                        json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
                        created_at,
                        updated_at,
                        responded_at,
                        app.timestamp_to_epoch(updated_at),
                        migrated_at,
                        source_sha,
                    ),
                )
            if keep_ids:
                cursor.execute(
                    "DELETE FROM future_server2.space_w_speak_skip_requests WHERE NOT (request_id = ANY(%s))",
                    (keep_ids,),
                )
            else:
                cursor.execute("DELETE FROM future_server2.space_w_speak_skip_requests")
        return {"ok": True, "requests": len(rows), "source_sha256": source_sha}

    return app.postgres_execute(_run)


def delete_request(request_id: str) -> bool:
    request_id = app.clean(request_id)
    if not request_id:
        return False

    def _run(connection):
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM future_server2.space_w_speak_skip_requests WHERE request_id=%s", (request_id,))
            return True

    return bool(app.postgres_execute(_run))


def signature() -> tuple:
    payload = load_payload()
    return ("postgres-space-w-speak-skip", fingerprint(payload))
