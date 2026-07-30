"""Vocabulary PostgreSQL runtime repository.

Added 2026-07-25: keep vocabulary runtime helpers out of the compatibility
adapter while Server 2 is still feature-flagging PostgreSQL per domain.
"""

from __future__ import annotations

import hashlib
import json

import FUTURE.server_app as app


def _public_payload(cursor, username: str) -> dict:
    cursor.execute(
        """
        SELECT word_key,word,meaning,pron,word_type,learn_count,first_at_utc,last_at_utc,sources_json,qmdict_missing
        FROM future_server2.vocabulary_registry
        WHERE username=%s
        ORDER BY word_key
        """,
        (username,),
    )
    words = {}
    updated_at = ""
    for row in cursor.fetchall():
        sources = row[8] if isinstance(row[8], list) else []
        item = {
            "word": app.clean(row[1]),
            "meaning": app.clean(row[2]),
            "pron": app.clean(row[3]),
            "type": app.clean(row[4]),
            "count": max(0, app.space_w_int(row[5], 0)),
            "first": app.clean(row[6]),
            "last": app.clean(row[7]),
            "sources": [app.clean(value) for value in sources if app.clean(value)],
        }
        if bool(row[9]):
            item["qmdict_missing"] = True
        words[app.clean(row[0])] = item
        updated_at = app.timestamp_latest_text(updated_at, row[7])
    return {"version": 1, "updated_at": updated_at, "words": words}


def load_registry(username: str) -> dict | None:
    normalized_user = app.normalize_username(username)
    if not normalized_user:
        return None

    def _read(connection):
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1 FROM future_server2.users WHERE username=%s", (normalized_user,))
            if cursor.fetchone() is None:
                return None
            return _public_payload(cursor, normalized_user)

    return app.postgres_execute(_read)


def registry_summary(username: str) -> dict:
    normalized_user = app.normalize_username(username)
    if not normalized_user:
        return {"total_words": 0, "updated_at": ""}

    def _read(connection):
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT COUNT(*),COALESCE(MAX(last_at_utc),'') FROM future_server2.vocabulary_registry WHERE username=%s",
                (normalized_user,),
            )
            row = cursor.fetchone()
        return {"total_words": int(row[0] or 0), "updated_at": app.clean(row[1])}

    return app.postgres_execute(_read)


def file_key_stats(username: str, word_keys: list[str], buckets: dict, resets: dict | None = None) -> dict:
    """Added 2026-07-29: count one lesson's New/Earn keys without loading the full registry."""
    normalized_user = app.normalize_username(username)
    keys = sorted({app.vocab_key(value) for value in (word_keys or []) if app.vocab_key(value)})
    if not normalized_user or not keys:
        return {"total_words": len(keys), "known_words": 0, "new_words": len(keys), "top_earnable": {scope: len(keys) for scope in ("day", "week", "month")}}
    bucket_rows = buckets if isinstance(buckets, dict) else {}
    reset_rows = resets if isinstance(resets, dict) else {}

    def _read(connection):
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    (SELECT COUNT(*) FROM future_server2.vocabulary_registry
                     WHERE username=%s AND word_key=ANY(%s)),
                    (SELECT COUNT(*) FROM future_server2.daily_earn
                     WHERE username=%s AND day_key=%s AND word_key=ANY(%s)
                       AND (%s='' OR learned_at_utc>=%s)),
                    (SELECT COUNT(*) FROM future_server2.weekly_earn
                     WHERE username=%s AND week_key=%s AND word_key=ANY(%s)
                       AND (%s='' OR learned_at_utc>=%s)),
                    (SELECT COUNT(*) FROM future_server2.monthly_earn
                     WHERE username=%s AND month_key=%s AND word_key=ANY(%s)
                       AND (%s='' OR learned_at_utc>=%s))
                """,
                (
                    normalized_user, keys,
                    normalized_user, app.clean(bucket_rows.get("day", "")), keys, app.clean(reset_rows.get("day", "")), app.clean(reset_rows.get("day", "")),
                    normalized_user, app.clean(bucket_rows.get("week", "")), keys, app.clean(reset_rows.get("week", "")), app.clean(reset_rows.get("week", "")),
                    normalized_user, app.clean(bucket_rows.get("month", "")), keys, app.clean(reset_rows.get("month", "")), app.clean(reset_rows.get("month", "")),
                ),
            )
            row = cursor.fetchone() or (0, 0, 0, 0)
        known = max(0, int(row[0] or 0))
        total = len(keys)
        recorded = {"day": max(0, int(row[1] or 0)), "week": max(0, int(row[2] or 0)), "month": max(0, int(row[3] or 0))}
        return {
            "total_words": total,
            "known_words": known,
            "new_words": max(0, total - known),
            "top_earnable": {scope: max(0, total - recorded[scope]) for scope in ("day", "week", "month")},
        }

    return app.postgres_execute(_read)


def replace_registry(username: str, registry: dict) -> dict:
    """Added 2026-07-27: replace learned vocabulary registry in PostgreSQL-only runtime."""
    normalized_user = app.normalize_username(username)
    if not normalized_user:
        raise RuntimeError("Missing PostgreSQL vocabulary username.")
    raw_words = registry.get("words") if isinstance(registry.get("words"), dict) else {}
    now_text = app.utc_timestamp()
    rows = []
    for raw_key, raw_item in raw_words.items():
        item = raw_item if isinstance(raw_item, dict) else {}
        key = app.vocab_key(raw_key or item.get("word", ""))
        if not key:
            continue
        last_at = app.normalize_timestamp_text(item.get("last")) if app.clean(item.get("last")) else ""
        rows.append(
            (
                normalized_user,
                key,
                app.clean(item.get("word")) or key,
                app.clean(item.get("meaning")),
                app.clean(item.get("pron")),
                app.clean(item.get("type")),
                max(0, app.space_w_int(item.get("count", 0), 0)),
                app.clean(item.get("first")),
                last_at,
                app.timestamp_to_epoch(last_at) if last_at else 0.0,
                json.dumps(item.get("sources") if isinstance(item.get("sources"), list) else [], ensure_ascii=False, separators=(",", ":")),
                bool(item.get("qmdict_missing")),
                now_text,
            )
        )

    def _write(connection):
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO future_server2.users(username,is_admin,is_test,profile_json,updated_at_utc,updated_epoch,migrated_at_utc,source_sha256)
                VALUES (%s,false,false,'{}'::jsonb,%s,%s,%s,'')
                ON CONFLICT(username) DO NOTHING
                """,
                (normalized_user, now_text, app.timestamp_to_epoch(now_text), now_text),
            )
            cursor.execute("DELETE FROM future_server2.vocabulary_registry WHERE username=%s", (normalized_user,))
            if rows:
                cursor.executemany(
                    """
                    INSERT INTO future_server2.vocabulary_registry
                        (username,word_key,word,meaning,pron,word_type,learn_count,first_at_utc,last_at_utc,last_epoch,sources_json,qmdict_missing,migrated_at_utc,source_sha256)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s,%s,'')
                    """,
                    rows,
                )
            return _public_payload(cursor, normalized_user)

    return app.postgres_execute(_write)

def record_transaction(
    username: str,
    learned: list[dict],
    source_path: str,
    increment_count: bool,
    now_stamp: str,
    buckets: dict,
    run_marker: str = "",
    record_period_activity: bool = True,
) -> dict:
    normalized_user = app.normalize_username(username)
    if not normalized_user:
        raise RuntimeError("Missing PostgreSQL vocabulary username.")
    now_text = app.normalize_timestamp_text(now_stamp, fallback_now=True)
    source = app.clean(source_path)

    def _write(connection):
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO future_server2.users(username,is_admin,is_test,profile_json,updated_at_utc,updated_epoch,migrated_at_utc,source_sha256)
                VALUES (%s,false,false,'{}'::jsonb,%s,%s,%s,'')
                ON CONFLICT(username) DO NOTHING
                """,
                (normalized_user, now_text, app.timestamp_to_epoch(now_text), app.utc_timestamp()),
            )
            items_by_key = {}
            for item in learned:
                key = app.vocab_key(item.get("word", ""))
                if key:
                    items_by_key[key] = item
            if items_by_key:
                keys = sorted(items_by_key)
                cursor.execute(
                    """
                    SELECT registry.word_key,registry.learn_count,registry.first_at_utc,registry.sources_json,totals.total_words
                    FROM (
                        SELECT COUNT(*)::bigint AS total_words
                        FROM future_server2.vocabulary_registry
                        WHERE username=%s
                    ) totals
                    LEFT JOIN future_server2.vocabulary_registry registry
                      ON registry.username=%s AND registry.word_key=ANY(%s)
                    """,
                    (normalized_user, normalized_user, keys),
                )
                existing_rows = cursor.fetchall()
                existing_total_words = int(existing_rows[0][4] or 0) if existing_rows else 0
                existing = {app.clean(row[0]): row for row in existing_rows if app.clean(row[0])}
                registry_rows = []
                event_rows = []
                added = 0
                updated = 0
                for key in keys:
                    item = items_by_key[key]
                    previous = existing.get(key)
                    if previous is None:
                        added += 1
                        previous_count = 0
                        first_at = now_text
                        previous_sources = []
                    else:
                        updated += 1
                        previous_count = max(0, app.space_w_int(previous[1], 0))
                        first_at = app.clean(previous[2]) or now_text
                        previous_sources = previous[3] if isinstance(previous[3], list) else []
                    sources = [app.clean(value) for value in previous_sources if app.clean(value)]
                    if source and source not in sources:
                        sources.append(source)
                    source_count = max(0, app.space_w_int(item.get("count", 0), 0))
                    next_count = previous_count + 1 if increment_count else max(1, previous_count, source_count)
                    registry_rows.append(
                        (
                            normalized_user,
                            key,
                            app.clean(item.get("word")) or key,
                            app.clean(item.get("meaning")),
                            app.clean(item.get("pron")),
                            app.clean(item.get("type")),
                            next_count,
                            first_at,
                            now_text,
                            app.timestamp_to_epoch(now_text),
                            json.dumps(sources[-40:], ensure_ascii=False, separators=(",", ":")),
                            bool(item.get("qmdict_missing")),
                            app.utc_timestamp(),
                        )
                    )
                    if record_period_activity:
                        event_key = hashlib.sha1(
                            f"{normalized_user}|{key}|{app.clean(run_marker) or source}|{app.clean(buckets.get('day',''))}".encode("utf-8")
                        ).hexdigest()
                        event_rows.append(
                            (
                                normalized_user,
                                key,
                                source,
                                event_key,
                                now_text,
                                app.timestamp_to_epoch(now_text),
                                app.clean(buckets.get("day")),
                                app.clean(buckets.get("week")),
                                app.clean(buckets.get("month")),
                                app.utc_timestamp(),
                            )
                        )
                recorded = {"day": 0, "week": 0, "month": 0}
                inserted_event_keys = set()
                event_ids = {}
                if event_rows:
                    # Added 2026-07-29: insert all learned-word events in one
                    # set-based round-trip; Earn remains keyed by inserted events.
                    cursor.execute(
                        """
                        INSERT INTO future_server2.vocabulary_events
                            (id,username,word_key,source_path,event_key,learned_at_utc,learned_epoch,local_day,iso_week,local_month,migrated_at_utc,source_sha256)
                        SELECT nextval('future_server2.vocabulary_events_runtime_id_seq'), rows.username,rows.word_key,rows.source_path,rows.event_key,
                               rows.learned_at_utc,rows.learned_epoch,rows.local_day,rows.iso_week,rows.local_month,rows.migrated_at_utc,''
                        FROM unnest(
                            %s::text[],%s::text[],%s::text[],%s::text[],%s::text[],%s::double precision[],
                            %s::text[],%s::text[],%s::text[],%s::text[]
                        ) AS rows(username,word_key,source_path,event_key,learned_at_utc,learned_epoch,local_day,iso_week,local_month,migrated_at_utc)
                        ON CONFLICT(username,word_key,event_key) DO NOTHING
                        RETURNING event_key,id
                        """,
                        tuple([row[index] for row in event_rows] for index in range(10)),
                    )
                    for inserted in cursor.fetchall():
                        inserted_key = app.clean(inserted[0])
                        if inserted_key:
                            inserted_event_keys.add(inserted_key)
                            event_ids[inserted_key] = int(inserted[1])
                effective_registry_rows = registry_rows
                if record_period_activity:
                    inserted_word_keys = {
                        row[1]
                        for row in event_rows
                        if app.clean(row[3]) in inserted_event_keys
                    }
                    effective_registry_rows = [row for row in registry_rows if row[1] in inserted_word_keys]
                    added = sum(1 for row in effective_registry_rows if row[1] not in existing)
                    updated = len(effective_registry_rows) - added
                if effective_registry_rows:
                    # Added 2026-07-29: one set-based upsert avoids executing
                    # one PostgreSQL statement per learned vocabulary word.
                    cursor.execute(
                        """
                        INSERT INTO future_server2.vocabulary_registry
                            (username,word_key,word,meaning,pron,word_type,learn_count,first_at_utc,last_at_utc,last_epoch,sources_json,qmdict_missing,migrated_at_utc,source_sha256)
                        SELECT rows.username,rows.word_key,rows.word,rows.meaning,rows.pron,rows.word_type,rows.learn_count,
                               rows.first_at_utc,rows.last_at_utc,rows.last_epoch,rows.sources_json::jsonb,
                               rows.qmdict_missing,rows.migrated_at_utc,''
                        FROM unnest(
                            %s::text[],%s::text[],%s::text[],%s::text[],%s::text[],%s::text[],%s::integer[],
                            %s::text[],%s::text[],%s::double precision[],%s::text[],%s::boolean[],%s::text[]
                        ) AS rows(username,word_key,word,meaning,pron,word_type,learn_count,first_at_utc,last_at_utc,last_epoch,sources_json,qmdict_missing,migrated_at_utc)
                        ON CONFLICT(username,word_key) DO UPDATE SET
                            word=excluded.word,
                            meaning=CASE WHEN excluded.meaning='' THEN future_server2.vocabulary_registry.meaning ELSE excluded.meaning END,
                            pron=CASE WHEN excluded.pron='' THEN future_server2.vocabulary_registry.pron ELSE excluded.pron END,
                            word_type=CASE WHEN excluded.word_type='' THEN future_server2.vocabulary_registry.word_type ELSE excluded.word_type END,
                            learn_count=excluded.learn_count,
                            last_at_utc=excluded.last_at_utc,
                            last_epoch=excluded.last_epoch,
                            sources_json=excluded.sources_json,
                            qmdict_missing=excluded.qmdict_missing,
                            migrated_at_utc=excluded.migrated_at_utc
                        """,
                        tuple([row[index] for row in effective_registry_rows] for index in range(13)),
                    )
                if event_rows:
                    earn_rows = []
                    migrated_at = app.utc_timestamp()
                    for row in event_rows:
                        event_key = app.clean(row[3])
                        if event_key not in inserted_event_keys:
                            continue
                        for scope, bucket_index in (("day", 6), ("week", 7), ("month", 8)):
                            bucket = app.clean(row[bucket_index])
                            if bucket:
                                earn_rows.append((scope, row[0], row[1], bucket, row[4], row[5], event_ids.get(event_key), migrated_at))
                    if earn_rows:
                        # Added 2026-07-29: persist all three Earn scopes in one
                        # PostgreSQL round-trip while retaining separate tables.
                        cursor.execute(
                            """
                            WITH rows AS (
                                SELECT * FROM unnest(
                                    %s::text[],%s::text[],%s::text[],%s::text[],%s::text[],
                                    %s::double precision[],%s::bigint[],%s::text[]
                                ) AS values(scope,username,word_key,bucket,learned_at_utc,learned_epoch,event_id,migrated_at_utc)
                            ), daily AS (
                                INSERT INTO future_server2.daily_earn(username,word_key,day_key,learned_at_utc,learned_epoch,event_id,migrated_at_utc,source_sha256)
                                SELECT username,word_key,bucket,learned_at_utc,learned_epoch,event_id,migrated_at_utc,'' FROM rows WHERE scope='day'
                                ON CONFLICT(username,word_key,day_key) DO NOTHING RETURNING 1
                            ), weekly AS (
                                INSERT INTO future_server2.weekly_earn(username,word_key,week_key,learned_at_utc,learned_epoch,event_id,migrated_at_utc,source_sha256)
                                SELECT username,word_key,bucket,learned_at_utc,learned_epoch,event_id,migrated_at_utc,'' FROM rows WHERE scope='week'
                                ON CONFLICT(username,word_key,week_key) DO NOTHING RETURNING 1
                            ), monthly AS (
                                INSERT INTO future_server2.monthly_earn(username,word_key,month_key,learned_at_utc,learned_epoch,event_id,migrated_at_utc,source_sha256)
                                SELECT username,word_key,bucket,learned_at_utc,learned_epoch,event_id,migrated_at_utc,'' FROM rows WHERE scope='month'
                                ON CONFLICT(username,word_key,month_key) DO NOTHING RETURNING 1
                            )
                            SELECT (SELECT COUNT(*) FROM daily),(SELECT COUNT(*) FROM weekly),(SELECT COUNT(*) FROM monthly)
                            """,
                            tuple([row[index] for row in earn_rows] for index in range(8)),
                        )
                        recorded_row = cursor.fetchone() or (0, 0, 0)
                        recorded = {scope: max(0, int(recorded_row[index] or 0)) for index, scope in enumerate(("day", "week", "month"))}
                total_words = existing_total_words + added
                # Added 2026-07-29: completion only needs the total and timestamp; do not rebuild all registry rows.
                registry = {"version": 1, "updated_at": now_text, "words": {}}
                return {"added": added, "updated": updated, "total_words": total_words, "registry": registry, "recorded": recorded, "event_key": ""}
            recorded = {"day": 0, "week": 0, "month": 0}
            added = 0
            updated = 0
            for item in learned:
                key = app.vocab_key(item.get("word", ""))
                if not key:
                    continue
                cursor.execute(
                    "SELECT learn_count,first_at_utc,sources_json FROM future_server2.vocabulary_registry WHERE username=%s AND word_key=%s",
                    (normalized_user, key),
                )
                previous = cursor.fetchone()
                if previous is None:
                    added += 1
                    previous_count = 0
                    first_at = now_text
                    previous_sources = []
                else:
                    updated += 1
                    previous_count = max(0, app.space_w_int(previous[0], 0))
                    first_at = app.clean(previous[1]) or now_text
                    previous_sources = previous[2] if isinstance(previous[2], list) else []
                sources = [app.clean(value) for value in previous_sources if app.clean(value)]
                if source and source not in sources:
                    sources.append(source)
                source_count = max(0, app.space_w_int(item.get("count", 0), 0))
                next_count = previous_count + 1 if increment_count else max(1, previous_count, source_count)
                cursor.execute(
                    """
                    INSERT INTO future_server2.vocabulary_registry
                        (username,word_key,word,meaning,pron,word_type,learn_count,first_at_utc,last_at_utc,last_epoch,sources_json,qmdict_missing,migrated_at_utc,source_sha256)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s,%s,'')
                    ON CONFLICT(username,word_key) DO UPDATE SET
                        word=excluded.word,
                        meaning=CASE WHEN excluded.meaning='' THEN future_server2.vocabulary_registry.meaning ELSE excluded.meaning END,
                        pron=CASE WHEN excluded.pron='' THEN future_server2.vocabulary_registry.pron ELSE excluded.pron END,
                        word_type=CASE WHEN excluded.word_type='' THEN future_server2.vocabulary_registry.word_type ELSE excluded.word_type END,
                        learn_count=excluded.learn_count,
                        last_at_utc=excluded.last_at_utc,
                        last_epoch=excluded.last_epoch,
                        sources_json=excluded.sources_json,
                        qmdict_missing=excluded.qmdict_missing,
                        migrated_at_utc=excluded.migrated_at_utc
                    """,
                    (
                        normalized_user,
                        key,
                        app.clean(item.get("word")) or key,
                        app.clean(item.get("meaning")),
                        app.clean(item.get("pron")),
                        app.clean(item.get("type")),
                        next_count,
                        first_at,
                        now_text,
                        app.timestamp_to_epoch(now_text),
                        json.dumps(sources[-40:], ensure_ascii=False, separators=(",", ":")),
                        bool(item.get("qmdict_missing")),
                        app.utc_timestamp(),
                    ),
                )
                if not record_period_activity:
                    continue
                event_key = hashlib.sha1(
                    f"{normalized_user}|{key}|{app.clean(run_marker) or source}|{app.clean(buckets.get('day',''))}".encode("utf-8")
                ).hexdigest()
                cursor.execute(
                    """
                    INSERT INTO future_server2.vocabulary_events
                        (id,username,word_key,source_path,event_key,learned_at_utc,learned_epoch,local_day,iso_week,local_month,migrated_at_utc,source_sha256)
                    VALUES (nextval('future_server2.vocabulary_events_runtime_id_seq'),%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'')
                    ON CONFLICT(username,word_key,event_key) DO NOTHING
                    RETURNING id
                    """,
                    (
                        normalized_user,
                        key,
                        source,
                        event_key,
                        now_text,
                        app.timestamp_to_epoch(now_text),
                        app.clean(buckets.get("day")),
                        app.clean(buckets.get("week")),
                        app.clean(buckets.get("month")),
                        app.utc_timestamp(),
                    ),
                )
                inserted = cursor.fetchone()
                cursor.execute(
                    "SELECT id FROM future_server2.vocabulary_events WHERE username=%s AND word_key=%s AND event_key=%s",
                    (normalized_user, key, event_key),
                )
                event_row = cursor.fetchone()
                event_id = int(event_row[0]) if event_row else None
                if inserted is None:
                    continue
                for scope, table, column in (
                    ("day", "future_server2.daily_earn", "day_key"),
                    ("week", "future_server2.weekly_earn", "week_key"),
                    ("month", "future_server2.monthly_earn", "month_key"),
                ):
                    bucket = app.clean(buckets.get(scope))
                    if not bucket:
                        continue
                    cursor.execute(
                        f"""
                        INSERT INTO {table}(username,word_key,{column},learned_at_utc,learned_epoch,event_id,migrated_at_utc,source_sha256)
                        VALUES (%s,%s,%s,%s,%s,%s,%s,'')
                        ON CONFLICT(username,word_key,{column}) DO NOTHING
                        """,
                        (normalized_user, key, bucket, now_text, app.timestamp_to_epoch(now_text), event_id, app.utc_timestamp()),
                    )
                    if int(cursor.rowcount or 0) > 0:
                        recorded[scope] += 1
            cursor.execute("SELECT COUNT(*) FROM future_server2.vocabulary_registry WHERE username=%s", (normalized_user,))
            total_words = int(cursor.fetchone()[0] or 0)
            registry = {"version": 1, "updated_at": now_text, "words": {}}
        return {"added": added, "updated": updated, "total_words": total_words, "registry": registry, "recorded": recorded, "event_key": ""}

    return app.postgres_execute(_write)


def period_scopes(username: str, buckets: dict, resets: dict | None = None) -> dict:
    normalized_user = app.normalize_username(username)
    reset_rows = resets if isinstance(resets, dict) else {}
    if not normalized_user:
        return {}

    def _read(connection):
        out = {}
        with connection.cursor() as cursor:
            for scope, table, column in (
                ("day", "future_server2.daily_earn", "day_key"),
                ("week", "future_server2.weekly_earn", "week_key"),
                ("month", "future_server2.monthly_earn", "month_key"),
            ):
                bucket = app.clean(buckets.get(scope, ""))
                if not bucket:
                    continue
                reset_stamp = app.normalize_timestamp_text(reset_rows.get(scope, "")) if app.clean(reset_rows.get(scope, "")) else ""
                params = [normalized_user, bucket]
                query = f"SELECT word_key,learned_at_utc FROM {table} WHERE username=%s AND {column}=%s"
                if reset_stamp:
                    query += " AND learned_at_utc>=%s"
                    params.append(reset_stamp)
                words = {}
                cursor.execute(query, tuple(params))
                for row in cursor.fetchall():
                    words[app.clean(row[0])] = app.clean(row[1])
                npc_params = [normalized_user, scope, bucket]
                npc_query = "SELECT word_key,learned_at_utc FROM future_server2.npc_period_earn WHERE username=%s AND scope=%s AND bucket_key=%s"
                if reset_stamp:
                    npc_query += " AND learned_at_utc>=%s"
                    npc_params.append(reset_stamp)
                cursor.execute(npc_query, tuple(npc_params))
                for row in cursor.fetchall():
                    words.setdefault(app.clean(row[0]), app.clean(row[1]))
                out[scope] = {"bucket": bucket, "words": words, "updated_at": max(words.values(), default="")}
        return out

    return app.postgres_execute(_read)


# Added 2026-07-30: clear requested leaderboard periods in PostgreSQL authority.
def reset_periods(scopes: list[str] | tuple[str, ...]) -> dict:
    requested = [app.clean(scope).lower() for scope in scopes if app.clean(scope).lower() in {"day", "week", "month"}]
    tables = {
        "day": "future_server2.daily_earn",
        "week": "future_server2.weekly_earn",
        "month": "future_server2.monthly_earn",
    }

    def _write(connection):
        removed = {}
        with connection.cursor() as cursor:
            for scope in requested:
                cursor.execute(f"DELETE FROM {tables[scope]}")
                registered_removed = int(cursor.rowcount or 0)
                cursor.execute("DELETE FROM future_server2.npc_period_earn WHERE scope=%s", (scope,))
                removed[scope] = registered_removed + int(cursor.rowcount or 0)
        return removed

    return app.postgres_execute(_write)


def record_npc_period_activity(username: str, scopes: dict) -> dict:
    normalized_user = app.normalize_username(username)
    if not normalized_user or not isinstance(scopes, dict):
        return {"recorded": 0}

    def _write(connection):
        recorded = 0
        by_scope = {"day": 0, "week": 0, "month": 0}
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1 FROM future_server2.users WHERE username=%s", (normalized_user,))
            if cursor.fetchone() is not None:
                return {"recorded": 0, "registered_user": True}
            for scope in ("day", "week", "month"):
                row = scopes.get(scope) if isinstance(scopes.get(scope), dict) else {}
                bucket = app.clean(row.get("bucket", ""))
                words = row.get("words") if isinstance(row.get("words"), dict) else {}
                if not bucket:
                    continue
                for raw_key, raw_stamp in words.items():
                    word_key = app.vocab_key(raw_key)
                    if not word_key:
                        continue
                    learned_at = app.normalize_timestamp_text(raw_stamp, fallback_now=True)
                    cursor.execute(
                        """
                        INSERT INTO future_server2.npc_period_earn(username,scope,bucket_key,word_key,learned_at_utc,learned_epoch,migrated_at_utc,source_sha256)
                        VALUES (%s,%s,%s,%s,%s,%s,%s,'')
                        ON CONFLICT(username,scope,bucket_key,word_key) DO NOTHING
                        """,
                        (normalized_user, scope, bucket, word_key, learned_at, app.timestamp_to_epoch(learned_at), app.utc_timestamp()),
                    )
                    if int(cursor.rowcount or 0) > 0:
                        recorded += 1
                        by_scope[scope] += 1
        return {"recorded": recorded, **by_scope}

    return app.postgres_execute(_write)
