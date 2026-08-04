"""PostgreSQL-backed Structure asset store for PostgreSQL-only Server 2 mode."""

from __future__ import annotations

import gzip
import hashlib
import json
import os
import queue
import threading
import time
from collections import OrderedDict
from pathlib import Path
from typing import Iterator

STRUCTURE_DIRECTORY = Path(os.environ.get("FUTURE_SERVER_DATA_ROOT") or r"C:\server data") / "Structure"
_POOL_LOCK = threading.RLock()
_POOL: dict[str, object] = {"dsn": "", "queue": None, "size": 0}
_RAW_CACHE_LOCK = threading.RLock()
_RAW_CACHE: OrderedDict[str, tuple[int, bytes]] = OrderedDict()
_RAW_CACHE_BYTES = 0
_RAW_CACHE_MAX_BYTES = 128 * 1024 * 1024
_RAW_CACHE_MAX_ITEMS = 96
_OCR_INDEX_LOCK = threading.RLock()
_OCR_INDEX_CACHE: dict[str, object] = {"revision_ns": -1, "folders": {}}


def _dsn() -> str:
    value = str(os.environ.get("FUTURE_PG_DSN") or "").strip()
    if not value:
        raise RuntimeError("FUTURE_PG_DSN is required for PostgreSQL Structure assets.")
    return value


def _driver():
    import psycopg

    return psycopg


def _pool_size() -> int:
    try:
        return max(1, min(32, int(os.environ.get("FUTURE_PG_STRUCTURE_POOL_SIZE", "4") or 4)))
    except Exception:
        return 4


def _get_connection():
    dsn = _dsn()
    with _POOL_LOCK:
        pool = _POOL.get("queue")
        if _POOL.get("dsn") != dsn or pool is None:
            driver = _driver()
            size = _pool_size()
            pool = queue.Queue(maxsize=size)
            for _index in range(size):
                pool.put(driver.connect(dsn, autocommit=False))
            _POOL.update({"dsn": dsn, "queue": pool, "size": size})
    return pool.get(timeout=10)


def _put_connection(connection) -> None:
    pool = _POOL.get("queue")
    if pool is not None:
        pool.put(connection)
    else:
        connection.close()


def _execute(callback):
    connection = _get_connection()
    try:
        result = callback(connection)
        connection.commit()
        return result
    except Exception:
        connection.rollback()
        raise
    finally:
        _put_connection(connection)


def run_postgres_transaction(callback):
    """Run one builder-side PostgreSQL transaction through the shared pool."""
    return _execute(callback)


def _asset_relative_path(path_value: object) -> str:
    raw = str(path_value or "").replace("\\", "/").strip()
    if not raw:
        raise RuntimeError("Structure asset path is empty.")
    absolute = Path(raw)
    if absolute.is_absolute():
        try:
            raw = absolute.resolve().relative_to(STRUCTURE_DIRECTORY.resolve()).as_posix()
        except Exception as exc:
            raise RuntimeError("Structure asset path is outside the managed root.") from exc
    raw = raw.strip("/")
    if raw.lower().startswith("structure/"):
        raw = raw.split("/", 1)[1]
    parts = [part.strip() for part in raw.split("/") if part.strip()]
    if not parts or any(part in {".", ".."} for part in parts):
        raise RuntimeError("Structure asset path is invalid.")
    return "/".join(parts)


def initialize_structure_database(database: Path | None = None) -> dict[str, object]:
    def _read(connection):
        with connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(*), COALESCE(SUM(raw_size), 0) FROM future_server2.assets")
            count, raw_bytes = cursor.fetchone()
            cursor.execute("SELECT COUNT(*) FROM future_server2.registry_documents")
            registry_documents = int(cursor.fetchone()[0] or 0)
            cursor.execute("SELECT COUNT(*) FROM future_server2.ocr_pages")
            ocr_pages = int(cursor.fetchone()[0] or 0)
        return {
            "database": "postgresql:future_server2.assets",
            "journal_mode": "postgresql",
            "synchronous": 0,
            "assets": int(count or 0),
            "raw_bytes": int(raw_bytes or 0),
            "ocr_pages": ocr_pages,
            "registry_documents": registry_documents,
            "migration_complete": int(count or 0) > 0,
        }

    return _execute(_read)


def close_structure_read_pool() -> None:
    with _POOL_LOCK:
        pool = _POOL.get("queue")
        _POOL.update({"dsn": "", "queue": None, "size": 0})
    if pool is not None:
        while not pool.empty():
            try:
                pool.get_nowait().close()
            except Exception:
                pass
    global _RAW_CACHE_BYTES
    with _RAW_CACHE_LOCK:
        _RAW_CACHE.clear()
        _RAW_CACHE_BYTES = 0


def structure_asset_logical_path(path_value: object) -> str:
    return "Structure/" + _asset_relative_path(path_value)


def _asset_row(path_value: object, columns: str):
    relative = _asset_relative_path(path_value)

    def _read(connection):
        with connection.cursor() as cursor:
            cursor.execute(
                f"SELECT {columns} FROM future_server2.assets WHERE path_key=%s",
                (relative.lower(),),
            )
            return cursor.fetchone()

    return _execute(_read)


def structure_asset_exists(path_value: object) -> bool:
    return _asset_row(path_value, "1") is not None


def structure_asset_gzip(path_value: object) -> tuple[bytes, dict[str, object]]:
    row = _asset_row(path_value, "content_gzip,path,raw_size,raw_sha256,source_mtime_ns,revision_ns")
    if row is None:
        raise FileNotFoundError(f"Structure asset not found in PostgreSQL: {structure_asset_logical_path(path_value)}")
    return bytes(row[0]), {
        "path": "Structure/" + str(row[1]),
        "raw_size": int(row[2]),
        "sha256": str(row[3]),
        "source_mtime_ns": int(row[4]),
        "revision_ns": int(row[5]),
    }


def structure_asset_bytes(path_value: object) -> bytes:
    global _RAW_CACHE_BYTES
    relative = _asset_relative_path(path_value)
    row = _asset_row(relative, "revision_ns")
    if row is None:
        raise FileNotFoundError(f"Structure asset not found in PostgreSQL: Structure/{relative}")
    revision_ns = int(row[0])
    with _RAW_CACHE_LOCK:
        cached = _RAW_CACHE.get(relative.lower())
        if cached and cached[0] == revision_ns:
            _RAW_CACHE.move_to_end(relative.lower())
            return cached[1]
    content, _meta = structure_asset_gzip(relative)
    raw = gzip.decompress(content)
    with _RAW_CACHE_LOCK:
        old = _RAW_CACHE.pop(relative.lower(), None)
        if old:
            _RAW_CACHE_BYTES -= len(old[1])
        _RAW_CACHE[relative.lower()] = (revision_ns, raw)
        _RAW_CACHE_BYTES += len(raw)
        while _RAW_CACHE and (len(_RAW_CACHE) > _RAW_CACHE_MAX_ITEMS or _RAW_CACHE_BYTES > _RAW_CACHE_MAX_BYTES):
            _old_key, (_old_revision, old_raw) = _RAW_CACHE.popitem(last=False)
            _RAW_CACHE_BYTES -= len(old_raw)
    return raw


def structure_asset_json(path_value: object) -> dict:
    payload = json.loads(structure_asset_bytes(path_value).decode("utf-8-sig"))
    if not isinstance(payload, dict):
        raise RuntimeError("Structure asset payload is not an object.")
    return payload


def structure_asset_signature(path_value: object) -> tuple[str, int, int]:
    relative = _asset_relative_path(path_value)
    row = _asset_row(relative, "revision_ns,raw_size")
    if row is None:
        return "structure:" + relative.lower(), 0, -1
    return "structure:" + relative.lower(), int(row[0]), int(row[1])


def write_structure_asset_json(path_value: object, payload: dict, database: Path | None = None) -> dict[str, object]:
    relative = _asset_relative_path(path_value)
    raw = json.dumps(payload if isinstance(payload, dict) else {}, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    compressed = gzip.compress(raw, compresslevel=6, mtime=0)
    digest = hashlib.sha256(raw).hexdigest()
    revision_ns = time.time_ns()

    def _write(connection):
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO future_server2.assets(path_key,path,content_gzip,raw_size,raw_sha256,source_mtime_ns,revision_ns)
                VALUES(%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT(path_key) DO UPDATE SET
                  path=EXCLUDED.path,
                  content_gzip=EXCLUDED.content_gzip,
                  raw_size=EXCLUDED.raw_size,
                  raw_sha256=EXCLUDED.raw_sha256,
                  source_mtime_ns=EXCLUDED.source_mtime_ns,
                  revision_ns=EXCLUDED.revision_ns
                """,
                (relative.lower(), relative, compressed, len(raw), digest, revision_ns, revision_ns),
            )

    _execute(_write)
    return {"path": "Structure/" + relative, "raw_size": len(raw), "stored_size": len(compressed), "sha256": digest, "revision_ns": revision_ns}


def write_structure_asset_bytes(path_value: object, payload: bytes, database: Path | None = None) -> dict[str, object]:
    relative = _asset_relative_path(path_value)
    raw = bytes(payload or b"")
    compressed = gzip.compress(raw, compresslevel=6, mtime=0)
    digest = hashlib.sha256(raw).hexdigest()
    revision_ns = time.time_ns()

    def _write(connection):
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO future_server2.assets(path_key,path,content_gzip,raw_size,raw_sha256,source_mtime_ns,revision_ns)
                VALUES(%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT(path_key) DO UPDATE SET
                  path=excluded.path,content_gzip=excluded.content_gzip,raw_size=excluded.raw_size,
                  raw_sha256=excluded.raw_sha256,source_mtime_ns=excluded.source_mtime_ns,revision_ns=excluded.revision_ns
                """,
                (relative.lower(), relative, compressed, len(raw), digest, revision_ns, revision_ns),
            )

    _execute(_write)
    return {"path": "Structure/" + relative, "raw_size": len(raw), "stored_size": len(compressed), "sha256": digest, "revision_ns": revision_ns}


def lesson_id_registry_load(database: Path | None = None) -> tuple[dict, int]:
    def _read(connection):
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT payload_json,revision_ns FROM future_server2.registry_documents WHERE key='lesson_ids'"
            )
            row = cursor.fetchone()
        if row is None:
            return {"version": 1, "ids": {}}, 0
        try:
            payload = json.loads(str(row[0] or "{}"))
        except Exception:
            payload = {}
        if not isinstance(payload, dict):
            payload = {}
        payload.setdefault("version", 1)
        payload.setdefault("ids", {})
        return payload, int(row[1] or 0)

    return _execute(_read)


def lesson_id_registry_write(payload: dict, database: Path | None = None) -> int:
    revision_ns = time.time_ns()
    raw = json.dumps(payload if isinstance(payload, dict) else {}, ensure_ascii=False, separators=(",", ":"))

    def _write(connection):
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO future_server2.registry_documents(key,payload_json,revision_ns)
                VALUES('lesson_ids',%s,%s)
                ON CONFLICT(key) DO UPDATE SET payload_json=excluded.payload_json,revision_ns=excluded.revision_ns
                """,
                (raw, revision_ns),
            )

    _execute(_write)
    return revision_ns


def iter_structure_assets(database: Path | None = None) -> Iterator[tuple[str, bytes]]:
    def _read(connection):
        with connection.cursor() as cursor:
            cursor.execute("SELECT path,content_gzip FROM future_server2.assets ORDER BY path_key")
            return cursor.fetchall()

    for path, content_gzip in _execute(_read):
        yield "Structure/" + str(path), gzip.decompress(bytes(content_gzip))


def ocr_cache_index(database: Path | None = None) -> dict[str, dict[str, object]]:
    def _read(connection):
        with connection.cursor() as cursor:
            cursor.execute("SELECT COALESCE(MAX(source_mtime_ns),0) FROM future_server2.ocr_pages")
            revision_ns = int(cursor.fetchone()[0] or 0)
            with _OCR_INDEX_LOCK:
                if int(_OCR_INDEX_CACHE.get("revision_ns", -1)) == revision_ns:
                    return _OCR_INDEX_CACHE.get("folders", {})
            cursor.execute("SELECT folder_key,folder_path,file_name FROM future_server2.ocr_pages ORDER BY folder_key,file_key")
            folders: dict[str, dict[str, object]] = {}
            for folder_key, folder_path, file_name in cursor.fetchall():
                item = folders.setdefault(str(folder_key), {"path": str(folder_path), "files": set()})
                item["files"].add(str(file_name).lower())
            with _OCR_INDEX_LOCK:
                _OCR_INDEX_CACHE["revision_ns"] = revision_ns
                _OCR_INDEX_CACHE["folders"] = folders
            return folders

    return _execute(_read)


def ocr_cache_page_text(folder_path: object, file_name: object, database: Path | None = None) -> str:
    folder_key = str(folder_path or "").replace("\\", "/").strip("/").lower()
    file_key = str(file_name or "").strip().lower()
    if not folder_key or not file_key:
        return ""

    def _read(connection):
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT content_text FROM future_server2.ocr_pages WHERE folder_key=%s AND file_key=%s",
                (folder_key, file_key),
            )
            row = cursor.fetchone()
            return str(row[0]) if row else ""

    return _execute(_read)


# Added 2026-07-31: expose the OCR revision without transferring every cached page.
def ocr_cache_revision_ns(database: Path | None = None) -> int:
    def _read(connection):
        with connection.cursor() as cursor:
            cursor.execute("SELECT COALESCE(MAX(source_mtime_ns),0) FROM future_server2.ocr_pages")
            return int(cursor.fetchone()[0] or 0)

    return _execute(_read)


# Added 2026-07-31: load one revision-bound OCR text snapshot for bulk vocabulary prioritization.
def ocr_cache_text_snapshot(database: Path | None = None) -> tuple[int, list[str]]:
    def _read(connection):
        with connection.cursor() as cursor:
            cursor.execute("SELECT COALESCE(MAX(source_mtime_ns),0) FROM future_server2.ocr_pages")
            revision_ns = int(cursor.fetchone()[0] or 0)
            cursor.execute(
                "SELECT content_text FROM future_server2.ocr_pages "
                "WHERE content_text IS NOT NULL AND content_text <> '' "
                "ORDER BY folder_key,file_key"
            )
            return revision_ns, [str(row[0]) for row in cursor.fetchall() if row and str(row[0] or "").strip()]

    return _execute(_read)
