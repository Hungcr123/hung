"""PostgreSQL runtime repository for lesson-time heartbeat writes.

Added 2026-07-25: route `/lesson/time` heartbeat writes through PostgreSQL
in process tests while SQLite remains production-authoritative.
"""

from __future__ import annotations

import hashlib
import json

import FUTURE.server_app as app

def _public_time(row) -> dict:
    if row is None:
        return {}
    source = {
        "file_id": row[0],
        "path": row[1],
        "title": row[2],
        "space": row[3],
        "seconds": row[4],
        "ticks": row[5],
        "updated_at_utc": row[6],
    }
    return app.server_database_lesson_time_row(source)

def _sha_for(row: dict) -> str:
    return hashlib.sha256(
        json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    ).hexdigest()

def add_lesson_time_heartbeat(context: dict) -> dict:
    normalized = app.normalize_username(context.get("username", ""))
    key = app.clean(context.get("lesson_key", ""))
    if not normalized or not key:
        raise RuntimeError("Lesson time requires user and lesson key.")

    legacy_key = app.clean(context.get("legacy_key", ""))
    path = app.clean_path_value(context.get("path", ""))
    title = app.clean(context.get("title", ""))[:180]
    space = app.clean(context.get("space", ""))[:40]
    requested_seconds = max(0, app.space_w_int(context.get("requested_seconds", 0), 0))
    safe_protocol = app.clean(context.get("protocol", "")).lower()
    safe_session_id = app.clean(context.get("session_id", ""))[:96]
    sequence = context.get("sequence")
    incoming_sequence_hint = int(sequence) if isinstance(sequence, int) else 0
    updated_at = app.clean(context.get("updated_at", ""))
    updated_epoch = max(0.0, float(context.get("updated_epoch", 0) or 0))
    normalized_offline_claims = list(context.get("offline_claims") or [])
    lease_info = dict(context.get("lease_info") or {})
    server_boot_id = app.clean(context.get("server_boot_id", ""))
    server_boot_epoch = max(0.0, float(context.get("server_boot_epoch", 0) or 0))

    def _write(connection):
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT file_id FROM future_server2.lesson_file_aliases WHERE normalized_path=%s AND active=TRUE",
                (path.lower(),),
            )
            alias_row = cursor.fetchone()
            file_id = app.clean(alias_row[0])[:240] if alias_row is not None else ""

            if legacy_key and legacy_key != key:
                cursor.execute(
                    "SELECT 1 FROM future_server2.lesson_time WHERE username=%s AND lesson_key=%s",
                    (normalized, key),
                )
                current = cursor.fetchone()
                cursor.execute(
                    "SELECT 1 FROM future_server2.lesson_time WHERE username=%s AND lesson_key=%s",
                    (normalized, legacy_key),
                )
                old = cursor.fetchone()
                if old is not None and current is None:
                    cursor.execute(
                        "UPDATE future_server2.lesson_time SET lesson_key=%s,file_id=%s,path=%s WHERE username=%s AND lesson_key=%s",
                        (key, file_id, path, normalized, legacy_key),
                    )
                elif old is not None:
                    cursor.execute(
                        """
                        UPDATE future_server2.lesson_time
                        SET seconds=seconds+(SELECT seconds FROM future_server2.lesson_time WHERE username=%s AND lesson_key=%s),
                            ticks=ticks+(SELECT ticks FROM future_server2.lesson_time WHERE username=%s AND lesson_key=%s),
                            file_id=CASE WHEN %s<>'' THEN %s ELSE file_id END
                        WHERE username=%s AND lesson_key=%s
                        """,
                        (normalized, legacy_key, normalized, legacy_key, file_id, file_id, normalized, key),
                    )
                    cursor.execute(
                        "DELETE FROM future_server2.lesson_time WHERE username=%s AND lesson_key=%s",
                        (normalized, legacy_key),
                    )

                cursor.execute(
                    "SELECT last_seen_epoch FROM future_server2.lesson_time_credit_state WHERE username=%s AND lesson_key=%s",
                    (normalized, legacy_key),
                )
                old_credit = cursor.fetchone()
                cursor.execute(
                    "SELECT last_seen_epoch FROM future_server2.lesson_time_credit_state WHERE username=%s AND lesson_key=%s",
                    (normalized, key),
                )
                current_credit = cursor.fetchone()
                if old_credit is not None and current_credit is None:
                    cursor.execute(
                        "UPDATE future_server2.lesson_time_credit_state SET lesson_key=%s,file_id=%s WHERE username=%s AND lesson_key=%s",
                        (key, file_id, normalized, legacy_key),
                    )
                elif old_credit is not None:
                    if float(old_credit[0] or 0) > float(current_credit[0] or 0):
                        cursor.execute(
                            """
                            UPDATE future_server2.lesson_time_credit_state
                            SET session_id=(SELECT session_id FROM future_server2.lesson_time_credit_state WHERE username=%s AND lesson_key=%s),
                                last_sequence=(SELECT last_sequence FROM future_server2.lesson_time_credit_state WHERE username=%s AND lesson_key=%s),
                                last_seen_epoch=(SELECT last_seen_epoch FROM future_server2.lesson_time_credit_state WHERE username=%s AND lesson_key=%s),
                                file_id=%s
                            WHERE username=%s AND lesson_key=%s
                            """,
                            (normalized, legacy_key, normalized, legacy_key, normalized, legacy_key, file_id, normalized, key),
                        )
                    cursor.execute(
                        "DELETE FROM future_server2.lesson_time_credit_state WHERE username=%s AND lesson_key=%s",
                        (normalized, legacy_key),
                    )

            cursor.execute(
                """
                SELECT session_id,last_sequence,last_seen_epoch,boot_id,lease_issued_epoch,offline_credited_seconds
                FROM future_server2.lesson_time_credit_state
                WHERE username=%s AND lesson_key=%s
                """,
                (normalized, key),
            )
            credit_row = cursor.fetchone()
            incoming_sequence = incoming_sequence_hint if isinstance(sequence, int) else (int(credit_row[1] or 0) + 1 if credit_row is not None else 1)
            lease_issued_epoch = max(0.0, float(credit_row[4] or 0.0)) if credit_row is not None else updated_epoch
            current_public_cache: dict | None = None

            def current_public() -> dict:
                nonlocal current_public_cache
                if current_public_cache is None:
                    cursor.execute(
                        "SELECT file_id,path,title,space,seconds,ticks,updated_at_utc FROM future_server2.lesson_time WHERE username=%s AND lesson_key=%s",
                        (normalized, key),
                    )
                    row = cursor.fetchone()
                    current_public_cache = _public_time(row) if row is not None else {
                        "path": path,
                        "title": title,
                        "space": space,
                        "seconds": 0,
                        "ticks": 0,
                        "minutes": 0,
                        "updatedAt": "",
                    }
                return current_public_cache

            def heartbeat_result(reason: str, accepted_seconds: int = 0, include_lease: bool = False) -> dict:
                result = {
                    **current_public(),
                    "acceptedSeconds": max(0, int(accepted_seconds or 0)),
                    "heartbeatAccepted": bool(accepted_seconds > 0 or reason in {"session_started", "session_resumed"}),
                    "heartbeatReason": reason,
                    "sessionId": safe_session_id if safe_protocol == app.LESSON_TIME_PROTOCOL else "",
                    "sequence": incoming_sequence if safe_protocol == app.LESSON_TIME_PROTOCOL else 0,
                    "serverTime": updated_at,
                }
                if include_lease and safe_protocol == app.LESSON_TIME_PROTOCOL and lease_issued_epoch > 0 and not app.clean(context.get("offline_lease", "")):
                    lease = app.server_database_lesson_time_offline_lease(normalized, key, safe_session_id, lease_issued_epoch)
                    result.update({
                        "offlineLease": lease["token"],
                        "offlineLeaseExpiresEpoch": lease["expiresEpoch"],
                        "offlineLeaseClaimDeadlineEpoch": lease["claimDeadlineEpoch"],
                        "offlineLeaseMaxSeconds": lease["maxOfflineSeconds"],
                    })
                return result

            def credit_time(accepted_seconds: int, reason: str) -> dict:
                payload = {
                    "username": normalized,
                    "lesson_key": key,
                    "file_id": file_id,
                    "path": path,
                    "title": title,
                    "space": space,
                    "seconds": accepted_seconds,
                    "ticks": 1,
                    "updated_at_utc": updated_at,
                    "updated_epoch": updated_epoch,
                }
                cursor.execute(
                    """
                    INSERT INTO future_server2.lesson_time(username,lesson_key,file_id,path,title,space,seconds,ticks,updated_at_utc,updated_epoch,migrated_at_utc,source_sha256)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    ON CONFLICT(username,lesson_key) DO UPDATE SET
                        file_id=CASE WHEN excluded.file_id<>'' THEN excluded.file_id ELSE future_server2.lesson_time.file_id END,
                        path=excluded.path,
                        title=CASE WHEN excluded.title<>'' THEN excluded.title ELSE future_server2.lesson_time.title END,
                        space=CASE WHEN excluded.space<>'' THEN excluded.space ELSE future_server2.lesson_time.space END,
                        seconds=future_server2.lesson_time.seconds+excluded.seconds,
                        ticks=future_server2.lesson_time.ticks+1,
                        updated_at_utc=excluded.updated_at_utc,
                        updated_epoch=excluded.updated_epoch,
                        migrated_at_utc=excluded.migrated_at_utc,
                        source_sha256=excluded.source_sha256
                    RETURNING file_id,path,title,space,seconds,ticks,updated_at_utc
                    """,
                    (
                        normalized, key, file_id, path, title, space, accepted_seconds, 1, updated_at,
                        updated_epoch, app.utc_timestamp(), _sha_for(payload),
                    ),
                )
                credited = _public_time(cursor.fetchone())
                return {
                    **credited,
                    "acceptedSeconds": accepted_seconds,
                    "heartbeatAccepted": True,
                    "heartbeatReason": reason,
                    "sessionId": safe_session_id if safe_protocol == app.LESSON_TIME_PROTOCOL else "",
                    "sequence": incoming_sequence if safe_protocol == app.LESSON_TIME_PROTOCOL else 0,
                    "serverTime": updated_at,
                }

            if credit_row is None:
                payload = {
                    "username": normalized,
                    "lesson_key": key,
                    "file_id": file_id,
                    "session_id": safe_session_id,
                    "last_sequence": incoming_sequence,
                    "last_seen_epoch": updated_epoch,
                    "boot_id": server_boot_id,
                    "lease_issued_epoch": updated_epoch,
                    "offline_credited_seconds": 0,
                    "updated_at_utc": updated_at,
                }
                cursor.execute(
                    """
                    INSERT INTO future_server2.lesson_time_credit_state(username,lesson_key,file_id,session_id,last_sequence,last_seen_epoch,boot_id,lease_issued_epoch,offline_credited_seconds,updated_at_utc,updated_epoch,migrated_at_utc,source_sha256)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    """,
                    (
                        normalized, key, file_id, safe_session_id, incoming_sequence, updated_epoch,
                        server_boot_id, updated_epoch, 0, updated_at, app.timestamp_to_epoch(updated_at),
                        app.utc_timestamp(), _sha_for(payload),
                    ),
                )
                return heartbeat_result("session_started", include_lease=True)

            stored_session_id = app.clean(credit_row[0])
            stored_sequence = max(0, int(credit_row[1] or 0))
            last_seen_epoch = max(0.0, float(credit_row[2] or 0.0))
            offline_credited_seconds = max(0, int(credit_row[5] or 0))
            if normalized_offline_claims:
                if stored_session_id != safe_session_id:
                    return heartbeat_result("session_conflict")
                if app.clean(credit_row[3]) != server_boot_id and updated_epoch > server_boot_epoch + app.LESSON_TIME_RESTART_CLAIM_BOUNDARY_SECONDS:
                    return heartbeat_result("offline_restart_window_expired")
                if abs(lease_issued_epoch - float(lease_info.get("i", 0) or 0)) >= 1.0:
                    raise RuntimeError("Lesson offline lease is no longer active.")
                fresh_claims = [row for row in normalized_offline_claims if row["sequence"] > stored_sequence]
                if not fresh_claims:
                    return heartbeat_result("replay", include_lease=True)
                incoming_sequence = fresh_claims[-1]["sequence"]
                requested_offline_seconds = sum(row["seconds"] for row in fresh_claims)
                elapsed_budget = max(0, int(updated_epoch - last_seen_epoch))
                remaining_budget = max(0, int(lease_info.get("m", 0) or 0) - offline_credited_seconds)
                accepted_seconds = min(requested_offline_seconds, elapsed_budget, remaining_budget)
                cursor.execute(
                    """
                    UPDATE future_server2.lesson_time_credit_state
                    SET last_sequence=%s,last_seen_epoch=%s,boot_id=%s,offline_credited_seconds=offline_credited_seconds+%s,updated_at_utc=%s,updated_epoch=%s
                    WHERE username=%s AND lesson_key=%s
                    """,
                    (incoming_sequence, max(last_seen_epoch, updated_epoch), server_boot_id, accepted_seconds, updated_at, app.timestamp_to_epoch(updated_at), normalized, key),
                )
                if accepted_seconds <= 0:
                    return heartbeat_result("offline_empty", include_lease=True)
                return credit_time(accepted_seconds, "offline_credited")
            if stored_session_id != safe_session_id:
                if max(0.0, updated_epoch - last_seen_epoch) < app.LESSON_TIME_ACTIVE_SESSION_LEASE_SECONDS:
                    return heartbeat_result("session_conflict")
                cursor.execute(
                    """
                    UPDATE future_server2.lesson_time_credit_state
                    SET session_id=%s,last_sequence=%s,last_seen_epoch=%s,boot_id=%s,lease_issued_epoch=%s,offline_credited_seconds=0,updated_at_utc=%s,updated_epoch=%s
                    WHERE username=%s AND lesson_key=%s
                    """,
                    (safe_session_id, incoming_sequence, updated_epoch, server_boot_id, updated_epoch, updated_at, app.timestamp_to_epoch(updated_at), normalized, key),
                )
                lease_issued_epoch = updated_epoch
                return heartbeat_result("session_resumed", include_lease=True)
            if app.clean(credit_row[3]) != server_boot_id:
                cursor.execute(
                    """
                    UPDATE future_server2.lesson_time_credit_state
                    SET last_sequence=%s,last_seen_epoch=%s,boot_id=%s,updated_at_utc=%s,updated_epoch=%s
                    WHERE username=%s AND lesson_key=%s
                    """,
                    (max(stored_sequence, incoming_sequence), updated_epoch, server_boot_id, updated_at, app.timestamp_to_epoch(updated_at), normalized, key),
                )
                return heartbeat_result("server_restarted", include_lease=True)
            if safe_protocol == app.LESSON_TIME_PROTOCOL and incoming_sequence <= stored_sequence:
                return heartbeat_result("replay")

            elapsed_seconds = max(0, min(app.LESSON_TIME_MAX_HEARTBEAT_SECONDS, int(max(0.0, updated_epoch - last_seen_epoch))))
            accepted_seconds = min(requested_seconds, elapsed_seconds)
            cursor.execute(
                """
                UPDATE future_server2.lesson_time_credit_state
                SET last_sequence=%s,last_seen_epoch=%s,updated_at_utc=%s,updated_epoch=%s
                WHERE username=%s AND lesson_key=%s
                """,
                (max(stored_sequence, incoming_sequence), max(last_seen_epoch, updated_epoch), updated_at, app.timestamp_to_epoch(updated_at), normalized, key),
            )
            if accepted_seconds <= 0:
                return heartbeat_result("too_fast")
            return credit_time(accepted_seconds, "credited")

    return app.postgres_execute(_write)


# Added 2026-07-30: replace imported lesson-time state without touching the retired SQLite store.
def replace_lesson_time_payload(username: str, payload: dict) -> bool:
    normalized = app.normalize_username(username)
    source = payload if isinstance(payload, dict) else {}
    states = source.get("states") if isinstance(source.get("states"), dict) else {}
    if not normalized:
        return False

    rows = []
    migrated_at = app.utc_timestamp()
    for lesson_key, row in states.items():
        if not app.clean(lesson_key) or not isinstance(row, dict):
            continue
        updated_at = app.normalize_timestamp_text(row.get("updatedAt") or row.get("updated_at"), fallback_now=True)
        rows.append((
            normalized,
            app.clean(lesson_key),
            app.clean(row.get("file_id") or row.get("lesson_id"))[:240],
            app.clean_path_value(row.get("path", "")),
            app.clean(row.get("title", ""))[:180],
            app.clean(row.get("space", ""))[:40],
            max(0, app.space_w_int(row.get("seconds", 0), 0)),
            max(0, app.space_w_int(row.get("ticks", 0), 0)),
            updated_at,
            max(0.0, app.timestamp_to_epoch(updated_at)),
            migrated_at,
        ))

    def _write(connection):
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM future_server2.lesson_time WHERE username=%s", (normalized,))
            if rows:
                cursor.executemany(
                    """
                    INSERT INTO future_server2.lesson_time
                        (username,lesson_key,file_id,path,title,space,seconds,ticks,updated_at_utc,updated_epoch,migrated_at_utc,source_sha256)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'')
                    """,
                    rows,
                )
        return True

    return bool(app.postgres_execute(_write))
