from __future__ import annotations

import argparse
import base64
import gzip
import hashlib
import json
import sys
from pathlib import Path
from time import localtime, sleep, strftime, time, time_ns

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from future_lesson_identity import (
    LESSON_ID_PREFIX,
    LESSON_ID_REGISTRY_PATH,
    apply_lesson_id_to_payload,
    generate_future_lesson_id,
    lesson_id_from_payload,
)
from future_structure_asset_store import (
    lesson_id_registry_load,
    lesson_id_registry_write,
    structure_asset_json,
    structure_asset_logical_path,
)


CODE_PREFIX = "FTG1."
SERVER_DATA_ROOT = Path(r"C:\server data")
SPACE_SUFFIXES = {".space_w", ".space_v", ".space_b", ".space_q", ".space_p", ".space_s", ".space_l"}


def long_path_text(path: Path) -> str:
    raw = str(path.resolve())
    if sys.platform.startswith("win") and not raw.startswith("\\\\?\\"):
        return "\\\\?\\" + raw
    return raw


def read_text(path: Path) -> str:
    with open(long_path_text(path), "r", encoding="utf-8-sig", errors="replace") as fh:
        return fh.read()


def write_text(path: Path, text: str) -> None:
    with open(long_path_text(path), "w", encoding="utf-8", newline="") as fh:
        fh.write(text)


def registry_load() -> dict:
    try:
        data, _revision_ns = lesson_id_registry_load()
        if isinstance(data, dict):
            data.setdefault("version", 1)
            data.setdefault("next_id", 1)
            ids = data.setdefault("ids", {})
            max_seen = 0
            if isinstance(ids, dict):
                for lesson_id in ids:
                    raw = str(lesson_id or "")
                    if raw.startswith(LESSON_ID_PREFIX):
                        suffix = raw[len(LESSON_ID_PREFIX):]
                        if suffix.isdigit():
                            max_seen = max(max_seen, int(suffix))
            data["next_id"] = max(int(data.get("next_id") or 1), max_seen + 1)
            return data
    except Exception:
        pass
    return {"version": 1, "next_id": 1, "ids": {}}


def registry_write(registry: dict) -> None:
    lesson_id_registry_write(registry)


def registry_next_id(registry: dict, reserved: set[str] | None = None) -> str:
    ids = registry.setdefault("ids", {})
    return generate_future_lesson_id({*ids, *(reserved or set())})


def stamp_payload_lesson_id(payload: dict, lesson_id: str) -> None:
    apply_lesson_id_to_payload(payload, lesson_id)


def registry_register(registry: dict, lesson_id: str, target: Path) -> None:
    ids = registry.setdefault("ids", {})
    now_ms = int(time() * 1000)
    row = ids.get(lesson_id) if isinstance(ids.get(lesson_id), dict) else {}
    if not row:
        row = {
            "id": lesson_id,
            "created_ms": now_ms,
            "created_at": strftime("%Y-%m-%dT%H:%M:%S", localtime(now_ms / 1000)),
            "first_path": str(target),
            "first_name": target.name,
            "space": target.suffix.lstrip("."),
        }
    else:
        row = dict(row)
    paths = row.get("paths") if isinstance(row.get("paths"), list) else []
    target_text = str(target)
    if target_text not in paths:
        paths.append(target_text)
    row["paths"] = paths[-20:]
    row["last_path"] = target_text
    row["last_seen_ms"] = now_ms
    row["space"] = str(row.get("space") or target.suffix.lstrip("."))
    ids[lesson_id] = row


def encode_base64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(bytes(data or b"")).decode("ascii").rstrip("=")


def decode_base64url(data: str) -> bytes:
    raw = str(data or "").strip()
    raw += "=" * (-len(raw) % 4)
    return base64.urlsafe_b64decode(raw.encode("ascii"))


def encode_payload(payload: dict) -> str:
    raw = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return CODE_PREFIX + encode_base64url(gzip.compress(raw, compresslevel=9))


def safe_structure_path(relative_path: str = "") -> str:
    return structure_asset_logical_path(relative_path)


def load_payload_from_text(text: str) -> tuple[dict, str, Path | None]:
    raw = str(text or "").lstrip("\ufeff").strip()
    if raw.startswith("{"):
        payload = json.loads(raw)
        if isinstance(payload, dict) and payload.get("k") == "ftg_manifest":
            structure = safe_structure_path(payload.get("structure") or payload.get("sp") or payload.get("path") or "")
            structure_payload = structure_asset_json(structure)
            if not isinstance(structure_payload, dict):
                raise RuntimeError("Structure payload is not a JSON object.")
            return payload, "manifest", structure
        if not isinstance(payload, dict):
            raise RuntimeError("Payload is not a JSON object.")
        return payload, "json", None
    if not raw.startswith(CODE_PREFIX):
        raise RuntimeError("Not an FTG1 payload or JSON manifest.")
    payload = json.loads(gzip.decompress(decode_base64url(raw[len(CODE_PREFIX):])).decode("utf-8-sig"))
    if not isinstance(payload, dict):
        raise RuntimeError("Decoded payload is not a JSON object.")
    return payload, "ftg1", None


def write_payload(target: Path, payload: dict, mode: str, structure: Path | None) -> None:
    if mode == "manifest":
        write_text(target, json.dumps(payload, ensure_ascii=False, indent=2))
        return
    if mode == "json":
        write_text(target, json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
        return
    write_text(target, encode_payload(payload) + "\n")


def payload_without_lesson_id(value, *, root: bool = False):
    if isinstance(value, dict):
        out = {}
        for key, item in value.items():
            if key in {"lesson_id", "lessonId", "identity", "lesson"}:
                continue
            if root and key in {"st", "study"}:
                continue
            if key == "meta" and isinstance(item, dict):
                meta = payload_without_lesson_id(item)
                if meta:
                    out[key] = meta
                continue
            out[key] = payload_without_lesson_id(item)
        return out
    if isinstance(value, list):
        return [payload_without_lesson_id(item) for item in value]
    return value


def payload_fingerprint(payload: dict, mode: str = "", structure: Path | None = None) -> str:
    source = payload
    if mode == "manifest" and structure is not None:
        try:
            structure_payload = structure_asset_json(structure)
            if isinstance(structure_payload, dict):
                source = structure_payload
        except Exception:
            source = payload
    normalized = payload_without_lesson_id(source, root=True)
    raw = json.dumps(normalized, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def common_path_rank(path: Path) -> tuple[int, str]:
    try:
        rel_parts = path.resolve().relative_to(SERVER_DATA_ROOT.resolve()).parts
    except Exception:
        rel_parts = ()
    is_common = bool(rel_parts and rel_parts[0].lower() == "common")
    return (0 if is_common else 1, str(path).lower())


def id_sort_key(lesson_id: str) -> tuple[int, str]:
    raw = str(lesson_id or "")
    if raw.startswith(LESSON_ID_PREFIX):
        suffix = raw[len(LESSON_ID_PREFIX):]
        if suffix.isdigit():
            return (int(suffix), raw)
    return (10**12, raw)


def choose_group_lesson_id(entries: list[dict]) -> str:
    common_ids = [
        str(entry.get("lesson_id") or "")
        for entry in sorted(entries, key=lambda item: common_path_rank(item["target"]))
        if str(entry.get("lesson_id") or "") and common_path_rank(entry["target"])[0] == 0
    ]
    if common_ids:
        return sorted(set(common_ids), key=id_sort_key)[0]
    existing_ids = [str(entry.get("lesson_id") or "") for entry in entries if str(entry.get("lesson_id") or "")]
    if existing_ids:
        counts = {lesson_id: existing_ids.count(lesson_id) for lesson_id in set(existing_ids)}
        return sorted(counts, key=lambda lesson_id: (-counts[lesson_id], id_sort_key(lesson_id)))[0]
    return ""


def should_scan_path(path: Path, root: Path = SERVER_DATA_ROOT) -> bool:
    if path.suffix.lower() not in SPACE_SUFFIXES:
        return False
    try:
        rel_parts = path.resolve().relative_to(Path(root).resolve()).parts
    except Exception:
        return False
    if not rel_parts:
        return False
    top = rel_parts[0].lower()
    if top in {"sound", "structure", "picture", "cache orc", "_future_path_backups"}:
        return False
    return top == "common" or not top.startswith("_")


# Updated 2026-07-21: missing IDs are unique per logical file; content equality never merges identity.
def assign_ids(root: Path, dry_run: bool = False, limit: int = 0) -> dict:
    registry = registry_load() if not dry_run else {"version": 1, "next_id": 1, "ids": {}}
    entries: list[dict] = []
    scanned = 0
    updated = 0
    skipped = 0
    registered = 0
    missing_detected = 0
    errors: list[dict] = []
    for target in root.rglob("*"):
        if not should_scan_path(target, root):
            continue
        scanned += 1
        try:
            payload, mode, structure = load_payload_from_text(read_text(target))
            before = lesson_id_from_payload(payload)
            fingerprint = payload_fingerprint(payload, mode, structure)
            entries.append({"target": target, "payload": payload, "mode": mode, "structure": structure, "lesson_id": before, "fingerprint": fingerprint})
            if limit and scanned >= limit:
                break
        except Exception as exc:
            errors.append({"path": str(target), "error": str(exc)})
    reserved_ids = {str(entry.get("lesson_id") or "") for entry in entries if str(entry.get("lesson_id") or "")}
    missing_assigned = 0
    used_ids: set[str] = set()
    for entry in entries:
        target = entry["target"]
        payload = entry["payload"]
        mode = entry["mode"]
        structure = entry["structure"]
        before = entry["lesson_id"]
        lesson_id = before
        if not lesson_id:
            missing_detected += 1
        if not lesson_id and not dry_run:
            lesson_id = registry_next_id(registry, reserved_ids)
            reserved_ids.add(lesson_id)
        try:
            if not before and lesson_id:
                updated += 1
                missing_assigned += 1
                if not dry_run:
                    stamp_payload_lesson_id(payload, lesson_id)
                    registry_register(registry, lesson_id, target)
                    registered += 1
                    write_payload(target, payload, mode, structure)
                used_ids.add(lesson_id)
            else:
                skipped += 1
                if lesson_id:
                    used_ids.add(lesson_id)
                if not dry_run:
                    stamp_payload_lesson_id(payload, lesson_id)
                    registry_register(registry, lesson_id, target)
                    registered += 1
        except Exception as exc:
            errors.append({"path": str(target), "error": str(exc)})
    if not dry_run:
        registry_write(registry)
    return {
        "scanned": scanned,
        "updated": updated,
        "skipped": skipped,
        "registered": registered,
        "missing_detected": missing_detected,
        "missing_assigned": missing_assigned,
        "changed_to_group_id": 0,
        "unique_ids_seen": len(used_ids),
        "content_groups": len({str(entry.get("fingerprint") or "") for entry in entries}),
        "errors": errors[:200],
        "error_count": len(errors),
    }


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="Assign persistent lesson ids to Space files under C:\\server data.")
    parser.add_argument("--root", default=str(SERVER_DATA_ROOT))
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()
    result = assign_ids(Path(args.root), dry_run=bool(args.dry_run), limit=max(0, int(args.limit or 0)))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if result.get("error_count") else 0


if __name__ == "__main__":
    raise SystemExit(main())
