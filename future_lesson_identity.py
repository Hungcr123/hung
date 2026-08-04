from __future__ import annotations

import json
import os
import re
import threading
import time
import hashlib
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any



def builder_identity_uses_postgres() -> bool:
    return True


def builder_identity_staging_enabled() -> bool:
    return str(os.environ.get("FUTURE_LESSON_IDENTITY_STAGING", "")).strip().lower() in {"1", "true", "yes", "on"}


from future_postgres_structure_asset_store import (
    lesson_id_registry_load,
    lesson_id_registry_write,
    run_postgres_transaction,
)


SERVER_DATA_ROOT = Path(os.environ.get("FUTURE_SERVER_DATA_ROOT") or r"C:\server data")
LESSON_ID_REGISTRY_PATH = SERVER_DATA_ROOT / "_future_space_lesson_ids.json"
LESSON_ID_LOCK = threading.RLock()
FILE_LESSON_ID_CACHE: dict[tuple[str, int, int, str], str] = {}
LESSON_ID_REGISTRY_CACHE: dict[str, Any] = {"signature": None, "payload": None}
LESSON_ID_REGISTRY_FIELD_INDEX: dict[tuple[int, str], dict[str, list[tuple[str, dict]]]] = {}
LESSON_ID_REGISTRY_PATH_SIZE_INDEX: dict[int, dict[tuple[str, int], str]] = {}
LESSON_ID_FIELD = "lesson_id"
LESSON_ID_CAMEL_FIELD = "lessonId"
LEGACY_ID_FIELDS = ("lesson_id", "lessonId", "identity", "lesson")
LESSON_ID_PREFIX = "ftg-lesson-"


def _clean(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def normalize_lesson_id(value: Any) -> str:
    raw = _clean(value)
    if not raw:
        return ""
    safe = re.sub(r"[^0-9A-Za-z._:-]+", "-", raw).strip("-._:")
    return safe[:120]


def lesson_id_from_payload(payload: dict | None = None) -> str:
    source = payload if isinstance(payload, dict) else {}
    for field in LEGACY_ID_FIELDS:
        value = normalize_lesson_id(source.get(field))
        if value:
            return value
    meta = source.get("meta") if isinstance(source.get("meta"), dict) else {}
    for field in LEGACY_ID_FIELDS:
        value = normalize_lesson_id(meta.get(field))
        if value:
            return value
    return ""


def apply_lesson_id_to_payload(payload: dict, lesson_id: str) -> None:
    clean_id = normalize_lesson_id(lesson_id)
    if not isinstance(payload, dict) or not clean_id:
        return
    payload[LESSON_ID_FIELD] = clean_id
    payload[LESSON_ID_CAMEL_FIELD] = clean_id
    payload["identity"] = clean_id
    payload["lesson"] = clean_id
    meta = payload.get("meta") if isinstance(payload.get("meta"), dict) else {}
    meta = dict(meta)
    meta[LESSON_ID_FIELD] = clean_id
    meta[LESSON_ID_CAMEL_FIELD] = clean_id
    payload["meta"] = meta


def lesson_payload_identity_fingerprint(payload: dict | None = None) -> str:
    # Embedded study (`st` in compact Space payloads) is mutable learner history,
    # not authored lesson content. It must never quarantine an identical replica.
    mutable_root_fields = {"st", "study"}

    def without_identity(value: Any, *, root: bool = False) -> Any:
        if isinstance(value, dict):
            cleaned = {}
            for key, item in value.items():
                if key in LEGACY_ID_FIELDS or (root and key in mutable_root_fields):
                    continue
                next_item = without_identity(item)
                if key == "meta" and isinstance(next_item, dict) and not next_item:
                    continue
                cleaned[key] = next_item
            return cleaned
        if isinstance(value, list):
            return [without_identity(item) for item in value]
        return value

    source = without_identity(payload if isinstance(payload, dict) else {}, root=True)
    encoded = json.dumps(source, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _database_lesson_path(path_value: str | Path = "") -> str:
    target = Path(path_value) if str(path_value or "") else None
    if target is None:
        return ""
    try:
        return target.resolve().relative_to(SERVER_DATA_ROOT.resolve()).as_posix()
    except Exception:
        return str(target).replace("\\", "/").strip()




# Added 2026-07-21: every builder reserves the portable wrapper ID in SQLite before writing the file.
def reserve_lesson_id_in_database(
    payload: dict,
    output_path: str | Path = "",
    space: str = "",
    requested_id: str = "",
) -> str:
    return _reserve_lesson_id_in_postgres(payload, output_path, space, requested_id)



def _reserve_lesson_id_in_postgres(
    payload: dict,
    output_path: str | Path = "",
    space: str = "",
    requested_id: str = "",
) -> str:
    fingerprint = lesson_payload_identity_fingerprint(payload)
    normalized_path = _database_lesson_path(output_path).lower()
    requested_clean = normalize_lesson_id(requested_id)
    now = datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
    now_epoch = time.time()

    def _write(connection):
        with connection.cursor() as cursor:
            if normalized_path:
                cursor.execute(
                    "SELECT pg_advisory_xact_lock(hashtext(%s))",
                    (f"future_server2.lesson_identity.path:{normalized_path}",),
                )
                cursor.execute(
                    "SELECT file_id,fingerprint,status FROM future_server2.lesson_file_replicas "
                    "WHERE lower(normalized_path)=lower(%s)",
                    (normalized_path,),
                )
                existing_path = cursor.fetchone()
            else:
                existing_path = None
            lesson_id = normalize_lesson_id(requested_id)
            if existing_path and not lesson_id and _clean(existing_path[2]).lower() in {"active", "reserved"}:
                lesson_id = normalize_lesson_id(existing_path[0])
            row = None
            if lesson_id:
                cursor.execute(
                    "SELECT canonical_fingerprint FROM future_server2.lesson_files WHERE file_id=%s",
                    (lesson_id,),
                )
                row = cursor.fetchone()
                if row and _clean(row[0]) and _clean(row[0]) != fingerprint:
                    same_path = bool(existing_path and normalize_lesson_id(existing_path[0]) == lesson_id)
                    if same_path:
                        cursor.execute(
                            "SELECT 1 FROM future_server2.lesson_file_replicas WHERE file_id=%s "
                            "AND lower(normalized_path)<>lower(%s) AND status='active' AND fingerprint<>'' "
                            "AND fingerprint<>%s LIMIT 1",
                            (lesson_id, normalized_path, fingerprint),
                        )
                        if cursor.fetchone():
                            raise RuntimeError("Cannot rebuild one replica with divergent content; use Duplicate as New Lesson.")
                    else:
                        if requested_clean:
                            raise RuntimeError("Lesson ID already belongs to different content; use Duplicate as New Lesson.")
                        lesson_id = ""
                        row = None
            while not lesson_id:
                candidate = generate_future_lesson_id()
                cursor.execute(
                    """
                    INSERT INTO future_server2.lesson_files
                        (file_id,space_id,kind,canonical_fingerprint,identity_revision,status,created_at_utc,created_epoch,
                         updated_at_utc,updated_epoch,deleted_at_utc,deleted_epoch,migrated_at_utc,source_sha256)
                    VALUES(%s,%s,'space',%s,1,'active',%s,%s,%s,%s,'',0,%s,%s)
                    ON CONFLICT(file_id) DO NOTHING RETURNING file_id
                    """,
                    (candidate, _clean(space), fingerprint, now, now_epoch, now, now_epoch, now, fingerprint),
                )
                inserted = cursor.fetchone()
                if inserted:
                    lesson_id = candidate
                    row = None
            cursor.execute(
                """
                INSERT INTO future_server2.lesson_files
                    (file_id,space_id,kind,canonical_fingerprint,identity_revision,status,created_at_utc,created_epoch,
                     updated_at_utc,updated_epoch,deleted_at_utc,deleted_epoch,migrated_at_utc,source_sha256)
                VALUES(%s,%s,'space',%s,1,'active',%s,%s,%s,%s,'',0,%s,%s)
                ON CONFLICT(file_id) DO UPDATE SET
                    space_id=CASE WHEN excluded.space_id<>'' THEN excluded.space_id ELSE future_server2.lesson_files.space_id END,
                    canonical_fingerprint=excluded.canonical_fingerprint,status='active',
                    updated_at_utc=excluded.updated_at_utc,updated_epoch=excluded.updated_epoch,
                    migrated_at_utc=excluded.migrated_at_utc,source_sha256=excluded.source_sha256
                """,
                (lesson_id, _clean(space), fingerprint, now, now_epoch, now, now_epoch, now, fingerprint),
            )
            if normalized_path:
                cursor.execute(
                    "SELECT replica_id FROM future_server2.lesson_file_replicas WHERE lower(normalized_path)=lower(%s)",
                    (normalized_path,),
                )
                replica = cursor.fetchone()
                if replica:
                    replica_id = int(replica[0])
                else:
                    cursor.execute("SELECT nextval('future_server2.lesson_file_replicas_runtime_id_seq')")
                    replica_id = int(cursor.fetchone()[0])
                cursor.execute(
                    """
                    INSERT INTO future_server2.lesson_file_replicas
                        (replica_id,file_id,normalized_path,fingerprint,file_mtime_ns,file_size,status,first_seen_at_utc,
                         first_seen_epoch,last_seen_at_utc,last_seen_epoch,migrated_at_utc,source_sha256)
                    VALUES(%s,%s,%s,%s,0,0,'reserved',%s,%s,%s,%s,%s,%s)
                    ON CONFLICT(normalized_path) DO UPDATE SET
                        file_id=excluded.file_id,fingerprint=excluded.fingerprint,status='reserved',
                        last_seen_at_utc=excluded.last_seen_at_utc,last_seen_epoch=excluded.last_seen_epoch,
                        migrated_at_utc=excluded.migrated_at_utc,source_sha256=excluded.source_sha256
                    """,
                    (replica_id, lesson_id, normalized_path, fingerprint, now, now_epoch, now, now_epoch, now, fingerprint),
                )
            return lesson_id

    if not callable(run_postgres_transaction):
        raise RuntimeError("PostgreSQL lesson identity backend is unavailable.")
    return str(run_postgres_transaction(_write))


def _read_registry_unlocked() -> dict:
    try:
        data, revision_ns = lesson_id_registry_load()
        signature = (revision_ns, len(data.get("ids", {})) if isinstance(data.get("ids"), dict) else 0)
        if LESSON_ID_REGISTRY_CACHE.get("signature") == signature and isinstance(LESSON_ID_REGISTRY_CACHE.get("payload"), dict):
            return LESSON_ID_REGISTRY_CACHE["payload"]
        data.setdefault("version", 1)
        data.setdefault("next_id", 1)
        ids = data.setdefault("ids", {})
        max_seen = 0
        if isinstance(ids, dict):
            for lesson_id in ids:
                match = re.fullmatch(re.escape(LESSON_ID_PREFIX) + r"(\d+)", str(lesson_id or ""))
                if match:
                    max_seen = max(max_seen, int(match.group(1) or 0))
        data["next_id"] = max(int(data.get("next_id") or 1), max_seen + 1)
        LESSON_ID_REGISTRY_CACHE["signature"] = signature
        LESSON_ID_REGISTRY_CACHE["payload"] = data
        LESSON_ID_REGISTRY_FIELD_INDEX.clear()
        LESSON_ID_REGISTRY_PATH_SIZE_INDEX.clear()
        return data
    except Exception:
        pass
    return {"version": 1, "next_id": 1, "ids": {}}


def _write_registry_unlocked(registry: dict) -> None:
    revision_ns = lesson_id_registry_write(registry)
    LESSON_ID_REGISTRY_CACHE["signature"] = (revision_ns, len(registry.get("ids", {})))
    LESSON_ID_REGISTRY_CACHE["payload"] = registry
    LESSON_ID_REGISTRY_FIELD_INDEX.clear()
    LESSON_ID_REGISTRY_PATH_SIZE_INDEX.clear()


# Added 2026-07-21: random IDs remain collision-safe when builders run on separate machines.
def generate_future_lesson_id(reserved: object = None) -> str:
    blocked = {
        normalize_lesson_id(value)
        for value in (reserved if isinstance(reserved, (set, list, tuple, dict)) else [])
        if normalize_lesson_id(value)
    }
    for _index in range(32):
        lesson_id = f"{LESSON_ID_PREFIX}{uuid.uuid4().hex}"
        if lesson_id not in blocked:
            return lesson_id
    raise RuntimeError("Unable to allocate a unique Future lesson ID.")


def _next_registry_lesson_id(registry: dict) -> str:
    ids = registry.setdefault("ids", {})
    return generate_future_lesson_id(ids)


FILE_TIER1_BYTES = 256 * 1024
FILE_TIER2_BYTES = 1024 * 1024
FILE_TIER3_BYTES = 2 * 1024 * 1024
FILE_FULL_HASH_MAX_BYTES = 8 * 1024 * 1024


def file_content_sha256(path: str | Path) -> str:
    hasher = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def file_tier_fingerprint(path: str | Path, sample_bytes: int, points: tuple[float, ...]) -> str:
    target = Path(path)
    stat = target.stat()
    size = int(stat.st_size)
    hasher = hashlib.sha256()
    hasher.update(str(size).encode("ascii"))
    with target.open("rb") as handle:
        if size <= sample_bytes * max(1, len(points)):
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                hasher.update(chunk)
            return f"tier-full:{size}:{sample_bytes}:{hasher.hexdigest()}"
        seen_offsets: set[int] = set()
        for point in points:
            point = max(0.0, min(1.0, float(point)))
            offset = int(max(0, min(size - sample_bytes, round((size - sample_bytes) * point))))
            if offset in seen_offsets:
                continue
            seen_offsets.add(offset)
            handle.seek(offset)
            hasher.update(handle.read(sample_bytes))
    return f"tier-sample:{size}:{sample_bytes}:{len(seen_offsets)}:{hasher.hexdigest()}"


def file_fast_fingerprint(path: str | Path) -> str:
    return file_tier_fingerprint(path, FILE_TIER1_BYTES, (0.0, 1.0))


def file_name_scope_fingerprint(path: str | Path, root: str | Path = SERVER_DATA_ROOT) -> str:
    target = Path(path)
    try:
        stat = target.stat()
        size = int(stat.st_size)
    except Exception:
        size = 0
    try:
        rel_parts = target.resolve().relative_to(Path(root).resolve()).parts
    except Exception:
        rel_parts = target.parts
    parent = rel_parts[-2].lower() if len(rel_parts) >= 2 else ""
    name = target.name.lower()
    return f"name-scope:{parent}/{name}:{size}"


def file_lesson_id_cache_key(path: Path, space: str = "") -> tuple[str, int, int, str]:
    try:
        stat = path.stat()
        resolved = str(path.resolve()).lower()
        return (resolved, int(stat.st_size), int(stat.st_mtime_ns), _clean(space))
    except Exception:
        return (str(path).lower(), 0, 0, _clean(space))


def _registry_rows_for_file_identity(registry: dict, field: str, value: str = "") -> list[tuple[str, dict]]:
    target_value = _clean(value).lower()
    if not target_value:
        return []
    index_key = (id(registry), field)
    index = LESSON_ID_REGISTRY_FIELD_INDEX.get(index_key)
    if index is None:
        index = {}
        ids = registry.setdefault("ids", {})
        for lesson_id, row in ids.items():
            if not isinstance(row, dict):
                continue
            row_value = _clean(row.get(field, "")).lower()
            if row_value:
                index.setdefault(row_value, []).append((normalize_lesson_id(lesson_id), row))
        LESSON_ID_REGISTRY_FIELD_INDEX[index_key] = index
    return list(index.get(target_value, []))


def _registry_id_for_path_size(registry: dict, path: Path, size: int = 0) -> str:
    try:
        key = (str(path.resolve()).lower(), int(size))
    except Exception:
        key = (str(path).lower(), int(size))
    index_key = id(registry)
    index = LESSON_ID_REGISTRY_PATH_SIZE_INDEX.get(index_key)
    if index is None:
        index = {}
        ids = registry.setdefault("ids", {})
        for lesson_id, row in ids.items():
            if not isinstance(row, dict):
                continue
            try:
                row_size = int(row.get("file_size", 0) or 0)
            except Exception:
                row_size = 0
            row_paths = row.get("paths") if isinstance(row.get("paths"), list) else []
            for value in [row.get("last_path", ""), row.get("first_path", ""), *row_paths]:
                raw = _clean(value)
                if raw:
                    index[(raw.lower(), row_size)] = normalize_lesson_id(lesson_id)
        LESSON_ID_REGISTRY_PATH_SIZE_INDEX[index_key] = index
    return index.get(key, "")


def _row_existing_path(row: dict) -> Path | None:
    paths = row.get("paths") if isinstance(row.get("paths"), list) else []
    for value in [row.get("last_path", ""), row.get("first_path", ""), *paths]:
        raw = _clean(value)
        if not raw:
            continue
        try:
            path = Path(raw)
            if path.is_file():
                return path
        except Exception:
            continue
    return None


def _ensure_row_fingerprint(row: dict, field: str, sample_bytes: int, points: tuple[float, ...]) -> str:
    existing = _clean(row.get(field, ""))
    if existing:
        return existing
    path = _row_existing_path(row)
    if path is None:
        return ""
    try:
        value = file_tier_fingerprint(path, sample_bytes, points)
        row[field] = value
        return value
    except Exception:
        return ""


def _ensure_row_full_hash(row: dict) -> str:
    existing = _clean(row.get("content_sha256", ""))
    if existing:
        return existing
    path = _row_existing_path(row)
    if path is None:
        return ""
    try:
        value = file_content_sha256(path)
        row["content_sha256"] = value
        return value
    except Exception:
        return ""


def _unique_id_from_rows(rows: list[tuple[str, dict]]) -> str:
    ids = sorted({normalize_lesson_id(lesson_id) for lesson_id, _row in rows if normalize_lesson_id(lesson_id)})
    return ids[0] if len(ids) == 1 else ""


def _registry_id_for_file_identity(registry: dict, target: Path, *, content_fingerprint: str = "", content_hash: str = "") -> tuple[str, str]:
    tier1 = _clean(content_fingerprint).lower()
    target_hash = _clean(content_hash).lower()
    if tier1:
        rows = _registry_rows_for_file_identity(registry, "content_fingerprint_t1", tier1)
        rows.extend(_registry_rows_for_file_identity(registry, "content_fingerprint", tier1))
        lesson_id = _unique_id_from_rows(rows)
        if lesson_id:
            return lesson_id, "tier1"
        if rows:
            tier2 = file_tier_fingerprint(target, FILE_TIER2_BYTES, (0.0, 0.5, 1.0))
            tier2_rows = [
                (lesson_id, row)
                for lesson_id, row in rows
                if _ensure_row_fingerprint(row, "content_fingerprint_t2", FILE_TIER2_BYTES, (0.0, 0.5, 1.0)).lower() == tier2.lower()
            ]
            lesson_id = _unique_id_from_rows(tier2_rows)
            if lesson_id:
                return lesson_id, "tier2"
            if tier2_rows:
                tier3 = file_tier_fingerprint(target, FILE_TIER3_BYTES, (0.0, 0.25, 0.5, 0.75, 1.0))
                tier3_rows = [
                    (lesson_id, row)
                    for lesson_id, row in tier2_rows
                    if _ensure_row_fingerprint(row, "content_fingerprint_t3", FILE_TIER3_BYTES, (0.0, 0.25, 0.5, 0.75, 1.0)).lower() == tier3.lower()
                ]
                lesson_id = _unique_id_from_rows(tier3_rows)
                if lesson_id:
                    return lesson_id, "tier3"
                if tier3_rows:
                    full_hash = target_hash or file_content_sha256(target)
                    hash_rows = [
                        (lesson_id, row)
                        for lesson_id, row in tier3_rows
                        if _ensure_row_full_hash(row).lower() == full_hash.lower()
                    ]
                    lesson_id = _unique_id_from_rows(hash_rows)
                    if lesson_id:
                        return lesson_id, "tier4_full_hash"
                    return "", full_hash
    if target_hash:
        legacy_id = _legacy_registry_id_for_content_hash(registry, target_hash)
        if legacy_id:
            return legacy_id, "legacy_full_hash"
    return "", ""


def _legacy_registry_id_for_content_hash(registry: dict, content_hash: str = "") -> str:
    target_hash = _clean(content_hash).lower()
    if not target_hash:
        return ""
    ids = registry.setdefault("ids", {})
    for lesson_id, row in ids.items():
        if isinstance(row, dict) and _clean(row.get("content_sha256", "")).lower() == target_hash:
            return normalize_lesson_id(lesson_id)
    return ""


# Added 2026-07-05: assigns stable ids to raw PDF/Picture files without modifying the binary file.
def ensure_future_file_lesson_id(path: str | Path, space: str = "") -> str:
    target = Path(path)
    if not target.is_file():
        return ""
    cache_key = file_lesson_id_cache_key(target, space)
    with LESSON_ID_LOCK:
        cached_id = FILE_LESSON_ID_CACHE.get(cache_key)
    if cached_id:
        return cached_id
    output = str(target)
    try:
        stat = target.stat()
        size = int(stat.st_size)
    except Exception:
        size = 0
    try:
        rel_parts = target.resolve().relative_to(SERVER_DATA_ROOT.resolve()).parts
    except Exception:
        rel_parts = ()
    with LESSON_ID_LOCK:
        registry = _read_registry_unlocked()
        path_size_id = _registry_id_for_path_size(registry, target, size)
        if path_size_id:
            FILE_LESSON_ID_CACHE[cache_key] = path_size_id
            return path_size_id
    suffix = target.suffix.lower()
    use_name_scope = bool(
        (rel_parts and rel_parts[0].lower() == "cache orc")
        or (_clean(space) == "Space_Picture")
    )
    content_fingerprint = file_name_scope_fingerprint(target) if use_name_scope else file_fast_fingerprint(target)
    content_hash = ""
    if not use_name_scope and size <= FILE_FULL_HASH_MAX_BYTES:
        content_hash = content_fingerprint.rsplit(":", 1)[-1]
    now_ms = int(time.time() * 1000)
    with LESSON_ID_LOCK:
        cached_id = FILE_LESSON_ID_CACHE.get(cache_key)
        if cached_id:
            return cached_id
        registry = _read_registry_unlocked()
        path_size_id = _registry_id_for_path_size(registry, target, size)
        if path_size_id:
            FILE_LESSON_ID_CACHE[cache_key] = path_size_id
            return path_size_id
        ids = registry.setdefault("ids", {})
        lesson_id, identity_source = _registry_id_for_file_identity(
            registry,
            target,
            content_fingerprint=content_fingerprint,
            content_hash=content_hash,
        )
        if identity_source and len(identity_source) == 64 and all(char in "0123456789abcdef" for char in identity_source.lower()):
            content_hash = identity_source.lower()
        if not lesson_id:
            lesson_id = _next_registry_lesson_id(registry)
        row = ids.get(lesson_id) if isinstance(ids.get(lesson_id), dict) else {}
        dirty = False
        if not row:
            row = {
                "id": lesson_id,
                "created_ms": now_ms,
                "created_at": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(now_ms / 1000)),
                "first_path": output,
                "first_name": target.name,
                "space": _clean(space),
            }
            dirty = True
        else:
            row = dict(row)
        paths = row.get("paths") if isinstance(row.get("paths"), list) else []
        if output and output not in paths:
            paths.append(output)
            next_paths = paths[-20:]
            if row.get("paths") != next_paths:
                row["paths"] = next_paths
                dirty = True
            if output and row.get("last_path", "") != output:
                row["last_path"] = output
                dirty = True
        elif not isinstance(row.get("paths"), list):
            row["paths"] = paths[-20:]
            dirty = True
        if not row.get("last_seen_ms"):
            row["last_seen_ms"] = now_ms
            dirty = True
        next_space = _clean(space) or _clean(row.get("space", ""))
        if row.get("space", "") != next_space:
            row["space"] = next_space
            dirty = True
        if row.get("content_fingerprint", "") != content_fingerprint:
            row["content_fingerprint"] = content_fingerprint
            dirty = True
        if row.get("content_fingerprint_t1", "") != content_fingerprint:
            row["content_fingerprint_t1"] = content_fingerprint
            dirty = True
        if content_hash and row.get("content_sha256", "") != content_hash:
            row["content_sha256"] = content_hash
            dirty = True
        if row.get("file_size") != size:
            row["file_size"] = size
            dirty = True
        if row.get("file_identity_kind", "") != "content_fingerprint":
            row["file_identity_kind"] = "content_fingerprint"
            dirty = True
        next_source = identity_source or ("full_hash" if content_hash else "fast_fingerprint")
        if row.get("file_identity_source", "") != next_source:
            row["file_identity_source"] = next_source
            dirty = True
        if next_source in {"tier2", "tier3", "tier4_full_hash"}:
            dirty = True
        if dirty:
            ids[lesson_id] = row
            _write_registry_unlocked(registry)
        FILE_LESSON_ID_CACHE[cache_key] = lesson_id
    return lesson_id


# Added 2026-07-04: gives every Space lesson a stable id that survives copy/rename.
def ensure_future_lesson_id(payload: dict, output_path: str | Path = "", space: str = "") -> str:
    if not isinstance(payload, dict):
        raise RuntimeError("Future lesson payload must be a JSON object.")
    existing = lesson_id_from_payload(payload)
    output = str(output_path or "")
    if builder_identity_staging_enabled():
        # Builder output is not visible to learners until Server 2 validates and
        # publishes the staged manifest/identity batch.
        lesson_id = existing or generate_future_lesson_id()
        apply_lesson_id_to_payload(payload, lesson_id)
        return lesson_id
    now_ms = int(time.time() * 1000)
    lesson_id = reserve_lesson_id_in_database(payload, output, space, requested_id=existing)
    with LESSON_ID_LOCK:
        registry = _read_registry_unlocked()
        ids = registry.setdefault("ids", {})
        if lesson_id in ids and _clean(ids.get(lesson_id, {}).get("deleted", "")):
            lesson_id = reserve_lesson_id_in_database(payload, output, space, requested_id="")
        row = ids.get(lesson_id) if isinstance(ids.get(lesson_id), dict) else {}
        if not row:
            row = {
                "id": lesson_id,
                "created_ms": now_ms,
                "created_at": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(now_ms / 1000)),
                "first_path": output,
                "first_name": Path(output).name if output else "",
                "space": _clean(space),
            }
        else:
            row = dict(row)
        paths = row.get("paths") if isinstance(row.get("paths"), list) else []
        if output and output not in paths:
            paths.append(output)
        row["paths"] = paths[-20:]
        row["last_path"] = output or row.get("last_path", "")
        row["last_seen_ms"] = now_ms
        row["space"] = _clean(space) or _clean(row.get("space", ""))
        ids[lesson_id] = row
        _write_registry_unlocked(registry)
    apply_lesson_id_to_payload(payload, lesson_id)
    return lesson_id


def register_existing_lesson_id(payload: dict, path: str | Path = "", space: str = "") -> str:
    return ensure_future_lesson_id(payload, output_path=path, space=space)
