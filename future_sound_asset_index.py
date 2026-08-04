from __future__ import annotations

import hashlib
import json
import os
import re
import threading
import time
from pathlib import Path


SERVER_DATA_ROOT = Path(os.environ.get("FUTURE_SERVER_DATA_ROOT", "") or r"C:\server data")
SERVER_SOUND_DIR = SERVER_DATA_ROOT / "Sound"
SERVER_SOUND_V2_DIR = SERVER_SOUND_DIR / "_v2"
SOUND_ASSET_INDEX_FILE = SERVER_DATA_ROOT / "_future_sound_asset_index.json"
SOUND_ASSET_INDEX_WAL_FILE = SERVER_DATA_ROOT / "_future_sound_asset_index.wal.jsonl"
SOUND_ASSET_INDEX_VERSION = 1
SOUND_ASSET_ALLOWED_EXTENSIONS = {
    "mp3", "wav", "m4a", "ogg",
    "webm", "mp4", "m4v", "mov", "avi", "mkv", "wmv", "flv", "mpeg", "mpg",
}

SOUND_ASSET_INDEX_LOCK = threading.RLock()
SOUND_ASSET_INDEX_RAM: dict | None = None
SOUND_ASSET_INDEX_DIRTY = False
SOUND_ASSET_INDEX_FLUSH_TIMER: threading.Timer | None = None


# Added 2026-08-01: switches the index to the active Server 2 root without carrying cached entries across production/test roots.
def configure_sound_asset_root(root: object) -> Path:
    global SERVER_DATA_ROOT, SERVER_SOUND_DIR, SERVER_SOUND_V2_DIR
    global SOUND_ASSET_INDEX_FILE, SOUND_ASSET_INDEX_WAL_FILE
    global SOUND_ASSET_INDEX_RAM, SOUND_ASSET_INDEX_DIRTY, SOUND_ASSET_INDEX_FLUSH_TIMER
    target = Path(root or r"C:\server data").resolve()
    with SOUND_ASSET_INDEX_LOCK:
        if SERVER_DATA_ROOT.resolve() == target:
            return target
        if SOUND_ASSET_INDEX_DIRTY and SOUND_ASSET_INDEX_RAM is not None:
            write_sound_asset_index_now("root-switch")
        if SOUND_ASSET_INDEX_FLUSH_TIMER is not None:
            SOUND_ASSET_INDEX_FLUSH_TIMER.cancel()
        SERVER_DATA_ROOT = target
        SERVER_SOUND_DIR = target / "Sound"
        SERVER_SOUND_V2_DIR = SERVER_SOUND_DIR / "_v2"
        SOUND_ASSET_INDEX_FILE = target / "_future_sound_asset_index.json"
        SOUND_ASSET_INDEX_WAL_FILE = target / "_future_sound_asset_index.wal.jsonl"
        SOUND_ASSET_INDEX_RAM = None
        SOUND_ASSET_INDEX_DIRTY = False
        SOUND_ASSET_INDEX_FLUSH_TIMER = None
    return target


def sound_asset_timestamp() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def clean_sound_asset_text(value: object = "") -> str:
    return str(value or "").replace("\r", " ").replace("\n", " ").replace("\t", " ").strip()


def sound_asset_safe_segment(value: object = "", fallback: str = "asset", limit: int = 64) -> str:
    text = re.sub(r"[^0-9A-Za-z._-]+", "-", clean_sound_asset_text(value)).strip("-._")
    return (text or fallback)[: max(8, int(limit or 64))]


def sound_asset_extension_from_mime(mime: object = "") -> str:
    low = clean_sound_asset_text(mime).lower()
    if "wav" in low:
        return "wav"
    if "mp4" in low or "m4a" in low:
        return "m4a"
    if "ogg" in low:
        return "ogg"
    if "webm" in low:
        return "webm"
    return "mp3"


def normalize_sound_asset_extension(extension: object = "") -> str:
    ext = re.sub(r"[^0-9A-Za-z]+", "", clean_sound_asset_text(extension).lstrip(".")).lower()
    if not ext:
        return "mp3"
    if ext not in SOUND_ASSET_ALLOWED_EXTENSIONS:
        return ext[:12]
    return ext


def sound_asset_key(digest: str, extension: str) -> str:
    return f"{clean_sound_asset_text(digest).lower()}.{normalize_sound_asset_extension(extension)}"


def sound_asset_empty_index() -> dict:
    return {
        "version": SOUND_ASSET_INDEX_VERSION,
        "updated_at": sound_asset_timestamp(),
        "root": str(SERVER_SOUND_DIR),
        "assets": {},
        "signatures": {},
        "quick_signatures": {},
        "stats": {"count": 0, "legacy_count": 0, "v2_count": 0},
    }


def sound_asset_rel_from_path(path: Path) -> str:
    target = Path(path).resolve()
    try:
        rel = target.relative_to(SERVER_DATA_ROOT.resolve())
    except Exception:
        rel = target
    return str(rel).replace("\\", "/")


def sound_asset_path_from_rel(relative_path: object = "") -> Path:
    raw = clean_sound_asset_text(relative_path).replace("\\", "/").strip("/")
    if raw.lower().startswith("sound/"):
        raw = raw[6:]
    target = (SERVER_SOUND_DIR / raw).resolve()
    target.relative_to(SERVER_SOUND_DIR.resolve())
    return target


def sound_asset_rel_under_sound(path: Path) -> str:
    target = Path(path).resolve()
    try:
        rel = target.relative_to(SERVER_SOUND_DIR.resolve())
    except Exception:
        rel = target.name
    return str(rel).replace("\\", "/")


def sound_asset_digest_from_name(path: Path) -> tuple[str, str] | None:
    match = re.search(r"(?:^|_)([0-9a-fA-F]{40})\.([0-9A-Za-z]+)$", path.name)
    if not match:
        return None
    return match.group(1).lower(), normalize_sound_asset_extension(match.group(2))


def sound_asset_register_path(index: dict, path: Path, digest: str = "", extension: str = "", *, update_signature: bool = True) -> bool:
    detected = (clean_sound_asset_text(digest).lower(), normalize_sound_asset_extension(extension))
    if not detected[0]:
        parsed = sound_asset_digest_from_name(path)
        if not parsed:
            return False
        detected = parsed
    key = sound_asset_key(detected[0], detected[1])
    rel = sound_asset_rel_from_path(path)
    assets = index.setdefault("assets", {})
    if not isinstance(assets, dict):
        index["assets"] = assets = {}
    previous = clean_sound_asset_text(assets.get(key, ""))
    if previous:
        try:
            if (SERVER_DATA_ROOT / previous).is_file():
                return False
        except Exception:
            pass
    assets[key] = rel
    if update_signature:
        sound_asset_update_signature(index, path.parent)
    return True


def sound_asset_folder_signature(folder: Path) -> dict:
    try:
        target = Path(folder).resolve()
        stat = target.stat()
        file_count = 0
        total_size = 0
        for child in target.iterdir():
            if child.is_file():
                file_count += 1
                try:
                    total_size += int(child.stat().st_size)
                except Exception:
                    pass
        return {
            "mtime_ns": int(stat.st_mtime_ns),
            "size": int(stat.st_size),
            "file_count": file_count,
            "bytes": total_size,
        }
    except Exception:
        return {"mtime_ns": 0, "size": -1, "file_count": 0, "bytes": 0}


def sound_asset_quick_folder_signature(folder: Path) -> dict:
    try:
        stat = Path(folder).stat()
        return {"mtime_ns": int(stat.st_mtime_ns), "size": int(stat.st_size)}
    except Exception:
        return {"mtime_ns": 0, "size": -1}


def sound_asset_signature_key(folder: Path) -> str:
    try:
        rel = Path(folder).resolve().relative_to(SERVER_SOUND_DIR.resolve())
        key = str(rel).replace("\\", "/").strip("/")
    except Exception:
        key = ""
    return key or "."


def sound_asset_update_signature(index: dict, folder: Path) -> None:
    signatures = index.setdefault("signatures", {})
    if not isinstance(signatures, dict):
        index["signatures"] = signatures = {}
    signatures[sound_asset_signature_key(folder)] = sound_asset_folder_signature(folder)
    quick = index.setdefault("quick_signatures", {})
    if not isinstance(quick, dict):
        index["quick_signatures"] = quick = {}
    quick[sound_asset_signature_key(folder)] = sound_asset_quick_folder_signature(folder)


def load_sound_asset_index(*, force: bool = False, build_if_missing: bool = False) -> dict:
    global SOUND_ASSET_INDEX_RAM
    with SOUND_ASSET_INDEX_LOCK:
        if SOUND_ASSET_INDEX_RAM is not None and not force:
            return SOUND_ASSET_INDEX_RAM
        payload = None
        if SOUND_ASSET_INDEX_FILE.is_file():
            try:
                payload = json.loads(SOUND_ASSET_INDEX_FILE.read_text(encoding="utf-8-sig", errors="replace"))
            except Exception:
                payload = None
        if not isinstance(payload, dict):
            payload = rebuild_sound_asset_index("missing-index", write=False) if build_if_missing else sound_asset_empty_index()
        assets = payload.get("assets")
        if not isinstance(assets, dict):
            payload["assets"] = {}
        if not isinstance(payload.get("signatures"), dict):
            payload["signatures"] = {}
        if not isinstance(payload.get("quick_signatures"), dict):
            payload["quick_signatures"] = {}
        if not payload["quick_signatures"] and isinstance(payload.get("signatures"), dict):
            for key in list(payload["signatures"].keys())[:4096]:
                folder = SERVER_SOUND_DIR if key == "." else SERVER_SOUND_DIR / key
                payload["quick_signatures"][key] = sound_asset_quick_folder_signature(folder)
        replay_sound_asset_wal(payload)
        payload["stats"] = sound_asset_index_stats(payload)
        SOUND_ASSET_INDEX_RAM = payload
        return SOUND_ASSET_INDEX_RAM


def replay_sound_asset_wal(index: dict) -> int:
    if not SOUND_ASSET_INDEX_WAL_FILE.is_file():
        return 0
    count = 0
    try:
        lines = SOUND_ASSET_INDEX_WAL_FILE.read_text(encoding="utf-8", errors="replace").splitlines()
    except Exception:
        return 0
    for line in lines:
        try:
            row = json.loads(line)
        except Exception:
            continue
        if not isinstance(row, dict):
            continue
        digest = clean_sound_asset_text(row.get("digest", "")).lower()
        ext = normalize_sound_asset_extension(row.get("extension", ""))
        rel = clean_sound_asset_text(row.get("path", ""))
        if digest and ext and rel:
            index.setdefault("assets", {})[sound_asset_key(digest, ext)] = rel
            try:
                sound_asset_update_signature(index, (SERVER_DATA_ROOT / rel).parent)
            except Exception:
                pass
            count += 1
    return count


def sound_asset_index_stats(index: dict) -> dict:
    assets = index.get("assets") if isinstance(index, dict) else {}
    assets = assets if isinstance(assets, dict) else {}
    legacy = 0
    v2 = 0
    for rel in assets.values():
        raw = clean_sound_asset_text(rel).replace("\\", "/").lower()
        if raw.startswith("sound/_v2/"):
            v2 += 1
        elif raw.startswith("sound/"):
            legacy += 1
    return {"count": len(assets), "legacy_count": legacy, "v2_count": v2}


def atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.name}.tmp-{threading.get_ident()}-{time.time_ns()}")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)


def atomic_write_bytes(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.name}.tmp-{threading.get_ident()}-{time.time_ns()}")
    with tmp.open("wb") as handle:
        handle.write(bytes(payload or b""))
        handle.flush()
        os.fsync(handle.fileno())
    tmp.replace(path)


def write_sound_asset_index_now(reason: str = "flush") -> dict:
    global SOUND_ASSET_INDEX_RAM, SOUND_ASSET_INDEX_DIRTY, SOUND_ASSET_INDEX_FLUSH_TIMER
    with SOUND_ASSET_INDEX_LOCK:
        if SOUND_ASSET_INDEX_RAM is None:
            return {"ok": False, "reason": "not-loaded"}
        if SOUND_ASSET_INDEX_FLUSH_TIMER is not None:
            SOUND_ASSET_INDEX_FLUSH_TIMER.cancel()
            SOUND_ASSET_INDEX_FLUSH_TIMER = None
        payload = dict(SOUND_ASSET_INDEX_RAM)
        payload["updated_at"] = sound_asset_timestamp()
        payload["reason"] = clean_sound_asset_text(reason)[:80]
        payload["stats"] = sound_asset_index_stats(payload)
        atomic_write_text(SOUND_ASSET_INDEX_FILE, json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
        try:
            SOUND_ASSET_INDEX_WAL_FILE.unlink(missing_ok=True)
        except Exception:
            pass
        SOUND_ASSET_INDEX_RAM = payload
        SOUND_ASSET_INDEX_DIRTY = False
        return {"ok": True, **payload.get("stats", {})}


def schedule_sound_asset_index_flush(delay: float = 2.0) -> None:
    global SOUND_ASSET_INDEX_FLUSH_TIMER
    with SOUND_ASSET_INDEX_LOCK:
        if SOUND_ASSET_INDEX_FLUSH_TIMER is not None:
            SOUND_ASSET_INDEX_FLUSH_TIMER.cancel()
        timer = threading.Timer(max(0.1, float(delay or 2.0)), lambda: write_sound_asset_index_now("debounced"))
        timer.daemon = True
        SOUND_ASSET_INDEX_FLUSH_TIMER = timer
        timer.start()


def append_sound_asset_wal(digest: str, extension: str, rel: str) -> None:
    row = {
        "at": sound_asset_timestamp(),
        "digest": clean_sound_asset_text(digest).lower(),
        "extension": normalize_sound_asset_extension(extension),
        "path": clean_sound_asset_text(rel),
    }
    SOUND_ASSET_INDEX_WAL_FILE.parent.mkdir(parents=True, exist_ok=True)
    with SOUND_ASSET_INDEX_WAL_FILE.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")


def sound_asset_source_slug(prefix: object = "") -> str:
    safe = sound_asset_safe_segment(prefix, "asset", 80).lower()
    if safe.startswith("pdf-media") or safe.startswith("pdf-video"):
        return "pdf-media"
    if safe.startswith("ai-question"):
        return "ai-question"
    first = safe.split("-", 1)[0]
    if first in {"chat", "vocab", "grammar", "voice", "fx", "spaceq", "spacep", "asset", "sound"}:
        return first
    if safe.startswith("kokoro"):
        return "kokoro"
    if safe.startswith("sot"):
        return "sot"
    if safe.startswith("edge") or safe.startswith("microsoft"):
        return "edge"
    return first or "asset"


def sound_asset_sharded_path(prefix: str, filename: str, digest: str) -> Path:
    month = time.strftime("%Y%m", time.localtime())
    source = sound_asset_source_slug(prefix)
    shard = clean_sound_asset_text(digest).lower()[:2] or "00"
    return SERVER_SOUND_V2_DIR / source / month / shard / filename


def sound_asset_lookup(digest: str, extension: str) -> str:
    index = load_sound_asset_index()
    key = sound_asset_key(digest, extension)
    rel = clean_sound_asset_text(index.get("assets", {}).get(key, ""))
    if rel:
        try:
            if (SERVER_DATA_ROOT / rel).is_file():
                return rel
        except Exception:
            pass
    canonical = SERVER_SOUND_DIR / f"asset_{clean_sound_asset_text(digest).lower()}.{normalize_sound_asset_extension(extension)}"
    if canonical.is_file():
        rel = sound_asset_rel_from_path(canonical)
        sound_asset_note_existing(digest, extension, rel)
        return rel
    return ""


def sound_asset_note_existing(digest: str, extension: str, rel: str) -> None:
    global SOUND_ASSET_INDEX_DIRTY
    with SOUND_ASSET_INDEX_LOCK:
        index = load_sound_asset_index()
        key = sound_asset_key(digest, extension)
        if clean_sound_asset_text(index.setdefault("assets", {}).get(key, "")) == clean_sound_asset_text(rel):
            return
        index["assets"][key] = clean_sound_asset_text(rel)
        try:
            sound_asset_update_signature(index, (SERVER_DATA_ROOT / rel).parent)
        except Exception:
            pass
        index["stats"] = sound_asset_index_stats(index)
        SOUND_ASSET_INDEX_DIRTY = True
        append_sound_asset_wal(digest, extension, rel)
        schedule_sound_asset_index_flush(2.0)


# Added 2026-08-01: repairs one existing Sound entry without scanning or rebuilding the full index.
def ensure_sound_asset_index_entry(relative_path: object) -> dict:
    raw = clean_sound_asset_text(relative_path).replace("\\", "/").strip("/")
    if not raw.lower().startswith("sound/"):
        return {"ok": False, "reason": "not-sound", "path": raw}
    target = (SERVER_DATA_ROOT / raw).resolve()
    target.relative_to(SERVER_SOUND_DIR.resolve())
    if not target.is_file() or target.stat().st_size <= 0:
        return {"ok": False, "reason": "missing-file", "path": raw}
    parsed = sound_asset_digest_from_name(target)
    if parsed:
        digest, extension = parsed
    else:
        digest_hash = hashlib.sha1()
        with target.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest_hash.update(chunk)
        digest = digest_hash.hexdigest()
        extension = normalize_sound_asset_extension(target.suffix)
    rel = sound_asset_rel_from_path(target)
    key = sound_asset_key(digest, extension)
    with SOUND_ASSET_INDEX_LOCK:
        index = load_sound_asset_index()
        before = clean_sound_asset_text(index.setdefault("assets", {}).get(key, ""))
    repaired = before != rel
    if repaired:
        sound_asset_note_existing(digest, extension, rel)
    return {
        "ok": True,
        "path": rel,
        "key": key,
        "digest": digest,
        "extension": extension,
        "index_repaired": repaired,
    }


# Added 2026-07-16: writes new Sound assets into small hash buckets and updates a WAL-backed index instead of globbing the flat Sound folder.
def write_server_sound_file_asset(prefix: str, payload: bytes, extension: str) -> str:
    SERVER_SOUND_DIR.mkdir(parents=True, exist_ok=True)
    data = bytes(payload or b"")
    digest = hashlib.sha1(data).hexdigest()
    ext = normalize_sound_asset_extension(extension)
    existing = sound_asset_lookup(digest, ext)
    if existing:
        return existing
    safe_prefix = sound_asset_safe_segment(prefix, "asset", 96)
    filename = f"asset_{digest}.{ext}" if safe_prefix.lower() in {"", "asset", "sound"} else f"{safe_prefix}_{digest}.{ext}"
    target = sound_asset_sharded_path(safe_prefix, filename, digest)
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.is_file():
        atomic_write_bytes(target, data)
    if not target.is_file() or target.stat().st_size != len(data):
        raise RuntimeError("Sound asset write did not finish successfully.")
    rel = sound_asset_rel_from_path(target)
    sound_asset_note_existing(digest, ext, rel)
    return rel


def warm_sound_asset_index(build_if_missing: bool = False) -> dict:
    started = time.perf_counter()
    index = load_sound_asset_index(build_if_missing=build_if_missing)
    stats = sound_asset_index_stats(index)
    quick = index.get("quick_signatures") if isinstance(index.get("quick_signatures"), dict) else {}
    return {
        "ok": True,
        "ms": int((time.perf_counter() - started) * 1000),
        "signatures": len(index.get("signatures", {}) if isinstance(index.get("signatures"), dict) else {}),
        "quick_signatures": len(quick),
        "root_quick_signature": sound_asset_quick_folder_signature(SERVER_SOUND_DIR),
        "root_index_signature": quick.get(".", {}) if isinstance(quick, dict) else {},
        **stats,
    }


def write_server_sound_asset(prefix: str, audio_bytes: bytes, mime: str) -> str:
    return write_server_sound_file_asset(prefix, audio_bytes, sound_asset_extension_from_mime(mime))


def rebuild_sound_asset_index(reason: str = "manual", *, write: bool = True) -> dict:
    payload = sound_asset_empty_index()
    assets = payload.setdefault("assets", {})
    legacy = 0
    v2 = 0
    touched_folders: set[Path] = set()
    if SERVER_SOUND_DIR.is_dir():
        for path in SERVER_SOUND_DIR.rglob("*"):
            if not path.is_file():
                continue
            if path.name == SOUND_ASSET_INDEX_FILE.name or path.name == SOUND_ASSET_INDEX_WAL_FILE.name:
                continue
            parsed = sound_asset_digest_from_name(path)
            if not parsed:
                continue
            key = sound_asset_key(parsed[0], parsed[1])
            if key in assets:
                continue
            try:
                rel_under_sound = str(path.relative_to(SERVER_SOUND_DIR)).replace("\\", "/")
            except Exception:
                rel_under_sound = path.name
            rel = f"Sound/{rel_under_sound}"
            assets[key] = rel
            touched_folders.add(path.parent)
            if rel.lower().startswith("sound/_v2/"):
                v2 += 1
            else:
                legacy += 1
    payload["updated_at"] = sound_asset_timestamp()
    payload["reason"] = clean_sound_asset_text(reason)[:80]
    payload["stats"] = {"count": len(payload.get("assets", {})), "legacy_count": legacy, "v2_count": v2}
    for folder in sorted(touched_folders, key=lambda item: str(item).lower()):
        sound_asset_update_signature(payload, folder)
    if write:
        global SOUND_ASSET_INDEX_RAM, SOUND_ASSET_INDEX_DIRTY
        with SOUND_ASSET_INDEX_LOCK:
            SOUND_ASSET_INDEX_RAM = payload
            SOUND_ASSET_INDEX_DIRTY = False
            atomic_write_text(SOUND_ASSET_INDEX_FILE, json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
            try:
                SOUND_ASSET_INDEX_WAL_FILE.unlink(missing_ok=True)
            except Exception:
                pass
    return payload


def sound_asset_index_status() -> dict:
    index = load_sound_asset_index()
    stats = sound_asset_index_stats(index)
    return {
        "loaded": True,
        "index_file": str(SOUND_ASSET_INDEX_FILE),
        "wal_file": str(SOUND_ASSET_INDEX_WAL_FILE),
        "dirty": bool(SOUND_ASSET_INDEX_DIRTY),
        **stats,
    }
