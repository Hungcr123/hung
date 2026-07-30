"""Repair embedded Space lesson ID collisions without using content as identity."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from time import time


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from future_lesson_identity import generate_future_lesson_id, lesson_id_from_payload
from FUTURE.tools.assign_space_lesson_ids import (
    SERVER_DATA_ROOT,
    encode_payload,
    load_payload_from_text,
    long_path_text,
    payload_fingerprint,
    read_text,
    registry_load,
    registry_register,
    registry_write,
    should_scan_path,
    stamp_payload_lesson_id,
)


DEFAULT_LEDGER = Path.home() / ".codex" / "plans" / "space_lesson_id_collision_ledger_20260721.json"
MIGRATION_VERSION = 1


def relative_key(path: Path, root: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def atomic_write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    with open(long_path_text(temporary), "w", encoding="utf-8", newline="") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(long_path_text(temporary), long_path_text(path))


def atomic_write_payload(target: Path, payload: dict, mode: str) -> None:
    if mode == "manifest":
        text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    elif mode == "json":
        text = json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n"
    else:
        text = encode_payload(payload) + "\n"
    temporary = target.with_name(f".{target.name}.lesson-id-{os.getpid()}.tmp")
    with open(long_path_text(temporary), "w", encoding="utf-8", newline="") as handle:
        handle.write(text)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(long_path_text(temporary), long_path_text(target))


def file_exists(path: Path) -> bool:
    return os.path.isfile(long_path_text(path))


# Added 2026-07-21: inventory is read-only and separates exact replicas from divergent collisions.
def scan_space_identities(root: Path) -> dict:
    entries = []
    errors = []
    for target in root.rglob("*"):
        if not should_scan_path(target, root):
            continue
        try:
            payload, mode, structure = load_payload_from_text(read_text(target))
            entries.append({
                "target": target,
                "path": relative_key(target, root),
                "payload": payload,
                "mode": mode,
                "lesson_id": lesson_id_from_payload(payload),
                "fingerprint": payload_fingerprint(payload, mode, structure),
            })
        except Exception as exc:
            errors.append({"path": str(target), "error": str(exc)})
    by_id = {}
    missing = []
    for entry in entries:
        lesson_id = entry["lesson_id"]
        if lesson_id:
            by_id.setdefault(lesson_id, []).append(entry)
        else:
            missing.append(entry)
    exact = {}
    divergent = {}
    for lesson_id, rows in by_id.items():
        if len(rows) < 2:
            continue
        fingerprints = {row["fingerprint"] for row in rows}
        (exact if len(fingerprints) == 1 else divergent)[lesson_id] = rows
    return {
        "entries": entries,
        "missing": missing,
        "exact": exact,
        "divergent": divergent,
        "errors": errors,
    }


def path_rank(path: str) -> tuple[int, str]:
    normalized = str(path or "").replace("\\", "/").lower()
    return (0 if normalized.startswith("common/") else 1, normalized)


def divergent_fingerprint_groups(rows: list[dict]) -> list[list[dict]]:
    groups = {}
    for row in rows:
        groups.setdefault(row["fingerprint"], []).append(row)
    return list(groups.values())


def canonical_group(groups: list[list[dict]]) -> list[dict]:
    return min(
        groups,
        key=lambda rows: (
            -len(rows),
            min(path_rank(row["path"]) for row in rows),
        ),
    )


def dry_run_summary(scan: dict) -> dict:
    reassigned = 0
    for rows in scan["divergent"].values():
        groups = divergent_fingerprint_groups(rows)
        keep = canonical_group(groups)
        reassigned += sum(len(group) for group in groups if group is not keep)
    return {
        "ok": not scan["errors"],
        "scanned": len(scan["entries"]),
        "missing_ids": len(scan["missing"]),
        "exact_replica_groups": len(scan["exact"]),
        "divergent_collision_groups": len(scan["divergent"]),
        "divergent_files": sum(len(rows) for rows in scan["divergent"].values()),
        "planned_reassigned_files": reassigned,
        "planned_total_writes": reassigned + len(scan["missing"]),
        "errors": scan["errors"][:100],
        "error_count": len(scan["errors"]),
    }


def load_ledger(path: Path, root: Path) -> dict:
    if not path.is_file():
        return {
            "version": MIGRATION_VERSION,
            "root": str(root.resolve()),
            "status": "new",
            "created_epoch": time(),
            "entries": {},
        }
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if int(payload.get("version", 0) or 0) != MIGRATION_VERSION:
        raise RuntimeError("Unsupported lesson ID migration ledger version.")
    if str(payload.get("root", "")).lower() != str(root.resolve()).lower():
        raise RuntimeError("Migration ledger belongs to another Server Data root.")
    if not isinstance(payload.get("entries"), dict):
        raise RuntimeError("Migration ledger entries are invalid.")
    return payload


def planned_ledger(scan: dict, ledger: dict) -> dict:
    reserved = {
        row["lesson_id"]
        for row in scan["entries"]
        if row.get("lesson_id")
    }
    planned = dict(ledger.get("entries") or {})
    for old_id, rows in sorted(scan["divergent"].items()):
        groups = divergent_fingerprint_groups(rows)
        keep = canonical_group(groups)
        for group in groups:
            after_id = old_id if group is keep else ""
            existing_after = {
                str((planned.get(row["path"]) or {}).get("after_id", ""))
                for row in group
                if str((planned.get(row["path"]) or {}).get("after_id", ""))
            }
            if not after_id:
                if len(existing_after) > 1:
                    raise RuntimeError(f"Ledger has conflicting target IDs for {old_id}.")
                after_id = next(iter(existing_after), "") or generate_future_lesson_id(reserved)
                reserved.add(after_id)
            for row in group:
                current = planned.get(row["path"]) if isinstance(planned.get(row["path"]), dict) else {}
                if current and (
                    str(current.get("before_id", "")) != old_id
                    or str(current.get("fingerprint", "")) != row["fingerprint"]
                    or str(current.get("after_id", "")) != after_id
                ):
                    raise RuntimeError(f"Ledger conflict for {row['path']}.")
                planned[row["path"]] = {
                    "reason": "divergent_collision",
                    "before_id": old_id,
                    "after_id": after_id,
                    "fingerprint": row["fingerprint"],
                }
    for row in scan["missing"]:
        current = planned.get(row["path"]) if isinstance(planned.get(row["path"]), dict) else {}
        after_id = str(current.get("after_id", "")) or generate_future_lesson_id(reserved)
        reserved.add(after_id)
        if current and (
            str(current.get("before_id", ""))
            or str(current.get("fingerprint", "")) != row["fingerprint"]
        ):
            raise RuntimeError(f"Ledger conflict for missing-ID file {row['path']}.")
        planned[row["path"]] = {
            "reason": "missing_id",
            "before_id": "",
            "after_id": after_id,
            "fingerprint": row["fingerprint"],
        }
    return {**ledger, "status": "prepared", "prepared_epoch": time(), "entries": planned}


def apply_ledger(root: Path, backup_root: Path, ledger_path: Path, scan: dict) -> dict:
    if scan["errors"]:
        raise RuntimeError("Identity scan has errors; refusing to modify lesson files.")
    ledger = planned_ledger(scan, load_ledger(ledger_path, root))
    atomic_write_json(ledger_path, ledger)
    rows_by_path = {row["path"]: row for row in scan["entries"]}
    registry = registry_load()
    changed = 0
    already_applied = 0
    unchanged = 0
    errors = []
    for rel_path, plan in sorted(ledger["entries"].items()):
        row = rows_by_path.get(rel_path)
        if not row:
            errors.append({"path": rel_path, "error": "File is missing from the current scan."})
            continue
        if row["fingerprint"] != str(plan.get("fingerprint", "")):
            errors.append({"path": rel_path, "error": "Content changed after the migration plan was prepared."})
            continue
        before_id = str(plan.get("before_id", ""))
        after_id = str(plan.get("after_id", ""))
        current_id = row["lesson_id"]
        if not after_id:
            errors.append({"path": rel_path, "error": "Target lesson ID is empty."})
            continue
        if current_id == after_id:
            already_applied += 1
            registry_register(registry, after_id, row["target"])
            continue
        if current_id != before_id:
            errors.append({"path": rel_path, "error": f"Unexpected current ID: {current_id!r}."})
            continue
        backup = backup_root / "wrappers" / Path(rel_path)
        if not file_exists(backup):
            errors.append({"path": rel_path, "error": f"Backup wrapper is missing: {backup}"})
            continue
        if before_id == after_id:
            unchanged += 1
            registry_register(registry, after_id, row["target"])
            continue
        stamp_payload_lesson_id(row["payload"], after_id)
        atomic_write_payload(row["target"], row["payload"], row["mode"])
        registry_register(registry, after_id, row["target"])
        changed += 1
    if errors:
        ledger["status"] = "partial_error" if changed else "error"
        ledger["last_errors"] = errors[:100]
        ledger["updated_epoch"] = time()
        atomic_write_json(ledger_path, ledger)
        raise RuntimeError(json.dumps({"changed": changed, "errors": errors[:20]}, ensure_ascii=False))
    registry_write(registry)
    ledger.update({
        "status": "applied",
        "applied_epoch": time(),
        "changed": changed,
        "already_applied": already_applied,
        "unchanged": unchanged,
        "last_errors": [],
    })
    atomic_write_json(ledger_path, ledger)
    return {
        "ok": True,
        "changed": changed,
        "already_applied": already_applied,
        "unchanged": unchanged,
        "ledger": str(ledger_path),
    }


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="Repair divergent or missing embedded Space lesson IDs.")
    parser.add_argument("--root", default=str(SERVER_DATA_ROOT))
    parser.add_argument("--ledger", default=str(DEFAULT_LEDGER))
    parser.add_argument("--backup-root", default="")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    root = Path(args.root)
    scan = scan_space_identities(root)
    if args.dry_run:
        result = dry_run_summary(scan)
    else:
        backup_root = Path(args.backup_root)
        if not backup_root.is_dir():
            raise RuntimeError("--backup-root must point to the verified phase backup directory.")
        result = {**dry_run_summary(scan), **apply_ledger(root, backup_root, Path(args.ledger), scan)}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
