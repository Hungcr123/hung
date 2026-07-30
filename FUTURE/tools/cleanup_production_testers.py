#!/usr/bin/env python3
"""Remove production tester accounts and their user-owned state.

Dry-run is the default. Destructive cleanup requires --apply and the exact
production roots/DSN; isolated test databases are intentionally rejected.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import psycopg
from psycopg import sql


PRODUCTION_DSN = "postgresql://future_server2_app@127.0.0.1:5432/future_server2"
SERVER_DATA_ROOT = Path(r"C:\server data")
QMLEARN_ROOT = Path(r"C:\QMLearn")
SQLITE_PATH = SERVER_DATA_ROOT / "server2.db"
OUTPUT_PATH = Path(r"C:\Users\Admin\.codex\plans\production_tester_cleanup_20260729.json")
IDENTITY_KEYS = {
    "username", "user", "owner", "task_owner", "target_user", "from_user",
    "to_user", "created_by", "updated_by",
}
TOKEN_RE = re.compile(r"(?i)(?:_?codex[a-z0-9_-]*|testuser)")
REMOVE = object()


def tester_name(value: object) -> bool:
    text = str(value or "").strip().lower()
    return text.startswith("codex") or text == "testuser"


def tester_path_name(value: str) -> bool:
    text = str(value or "").strip().lower()
    return text.startswith("codex") or text.startswith("_codex") or text == "testuser"


def pg_username_tables(connection) -> list[str]:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT columns.table_name
            FROM information_schema.columns columns
            JOIN information_schema.tables tables
              ON tables.table_schema=columns.table_schema AND tables.table_name=columns.table_name
            WHERE columns.table_schema='future_server2'
              AND columns.column_name='username'
              AND tables.table_type='BASE TABLE'
            ORDER BY CASE WHEN columns.table_name='users' THEN 1 ELSE 0 END, columns.table_name
            """
        )
        return [str(row[0]) for row in cursor.fetchall()]


def collect_pg_candidates(connection) -> set[str]:
    candidates: set[str] = set()
    with connection.cursor() as cursor:
        for table in pg_username_tables(connection):
            cursor.execute(
                sql.SQL("SELECT DISTINCT lower(username) FROM {}.{} WHERE lower(username) LIKE 'codex%%' OR lower(username)='testuser'").format(
                    sql.Identifier("future_server2"), sql.Identifier(table)
                )
            )
            candidates.update(str(row[0]) for row in cursor.fetchall() if tester_name(row[0]))
        cursor.execute("SELECT lower(username) FROM future_server2.users WHERE COALESCE(is_test,false)=true")
        candidates.update(str(row[0]) for row in cursor.fetchall() if str(row[0] or "").strip())
    return candidates


def sqlite_username_tables(connection: sqlite3.Connection) -> list[str]:
    tables = [
        str(row[0]) for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        )
    ]
    result = []
    for table in tables:
        quoted = '"' + table.replace('"', '""') + '"'
        columns = {str(row[1]) for row in connection.execute(f"PRAGMA table_info({quoted})")}
        if "username" in columns:
            result.append(table)
    return result


def collect_sqlite_candidates(connection: sqlite3.Connection) -> set[str]:
    candidates: set[str] = set()
    for table in sqlite_username_tables(connection):
        quoted = '"' + table.replace('"', '""') + '"'
        rows = connection.execute(
            f"SELECT DISTINCT lower(username) FROM {quoted} WHERE lower(username) LIKE 'codex%' OR lower(username)='testuser'"
        )
        candidates.update(str(row[0]) for row in rows if tester_name(row[0]))
    return candidates


def matched_paths() -> list[Path]:
    roots = [
        SERVER_DATA_ROOT,
        QMLEARN_ROOT / "users",
        QMLEARN_ROOT / "server_users",
        SERVER_DATA_ROOT / "Picture" / "UserAvatar",
        SERVER_DATA_ROOT / "Picture" / "UserProfile",
        SERVER_DATA_ROOT / "Picture" / "TaskNotice",
    ]
    result: dict[str, Path] = {}
    for root in roots:
        if not root.is_dir():
            continue
        for child in root.iterdir():
            if tester_path_name(child.name):
                result[str(child.resolve()).lower()] = child
    return sorted(result.values(), key=lambda item: str(item).lower())


def collect_filesystem_candidates(paths: list[Path]) -> set[str]:
    candidates = set()
    for path in paths:
        name = path.name.lower().lstrip("_")
        if tester_name(name):
            candidates.add(name)
        match = TOKEN_RE.match(path.name)
        if match and tester_name(match.group(0).lstrip("_")):
            candidates.add(match.group(0).lower().lstrip("_"))
    return candidates


def prune_json(value, candidates: set[str]):
    if isinstance(value, dict):
        for key in IDENTITY_KEYS:
            if str(value.get(key, "")).strip().lower() in candidates:
                return REMOVE, True
        changed = False
        result = {}
        for key, item in value.items():
            if str(key).strip().lower() in candidates:
                changed = True
                continue
            next_item, item_changed = prune_json(item, candidates)
            changed = changed or item_changed
            if next_item is REMOVE:
                continue
            result[key] = next_item
        return result, changed
    if isinstance(value, list):
        changed = False
        result = []
        for item in value:
            next_item, item_changed = prune_json(item, candidates)
            changed = changed or item_changed
            if next_item is REMOVE:
                continue
            result.append(next_item)
        return result, changed
    if isinstance(value, str) and value.strip().lower() in candidates:
        return REMOVE, True
    return value, False


def path_owned_by_tester(path_text: str, candidates: set[str]) -> bool:
    normalized = str(path_text or "").replace("/", "\\").lower()
    parts = [part for part in normalized.split("\\") if part]
    for part in parts:
        if part in candidates:
            return True
        if any(part == f"{candidate}.txt" or part.startswith(candidate + "-") for candidate in candidates):
            return True
    return False


def clean_postgres(connection, candidates: set[str], apply: bool) -> dict:
    result = {"rows": {}, "documents_deleted": 0, "documents_scrubbed": 0, "registry_documents_scrubbed": 0}
    with connection.cursor() as cursor:
        for table in pg_username_tables(connection):
            statement = sql.SQL("SELECT count(*) FROM {}.{} WHERE lower(username)=ANY(%s)").format(
                sql.Identifier("future_server2"), sql.Identifier(table)
            )
            cursor.execute(statement, (sorted(candidates),))
            count = int(cursor.fetchone()[0] or 0)
            if count:
                result["rows"][table] = count
            if apply and count:
                cursor.execute(
                    sql.SQL("DELETE FROM {}.{} WHERE lower(username)=ANY(%s)").format(
                        sql.Identifier("future_server2"), sql.Identifier(table)
                    ),
                    (sorted(candidates),),
                )

        cursor.execute("SELECT path_key,path,content,encoding FROM future_server2.documents")
        for path_key, path, content, encoding in cursor.fetchall():
            raw = bytes(content or b"")
            if path_owned_by_tester(str(path), candidates):
                result["documents_deleted"] += 1
                if apply:
                    cursor.execute("DELETE FROM future_server2.documents WHERE path_key=%s", (path_key,))
                continue
            if str(encoding or "").lower() != "utf-8":
                continue
            try:
                payload = json.loads(raw.decode("utf-8"))
            except Exception:
                continue
            next_payload, changed = prune_json(payload, candidates)
            if not changed or next_payload is REMOVE:
                continue
            result["documents_scrubbed"] += 1
            if apply:
                encoded = json.dumps(next_payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
                cursor.execute(
                    "UPDATE future_server2.documents SET content=%s,sha256=%s,file_size=%s,updated_at_utc=%s,updated_epoch=%s WHERE path_key=%s",
                    (encoded, hashlib.sha256(encoded).hexdigest(), len(encoded), datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"), datetime.now(timezone.utc).timestamp(), path_key),
                )

        cursor.execute("SELECT key,payload_json FROM future_server2.registry_documents")
        for key, payload in cursor.fetchall():
            next_payload, changed = prune_json(payload, candidates)
            if not changed or next_payload is REMOVE:
                continue
            result["registry_documents_scrubbed"] += 1
            if apply:
                cursor.execute("UPDATE future_server2.registry_documents SET payload_json=%s WHERE key=%s", (json.dumps(next_payload, ensure_ascii=False), key))
    if apply:
        connection.commit()
    else:
        connection.rollback()
    return result


def clean_sqlite(connection: sqlite3.Connection, candidates: set[str], apply: bool) -> dict:
    result = {"rows": {}, "documents_deleted": 0, "documents_scrubbed": 0}
    for table in sqlite_username_tables(connection):
        quoted = '"' + table.replace('"', '""') + '"'
        placeholders = ",".join("?" for _ in candidates)
        params = sorted(candidates)
        count = int(connection.execute(f"SELECT count(*) FROM {quoted} WHERE lower(username) IN ({placeholders})", params).fetchone()[0])
        if count:
            result["rows"][table] = count
        if apply and count:
            connection.execute(f"DELETE FROM {quoted} WHERE lower(username) IN ({placeholders})", params)

    for path_key, path, content, encoding in list(connection.execute("SELECT path_key,path,content,encoding FROM documents")):
        raw = content if isinstance(content, bytes) else str(content or "").encode("utf-8")
        if path_owned_by_tester(str(path), candidates):
            result["documents_deleted"] += 1
            if apply:
                connection.execute("DELETE FROM documents WHERE path_key=?", (path_key,))
            continue
        if str(encoding or "").lower() != "utf-8":
            continue
        try:
            payload = json.loads(raw.decode("utf-8"))
        except Exception:
            continue
        next_payload, changed = prune_json(payload, candidates)
        if not changed or next_payload is REMOVE:
            continue
        result["documents_scrubbed"] += 1
        if apply:
            encoded = json.dumps(next_payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
            connection.execute(
                "UPDATE documents SET content=?,sha256=?,file_size=?,updated_at_utc=? WHERE path_key=?",
                (encoded, hashlib.sha256(encoded).hexdigest(), len(encoded), datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"), path_key),
            )
    if apply:
        connection.commit()
        connection.execute("PRAGMA wal_checkpoint(FULL)")
        connection.execute("VACUUM")
    else:
        connection.rollback()
    return result


def scrub_root_json_files(candidates: set[str], apply: bool) -> dict:
    result = {"checked": 0, "changed": 0}
    for path in SERVER_DATA_ROOT.iterdir():
        if not path.is_file() or path.suffix.lower() != ".json":
            continue
        result["checked"] += 1
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        next_payload, changed = prune_json(payload, candidates)
        if not changed or next_payload is REMOVE:
            continue
        result["changed"] += 1
        if apply:
            temporary = path.with_name(path.name + ".tester-cleanup.tmp")
            temporary.write_text(json.dumps(next_payload, ensure_ascii=False, indent=2), encoding="utf-8")
            os.replace(temporary, path)
    return result


def remove_paths(paths: list[Path], apply: bool) -> int:
    if not apply:
        return len(paths)
    removed = 0
    allowed = {
        str(SERVER_DATA_ROOT.resolve()).lower(),
        str((QMLEARN_ROOT / "users").resolve()).lower(),
        str((QMLEARN_ROOT / "server_users").resolve()).lower(),
        str((SERVER_DATA_ROOT / "Picture" / "UserAvatar").resolve()).lower(),
        str((SERVER_DATA_ROOT / "Picture" / "UserProfile").resolve()).lower(),
        str((SERVER_DATA_ROOT / "Picture" / "TaskNotice").resolve()).lower(),
    }
    for path in paths:
        resolved = path.resolve()
        if str(resolved.parent).lower() not in allowed or not tester_path_name(resolved.name):
            raise RuntimeError(f"unsafe tester cleanup path: {resolved}")
        if resolved.is_dir():
            shutil.rmtree(resolved)
        elif resolved.exists():
            resolved.unlink()
        removed += 1
    return removed


def remaining_pg_rows(connection, candidates: set[str]) -> dict[str, int]:
    remaining = {}
    with connection.cursor() as cursor:
        for table in pg_username_tables(connection):
            cursor.execute(
                sql.SQL("SELECT count(*) FROM {}.{} WHERE lower(username)=ANY(%s)").format(
                    sql.Identifier("future_server2"), sql.Identifier(table)
                ),
                (sorted(candidates),),
            )
            count = int(cursor.fetchone()[0] or 0)
            if count:
                remaining[table] = count
    return remaining


def remaining_sqlite_rows(connection: sqlite3.Connection, candidates: set[str]) -> dict[str, int]:
    remaining = {}
    placeholders = ",".join("?" for _ in candidates)
    params = sorted(candidates)
    for table in sqlite_username_tables(connection):
        quoted = '"' + table.replace('"', '""') + '"'
        count = int(connection.execute(
            f"SELECT count(*) FROM {quoted} WHERE lower(username) IN ({placeholders})", params
        ).fetchone()[0])
        if count:
            remaining[table] = count
    return remaining


def remaining_json_state(pg_connection, sqlite_connection: sqlite3.Connection, candidates: set[str]) -> dict[str, int]:
    remaining = {"postgres_documents": 0, "postgres_registry_documents": 0, "sqlite_documents": 0, "root_json": 0}
    with pg_connection.cursor() as cursor:
        cursor.execute("SELECT path,content,encoding FROM future_server2.documents")
        for path, content, encoding in cursor.fetchall():
            if path_owned_by_tester(str(path), candidates):
                remaining["postgres_documents"] += 1
                continue
            if str(encoding or "").lower() != "utf-8":
                continue
            try:
                payload = json.loads(bytes(content or b"").decode("utf-8"))
            except Exception:
                continue
            _next_payload, changed = prune_json(payload, candidates)
            remaining["postgres_documents"] += int(changed)
        cursor.execute("SELECT payload_json FROM future_server2.registry_documents")
        for (payload,) in cursor.fetchall():
            _next_payload, changed = prune_json(payload, candidates)
            remaining["postgres_registry_documents"] += int(changed)
    for path, content, encoding in sqlite_connection.execute("SELECT path,content,encoding FROM documents"):
        if path_owned_by_tester(str(path), candidates):
            remaining["sqlite_documents"] += 1
            continue
        if str(encoding or "").lower() != "utf-8":
            continue
        raw = content if isinstance(content, bytes) else str(content or "").encode("utf-8")
        try:
            payload = json.loads(raw.decode("utf-8"))
        except Exception:
            continue
        _next_payload, changed = prune_json(payload, candidates)
        remaining["sqlite_documents"] += int(changed)
    for path in SERVER_DATA_ROOT.iterdir():
        if not path.is_file() or path.suffix.lower() != ".json":
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        _next_payload, changed = prune_json(payload, candidates)
        remaining["root_json"] += int(changed)
    return remaining


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--confirm-production", default="")
    args = parser.parse_args()
    if args.apply and args.confirm_production != "DELETE-PRODUCTION-TESTERS":
        raise RuntimeError("--apply requires --confirm-production DELETE-PRODUCTION-TESTERS")
    if Path(os.environ.get("FUTURE_SERVER_DATA_ROOT", str(SERVER_DATA_ROOT))).resolve() != SERVER_DATA_ROOT.resolve():
        raise RuntimeError("refusing non-production server-data root")

    paths = matched_paths()
    with psycopg.connect(PRODUCTION_DSN) as pg_connection, sqlite3.connect(SQLITE_PATH) as sqlite_connection:
        candidates = collect_pg_candidates(pg_connection) | collect_sqlite_candidates(sqlite_connection) | collect_filesystem_candidates(paths)
        candidates = {value for value in candidates if tester_name(value)}
        before = {
            "candidate_count": len(candidates),
            "candidate_sample": sorted(candidates)[:20],
            "filesystem_paths": len(paths),
        }
        postgres = clean_postgres(pg_connection, candidates, args.apply)
        sqlite = clean_sqlite(sqlite_connection, candidates, args.apply)
        root_json = scrub_root_json_files(candidates, args.apply)
        removed_paths = remove_paths(paths, args.apply)
        remaining = {
            "postgres_rows": remaining_pg_rows(pg_connection, candidates) if args.apply else {},
            "sqlite_rows": remaining_sqlite_rows(sqlite_connection, candidates) if args.apply else {},
            "json_state": remaining_json_state(pg_connection, sqlite_connection, candidates) if args.apply else {},
            "filesystem_paths": len(matched_paths()) if args.apply else len(paths),
        }
    output = {
        "mode": "apply" if args.apply else "dry-run",
        "production_dsn": "127.0.0.1:5432/future_server2",
        "server_data_root": str(SERVER_DATA_ROOT),
        "qml_root": str(QMLEARN_ROOT),
        "before": before,
        "postgres": postgres,
        "sqlite": sqlite,
        "root_json": root_json,
        "removed_paths": removed_paths,
        "remaining": remaining,
        "ok": (
            not remaining["postgres_rows"]
            and not remaining["sqlite_rows"]
            and not any(remaining["json_state"].values())
            and remaining["filesystem_paths"] == 0
        ) if args.apply else True,
    }
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0 if output["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
